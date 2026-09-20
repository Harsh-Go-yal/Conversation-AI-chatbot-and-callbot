"""FastAPI surface.

POST /chat            → SSE stream of pipeline stage events, then the final answer (+ AnswerIR for the debug drawer)
POST /convert         → re-render the session's last AnswerIR in another format (no retrieval)
GET  /download/{id}   → Excel / JSON / XML file produced by a previous call
GET  /docs/list       → corpus inventory for the UI
GET  /audit           → routing audit (leak test data)
+ actions router (orders, warranty, claims, inbox)
"""
from __future__ import annotations

import asyncio
import base64
import json
import queue
import threading
import time
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.actions.api import router as actions_router
from app.agent import graph, memory
from app.agent.compiler import compile_answer
from app.config import settings
from app.llm.clients import AUDIT
from app.models.ir import OutputFormat, Persona

app = FastAPI(title="Kohler Unified Enterprise AI Agent", version="0.1")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(actions_router, prefix="/actions", tags=["actions"])

_FILES: dict[str, tuple[bytes, str, str]] = {}  # download id → (bytes, filename, mime)


@app.on_event("startup")
def _warm_models():
    """Load the embedding + reranker models in the background so the first real request (or the first voice-agent
    tool call, which has a 30 s timeout) does not pay the ~30 s cold start."""
    def work():
        try:
            from app.retrieval.search import hybrid_search
            hybrid_search("warranty period for faucets", Persona.customer, None, k=2, rerank_n=4)
        except Exception:  # noqa: BLE001 — Qdrant may not be up yet; the next request will load the models instead
            pass
    threading.Thread(target=work, daemon=True).start()


class ChatRequest(BaseModel):
    session_id: str | None = None
    persona: Persona = Persona.customer
    message: str
    json_schema: Any | None = None
    customer_phone: str | None = None  # customer mode: identifies the person so account questions use the shared memory


class ConvertRequest(BaseModel):
    session_id: str
    format: OutputFormat
    json_schema: Any | None = None
    recipient: str | None = None


def _package(out: dict) -> dict:
    """Move binary payloads to the download store and return JSON-safe output."""
    o = dict(out)
    if "bytes" in o:
        did = uuid.uuid4().hex
        _FILES[did] = (o.pop("bytes"), o.get("filename", "file.bin"), o.get("mime", "application/octet-stream"))
        o["download_id"] = did
    elif o.get("format") in ("json", "xml") and o.get("content"):
        did = uuid.uuid4().hex
        _FILES[did] = (o["content"].encode("utf-8"), o.get("filename", f"answer.{o['format']}"), o.get("mime", "text/plain"))
        o["download_id"] = did
    return o


@app.post("/chat")
async def chat(req: ChatRequest, request: Request):
    session_id = req.session_id or uuid.uuid4().hex
    from app.actions.api import _SESSIONS
    sess = _SESSIONS.get(request.headers.get("x-customer-token", ""))
    customer_phone = sess["phone"] if sess else ""  # identity comes from the login, never from the request body
    q: queue.Queue = queue.Queue()

    stages: list[dict] = []

    def emit(stage: str, data: dict):
        ev = {"stage": stage, **data}
        stages.append(json.loads(json.dumps(ev, default=str)))
        q.put({"event": "stage", "data": json.dumps(ev, default=str)})

    def work():
        memory.record_turn(session_id, {"role": "user", "text": req.message, "ts": time.time()})
        try:
            final = graph.run(session_id, req.persona, req.message, user_schema=req.json_schema, emit=emit, customer_phone=customer_phone)
            ir = final["ir"]
            payload = {"session_id": session_id, "output": _package(final["output"]), "ir": ir.model_dump(mode="json")}
            q.put({"event": "final", "data": json.dumps(payload, default=str)})
            memory.record_turn(session_id, {"role": "assistant", "text": payload["output"].get("content") or ir.summary, "stages": stages,
                                            "output": payload["output"], "ir": payload["ir"], "ts": time.time()})
        except Exception as e:  # noqa: BLE001
            q.put({"event": "error", "data": json.dumps({"message": str(e)[:500]})})
            memory.record_turn(session_id, {"role": "assistant", "text": "", "error": str(e)[:500], "stages": stages, "ts": time.time()})
        finally:
            q.put(None)

    threading.Thread(target=work, daemon=True).start()

    async def gen():
        yield {"event": "session", "data": json.dumps({"session_id": session_id})}
        while True:
            item = await asyncio.get_event_loop().run_in_executor(None, q.get)
            if item is None:
                break
            yield item

    return EventSourceResponse(gen())


