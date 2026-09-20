# Conversation AI chatbot and callbot — Kohler Unified Enterprise AI Agent (Track 3)

An India-first enterprise assistant for **customers** and the **internal team**: it answers questions across HR,
Finance, Legal/Compliance, Privacy, Customer Support and Sustainability knowledge bases with citations, renders any
answer as text / JSON (your schema) / Excel / XML / Markdown / email, detects superseded policy versions, keeps
restricted content on a self-hosted model, and can **act** — register warranties, check coverage, open claims,
place orders, raise tickets for the team or hand the whole conversation to a **Sarvam AI voice agent** on a real phone
number (11 Indian languages). Claims are never auto-approved: the agent prepares the case, a person decides in the Tickets console.

> `docs/SPEC.md` is the technical source of truth; `docs/Prompt_Documentation.pdf` records every prompt and decision.
> This is a prototype for **educational and personal use only**. All customer, order, claim and internal policy data is
> **fictional** (banner on every generated page); public documents are referenced for educational purposes under their
> published terms and are never committed or redistributed (see `NOTICE.md`). Nothing entered is shared with anyone.

## Architecture (one line)

`React UI ──SSE──► FastAPI ──► LangGraph: Intent Router (OpenAI) → Hybrid Retrieval (BGE-M3 + BM25 + reranker, on-device, persona-filtered) → Sensitivity Gate (restricted → local Ollama, else OpenAI) → Reasoner + Contradiction Detector → AnswerIR → Response Compiler (text/JSON/Excel/XML/table/email)` plus an **Operations layer** (SQLite CRM, guarded tools, customer memory, shared ticket queue, audit log) and the Sarvam voice endpoints.

## Working model — how to run the prototype (Windows, CPU-only laptop)

Everything runs locally except the OpenAI calls (public/internal answers) and the optional Sarvam voice line.
Run scripts live in the repo root: `run_backend.ps1`, `run_frontend.ps1`, `run_tunnel.ps1`, `docker-compose.yml`.

```powershell
# 0. prerequisites: Python 3.13, Node 24, Docker Desktop, Ollama
ollama pull qwen3:4b                       # self-hosted model for restricted content
pip install -r backend/requirements.txt
cd frontend; npm install; cd ..
copy .env.example .env                     # fill OPENAI_API_KEY (voice keys are optional, see below)

# 1. corpus — public documents are fetched by you under their terms; internal ones are generated (fictional)
python scripts/fetch_sources.py            # → data/raw/  (a few need a manual browser save; the script lists them)
python scripts/ocr_scanned.py              # OCR sidecars for the two scanned reports
python scripts/generate_synthetic.py       # 23 fictional internal documents + docs/Document_Inventory.xlsx

# 2. index (first run downloads BGE-M3 ONNX ≈ 2.3 GB; ~30 min on CPU) → 1,540 chunks in Qdrant
docker compose up -d
cd backend; python -m app.ingest.run --recreate; cd ..

# 3. run the app
.un_backend.ps1                          # FastAPI  http://localhost:8010  (OpenAPI docs at /docs)
.un_frontend.ps1                         # React    http://localhost:5180

# 4. (optional) pre-run the demo conversations so signed-in users open finished chats
python scripts/seed_demo_conversations.py --employees E001 E003
```

**Demo identities** (all fictional; the CRM is created and seeded automatically on first start, password `1234`)

| Who | Sign in with | Sees |
|---|---|---|
| Customer — Harsh Goyal | phone `7093523468` | two older registered orders, claim history |
| Customer — Vaidehi Bhangdia | phone `9860231200` | one recent unregistered order |
| Guest | no sign-in | public knowledge only; actions ask to sign in |
| Internal team — E001 … E005 | employee id | all knowledge bases, Tickets console |

**Voice line (optional).** The Sarvam agent is configured on the platform, not in this repo; `docs/VOICE_AGENT.md` has the
tool list, prompt rules and ids. To connect it to your own backend: expose port 8010 on a stable https hostname
(`.un_tunnel.ps1` runs localtunnel on a fixed subdomain), set `PUBLIC_BASE_URL` and the `SARVAM_*` values in `.env`,
and point the agent's HTTP tools and call-end webhook at that hostname.

