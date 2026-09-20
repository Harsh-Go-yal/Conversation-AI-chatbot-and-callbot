"""REST surface for the actions layer: used by the customer "Help with my product" panel, the internal Inbox tab,
and (over a tunnel) by the Sarvam voice agent's API tools."""
from __future__ import annotations

from datetime import datetime

import json
import re
import uuid

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.actions import crm, tools
from app.actions.voice import instant_outbound, voice_status
from app.config import settings

router = APIRouter()

# ───────────────────────── customer login (prototype) ─────────────────────────
# Questions never need a login. Anything that reads or changes a customer's record does: the web UI logs in with a
# mobile number + the demo password and sends X-Customer-Token; the voice platform is trusted by channel="voice"
# (the caller is identified by the phone call itself) plus an optional X-Voice-Key shared secret.
class _SessionStore:
    """Login sessions kept in SQLite so a backend restart does not sign everyone out (dict-like API)."""
    def __init__(self, kind: str):
        self.kind = kind

    def get(self, token: str, default=None):
        if not token:
            return default
        r = crm.rows("SELECT subject FROM sessions WHERE token=? AND kind=?", token, self.kind)
        return json.loads(r[0]["subject"]) if r else default

    def __setitem__(self, token: str, subject: dict):
        c = crm.conn()
        c.execute("INSERT OR REPLACE INTO sessions(token, kind, subject, created_on) VALUES (?,?,?,?)",
                  (token, self.kind, json.dumps(dict(subject)), datetime.utcnow().isoformat(timespec="seconds")))
        c.commit(); c.close()

    def pop(self, token: str, default=None):
        c = crm.conn(); c.execute("DELETE FROM sessions WHERE token=? AND kind=?", (token, self.kind)); c.commit(); c.close()
        return default


_SESSIONS = _SessionStore("customer")  # token → {phone, name, since}


class Login(BaseModel):
    phone: str
    password: str
    name: str = ""


@router.post("/login")
def login(b: Login):
    phone = "".join(ch for ch in b.phone if ch.isdigit())[-10:]
    if len(phone) != 10 or b.password != settings.customer_demo_password:
        raise HTTPException(401, "Invalid mobile number or password (demo password: 1234).")
    cust = crm.rows("SELECT name, email FROM customers WHERE phone LIKE ?", f"%{phone}")
    mem = crm.rows("SELECT name FROM customer_memory WHERE phone=?", phone)
    name = (cust[0]["name"] if cust else "") or (mem[0]["name"] if mem else "") or b.name.strip()
    if name:
        tools.remember(phone, "web", "", None, name=name)
    token = uuid.uuid4().hex
    _SESSIONS[token] = {"phone": phone, "name": name, "since": datetime.utcnow().isoformat(timespec="seconds")}
    crm.audit("web", phone, "login", {"phone": phone}, {"ok": True}, "demo password", "")
    return {"ok": True, "token": token, "phone": phone, "name": name, "known": bool(cust or mem)}


@router.post("/logout")
def logout(request: Request):
    _SESSIONS.pop(request.headers.get("x-customer-token", ""), None)
    return {"ok": True}


def _identity(request: Request, channel: str) -> dict:
    """Who is acting. Web calls must carry a valid session token; voice calls are trusted per channel (+ optional key)."""
    if channel == "voice":
        if settings.voice_tool_key and request.headers.get("x-voice-key") != settings.voice_tool_key:
            raise HTTPException(401, "voice key required")
        return {"phone": "", "name": "", "via": "voice"}
    sess = _SESSIONS.get(request.headers.get("x-customer-token", ""))
    if not sess:
        raise HTTPException(401, "Please log in with your mobile number to do this (questions do not need a login).")
    return {**sess, "via": "web"}


@router.get("/me")
def me(request: Request):
    sess = _SESSIONS.get(request.headers.get("x-customer-token", ""))
    if not sess:
        raise HTTPException(401, "not logged in")
    return {**sess, "context": tools.customer_context(sess["phone"])}

crm.init()