@app.post("/convert")
def convert(req: ConvertRequest):
    ir = memory.last_ir(req.session_id)
    if ir is None:
        raise HTTPException(404, "No previous answer in this session to convert.")
    out = compile_answer(ir, req.format, user_schema=req.json_schema, recipient=req.recipient, instruction=f"Render the previous answer as {req.format.value}" + (f" for {req.recipient}" if req.recipient else ""))
    packed = _package(out)
    memory.update_last_assistant(req.session_id, output=packed, text=packed.get("content") or ir.summary)
    return {"session_id": req.session_id, "output": packed}


@app.get("/session/{session_id}/turns")
def session_turns(session_id: str):
    """Restore a conversation exactly as it was shown (user turns, pipeline stages, outputs, AnswerIR)."""
    return {"session_id": session_id, "turns": memory.turns(session_id)}


@app.get("/download/{download_id}")
def download(download_id: str):
    if download_id not in _FILES:
        raise HTTPException(404, "expired")
    data, name, mime = _FILES[download_id]
    return Response(content=data, media_type=mime, headers={"Content-Disposition": f'attachment; filename="{name}"'})


@app.get("/docs/list")
def docs_list():
    from app.ingest.catalog import load_catalog
    return [{"doc_id": d.doc_id, "title": d.title, "domain": d.domain, "region": d.region, "sensitivity": d.sensitivity,
             "origin": d.origin, "kind": d.kind, "version": d.version, "effective_date": d.effective_date} for d in load_catalog()]


@app.get("/audit")
def audit(limit: int = 200):
    recs = AUDIT[-limit:]
    leaks = [r for r in recs if r["provider"] == "openai" and "restricted" in r["sensitivities"]]
    return {"calls": recs, "restricted_to_cloud": len(leaks)}


@app.post("/session/reset")
def reset(session_id: str):
    memory.reset(session_id)
    return {"ok": True}


@app.get("/health")
def health():
    from app.ingest import index
    try:
        n = index.count()
    except Exception:
        n = -1
    return {"ok": True, "points": n, "router": settings.router_provider, "local_model": settings.local_model,
            "reasoner": settings.reasoner_model}


# ───────────────────────── voice-agent endpoints (Sarvam API tools call these over a tunnel) ─────────────────────────
import os
import time
from fastapi import Body

from app.actions import crm as _crm
from app.actions import tools
from app.actions.voice import tts_preview, voice_agent_definition
from app.agent.voice_qa import voice_answer


@app.post("/voice/ask")
def voice_ask(question: str = Body(..., embed=True), full: bool = Body(False, embed=True)):
    """Public-persona answer for the voice agent: plain text, short, cited by document title.
    Default is the low-latency path (app.agent.voice_qa); full=true runs the complete pipeline."""
    if not full:
        return voice_answer(question)
    final = graph.run("voice-" + uuid.uuid4().hex[:8], Persona.customer, question)
    ir = final["ir"]
    cites = "; ".join(sorted({s.title for s in ir.sources}))[:300]
    return {"answer": ir.summary or final["output"].get("content", ""), "sources": cites}


@app.post("/voice/echo")
async def voice_echo(request: Request):
    """Debug: records exactly what the voice platform sends for a tool call (logs/voice_echo.jsonl)."""
    raw = await request.body()
    rec = {"ts": time.time(), "headers": {k: v for k, v in request.headers.items() if k.lower() not in ("authorization",)}, "body": raw.decode("utf-8", "replace")[:5000]}
    (settings.raw_dir.parents[1] / "logs" / "voice_echo.jsonl").open("a", encoding="utf-8").write(json.dumps(rec) + "\n")
    return {"ok": True, "echo": rec["body"]}


