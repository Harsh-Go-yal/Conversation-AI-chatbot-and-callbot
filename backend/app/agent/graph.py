"""LangGraph pipeline: router → retrieve → gate/reason → compile, with an event callback for SSE streaming.

State is a TypedDict; conversation memory (last AnswerIR per session) lives in app.agent.memory so format
conversions and follow-ups reuse the IR without re-retrieval."""
from __future__ import annotations

import re
import time
from typing import Any, Callable, TypedDict

from langgraph.graph import END, StateGraph

from app.agent import memory
from app.agent.compiler import compile_answer
from app.agent.conflicts import find_conflicts
from app.agent.reasoner import reason
from app.agent.router import RouteDecision, route
from app.config import settings
from app.models.ir import AnswerIR, Domain, Intent, OutputFormat, Persona, RetrievedChunk
from app.retrieval.search import hybrid_search

Emit = Callable[[str, dict], None]


class AgentState(TypedDict, total=False):
    session_id: str
    persona: Persona
    query: str
    history: list[dict]
    user_schema: Any
    customer_phone: str
    emit: Emit
    timings: dict[str, int]
    decision: RouteDecision
    chunks: list[RetrievedChunk]
    withheld: int
    ir: AnswerIR
    output: dict


def _emit(state: AgentState, stage: str, **data):
    if state.get("emit"):
        state["emit"](stage, data)


_DRAFT_RE = re.compile(r"\b(draft|write|compose|prepare|frame)\b.{0,60}\b(e-?mail|mail|reply|response|letter|note|message|msg|sms|text|communication|update)\b", re.I)


def _guard_decision(d: RouteDecision, state: "AgentState") -> RouteDecision:
    """Deterministic corrections on top of the LLM router. Drafting an email/reply is a *rendering* request, never a
    CRM action: with a previous answer in the session it is a format conversion, otherwise a retrieval question
    rendered as email."""
    if d.intent == Intent.action_request and _DRAFT_RE.search(state["query"]):
        has_prev = memory.last_ir(state["session_id"]) is not None
        d = d.model_copy(update={
            "intent": Intent.format_conversion if has_prev else Intent.retrieval_question,
            "requested_format": OutputFormat.email,
            "reason": d.reason + " [guard: drafting text is not a CRM action]",
        })
    elif d.intent == Intent.action_request and state["persona"] == Persona.internal:
        # employees do not register products or raise claims through the chat — answer from the knowledge base instead
        d = d.model_copy(update={"intent": Intent.retrieval_question, "reason": d.reason + " [guard: internal persona → knowledge question]"})
    return d


# ───────────────────────── nodes ─────────────────────────
def node_route(state: AgentState) -> AgentState:
    t = time.time()
    d = route(state["query"], state.get("history", []), state["persona"])
    d = _guard_decision(d, state)
    state["decision"] = d
    state.setdefault("timings", {})["router"] = int((time.time() - t) * 1000)
    _emit(state, "router", intent=d.intent.value, domains=[x.value for x in d.domains], format=d.requested_format.value,
          standalone_query=d.standalone_query, sub_queries=d.sub_queries, ms=state["timings"]["router"], reason=d.reason)
    return state