class Lookup(BaseModel):
    order_no: str | None = None
    phone: str | None = None
    channel: str = "chat"


class Register(BaseModel):
    order_no: str
    sku: str
    channel: str = "chat"


class Check(BaseModel):
    order_no: str
    sku: str
    issue: str = ""
    channel: str = "chat"


class Claim(BaseModel):
    order_no: str
    sku: str
    issue: str
    estimated_cost_inr: int | None = None
    channel: str = "chat"
    # intake (all optional; the voice agent may pack them into `issue` as 'Problem: …; Since: …')
    since_when: str = ""
    symptoms: str = ""
    installed_by: str = ""
    usage: str = ""
    preferred_slot: str = ""
    contact_phone: str = ""


class Order(BaseModel):
    sku: str
    qty: int = 1
    phone: str
    address: str
    channel: str = "chat"


class Callback(BaseModel):
    phone: str
    reason: str
    channel: str = "chat"


class Email(BaseModel):
    subject: str
    body: str
    order_no: str | None = None
    from_addr: str
    channel: str = "chat"


@router.post("/lookup_order")
def lookup(b: Lookup, request: Request):
    who = _identity(request, b.channel)
    if who["via"] == "web" and b.phone:
        b.phone = who["phone"]  # a logged-in customer can only search their own number
    return tools.lookup_order(b.order_no, b.phone, b.channel)


@router.post("/register_warranty")
def register(b: Register, request: Request):
    who = _identity(request, b.channel)
    return tools.register_warranty(b.order_no, b.sku, b.channel)


@router.post("/check_warranty")
def check(b: Check, request: Request):
    _identity(request, b.channel)
    return tools.check_warranty(b.order_no, b.sku, b.issue, b.channel)


@router.post("/open_claim")
def claim(b: Claim, request: Request):
    who = _identity(request, b.channel)
    if who["via"] == "web" and not b.contact_phone:
        b.contact_phone = who["phone"]
    details = {k: getattr(b, k) for k in ("since_when", "symptoms", "installed_by", "usage", "preferred_slot") if getattr(b, k)}
    return tools.open_claim(b.order_no, b.sku, b.issue, b.estimated_cost_inr, b.channel, details=details, contact_phone=b.contact_phone)


@router.post("/claims/{claim_id}/photos")
async def claim_photos(claim_id: str, request: Request, files: list[UploadFile] = File(...)):
    _identity(request, "web")
    """Photo upload from the web Help panel (multipart)."""
    data = [(f.filename or "photo", await f.read()) for f in files]
    return tools.add_claim_photos(claim_id, data, None, "web")


@router.post("/claims/upload/{token}")
async def claim_photos_by_token(token: str, files: list[UploadFile] = File(...)):
    """Photo upload from the link sent to a phone caller (token instead of login)."""
    row = crm.rows("SELECT id FROM claims WHERE upload_token=?", token)
    if not row:
        raise HTTPException(404, "invalid upload link")
    data = [(f.filename or "photo", await f.read()) for f in files]
    return tools.add_claim_photos(row[0]["id"], data, token, "upload-link")


@router.get("/claims/{claim_id}/photo/{name}")
def claim_photo(claim_id: str, name: str):
    path = crm.UPLOADS / claim_id / name
    if not path.exists() or ".." in name:
        raise HTTPException(404, "no such photo")
    return FileResponse(path)


@router.post("/place_order")
def order(b: Order, request: Request):
    who = _identity(request, b.channel)
    if who["via"] == "web" and not b.phone:
        b.phone = who["phone"]
    return tools.place_order(b.sku, b.qty, b.phone, b.address, b.channel)


@router.post("/request_callback")
def callback(b: Callback, request: Request):
    who = _identity(request, b.channel)
    if who["via"] == "web" and not b.phone:
        b.phone = who["phone"]
    res = tools.request_callback(b.phone, b.reason, b.channel)
    if b.channel != "voice":  # from the web Help panel: try to have the Sarvam agent call the customer right now
        res["voice"] = instant_outbound(b.phone, b.reason)
    else:  # the voice agent itself asked for a human call-back — never dial the caller back automatically
        res["voice"] = {"placed": False, "status": "human_callback"}
    return res


