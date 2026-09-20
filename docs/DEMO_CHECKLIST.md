# Demo-day checklist

## 30 minutes before
1. Laptop on power, lid open, sleep disabled. Close other heavy apps (the other project's dev servers use ports 5173/8000/6333 — ours are 5180/8010/6343).
2. `docker compose up -d` (Qdrant) → check `http://localhost:6343/collections/kohler_kb` shows 1,540 points.
3. `ollama list` shows `qwen3:4b`; run `ollama run qwen3:4b "hi"` once to load it into memory (first local answer is otherwise ~30 s slower).
4. `.\run_backend.ps1` → `http://localhost:8010/health` returns `{"ok": true, "points": …}`.
5. `.\run_frontend.ps1` → `http://localhost:5180`. Pick a theme.
6. Warm the models: ask one internal question and one customer question (embedding + reranker load on first use).
7. Reset demo data if needed: `POST http://localhost:8010/actions/reset_demo_data`.
8. Voice: `npx --yes localtunnel --port 8010 --subdomain kohler-care-demo` (must print `https://kohler-care-demo.loca.lt`; if the subdomain is taken, see `docs/VOICE_AGENT.md`). `PUBLIC_BASE_URL` in `.env` already points there. Call **+917965853481** (with +91 — the 0-STD form is rejected) once to warm the line. The Help panel shows "Call +917965853481" when `SARVAM_AGENT_ID`/`SARVAM_PHONE_NUMBER` are set.

## Demo identities (fictional; password `1234` everywhere)
| Who | Number | Data |
|---|---|---|
| Harsh Goyal (customer) | 7093523468 | orders KI-2020-0117 (Cimarron toilet + Kumin faucets, 2020, registered) and KI-2021-0342 (Forte showerhead, 2021, registered → outside warranty) |
| Vaidehi Bhangdia (customer) | 9860231200 | order KI-2026-0891 (Highline toilet + Simplice faucet, 15 days old, **not registered**) |
| Rohan Mehta (customer) | 9810000101 | KI-2022-0412 Veil intelligent toilet (~4 yrs, electronics still covered) |
| Team | Priya Sharma (Care Lead, T2) · Arjun Nair (Service Engineer) · Meera Iyer (Warranty Desk) · Rahul Verma (Sales Support, T1) · Kavya Reddy (Care Agent, T1) | Internal → Team sign-in → Tickets |

## Script (all India personas)
| # | Mode | Ask | What to point at |
|---|---|---|---|
| 1 | Internal | *What is our paternity leave entitlement?* | Pipeline strip; cloud badge; **superseded banner** (v1.0 → v2.0, 5 → 10 days); citations with version + page |
| 2 | Internal | *Give me that as JSON* | "reused previous answer" chip — no retrieval; validated JSON; paste a schema in the box and click JSON again |
| 3 | Internal | *Now make an Excel summary* → *Draft an email to my manager requesting the leave* | Download; email with subject/body and "Based on:" citations |
| 4 | Internal | *Can I claim a ₹20,000 client dinner and does it comply with anti-bribery policy?* | Router shows 2 sub-queries (finance + legal); one synthesised answer; ₹15,000 cap flagged superseded |
| 5 | Internal | *A customer's intelligent toilet electronics failed after 4 years — is it covered? Draft the reply.* | **Real** IN12-A → IN12-B conflict (3 → 5 years); email with 1800-103-2244 |
| 6 | Customer | *Compare water use of Cimarron, Highline and Wellworth in litres and show yearly savings for a family of four as an Excel download* | Excel with live "Water savings" sheet; litres first; public sources only |
| 7 | Internal | *What's the FY26 salary band for a Grade 7 in Pune?* | Gate → **on-device badge** (restricted); Inbox → "leak test: 0". Then switch to Customer and ask the same: "not available", access note |
| 8 | Customer | Sign in (9810000101 / 1234) → Help with my product → `KI-2022-0412` → Claim warranty → intake fields + a photo → Proceed | Claim **pending** with system recommendation (never auto-approved); SMS/email follow-up under *My messages*; Internal → Inbox → intake, photo, Approve with a note → customer notified; ask the chat "what is the status of my claim?" → answered from memory |
| 8b | Internal | Team sign-in as Meera Iyer → Tickets → take Vaidehi's claim → reply "please upload a flush video" → customer replies from the Help panel → approve with a note | Shared queue, stats, full history; customer gets SMS/email; chat + phone quote the team's reply |
| 9 | Phone | Call +91 79658 53481 from the same number | Greets by name, resumes the open claim ("photos received, under review"); intake questions if a new claim; SMS + email recap after the call |
| Bonus | Internal | *Does Kohler still require ISO/TS 16949 from suppliers?* | Real Supplier Quality Manual Rev 2.0 → 5.0 superseded |
| Bonus | Internal | *Is our India privacy policy DPDP-ready?* | `review_recommended` banner — never "non-compliant" |

## Pre-seeded conversations (for the recorded demo)
Conversations persist server-side (`logs/transcripts_ui/`) and reopen automatically per identity — no live queries needed:
| Where | Sign in as | What is already there |
|---|---|---|
| Internal → Chat | Priya Sharma (E001) or Meera Iyer (E003) | paternity (v1.0→v2.0 flag) → JSON → Excel → email to manager; ₹20k dinner + anti-bribery; intelligent-toilet 4-yr email (IN12-A→B); ISO/TS 16949 (Rev 2.0→5.0); DPDP *review recommended*; FY26 salary band **on-device** |
| Customer → Chat | 7093523468 (Harsh) | intelligent-toilet warranty; water-use comparison + Excel download; cancel/refund; **status of my claim (from memory)**; salary band → refused |
| Customer → Chat | 9860231200 (Vaidehi) | "is my Highline registered?" (from memory → not yet, how to); Highline vs Cimarron water use; Simplice faucet warranty |
| Customer → Chat | not signed in | intelligent-toilet warranty; personal data & grievance |
Re-seed any time: `python scripts/seed_demo_conversations.py [--only internal harsh vaidehi guest] [--reset]`. "New" in the chat starts a fresh conversation without touching these.

## Recording-day notes
- Reasoner is `gpt-5-mini` (set in `.env`); cloud answers take 13–25 s — say "it is routing, retrieving and reasoning" while the pipeline strip animates.
- Step 7 (salary band) runs on-device: ~2 min on this CPU. Start it, switch to the Customer tab to show the same question being refused, come back.
- Queue is seeded with real activity from today: Harsh's claim TKT-C5D198 (with a 4-turn policy thread and a draft), his two product queries, Vaidehi's resolved claim. `POST /actions/reset_demo_data` wipes everything if you want a clean slate (then re-create one claim by phone/website first).
- Voice line is on v8; dial **+917965853481** with the +91.

## If something goes wrong
- Local model slow (> 2 min): say so honestly — it is a 4B model on a CPU; switch `LOCAL_MODEL=llama3.2:3b` in `.env` for speed, or point `LOCAL_LLM_URL` at a GPU box.
- OpenAI error: the reasoner falls back to `gpt-4.1-mini` automatically; check the API key in `.env`.
- No sources / odd answers: `http://localhost:8010/health` → `points` should be > 1,500; otherwise `python -m app.ingest.run`.
- UI stuck on "Thinking…": refresh; check `logs/backend.log`.