def node_retrieve(state: AgentState) -> AgentState:
    t = time.time()
    d = state["decision"]
    persona = state["persona"]
    queries = d.sub_queries or [d.standalone_query or state["query"]]
    domains = [x.value for x in d.domains] or None
    seen: dict[str, RetrievedChunk] = {}
    withheld = 0
    per_query_k = settings.top_k if len(queries) == 1 else max(4, settings.top_k // len(queries) + 2)
    for q in queries:
        chunks, stats = hybrid_search(q, persona, domains, k=per_query_k, rerank_n=settings.rerank_n)
        withheld += stats.filtered_out_for_persona
        for c in chunks:
            if c.id not in seen or (c.rerank_score or 0) > (seen[c.id].rerank_score or 0):
                seen[c.id] = c
    chunks = sorted(seen.values(), key=lambda c: c.rerank_score or 0, reverse=True)[: settings.top_k + 2]
    # drop weak tail evidence: anything far below the best candidate is noise (and would otherwise trigger the
    # sensitivity gate for an irrelevant restricted chunk). Always keep at least evidence_min chunks.
    if chunks:
        top = chunks[0].rerank_score or 0
        strong = [c for c in chunks if (c.rerank_score or 0) >= top - settings.evidence_margin]
        chunks = strong if len(strong) >= settings.evidence_min else chunks[: settings.evidence_min]
    state["chunks"] = chunks
    state["withheld"] = withheld
    state["timings"]["retrieval"] = int((time.time() - t) * 1000)
    _emit(state, "retrieval", n=len(chunks), queries=queries, withheld=withheld, ms=state["timings"]["retrieval"],
          docs=sorted({c.meta.title for c in chunks}))
    return state


def node_reason(state: AgentState) -> AgentState:
    t0 = time.time()
    chunks = state["chunks"]
    restricted = sum(1 for c in chunks if c.meta.sensitivity == "restricted")
    _emit(state, "gate", restricted_chunks=restricted, llm="local" if restricted else "openai",
          reason=("restricted evidence present → self-hosted model" if restricted else "no restricted evidence → cloud model"))
    t = time.time()
    conflicts = find_conflicts(chunks, state["persona"])
    state["timings"]["conflicts"] = int((time.time() - t) * 1000)
    if conflicts:
        _emit(state, "conflicts", pairs=[{"verdict": c.verdict.value, "older": c.older_label, "newer": c.newer_label} for c in conflicts])
    d = state["decision"]
    ir = reason(d.standalone_query or state["query"], chunks, state["persona"], list(d.domains), d.intent,
                d.requested_format, conflicts, state.get("withheld", 0), state["timings"])
    state["timings"]["reasoner"] = int((time.time() - t0) * 1000) - state["timings"]["conflicts"]
    ir.routing.stage_timings_ms = dict(state["timings"])
    state["ir"] = ir
    memory.store_ir(state["session_id"], ir)
    _emit(state, "reasoner", claims=len(ir.claims), sources=len(ir.sources), conflicts=len(ir.conflicts),
          llm=ir.routing.llm_used, model=ir.routing.model, ms=state["timings"]["reasoner"])
    return state


def node_reuse_ir(state: AgentState) -> AgentState:
    ir = memory.last_ir(state["session_id"])
    if ir is None:  # nothing to convert — fall back to a fresh retrieval
        return node_reason(node_retrieve(state))
    d = state["decision"]
    ir = ir.model_copy(deep=True)
    ir.requested_format = d.requested_format
    ir.intent = Intent.format_conversion
    state["ir"] = ir
    state["chunks"] = []
    _emit(state, "reuse", message="Reusing the previous answer — no new retrieval", format=d.requested_format.value)
    return state


def node_compile(state: AgentState) -> AgentState:
    t = time.time()
    d = state["decision"]
    ir = state["ir"]
    fmt = d.requested_format
    out = compile_answer(ir, fmt, user_schema=state.get("user_schema") or d.json_schema_hint, recipient=d.email_recipient, instruction=state["query"])
    state["timings"]["compiler"] = int((time.time() - t) * 1000)
    state["output"] = out
    _emit(state, "compiler", format=fmt.value, ms=state["timings"]["compiler"])
    return state


def node_out_of_scope(state: AgentState) -> AgentState:
    ir = AnswerIR(query=state["query"], intent=Intent.out_of_scope, persona=state["persona"],
                  summary="I can help with Kohler India's products, warranties, policies and services. That question is outside what I can answer.")
    state["ir"] = ir
    state["output"] = {"format": "text", "content": ir.summary}
    _emit(state, "compiler", format="text", ms=0)
    return state


def node_action(state: AgentState) -> AgentState:
    """Account questions ("status of my claim", "what do I need to send", "register my product") never go to the LLM:
    when the customer has identified themselves (phone), the answer comes from the same customer memory the voice
    agent uses, so a conversation started on the phone continues here with the same facts."""
    from app.actions.tools import customer_context
    phone = state.get("customer_phone") or ""
    ctx = customer_context(phone) if phone else None
    if ctx and ctx.get("known"):
        lines = [f"Welcome back{(', ' + ctx['name']) if ctx.get('name') else ''}."]
        if ctx.get("last_summary"):
            lines.append(f"Last time ({ctx.get('open_items') and 'open items pending' or 'nothing pending'}): {ctx['last_summary']}")
        for cl in ctx["claims"][:3]:
            lines.append(f"• Claim {cl['claim_id']} — {cl['sku']}, \"{cl['issue']}\": **{cl['status']}**. {cl['next_step']}"
                         + (f" [Upload photos]({cl['upload_url']})" if cl["status"] == "pending" and cl["photos"] == 0 else "")
                         + (f" Still needed: {', '.join(cl['missing_info'])}." if cl["missing_info"] else ""))
        if not ctx["claims"] and ctx["orders"]:
            lines.append("Your orders: " + ", ".join(f"{o['order_no']} ({o['order_date']}, {o['status']})" for o in ctx["orders"][:3]))
        lines.append("To register a product, raise a claim, order or request a call-back, use “Help with my product” — or just call us; the phone assistant sees the same record.")
        summary = "\n".join(lines)
        hint = False
    else:
        summary = ("To register a product, raise a warranty claim, place an order or request a call-back, use the “Help with my product” panel — "
                   "it can act on your order directly. If you have contacted us before, enter your mobile number there and I will pick up where we left off.")
        hint = True
    ir = AnswerIR(query=state["query"], intent=Intent.action_request, persona=state["persona"], summary=summary)
    state["ir"] = ir
    state["output"] = {"format": "text", "content": ir.summary, "action_hint": hint, "customer_context": bool(ctx and ctx.get("known"))}
    _emit(state, "compiler", format="text", ms=0, source="customer memory" if ctx and ctx.get("known") else "none")
    return state


def _branch(state: AgentState) -> str:
    i = state["decision"].intent
    if i == Intent.format_conversion:
        return "reuse"
    if i == Intent.out_of_scope:
        return "oos"
    if i == Intent.action_request:
        return "action"
    return "retrieve"


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("route", node_route)
    g.add_node("retrieve", node_retrieve)
    g.add_node("reason", node_reason)
    g.add_node("reuse", node_reuse_ir)
    g.add_node("compile", node_compile)
    g.add_node("oos", node_out_of_scope)
    g.add_node("action", node_action)
    g.set_entry_point("route")
    g.add_conditional_edges("route", _branch, {"retrieve": "retrieve", "reuse": "reuse", "oos": "oos", "action": "action"})
    g.add_edge("retrieve", "reason")
    g.add_edge("reason", "compile")
    g.add_edge("reuse", "compile")
    g.add_edge("compile", END)
    g.add_edge("oos", END)
    g.add_edge("action", END)
    return g.compile()


GRAPH = build_graph()


def run(session_id: str, persona: Persona, query: str, user_schema=None, emit: Emit | None = None,
        customer_phone: str = "") -> AgentState:
    history = memory.history(session_id)
    state: AgentState = {"session_id": session_id, "persona": persona, "query": query, "history": history,
                         "user_schema": user_schema, "emit": emit, "timings": {}, "customer_phone": customer_phone}
    final = GRAPH.invoke(state)
    memory.append(session_id, "user", query)
    memory.append(session_id, "assistant", final["output"].get("content") or final["ir"].summary)
    return final