@router.post("/send_email")
def send_email(b: Email, request: Request):
    who = _identity(request, b.channel)
    return tools.send_email_to_team(b.subject, b.body, b.order_no, b.from_addr, b.channel, phone=who.get("phone", ""))


@router.get("/customer_context")
def customer_context(phone: str, request: Request):
    """Cross-channel memory. Web: only the logged-in customer's own record; voice platform: by caller number."""
    sess = _SESSIONS.get(request.headers.get("x-customer-token", ""))
    if sess:
        phone = sess["phone"]
    elif settings.voice_tool_key and request.headers.get("x-voice-key") != settings.voice_tool_key:
        raise HTTPException(401, "login required")
    """Cross-channel memory: who is this customer, what is open, what happens next (voice on_start tool + chat)."""
    return tools.customer_context(phone)


@router.get("/my_messages")
def my_messages(request: Request, phone: str = ""):
    sess = _SESSIONS.get(request.headers.get("x-customer-token", ""))
    if not sess:
        raise HTTPException(401, "login required")
    phone = sess["phone"]
    return tools.my_messages(phone)


class FollowUp(BaseModel):
    phone: str
    channel: str = "chat"
    summary: str = ""
    actions: list[str] = []


@router.post("/follow_up")
def follow_up(b: FollowUp):
    return tools.follow_up_after_conversation(b.phone, b.channel, b.summary, b.actions)


class AskTeam(BaseModel):
    subject: str
    body: str
    kind: str = "product_query"   # product_query | order_help | other
    order_no: str | None = None
    channel: str = "chat"


@router.post("/ask_team")
def ask_team(b: AskTeam, request: Request):
    """Customer → internal team. Web: the logged-in number; voice: the number the agent collected (phone in body)."""
    who = _identity(request, b.channel)
    phone = who["phone"] if who["via"] == "web" else ""
    return tools.ask_team(phone, b.subject, b.body, b.kind if b.kind in tools.TICKET_KINDS else "other", b.order_no, b.channel)


class AskTeamVoice(BaseModel):
    phone: str
    subject: str
    body: str
    channel: str = "voice"


@router.post("/ask_team_voice")
def ask_team_voice(b: AskTeamVoice, request: Request):
    _identity(request, "voice")
    return tools.ask_team(b.phone, b.subject, b.body, "product_query", None, "voice")


class TicketMessage(BaseModel):
    ticket_id: str
    text: str
    channel: str = "chat"


@router.post("/ticket_message")
def ticket_message(b: TicketMessage, request: Request):
    who = _identity(request, b.channel)
    return tools.customer_message_on_ticket(b.ticket_id, who.get("phone", ""), b.text, b.channel)


# ───────────────────────── internal team: login + ticket dashboard ─────────────────────────
_TEAM_SESSIONS = _SessionStore("team")  # token → employee row


class TeamLogin(BaseModel):
    employee_id: str
    password: str


@router.get("/team/employees")
def team_employees():
    return crm.rows("SELECT id, name, role, team, tier FROM employees ORDER BY id")


@router.post("/team/login")
def team_login(b: TeamLogin):
    emp = crm.rows("SELECT * FROM employees WHERE id=?", b.employee_id)
    if not emp or b.password != settings.customer_demo_password:
        raise HTTPException(401, "Unknown employee or wrong password (demo password: 1234).")
    token = uuid.uuid4().hex
    _TEAM_SESSIONS[token] = emp[0]
    crm.audit("internal", emp[0]["id"], "team_login", {}, {"ok": True}, "demo password (SSO in production)", "")
    return {"ok": True, "token": token, **emp[0]}


def _employee(request: Request) -> dict:
    emp = _TEAM_SESSIONS.get(request.headers.get("x-employee-token", ""))
    if not emp:
        raise HTTPException(401, "Sign in as a team member to work on tickets.")
    return emp