@app.post("/voice/transcript")
def voice_transcript(payload: dict = Body(...)):
    """Call-end webhook from the Sarvam platform (deployment inbound calls and Instant Outbound attempts share the
    shape: attempt_id/interaction_id, status, channel_info, duration, final_agent_variables, interaction_transcript).
    Stored for the internal Inbox so a claim raised on the phone can be traced back to the call."""
    turns = payload.get("interaction_transcript") or payload.get("transcript") or []
    transcript = "\n".join(f"{t.get('role', '?')}: {t.get('en_text') or t.get('text', '')}" for t in turns) if isinstance(turns, list) else str(turns)
    variables = payload.get("final_agent_variables") or {}
    ch = payload.get("channel_info") or {}
    summary = variables.get("call_summary") or payload.get("summary") or ""
    status = payload.get("status") or ""
    c = _crm.conn()
    c.execute("INSERT INTO transcripts(call_id, phone, started, transcript, summary, actions) VALUES (?,?,?,?,?,?)",
              (str(payload.get("interaction_id") or payload.get("attempt_id") or payload.get("call_id") or uuid.uuid4().hex[:8]),
               str(payload.get("user_phone_number") or variables.get("customer_phone") or payload.get("phone") or ch.get("user_phone_number") or ""),
               str(payload.get("start_datetime") or payload.get("started_at") or ""),
               (transcript or json.dumps(payload, default=str))[:20000],
               f"[{status}] {summary}".strip()[:1000] + (f" ({payload.get('duration')} s)" if payload.get("duration") else ""),
               json.dumps({"variables": variables, "channel": ch, "failure_reason": payload.get("failure_reason"),
                           "recording_url": payload.get("recording_url"), "duration": payload.get("duration"), "app_version": payload.get("app_version")}, default=str)[:5000]))
    c.commit(); c.close()
    (settings.raw_dir.parents[1] / "logs" / "voice_webhooks.jsonl").open("a", encoding="utf-8").write(json.dumps(payload, default=str) + "\n")
    # follow-up: remember the call and send the caller a recap (SMS + email, simulated) with the next steps
    phone = (variables.get("customer_phone") or payload.get("user_phone_number") or ch.get("user_phone_number") or "")
    if not phone and isinstance(payload.get("user_information"), dict):
        phone = payload["user_information"].get("phone_number", "")
    fu = tools.follow_up_after_conversation(phone, "voice", summary) if (phone and status in ("", "connected")) else {"ok": False}
    return {"ok": True, "follow_up": fu.get("ok", False)}


@app.get("/claim-upload/{token}")
def claim_upload_page(token: str):
    """Tiny public page behind the link the voice agent sends by SMS: the caller attaches photos of the product and
    the fault; they land on the claim in the internal Inbox. Token-scoped, no login."""
    from fastapi.responses import HTMLResponse
    row = _crm.rows("SELECT id, sku, issue, status FROM claims WHERE upload_token=?", token)
    if not row:
        return HTMLResponse("<h3>This upload link is not valid.</h3>", status_code=404)
    c = row[0]
    html = f"""<!doctype html><meta name=viewport content="width=device-width,initial-scale=1">
<title>Kohler India — claim {c['id']} photos</title>
<style>body{{font-family:system-ui,sans-serif;max-width:520px;margin:32px auto;padding:0 16px;color:#1c1c1c}}
.box{{border:1px solid #ddd;border-radius:12px;padding:20px}} button{{background:#1c1c1c;color:#fff;border:0;border-radius:8px;padding:10px 16px;font-size:15px}}
.note{{color:#666;font-size:13px}} .ok{{color:#0a7a3d}}</style>
<div class=box><h2>Kohler India Customer Care</h2>
<p>Claim <b>{c['id']}</b> · {c['sku']}<br><span class=note>{c['issue']}</span></p>
<p>Please attach 2–4 photos: the product, the fault (e.g. the control panel / leak), the model label, and the purchase invoice if you have it.</p>
<form id=f><input type=file name=files accept="image/*" multiple required><br><br><button>Upload photos</button></form>
<p id=msg class=note></p>
<p class=note>Prototype — fictional demo data; photos are stored only on the demo server.</p></div>
<script>
document.getElementById('f').onsubmit=async e=>{{e.preventDefault();const fd=new FormData(e.target);const m=document.getElementById('msg');m.textContent='Uploading…';
const r=await fetch('/actions/claims/upload/{token}',{{method:'POST',body:fd}});const j=await r.json();m.className=j.ok?'ok':'note';m.textContent=j.message||JSON.stringify(j);}};
</script>"""
    return HTMLResponse(html)


@app.get("/voice/agent_definition")
def voice_definition():
    return voice_agent_definition(settings.public_base_url or "http://localhost:8010")


@app.get("/voice/tts")
def voice_tts(text: str = "Namaste, Kohler India Customer Care mein aapka swagat hai.", speaker: str = "priya"):
    return Response(content=tts_preview(text, speaker), media_type="audio/wav")