## Evaluate

```powershell
cd backend; python ../eval/run_eval.py            # 56 questions → eval/results/latest.md
python ../eval/run_eval.py --tag conflict --no-judge
```
Metrics: retrieval hit, routing accuracy, conflict recall, access control, answer hits, JSON validity,
LLM-judged faithfulness, **leak test** (restricted chunks sent to the cloud must be 0), latency p50/p95.

## Repository map

| Path | What |
|---|---|
| `docs/SPEC.md` | Frozen specification (architecture, stack, data model, features, eval, demo) |
| `docs/Document_Inventory.xlsx` | Every document: original vs created-by-us (reference only) |
| `data/sources.yaml` · `scripts/fetch_sources.py` | Real-document manifest + terms-compliant fetcher |
| `scripts/synthetic/` · `scripts/generate_synthetic.py` | Fictional document generator (PDF/DOCX/XLSX/MD with banner) |
| `backend/app/models/ir.py` | `AnswerIR` and chunk metadata models |
| `backend/app/ingest/` | catalog → parsers (PDF/DOCX/XLSX/MD, tables) → chunker (prose / table_card / table_rows) → embeddings → Qdrant |
| `backend/app/retrieval/search.py` | Hybrid search, persona filters, rerank, India-precedence boost |
| `backend/app/agent/` | router · conflicts · reasoner · compiler · graph (LangGraph) · memory |
| `backend/app/actions/` | CRM (SQLite), guarded tools, tickets + customer memory, team console API, Sarvam voice integration |
| `backend/app/api/main.py` | FastAPI: `/chat` (SSE), `/convert`, `/download`, `/actions/*`, `/voice/*`, `/audit` |
| `frontend/` | React + Vite UI: landing page, Customer / Internal-team modes, citations, badges, formats, Help panel, Tickets console, themes |
| `eval/` | Question set, harness and stored results |
| `docs/Prompt_Documentation.pdf` | Consolidated prompt log and decision register |
| `docs/DEMO_CHECKLIST.md` · `docs/VOICE_AGENT.md` | Demo identities and steps · voice-agent setup and ids |

## Demo script
See `docs/DEMO_CHECKLIST.md` — India-persona steps for customer, internal team and the voice call.

## Evaluation
`python eval/run_eval.py` — our own 56-question suite (`eval/questions.yaml`: 20 customer-persona, 36 internal; expectations written by us against this corpus).
Last full CPU run: retrieval hit 49/49, faithfulness 0.97 (LLM-judged, n=43), customer-public-only 20/20 (structural: the persona filter runs inside Qdrant),
**leak test 0 restricted chunks in any cloud call** (also covers voice and ticket policy checks), conflict recall 6/7 → 7/7 after fixes, JSON validity 1/1 (single JSON question),
p50 ≈ 14 s cloud / ≈ 2 min on-device. This is an internal harness, not an independent benchmark. Details and per-question table: `eval/results/latest.md`, targets vs results in `docs/SPEC.md` §7.

## Voice agent (Sarvam AI)
Deployed on the Sarvam Voice Agents platform as **"Kohler India Care (prototype)"** and reachable on **+91 79658 53481**
(inbound + outbound). The agent has no knowledge of its own: eight HTTP tools call this backend through a public
tunnel — `/voice/ask` (public-only retrieval + `gpt-4.1-mini`, ~8 s) for every policy/product question and
`/actions/*` for order lookup, warranty check/registration, claims (rules applied server-side), orders and call-backs.
The call-end webhook posts the transcript and a `call_summary` to `/voice/transcript`; it is written to the customer's
memory, triggers the follow-up SMS/email and appears under Tickets → Call transcripts.
Setup, ids, the dashboard step for tool parameters (*Let the agent decide*) and the tunnel notes are in
`docs/VOICE_AGENT.md`. "Call me back" from the Help panel uses the Instant Outbound API and needs a platform API key
(`SARVAM_VOICE_API_KEY`).