@router.get("/team/tickets")
def team_tickets(request: Request, status: str = "active", mine: bool = False, kind: str | None = None):
    emp = _employee(request)
    return {"me": emp, "stats": tools.ticket_stats(), "employees": crm.rows("SELECT id, name, role FROM employees ORDER BY id"),
            "tickets": tools.list_tickets(status, emp["id"] if mine else None, kind)}


@router.get("/team/tickets/{tid}")
def team_ticket(tid: str, request: Request):
    _employee(request)
    t = tools.get_ticket(tid)
    if not t:
        raise HTTPException(404, "ticket not found")
    return t


class TicketAction(BaseModel):
    text: str = ""
    status: str | None = None
    decision: str | None = None   # approved | declined (claims)
    assignee: str | None = None


@router.post("/team/tickets/{tid}/take")
def team_take(tid: str, request: Request, b: TicketAction | None = None):
    emp = _employee(request)
    return tools.assign_ticket(tid, (b.assignee if b and b.assignee else emp["id"]), emp["name"])


@router.post("/team/tickets/{tid}/note")
def team_note(tid: str, b: TicketAction, request: Request):
    emp = _employee(request)
    return tools.add_ticket_note(tid, emp["name"], b.text)


@router.post("/team/tickets/{tid}/reply")
def team_reply(tid: str, b: TicketAction, request: Request):
    emp = _employee(request)
    if not b.text.strip():
        raise HTTPException(400, "empty reply")
    return tools.reply_to_customer(tid, emp["name"], b.text.strip())


@router.post("/team/tickets/{tid}/status")
def team_status(tid: str, b: TicketAction, request: Request):
    emp = _employee(request)
    return tools.set_ticket_status(tid, b.status or "resolved", emp["name"], b.text)


@router.post("/team/tickets/{tid}/priority")
def team_priority(tid: str, b: TicketAction, request: Request):
    emp = _employee(request)
    pr = (b.text or "normal").strip().lower()
    if pr not in ("low", "normal", "high", "urgent"):
        raise HTTPException(400, "priority must be low | normal | high | urgent")
    c = crm.conn(); c.execute("UPDATE tickets SET priority=?, updated_on=? WHERE id=?", (pr, tools._now(), tid)); c.commit(); c.close()
    tools.ticket_event(tid, emp["name"], "priority", f"Priority → {pr}")
    return {"ok": True, "ticket_id": tid, "priority": pr}


class TicketAsk(BaseModel):
    question: str


