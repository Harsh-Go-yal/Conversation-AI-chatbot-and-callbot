# Voice agent — "India Care (prototype)"

The phone channel is a **Sarvam Voice Agents** app that calls back into this backend for every fact and every action.
Nothing about warranties, orders or policies lives on the voice platform: the agent's prompt tells it to *always* use a
tool, and every tool is one of our `/voice/*` or `/actions/*` endpoints reached through a Cloudflare tunnel.

```
caller ──phone──▶ Sarvam (STT · LLM · TTS, voice "priya", Hindi/English)
                     │ tool call (HTTPS, JSON)
                     ▼
        cloudflared tunnel ─▶ FastAPI :8010
                     ├─ /voice/ask            → app.agent.voice_qa  (hybrid retrieval, public-only, gpt-4.1-mini, ~8 s)
                     ├─ /actions/lookup_order, check_warranty, register_warranty, open_claim, place_order, request_callback
                     └─ /voice/transcript     ← call-end webhook (transcript + call_summary → Inbox › Call transcripts)
```

## What exists on the platform (created through the Sarvam Voice Agents MCP)

| Item | Value |
|---|---|
| Agent (app) id | `Kohler-Indi-73069449-a794` — committed **v8** (v4 LLM-filled params + 11 languages · v5 caller's own number · v6 human-decided claims + memory at call start · v7 stable hostname · v8 `ask_team` + number confirmation + greet by name) |
| Voice / language | `priya` (Sarvam), initial language Hindi, LID on, code-mixed words: Kohler, warranty, claim, order, SKU, Tier 1, product names |
| Agent variables | `customer_phone`, `reason` (filled by Instant Outbound "Call me back"), `call_summary` (post-call, written by the platform) |
| Tools (state `start`) | `ask_kohler_assist`, `lookup_order`, `check_warranty`, `register_warranty`, `open_claim`, `place_order`, `request_callback`, `ask_team` (→ team ticket), `end_interaction`; on-start `load_customer_context` |
| Deployment | `Kohler-Indi-a0c8d26f-5744` — inbound+outbound on **+91 79658 53481** (Vobiz connection `e4b611e6-5b-5cc6578d-5888`), webhook → `<PUBLIC_BASE_URL>/voice/transcript` |
| Org / workspace | `01a038f8-4104-7041-bf52-a7dac9db5953` / `01a038f8-410c-743e-b2c9-20396c451032` |

All ids are also in `.env` (`SARVAM_AGENT_ID`, `SARVAM_PHONE_NUMBER`, `SARVAM_DEPLOYMENT_ID`, `SARVAM_ORG_ID`,
`SARVAM_WORKSPACE_ID`, `SARVAM_CONNECTION_ID`, `SARVAM_AGENT_VERSION`).

## Tool parameters are "Let the agent decide" (done)

The MCP's `create_http_tool` can only create **static** body parameters (verified with `/voice/echo`). The 17
caller-filled parameters were switched to *Let the agent decide* in the dashboard (Tools → each tool → Body → ⚙);
`channel` stays fixed = `voice`. Because the dashboard drops the field descriptions when switching, the parameter guide
lives in the agent prompt ("TOOL PARAMETERS"). Recreating a tool through the MCP would reset this — patch the prompt or
the deployment instead of recreating tools.

**First real call (v4, 194 s):** English question answered in English from the KB; caller switched to Hindi and the
agent followed; order `KI-2022-0412` looked up and confirmed; claim `CLM-05EFA0` created *pending* with the Tier-1
rule explained; call-back requested; transcript + summary arrived on the webhook. Recording: Sarvam dashboard →
Monitor → Call Logs (the MCP/API expose transcript and events, not the audio file).

## Human-in-the-loop claims, memory and follow-ups (v6)

* `open_claim` never decides: the agent runs a 7-question intake, packs it as labelled segments into `issue`, the
  backend files the claim as *pending* with a recommendation, and a person decides in the Inbox.
* `load_customer_context` (on-start tool) → `GET /actions/customer_context?phone=<caller>` → saved into the agent
  variables `customer_context` / `customer_name`, so the greeting names the caller and resumes open items.
* The call-end webhook now also writes the customer memory and sends the SMS + email recap (simulated outbox).

Dashboard steps for v6 (the MCP creates static parameters only):
1. Tools → `open_claim` → Body → ⚙ **Let the agent decide** on `order_no`, `sku`, `issue` (channel stays fixed).
2. Tools → `load_customer_context` → Params → `phone` → ⚙ → **Agent variable → User Identifier** (the caller's number).
Then commit and move the deployment (Claude: *"commit v6 and deploy it"*).

## v8: team tickets from the phone (deployed)

`ask_team` → `POST /actions/ask_team_voice` creates a ticket in the shared team queue (product info, quotes, anything a
person must handle). The prompt makes the agent collect and read back the caller's mobile number before orders,
call-backs or team requests. Dashboard step for v8: Tools → `ask_team` → Body → ⚙ **Let the agent decide** on `phone`,
`subject`, `body` (channel stays fixed); then commit + move the deployment.

## "Call me back" (Instant Outbound) needs a platform API key

`POST /actions/request_callback` from the Help panel asks the platform to dial the customer
(`https://apps.sarvam.ai/api/outbounds/v1/orgs/{org}/workspaces/{ws}/outbounds`, header `X-API-Key`). That key is a
**Voice Agents platform key** (dashboard → Settings → API Key), not the speech-API subscription key (tested: the
subscription key returns 401). It is in `.env` as `SARVAM_VOICE_API_KEY` and the outbound path is verified (the demo
test call was placed through it). A deployment must be **paused** before its version can be patched.

## Public hostname: localtunnel with a fixed subdomain

The Cloudflare quick tunnel died mid-day (its retry loop never re-registered) and every restart gives a new random
hostname, which would mean re-pointing all tools. The backend is now exposed as **`https://kohler-care-demo.loca.lt`**:

```bash
npx --yes localtunnel --port 8010 --subdomain kohler-care-demo
```

(no account; the subdomain is re-claimed on restart as long as nobody else holds it; JSON POSTs from the platform's
`python-httpx` client pass without the browser interstitial). If the hostname ever has to change: edit the URL host of
the 8 tools **in the dashboard** (keeps the "Let the agent decide" parameters), patch the deployment webhook via the
MCP (pause → patch → resume), set `PUBLIC_BASE_URL` in `.env`, restart the backend.

## Testing without a phone

* Text turn against the committed version: MCP `send_chat` (what Claude uses), or the Playground in the dashboard.
* Backend side: `logs/routing_audit.jsonl` shows `purpose: voice_qa` calls (leak test covers voice traffic —
  `/voice/ask` uses the *customer* persona filter, so restricted/internal chunks can never be retrieved for a caller);
  `logs/voice_webhooks.jsonl` keeps every call-end payload; the Inbox › *Call transcripts* tab shows them.
* `POST /voice/echo` records exactly what the platform sends (used to verify the static-parameter behaviour).

## Demo flow on the phone (fictional data)

**Dial with the +91 prefix** (`+917965853481`); the `0`-STD form is rejected by mobile carriers as invalid. Verified on a
7-minute inbound call (v7): the on-start context loaded Harsh Goyal's record from the caller ID, orders were found by
number, warranty checked, claim `CLM-A93DCD` registered pending with the full intake, recap delivered by webhook.

1. Call +91 79658 53481 → greeting in Hindi.
2. *"Mera intelligent toilet ka electronics kharab ho gaya, order KI-2022-0412"* → `lookup_order` → reads back Rohan Mehta / Veil → confirm.
3. *"Kya ye warranty mein hai?"* → `check_warranty` → 5 years electronics under IN12-B (the old IN12-A said 3).
4. *"Claim register karo"* → 7-question intake → `open_claim` → claim id read out, *pending* for a person; Internal → Tickets shows it with channel `voice`.
5. Hang up → transcript + `call_summary` appear under Inbox › Call transcripts.
