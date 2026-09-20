"""Intent router — first node. An LLM call (OpenAI by default) that sees only the query + recent history, never
document text. Decides whether to retrieve at all, which knowledge bases, and how to decompose."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.config import settings
from app.llm.clients import local_client, openai_client
from app.models.ir import Domain, Intent, OutputFormat, Persona


class RouteDecision(BaseModel):
    intent: Intent
    domains: list[Domain] = Field(default_factory=list, description="Knowledge bases to search (1–3). Empty for non-retrieval intents.")
    standalone_query: str = Field(description="The user's question rewritten to stand alone (resolve 'that', 'it', follow-ups).")
    sub_queries: list[str] = Field(default_factory=list, description="For cross-domain questions: one focused query per knowledge base (max 3). Empty if a single search suffices.")
    requested_format: OutputFormat = OutputFormat.text
    json_schema_hint: str | None = Field(default=None, description="If the user supplied or described a JSON schema, echo it verbatim here.")
    email_recipient: str | None = Field(default=None, description="If an email is requested, who it is addressed to (e.g. 'my manager', 'the customer').")
    reason: str = Field(description="One short sentence on why this routing.")


SYSTEM = """You are the intent router for Kohler India's enterprise assistant. Classify the latest user message.

Intents:
- retrieval_question: needs facts from the knowledge bases (policies, warranties, products, HR, finance, legal, privacy, sustainability).
- format_conversion: the user wants the PREVIOUS answer in another form (JSON, Excel, XML, table, email) — no new facts needed.
- follow_up: a short follow-up that refines or extends the previous answer (e.g. "and for commercial use?") — rewrite it as a standalone question and retrieve.
- action_request: the user asks the SYSTEM to perform or report on an operation on THEIR order/account (register my product, open/raise a claim for my order, place an order, call me back, status of my claim/order/call-back, what do I still need to send, did you receive my photos). "Draft a reply/email", "write to the customer" or "is it covered?" are NOT actions — they are retrieval questions with requested_format email/text.
- out_of_scope: unrelated to Kohler, its products, policies or services.

Knowledge bases (choose by TOPIC):
- hr (leave, handbook, remote work, performance, compensation) — internal only
- finance (travel & expense, per-diem, corporate card, capex, financial results) — internal only
- legal (anti-bribery, supplier code and quality manual, ethics, human rights, water-efficiency standards matrix incl. BIS IS 17953 / WaterSense test pressures, India certification & ISI register, DPDP readiness, legal hold)
- privacy (privacy notices, cookies, data retention, breach response)
- support (warranties, returns/refunds/shipping, installation, product specs, product catalog, customer-care procedures incl. escalation matrix, tiers, refund authority limits, SLAs, email templates, recall procedure, terms & conditions)
- sustainability (Impact Reports, CSR, WaterSense, water-efficiency references)

Rules:
- A question that mixes an expense/finance rule with anti-bribery/compliance is cross-domain: domains [finance, legal] and one sub_query each.
- Otherwise keep ONE domain and NO sub_queries. Warranty coverage, claims, returns, product faults and "draft the reply to the customer" are support only — do not add legal unless the user explicitly asks about law, contracts, regulation or compliance. Sub-queries must keep the user's own words for the product and the fault (e.g. "intelligent toilet electronics").
- Product water-use / comparison questions: support (and sustainability if about savings/impact).
- Persona "customer" can only ever see public documents; still route by topic.
- requested_format: json | excel | xml | markdown_table | email | text. If a format is requested together with a NEW question, intent is retrieval_question with that format.
- Always fill standalone_query (for format_conversion, restate what the previous answer was about)."""


def route(query: str, history: list[dict], persona: Persona) -> RouteDecision:
    hist = "\n".join(f"{h['role']}: {h['content'][:400]}" for h in history[-6:]) or "(none)"
    user = f"Persona: {persona.value}\nRecent conversation:\n{hist}\n\nLatest user message:\n{query}"
    if settings.router_provider == "local":
        return local_client().complete_json(settings.local_model, SYSTEM, user, RouteDecision, purpose="router")
    return openai_client().complete_json(settings.router_model, SYSTEM, user, RouteDecision, purpose="router", reasoning="minimal")