@router.post("/team/tickets/{tid}/ask")
def team_ask(tid: str, b: TicketAsk, request: Request):
    """Policy check from inside a ticket: the employee's question is run through the full internal assistant
    (Router → Retrieval → Sensitivity gate → Reasoner) with the case facts prepended, so the answer cites the
    warranty policy / escalation matrix / T&Cs that apply to THIS order. The check is recorded on the ticket."""
    from app.agent import graph
    from app.models.ir import Persona
    emp = _employee(request)
    t = tools.get_ticket(tid)
    if not t:
        raise HTTPException(404, "ticket not found")
    if not b.question.strip():
        raise HTTPException(400, "empty question")
    if _DRAFT_INTENT.search(b.question):
        # "draft a message asking the customer to upload photos…" → write it from the thread so far + case facts
        thread = _thread_from_events(t)
        d = _write_draft(t, thread, "", "warm, clear, professional", b.question.strip(), emp)
        tools.ticket_event(tid, emp["name"], "policy_check", f"Q: {b.question.strip()}\nA: {d['draft']}\nSources: (draft written from the {d['turns']} earlier turn(s) and the case facts)\n(model: {d['llm']})")
        return {"ok": True, "ticket_id": tid, "question": b.question.strip(), "answer": d["draft"], "summary": d["draft"], "sources": [], "conflicts": [],
                "routing": {"llm": d["llm"], "model": None, "restricted_chunks": 0}, "timings_ms": {}, "is_draft": True}
    # the knowledge question carries a compact case brief (the full dossier goes to drafting); transcripts are
    # summarised here so the retrieval query stays focused on the policy question
    dossier = tools.case_dossier(t, max_transcript_turns=0)
    brief = "; ".join(f"{p['title']}: {p['text'][:300]}" for p in dossier["parts"] if p["title"] in ("Customer", "Request", "Claim", "Reported issue", "Last interaction (memory)", "Orders", "Photos"))
    query = "Case facts: " + brief + f".\n\nQuestion from the customer-care specialist: {b.question.strip()}"
    final = graph.run(f"ticket-{tid}-{emp['id']}", Persona.internal, query)
    ir = final["ir"]
    out = final["output"]
    answer = out.get("content") or ir.summary
    sources = [{"id": src.id, "title": src.title, "doc_code": src.doc_code, "version": src.version, "effective_date": src.effective_date,
                "page": src.page, "section": src.section, "sensitivity": str(getattr(src.sensitivity, "value", src.sensitivity)),
                "excerpt": src.excerpt} for src in ir.sources]
    conflicts = [{"verdict": c.verdict.value, "resolution": c.resolution, "reason": c.reason, "a": c.source_a, "b": c.source_b} for c in ir.conflicts]
    routing = {"llm": ir.routing.llm_used if ir.routing else None, "model": ir.routing.model if ir.routing else None,
               "restricted_chunks": ir.routing.restricted_chunks if ir.routing else 0}
    tools.ticket_event(tid, emp["name"], "policy_check",
                       f"Q: {b.question.strip()}\nA: {answer[:2000]}\nSources: " + "; ".join(f"{x['title']}" + (f" v{x['version']}" if x['version'] else "") + (f" p.{x['page']}" if x['page'] else "") for x in sources[:6])
                       + (f"\nVersion note: {conflicts[0]['resolution']}" if conflicts else "") + f"\n(model: {routing['llm']})")
    return {"ok": True, "ticket_id": tid, "question": b.question.strip(), "answer": answer, "summary": ir.summary, "sources": sources,
            "conflicts": conflicts, "routing": routing, "timings_ms": ir.routing.stage_timings_ms if ir.routing else {}}


class DraftReply(BaseModel):
    thread: list[dict] = []   # [{question, answer, llm}] — the policy-check conversation shown in the UI
    decision: str = ""        # optional: approved | declined | pending
    tone: str = "warm, clear, professional"
    instruction: str = ""     # extra guidance from the specialist (what the message should ask for / say)


_DRAFT_INTENT = re.compile(r"\b(draft|write|compose|prepare|frame)\b.{0,80}\b(e-?mail|mail|reply|response|letter|message|msg|sms|text|communication|update)\b", re.I)


def _thread_from_events(t: dict) -> list[dict]:
    thread = []
    for e in t["events"]:
        if e["kind"] == "policy_check" and e["text"].startswith("Q: "):
            qa = e["text"].split("\nA: ", 1)
            a_part = qa[1] if len(qa) > 1 else ""
            a_txt = a_part.split("\nSources:", 1)[0]
            thread.append({"question": qa[0][3:], "answer": a_txt, "llm": "local" if "(model: local)" in e["text"] else "openai"})
    return thread


