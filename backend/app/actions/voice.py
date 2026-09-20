"""Sarvam voice integration.

Two pieces:
1. `instant_outbound(phone, reason)` — asks the Sarvam Voice Agents platform to call the customer ("Call me back").
   Needs a deployed agent + phone number on the platform; configured via SARVAM_AGENT_ID / SARVAM_PHONE_NUMBER.
   Until the agent is deployed (requires the platform login), it returns a clear "not configured" status so the UI
   can show the tap-to-call number instead.
2. `tts_preview(text)` — Bulbul v3 text-to-speech via the API key (works today) for demo audio of the agent greeting.

The agent definition the voice platform should use lives in `voice_agent_definition()` — prompt + API tools that
point at our /actions endpoints — so it can be created through the Sarvam MCP with one instruction.
"""
from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request

from app.config import settings

SARVAM_API = "https://api.sarvam.ai"       # speech APIs (subscription key)
SARVAM_APPS = "https://apps.sarvam.ai"     # Voice Agents platform APIs (X-API-Key)


def voice_status() -> dict:
    return {
        "api_key": bool(settings.sarvam_api_key),
        "agent_id": settings.sarvam_agent_id,
        "phone_number": settings.sarvam_phone_number,
        "deployment_id": settings.sarvam_deployment_id,
        "outbound_ready": bool(settings.sarvam_agent_id and settings.sarvam_phone_number),
        "public_base_url": settings.public_base_url,
    }


def instant_outbound(phone: str, reason: str, customer_phone: str = "") -> dict:
    """Ask the Sarvam Voice Agents platform to call the customer now (Instant Outbound API).
    POST https://apps.sarvam.ai/api/outbounds/v1/orgs/{org}/workspaces/{ws}/outbounds, auth header X-API-Key
    (a Voice Agents platform key from Settings → API Key — the speech API subscription key is not accepted)."""
    st = voice_status()
    missing = [k for k in ("sarvam_agent_id", "sarvam_phone_number", "sarvam_voice_api_key", "sarvam_org_id",
                           "sarvam_workspace_id", "sarvam_connection_id", "sarvam_agent_version") if not getattr(settings, k)]
    if missing:
        return {"placed": False, "status": "not_configured",
                "message": "Outbound calling needs " + ", ".join(m.upper() for m in missing) + " in .env. "
                           f"The customer can call {st['phone_number'] or 'the care line'} instead."}
    body = {
        "app_config": {
            "app_id": settings.sarvam_agent_id,
            "app_version": settings.sarvam_agent_version,
            "connection_config": {"connection_id": settings.sarvam_connection_id, "agent_phone_number": settings.sarvam_phone_number},
            "agent_variables": {"reason": reason[:200], "customer_phone": customer_phone or phone},
        },
        "user_config": {"user_phone_number": _e164(phone)},
    }
    if settings.public_base_url:
        body["webhook_config"] = {"url": settings.public_base_url.rstrip("/") + "/voice/transcript", "metadata": {"reason": reason[:200]}}
    url = (f"{SARVAM_APPS}/api/outbounds/v1/orgs/{settings.sarvam_org_id}/workspaces/{settings.sarvam_workspace_id}/outbounds")
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "X-API-Key": settings.sarvam_voice_api_key})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            out = json.load(r)
        return {"placed": True, "status": "dialing", "attempt_id": out.get("attempt_id"), "from": settings.sarvam_phone_number}
    except urllib.error.HTTPError as e:  # noqa: PERF203
        return {"placed": False, "status": "error", "message": f"{e.code}: {e.read().decode('utf-8', 'replace')[:300]}"}
    except Exception as e:  # noqa: BLE001
        return {"placed": False, "status": "error", "message": str(e)[:300]}


def _e164(phone: str) -> str:
    digits = "".join(ch for ch in phone if ch.isdigit())
    if phone.strip().startswith("+"):
        return "+" + digits
    return "+91" + digits[-10:] if len(digits) >= 10 else "+" + digits


def tts_preview(text: str, speaker: str = "priya", language: str = "hi-IN") -> bytes:
    body = {"text": text[:2500], "target_language_code": language, "speaker": speaker, "model": "bulbul:v3"}
    req = urllib.request.Request(f"{SARVAM_API}/text-to-speech", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "api-subscription-key": settings.sarvam_api_key})
    with urllib.request.urlopen(req, timeout=60) as r:
        return base64.b64decode(json.load(r)["audios"][0])


def voice_agent_definition(public_base_url: str) -> dict:
    """What to create on the Sarvam Voice Agents platform (via its MCP or dashboard)."""
    base = public_base_url.rstrip("/")
    return {
        "name": "Kohler India Care (prototype)",
        "languages": ["hi-IN", "en-IN"],
        "voice": "priya",
        "greeting": "Namaste, Kohler India Customer Care mein aapka swagat hai. Main aapki kaise madad kar sakti hoon?",
        "prompt": (
            "You are Kohler India's customer care voice assistant (a prototype; all data is fictional). Speak naturally in the "
            "caller's language — Hindi, English or a mix. Keep turns short. Never invent policy: for any question about "
            "warranty terms, returns, products or policies call ask_kohler_assist and read its answer. To act on an order, "
            "first identify it with lookup_order (order number or the caller's phone number), confirm the product with the "
            "caller, then use check_warranty / register_warranty / open_claim / place_order. Read back every decision and the "
            "rule it was based on. If a claim is 'pending', explain that the internal team will approve within 2 working days. "
            "For anything you cannot do, use request_callback. Do not discuss internal documents, salaries, finances or legal matters."
        ),
        "tools": [
            {"name": "ask_kohler_assist", "method": "POST", "url": f"{base}/voice/ask", "description": "Answer a policy/product question from Kohler's public knowledge base (customer persona).", "params": {"question": "string"}},
            {"name": "lookup_order", "method": "POST", "url": f"{base}/actions/lookup_order", "params": {"order_no": "string?", "phone": "string?", "channel": "voice"}},
            {"name": "check_warranty", "method": "POST", "url": f"{base}/actions/check_warranty", "params": {"order_no": "string", "sku": "string", "issue": "string", "channel": "voice"}},
            {"name": "register_warranty", "method": "POST", "url": f"{base}/actions/register_warranty", "params": {"order_no": "string", "sku": "string", "channel": "voice"}},
            {"name": "open_claim", "method": "POST", "url": f"{base}/actions/open_claim", "params": {"order_no": "string", "sku": "string", "issue": "string", "channel": "voice"}},
            {"name": "place_order", "method": "POST", "url": f"{base}/actions/place_order", "params": {"sku": "string", "qty": "integer", "phone": "string", "address": "string", "channel": "voice"}},
            {"name": "request_callback", "method": "POST", "url": f"{base}/actions/request_callback", "params": {"phone": "string", "reason": "string", "channel": "voice"}},
        ],
        "on_end_webhook": f"{base}/voice/transcript",
    }