def _write_draft(t: dict, thread: list[dict], decision: str, tone: str, instruction: str, emp: dict) -> dict:
    """Customer-facing message from the whole policy-check thread + case facts (+ the specialist's instruction).
    Runs on the self-hosted model if any turn came from restricted evidence."""
    from app.config import settings
    from app.llm.clients import local_client, openai_client
    cl = t.get("claim")
    facts = "\n" + tools.case_dossier(t)["text"]  # the whole case: request, claim, coverage, photos, memory, calls, ticket history
    convo = "\n\n".join(f"Specialist asked: {x.get('question', '')}\nAssistant answered: {x.get('answer', '')}" for x in thread) or "(no research turns yet)"
    decision = decision or (cl["status"] if cl else "")
    system = ("You write replies from Kohler India Customer Care to customers. The message is about the CURRENT CASE only — the one issue, "
              "product, order and claim/ticket listed under CURRENT CASE. Everything under BACKGROUND (other orders, earlier claims or "
              "tickets, previous calls) is reference to help you understand the customer; do not mention it unless the current issue "
              "depends on it. Use ONLY the dossier and the policy conclusions in the research conversation — do not invent coverage, "
              "amounts or dates; you may refer to what the customer told us about THIS issue on the phone or in chat. Plain, warm, professional English; short paragraphs; "
              "greet the customer by name; state the outcome or next step clearly; mention the policy the conclusion is based on "
              "in one line (document name, not internal codes like Tier authority or thresholds); quote the reference numbers exactly as given (claim id and ticket id are different things — never swap them); "
              "close with how to reach Customer Care (reply on the website chat or call the care line, Mon–Sat 8 am–8 pm). "
              "Never mention internal notes, recommendations, or the assistant. 120–200 words.")
    user = (f"CASE DOSSIER: {facts}\n\nINTENDED OUTCOME: {decision or 'not decided yet — write a status update asking for anything still needed'}\nTONE: {tone}\n"
            + (f"SPECIALIST'S INSTRUCTION FOR THIS MESSAGE (follow it exactly): {instruction}\n" if instruction else "")
            + f"\nCONVERSATION:\n{convo}\n\nWrite the message.")
    use_local = any((x.get("llm") == "local") for x in thread)

    class _Draft(BaseModel):
        reply: str

    if use_local:  # restricted evidence somewhere in the thread → the draft never leaves the machine
        out = local_client().complete_json(settings.local_model, system + " Return JSON with a single field `reply` containing only the customer-facing message.",
                                           user, _Draft, purpose="draft_reply", chunk_ids=[], sensitivities=["restricted"])
    else:
        out = openai_client().complete_json(settings.reasoner_model, system, user, _Draft, purpose="draft_reply", chunk_ids=[], sensitivities=[])
    draft = re.sub(r"<think>.*?</think>", "", out.reply, flags=re.S).strip()
    tools.ticket_event(t["id"], emp["name"], "note", f"Draft reply prepared from the policy-check thread ({len(thread)} turn(s), model: {'local' if use_local else 'openai'})"
                       + (f" — instruction: {instruction[:200]}" if instruction else "") + f":\n{draft}")
    return {"ok": True, "ticket_id": t["id"], "draft": draft, "llm": "local" if use_local else "openai", "turns": len(thread)}


@router.post("/team/tickets/{tid}/draft_reply")
def team_draft_reply(tid: str, b: DraftReply, request: Request):
    emp = _employee(request)
    t = tools.get_ticket(tid)
    if not t:
        raise HTTPException(404, "ticket not found")
    thread = b.thread or _thread_from_events(t)
    return _write_draft(t, thread, b.decision, b.tone, b.instruction, emp)


@router.get("/team/tickets/{tid}/dossier")
def team_dossier(tid: str, request: Request):
    """What the assistants see when asked about / drafting for this ticket."""
    _employee(request)
    t = tools.get_ticket(tid)
    if not t:
        raise HTTPException(404, "ticket not found")
    return tools.case_dossier(t)


@router.post("/team/tickets/{tid}/decide_claim")
def team_decide_claim(tid: str, b: TicketAction, request: Request):
    """Approve / decline the claim behind a ticket — the human decision — then resolve the ticket."""
    emp = _employee(request)
    t = tools.get_ticket(tid)
    if not t or not (t["ref"] or "").startswith("CLM-"):
        raise HTTPException(404, "no claim on this ticket")
    if b.decision not in ("approved", "declined"):
        raise HTTPException(400, "decision must be approved or declined")
    out = _decide(t["ref"], b.decision, b.text, emp)
    tools.ticket_event(tid, emp["name"], "decision", f"Claim {t['ref']} {b.decision}" + (f": {b.text}" if b.text else ""))
    tools.set_ticket_status(tid, "resolved", emp["name"], f"claim {b.decision}")
    return {**out, "ticket_id": tid}


@router.get("/products")
def products():
    return crm.rows("SELECT * FROM products ORDER BY category, sku")


# ───────────────────────── internal inbox ─────────────────────────
@router.get("/inbox")
def inbox():
    return {
        "emails": crm.rows("SELECT * FROM outbox ORDER BY id DESC LIMIT 50"),
        "claims": crm.rows("SELECT c.*, o.customer_id, cu.name AS customer FROM claims c JOIN orders o ON o.order_no=c.order_no JOIN customers cu ON cu.id=o.customer_id ORDER BY c.created_on DESC LIMIT 50"),
        "callbacks": crm.rows("SELECT * FROM callbacks ORDER BY id DESC LIMIT 50"),
        "transcripts": crm.rows("SELECT * FROM transcripts ORDER BY id DESC LIMIT 20"),
        "audit": crm.rows("SELECT * FROM audit_log ORDER BY id DESC LIMIT 100"),
        "voice": voice_status(),
        "tickets": tools.ticket_stats(),
    }


class Decide(BaseModel):
    claim_id: str
    decision: str  # approved | declined
    note: str = ""


def _decide(claim_id: str, decision: str, note: str, emp: dict | None) -> dict:
    c = crm.conn()
    row = c.execute("SELECT * FROM claims WHERE id=?", (claim_id,)).fetchone()
    if not row:
        c.close()
        raise HTTPException(404, "claim not found")
    remedy = {"approved": "Approved by Customer Care — replacement part + service visit within 2 working days",
              "declined": "Declined by Customer Care — paid service visit offered"}[decision]
    who = emp["name"] if emp else "customer_care"
    c.execute("UPDATE claims SET status=?, remedy=?, decided_by=?, decided_on=?, decision_note=? WHERE id=?",
              (decision, remedy, who, datetime.utcnow().isoformat(timespec="seconds"), note, claim_id))
    c.execute("UPDATE outbox SET status='handled' WHERE subject LIKE ?", (f"Claim {claim_id}%",))
    c.commit(); c.close()
    phone = row["contact_phone"] or crm.rows("SELECT cu.phone FROM orders o JOIN customers cu ON cu.id=o.customer_id WHERE o.order_no=?", row["order_no"])[0]["phone"]
    tools.notify_customer(phone, f"Claim {claim_id} {decision}",
                          f"Kohler India: your warranty claim {claim_id} has been {decision} by Customer Care. {remedy}." + (f" Note: {note}" if note else ""), claim_id, "internal")
    tools.remember(phone, "internal", f"Claim {claim_id} {decision} by Customer Care", tools._claim_open_items(phone))
    crm.audit("internal", who, "decide_claim", {"claim_id": claim_id, "decision": decision, "note": note}, {"ok": True}, "Human decision (every claim is decided by Customer Care)", "Escalation Matrix v3.4")
    return {"ok": True, "claim_id": claim_id, "status": decision}


@router.post("/inbox/decide_claim")
def decide(b: Decide, request: Request):
    """Legacy Inbox button: same human decision, also closes the claim's ticket."""
    if b.decision not in ("approved", "declined"):
        raise HTTPException(400, "decision must be approved or declined")
    emp = _TEAM_SESSIONS.get(request.headers.get("x-employee-token", ""))
    out = _decide(b.claim_id, b.decision, b.note, emp)
    t = tools.ticket_for_ref(b.claim_id)
    if t:
        tools.ticket_event(t["id"], emp["name"] if emp else "customer_care", "decision", f"Claim {b.claim_id} {b.decision}" + (f": {b.note}" if b.note else ""))
        tools.set_ticket_status(t["id"], "resolved", emp["name"] if emp else "customer_care", f"claim {b.decision}")
    return out


@router.post("/inbox/mark_read")
def mark_read(inbox_id: int):
    c = crm.conn(); c.execute("UPDATE outbox SET status='read' WHERE id=? AND status='unread'", (inbox_id,)); c.commit(); c.close()
    return {"ok": True}


@router.post("/reset_demo_data")
def reset_demo():
    crm.init(reset=True)
    return {"ok": True, "reset_at": datetime.utcnow().isoformat()}
