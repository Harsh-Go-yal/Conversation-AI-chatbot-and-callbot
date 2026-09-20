# Kohler Unified Enterprise AI Agent — Project Specification (v1.8, as built)

Track 3 — *Unified Enterprise AI Agent*. This document is the single source of truth for scope, architecture,
technology choices, features and evaluation. Changes require an entry in `Prompt Documentation.md`.

---

## 1. Problem statement → our reading

| PS requirement | How we meet it |
|---|---|
| Answer complex **internal and external** queries | Two audiences on one platform: external **Customer** (public chat) and **Internal team** (one shared internal knowledge base — no per-role gating). **India-first**: the product, demo and evaluation target Kohler India; two regions only — `global` (parent, applies everywhere) and `IN` (child, overrides) |
| Knowledge bases: **HR, financial guidelines, customer support, privacy, legal/compliance** | The five required knowledge bases plus a customer-facing **Sustainability** KB (Impact Reports, CSR, WaterSense, water-efficiency references). Two sides: **Internal-only KBs** = HR · Finance · Legal (nothing public); **Customer-facing KBs** = Privacy · Support · Sustainability (public documents plus the internal procedures for handling those topics; per-document visibility is decided by `sensitivity`) |
| **Multi-turn conversational reasoning** | Intent router distinguishes new questions from follow-ups and format conversions; conversation memory holds the last structured answer |
| **Dynamic output formatting** — JSON schema, downloadable Excel, XML, ready-to-send emails | Response Compiler transforms one structured intermediate (`AnswerIR`) into NL, JSON (user schema, Pydantic-validated), Excel, XML, Markdown table, email |
| Evaluation weights 45 / 25 / 20 / 10 | Novelty is concentrated in five named mechanisms (§5); execution proven by an eval harness (§7); UX by a two-mode React UI (§6); sustainability by real WaterSense data and a water-savings calculator |

Corpus: **80 documents** — 57 real, publicly published Kohler / Kohler India / Kohler Mira / third-party documents
(used under their terms, never redistributed) + 23 fictional documents (banner on every page) that fill the gaps no
company publishes. See `NOTICE.md`, `data/sources.yaml`, `data/synthetic_manifest.yaml`, `docs/Document_Inventory.xlsx`.

---

## 2. Architecture

```
                         ┌──────────────────────────────────────────────────────────┐
  React UI ───SSE──►    │  FastAPI  /chat  /formats/{json|xlsx|xml|email}  /docs   │
  (Customer | Internal)  └──────────────────────────────┬───────────────────────────┘
                                                        │ LangGraph state machine
   ┌────────────────────────────────────────────────────▼─────────────────────────────────────────────┐
   │ [1] INTENT ROUTER (LLM, OpenAI)                                                                  │
   │     intent ∈ {retrieval_question, format_conversion, follow_up, out_of_scope}                    │
   │     domains[], region, sub_queries[] (cross-domain), requested_format                            │
   │        ├── format_conversion / follow_up on last IR ─────────────────────────────► [5]           │
   │        ▼                                                                                         │
   │ [2] RETRIEVAL (all on-device)  fastembed BGE-M3 dense + BM25 sparse → Qdrant hybrid (RRF)        │
   │     payload filters: domain ∈ router.domains · region ∈ {IN, global}                             │
   │                      audience ∈ {public} (Customer) or {public, internal} (Internal team)          │
   │     → BGE-reranker-v2-m3 → top-k chunks (k=8 per sub-query)                                      │
   │        ▼                                                                                         │
   │ [3] SENSITIVITY GATE   any chunk.sensitivity == "restricted" → local LLM (Ollama)                 │
   │                        else                                  → OpenAI                            │
   │        ▼                                                                                         │
   │ [4] REASONER (chosen LLM)  + CONTRADICTION DETECTOR (same policy_key, ≠ version)                  │
   │     → AnswerIR {claims[], entities{}, sources[], conflicts[], access_notes[], summary, badge}     │
   │        ▼                                                                                         │
   │ [5] RESPONSE COMPILER (no LLM for JSON/XML/Excel; LLM only for NL prose and email tone)          │
   │     NL · JSON(schema) · Excel · XML · Markdown table · Email                                     │
   └──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

**Design rules (locked)**
1. Retrieval and embeddings never leave the machine. Only the router (query + history) and the reasoner
   (non-restricted evidence) call OpenAI.
2. Access control and model routing both read the **same chunk metadata** — one source of truth.
3. `AnswerIR` is the contract between reasoning and formatting; formatting is deterministic code wherever possible.
4. The contradiction detector is engineered, not prompted: it triggers only on chunks sharing a `policy_key` with
   different `version`/`effective_date`, then asks the LLM to describe the difference.

---

## 3. Technology stack (final)

| Layer | Choice | Version / model | Why |
|---|---|---|---|
| Language | Python | 3.13 | Already installed; all libs support it |
| API | FastAPI + uvicorn, `sse-starlette` | latest | Async, streaming, Pydantic-native |
| Orchestration | LangGraph (+ langchain-core only) | latest | Explicit state graph = the architecture slide; checkpointer for conversation memory |
| Cloud LLM | OpenAI API | Router: `gpt-5-mini` (structured outputs, minimal reasoning) · Reasoner: `gpt-5` (low reasoning) with `gpt-4.1` as configurable fallback | Best structured-output reliability; configurable via `.env` |
| Local LLM | Ollama | `qwen3:4b` (thinking off) default; `ministral-3:8b` fallback | Runs on CPU-only laptop at usable speed; JSON mode |
| Embeddings | fastembed (ONNX, CPU) | `BAAI/bge-m3` dense (1024-d, official ONNX build registered as a fastembed custom model) + `Qdrant/bm25` sparse | PS-specified model; ONNX avoids PyTorch on CPU; ~2.7 chunks/s on the i7-1355U |
| Reranker | fastembed | `BAAI/bge-reranker-base` (v2-m3 is not in the fastembed 0.8 registry; swap via `RERANK_MODEL` when available) | Closest BGE reranker available on CPU |
| Vector DB | Qdrant (Docker) | `qdrant/qdrant` latest; one collection `kohler_kb`, named vectors `dense` + `sparse`, payload indexes on domain/region/audience/sensitivity/policy_key | Native hybrid search + payload filtering |
| Parsing | PyMuPDF (PDF, page-anchored), python-docx, openpyxl (row-wise), Markdown | — | Page numbers for citations; tables as structured rows |
| OCR | RapidOCR (ONNX) + wordsegment | — | Already built (`scripts/ocr_scanned.py`) |
| Validation / IR | Pydantic v2 | — | `AnswerIR`, user JSON-schema validation with retry |
| Output formats | openpyxl (Excel), `xml.etree` (XML), Markdown, email via compiler prompt | — | Deterministic where possible |
| Frontend | React 18 + Vite, TypeScript, Tailwind, shadcn/ui | Node 24 | SPA is enough — no SSR needed; two modes, citation panel, format selector, downloads |
| Streaming | Server-Sent Events (stage events + token stream) | — | "Routing → Retrieving → Reasoning → Compiling" progress |
| Eval | Custom harness (`eval/`) + LLM-as-judge (OpenAI) | — | Metrics in §7; RAGAS optional |
| Observability | structlog JSON logs, per-stage timings, routing audit log | — | Feeds the metrics panel and the leak test |
| Voice / telephony | Sarvam AI — Voice Agents platform (agent, API tools, inbound number, Instant Outbound), Saaras STT, Bulbul v3 TTS; managed via the Sarvam Voice Agents MCP server | `bulbul:v3`, `saaras:v3`, `sarvam-105b` available | Hindi/English code-mixed calls; phone number already provisioned; no browser WebRTC needed |
| Actions store | SQLite `crm.db` (orders, customers, registrations, claims, callbacks, outbox, audit_log) | — | Small, inspectable, resettable for demos |
| Tunnel | `cloudflared` (or ngrok) | — | Lets Sarvam's cloud reach the local FastAPI action endpoints during the demo |
| Config / infra | `.env` (OpenAI + Sarvam keys), `.mcp.json` (Sarvam MCP servers; git-ignored, `.mcp.json.example` committed), `docker-compose.yml` (Qdrant only) | — | One command to run |

Not used (deliberately): PyTorch, LlamaIndex, hosted vector DBs, LangChain agents/chains beyond core types.

---

## 4. Data model

### 4.1 Chunk payload (Qdrant)
```
doc_id, title, domain{hr|finance|legal (internal) | privacy|support|sustainability (customer-visible)}, region{global|IN},
audience{public|internal}, sensitivity{public|internal|restricted},
tags[], origin{original|synthetic}, doc_code?, version?, effective_date?, policy_key?, supersedes?,
source_path, source_url?, page?, section?, chunk_index, text
```
Chunking (SecureGPT-v2 scheme): three kinds — `prose` (section-based, target 320 tokens, small sections merged to
≥ 120, never across pages), `table_card` (per table: title, columns, row count, sample rows) and `table_rows` (row
groups ≤ 450 tokens with the header repeated, "rows i–j of N"). Every chunk starts with a context header
`kb/region › document (code, version, effective date) › section` then `———`. 1,526 chunks, avg 251 tokens.

### 4.2 Region model (India-first, two regions)
| Tag | Meaning | Examples |
|---|---|---|
| `global` | **Parent** — applies to every Kohler entity, or product engineering data. Where another market's data is important (USD reference bands, US-state breach timelines, WaterSense thresholds) it lives inside a global document. | Supplier Code, Human Rights Policy, Impact Reports, corporate Privacy Notice, Cookie Policy, Handbook, Anti-Bribery Policy, product spec sheets, product catalog, standards matrix |
| `IN` | **Child** — Kohler India-specific; inherits everything from the parent and overrides it on the same topic. | India Warranty IN12-B and product-line warranties, India Privacy Policy, T&Cs, Refund/Shipping/Installation, India Leave Policy, India T&E Addendum, CSR reports, certification register, escalation matrix, email templates |

There are no other region tags. US/UK-specific documents that were downloaded are parked under `data/raw/_excluded/`
(`method: excluded` in the manifest) and are not ingested.

**Inheritance model.** `global` is the parent; `IN` is the child, which inherits everything and *overrides* wherever
India has its own document (India Leave Policy over the Handbook's leave section; India T&E Addendum over Global T&E
limits). A query resolves child-first, then parent for anything the child does not define. Retrieval always pulls
both tags; precedence is implemented twice — a rerank boost for `region == IN` over `global`, and a reasoner
instruction ("India-specific documents take precedence; global documents fill gaps; say which applied"). An `IN`
document overriding a `global` one is **not** a contradiction — the detector fires only on the same `policy_key`
with a different `version` / `effective_date`. Synthetic global documents are written parent-shaped (principles and
minimums), with the operative numbers in the India child. Locale in the compiler: ₹ with Indian grouping
(₹1,00,000), litres first with gallons in brackets, dd-mm-yyyy.

### 4.3 Knowledge-base sides
| Side | Knowledge bases | Contents | Default audience |
|---|---|---|---|
| Internal-only | `hr`, `finance`, `legal` | Handbook, leave and T&E policies, compensation, CapEx, anti-bribery, supplier code and quality manuals, ethics and human-rights statements, standards matrix, certification register, DPDP note, legal hold | `internal` (some `restricted`) |
| Customer-facing | `privacy`, `support`, `sustainability` | Privacy notices and cookie policy; warranties, returns/shipping/installation, customer terms, spec sheets, product catalog; Impact Reports, CSR reports, WaterSense brochure, water-efficiency references — **plus** the internal procedures for handling those topics (escalation matrix, tone guide, recall procedure, retention schedule, breach playbook, workforce privacy notice, internal warranty copy) | `public` for customer documents; the internal procedures keep `internal`/`restricted` and stay hidden from customers |

Folders on disk mirror this: `data/raw/<kb>/<region>/`. A folder is a **topic**, not a permission: the router picks
knowledge bases by topic, and visibility is decided per document by `sensitivity`. This is deliberate — an internal
agent asking about a refund retrieves the public Refund Policy and the escalation matrix's authority limits from the
same KB in one pass, while a customer asking the same question never sees the escalation matrix.

### 4.4 Persona → filter (two levels, not roles)
| Persona | audience ∈ | sensitivity ≤ | region ∈ | Model |
|---|---|---|---|---|
| Customer (external) | public | public | {IN, global} | OpenAI |
| Internal team | public, internal | restricted (everything) | same | OpenAI; local model when any retrieved chunk is `restricted` |

Every internal document is visible to the whole internal team — access is not personalised by role. `sensitivity`
therefore does two jobs: `public` vs `internal` decides *visibility* (external vs internal), and `restricted`
decides *which model reasons* (never the cloud). Role words that appear inside documents ("for managers", "Customer
Care") are content, not access rules.

### 4.5 `AnswerIR` — Answer Intermediate Representation

The structured, format-neutral answer the reasoner produces before anything is shown. It is the contract between
reasoning and presentation: the reasoner emits claims, entities, sources, conflicts and access notes (Pydantic,
validated); the Response Compiler renders them as NL, JSON (user schema), Excel, XML, Markdown or email. Because
sources attach at claim level, every format carries the same document/version/page citations, and format
switches ("now as Excel") reuse the IR without re-retrieval.

```
query, intent, persona, region, domains[], llm_used{openai|local}, routing_reason
claims[]       {id, text, type{fact|policy|number|recommendation}, confidence, source_ids[]}
entities{}     {amounts[], durations[], dates[], products[], roles[], thresholds[]}
sources[]      {id, doc_id, title, domain, region, version, effective_date, page, section, excerpt, origin}
conflicts[]    {claim_a, claim_b, verdict{superseded|review_recommended|conflict}, resolution, reason}
access_notes[] e.g. "3 internal documents match this question but are not available to external customers"
summary        2–4 sentences
```

Example (abridged): for "What is our paternity leave entitlement?" the IR holds claim c1 "10 working days, paid,
within 90 days" → source s1 (India Leave Policy v2.0, p.1); source s2 (v1.0: 5 days) with
`conflicts: [{s1, s2, superseded, "v2.0 effective 01-04-2025 raised paternity leave from 5 to 10 days"}]`; and a
global Handbook source marked as minimum only.

---

## 4A. Use cases

### Customer (external — public documents only, OpenAI)
| # | Scenario | Documents used | Output |
|---|---|---|---|
| C1 | Warranty on an intelligent toilet | India Warranty IN12-B | Cited answer |
| C2 | How to register a product and claim | Warranty policy, T&Cs | Answer + draft claim email |
| C3 | Compare Cimarron / Highline / Wellworth water use for a family of four | Spec sheets, product catalog, savings model | Excel with formulas |
| C4 | Which toilets are water-efficient / WaterSense | Catalog, WaterSense brochure, Impact Report | Markdown table |
| C5 | Cancel a kohler.co.in order; how the refund is paid | India T&Cs, Refund Policy | Answer + email to customer care |
| C6 | What data Kohler keeps and how to raise a grievance | India Privacy Policy (retention schedule withheld — access note) | Answer / JSON |
| C7 | What Kohler does on sustainability in India | CSR reports, Impact Report | Answer / XML |
| C8 | Is the Kumin faucet suitable for 5 bar supply pressure | Kumin installation instructions | Answer |

### Internal team (all documents; local model when restricted evidence is involved)
| # | Scenario | Documents used | Output |
|---|---|---|---|
| I1 | Paternity leave → JSON → Excel → email to manager | India Leave Policy v2.0 (v1.0 superseded), Handbook | NL → JSON → Excel → email |
| I2 | ₹20,000 client dinner + anti-bribery compliance | India T&E v2.1 (v1.4 superseded) + Anti-Bribery Policy | Cross-domain cited synthesis |
| I3 | Intelligent toilet electronics failed after 4 years — covered? draft reply | IN12-B vs IN12-A (real conflict), escalation matrix (internal), tone guide | Email (cloud badge) |
| I4 | FY26 salary band for Grade 7 in Pune | Compensation bands 🔒 | Answer / Excel (🔒) |
| I5 | Does Kohler still require ISO/TS 16949 from suppliers | Supplier Quality Manual Rev 5.0 vs Rev 2.0 (real) | Answer with version diff |
| I6 | Is the India privacy policy DPDP-ready | India Privacy Policy + DPDP Readiness Note → `review_recommended` | Markdown table / XML |
| I7 | Is the Simplice faucet water-efficient under Indian standards | Standards matrix (normalisation), certification register, spec sheet | Answer + JSON |
| I8 | Suspected customer-data breach — first 24 hours | Breach playbook 🔒 (DPDP Board, CERT-In 6 h) | Checklist / email to Legal (🔒) |
| I9 | Who approves a ₹3 crore plant upgrade | CapEx matrix 🔒 | Answer / JSON (🔒) |
| I10 | Gifts & hospitality rules as an email to the sales team | Anti-Bribery Policy, India T&E Addendum | Ready-to-send email |

---

## 5. Features and novelty (ranked for the 45% criterion)

| # | Feature | What is novel / why judges should care |
|---|---|---|
| 1 | **Evidence-driven Data Sovereignty Routing** | LLM choice is made *after* local retrieval from chunk metadata, not from the query or the user. Restricted text can never reach the cloud; the UI shows ☁️/🔒 with the reason. Turns a hardware constraint (no GPU) into a governance feature. |
| 2 | **`AnswerIR` + Response Compiler** | One structured answer, many renderings. "Give me that as JSON / Excel / email" re-uses the IR without re-retrieval; JSON is validated against the *user's* schema with automatic repair. Formats are code, not prompts → deterministic, testable. |
| 3 | **Version-aware contradiction & staleness detection on real revision history** | Triggered by metadata (`policy_key` + version), verified by LLM. Demonstrated on genuine Kohler revisions (Supplier Quality Manual 2008→2013→2020→current; India Warranty IN12-A→B) plus planted HR/Finance conflicts. Three verdicts: `superseded`, `review_recommended`, `conflict` — never "non-compliant". |
| 4 | **External / internal boundary enforced at the vector-store level** | The public-vs-internal filter is applied before search, so internal content is never retrieved for an external customer. The IR still reports "n internal documents withheld" so the agent is transparent. Same question, different answer for Customer vs Internal team. |
| 5 | **Cross-market standards reasoning** | Deterministic unit/pressure normalisation tool (gpm↔l/min, psi↔bar, √-pressure scaling) + a global standards matrix (EPA WaterSense, BIS IS 17953, WELS, PUB, Water Label, GB) so the agent can compare one product across US and India certification regimes. Directly addresses Kohler's global-solutions context. |
| 6 | **Cross-domain planner** | Router decomposes "₹20k client dinner + anti-bribery?" into Finance + Legal sub-queries and synthesises one cited answer; sensitivity gate applies across all sub-queries. |
| 7 | **Water-savings Excel from real data** | Product comparison pulls gpf/gpm from real spec sheets, applies the savings model, and emits a downloadable workbook with formulas — the sustainability criterion made tangible. |
| 8 | **Compliance-first corpus** | Real documents fetched under published terms (manifest, hashes, no crawling), fictional documents banner-marked and grounded in the real ones, inventory workbook — feasibility and integrity judges can verify. |
| 9 | **Measurable safety: the leak test** | Eval harness asserts that zero restricted chunks were sent to OpenAI across all runs (routing audit log). A number, not a promise. |
| 10 | **Stage-streaming UX** | Router → Retrieval → Gate → Reasoner → Compiler events stream to the UI with timings; citation panel with page-level jump; badge with routing reason. |

---

## 5B. Actions and voice layer — "from answers to actions"

The chat answers questions; this layer lets the same agent **do** things for a customer, through two channels that
share one brain.

**Customer flow ("Help with my product")** — three steps in one panel: (1) order number *or* phone + product;
(2) need: register warranty · claim warranty · product help · new order · other; (3) channel: **Email the team**
(the compiler drafts the email from order details + policy; customer reviews and sends; lands in the internal Inbox)
or **Talk to us** (tap-to-call the Sarvam number, or "Call me back" → Instant Outbound dials the customer).

**One brain, two channels.** The Sarvam voice agent has no knowledge base of its own. It gets API tools pointing at
our FastAPI backend: `ask_kohler_assist(question)` → the RAG pipeline in Customer persona (public documents only),
and the guarded action tools below. Chat and phone therefore give the same policy answer and apply the same rules.

| Tool | What the system does | Who decides |
|---|---|---|
| `lookup_order(order_no or phone)` | Read-only | — |
| `register_warranty(order, product)` | Allowed if the order exists and the product is unregistered | system |
| `check_warranty(order, product, issue)` | Eligibility from purchase date + IN12-B periods + registration | system (read-only) |
| `open_claim(order, product, intake…)` | **Never approves or declines.** Runs a structured intake (what is wrong, since when, symptoms, installer, usage, preferred visit slot, contact), checks coverage, computes a *recommendation* from the policy rules (Tier-1 eligible / Tier-2 / out of warranty), files the claim as **pending**, sends the customer an SMS + email with a photo-upload link | **a person** in the Inbox (approve / decline + note → customer notified) |
| `add_claim_photos(claim, files)` | Photos from the website or the token link attach to the claim; team and customer notified | — |
| `place_order(sku, qty, address)` | Catalog SKUs only; status *awaiting payment* | system |
| `request_callback(reason)` | Always allowed | — |

**Team queue (tickets).** Everything that needs a person — claim reviews, customer emails, call-back requests,
product/buying/info queries, order help — is a **ticket** in one queue visible to the whole internal team (5 seeded
employees, prototype sign-in). An employee *takes* a ticket (→ in progress), adds internal notes, *replies to the
customer* (SMS + email, remembered by chat and voice; → waiting on customer), decides the claim behind it, and
resolves it. Every step is a `ticket_events` row, so the history is complete and auditable; a customer reply from
chat or phone reopens the ticket. Customer-side rule: anything sent to the team, any order and any product-information
request needs the customer's mobile number (login on the web; the voice agent asks and reads it back).

**Customer identity and memory.** Questions never need a login. Any action needs one: the web UI signs in with a mobile
number + demo password (`1234`; an OTP/SSO in production) and sends a session token; the voice platform is trusted per
channel (the phone number *is* the identity). One `customer_memory` row per number — name, last conversation summary,
open items — is written after every action, every chat turn about the account and every call (webhook), and read by
both channels: the voice agent loads it at call start (`load_customer_context` on-start tool → greets by name, resumes
"your photos have arrived…"), and the chat answers "what is the status of my claim / what do I still need to send"
from it deterministically. Follow-ups (SMS + email, simulated in the outbox and shown under *My messages*) go out after
each call, claim, photo upload and human decision, so the customer can switch between phone and chat at will.

Every tool call writes an audit row (channel, caller, tool, rule applied, evidence cited). Decisions the rules do not
cover go to a human — the agent never invents policy. The internal console gets an **Inbox and actions** tab:
emails, call transcripts (Sarvam call logs), decisions taken, pending claims to approve or reject, audit log.

**As built (via the Sarvam Voice Agents MCP).** Agent `Kohler-Indi-73069449-a794` "Kohler India Care (prototype)",
voice `priya`, Hindi-first with language identification, committed v3; the seven tools above plus `end_interaction`
in its single state; inbound+outbound deployment `Kohler-Indi-a0c8d26f-5744` on **+91 79658 53481** with the
call-end webhook → `/voice/transcript`. The MCP creates tools with *static* parameters only, so the parameter type
(→ *LLM prompt*) is switched once in the dashboard — see `docs/VOICE_AGENT.md`. "Call me back" uses the Instant
Outbound REST API (`X-API-Key` platform key). The Sarvam API MCP (`uvx sarvam-mcp`) exposes STT/TTS/translate for
tests and demo audio.

**Voice latency path.** A phone tool call must finish in < 30 s, so `/voice/ask` runs `app.agent.voice_qa`: the same
hybrid retrieval with the customer filter (k = 5, rerank 12), then one `gpt-4.1-mini` call that writes a two-sentence
spoken answer preferring the newest document version (~8 s warm on CPU; models are pre-warmed at startup). The full
Router → Reasoner → Compiler chain stays for chat (`full: true` selects it).

**Sovereignty note.** The voice channel is customer-facing, so it only ever touches `public` documents and the
customer's own order record; restricted content is never in scope for a call.

---

## 6. User experience

- **Customer mode** (India): public chat, suggested prompts (warranty, refunds/shipping, water savings, BIS rating),
  downloads (Excel comparison, JSON), "draft an email to support" action. Region is India by default; other
  markets appear only when the user explicitly asks for a comparison.
- **Internal console**: one shared mode for the whole internal team (simulated SSO, no role picker), same chat,
  plus the 🔒 restricted-content badge, conflict banner with version diff, format selector (NL · JSON(+schema box) ·
  Excel · XML · Markdown · Email), conversation history.
- Shared: citation side-panel (document, version, page, excerpt, original/fictional tag), pipeline-stage progress
  strip with timings, ☁️ Cloud / 🔒 On-device badge with reason; **light / dark / system theme** toggle in the top
  bar (shadcn theming, remembered per browser).
- Customer mode adds the **"Help with my product"** panel (order lookup → need → Email the team / Talk to us).
- Internal mode adds the **Inbox and actions** tab (emails, call transcripts, decisions, pending approvals, audit log).

---

## 7. Evaluation

50 questions (10 per KB) + 10 cross-domain + 10 adversarial, each with expected sources, expected verdicts and persona.

| Metric | Method | Target | Result (56-question run, CPU) |
|---|---|---|---|
| Retrieval hit@5 | Expected doc appears in top-5 after rerank | ≥ 0.85 | **1.00** (49) |
| Faithfulness | LLM-judge: every claim supported by cited excerpt | ≥ 0.90 | **0.97** (43) |
| Answer hit | Expected fact present in the answer | — | 0.98 (42) |
| Routing | Cloud vs on-device as expected by the sensitivity of the evidence | — | 0.98 (49) |
| JSON schema validity | Pydantic validation pass rate (first try / after repair) | 100% after repair | **1.00** |
| Contradiction detection | Recall on the planted + real conflict pairs | recall 1.0 | 0.86 → **1.00** after the "strong-evidence" surfacing fix (targeted re-run 8/8) |
| Access control | 0 internal/restricted chunks retrieved for the Customer persona | 0 | **0** (20 customer questions) |
| **Leak test** | 0 restricted chunks in any OpenAI request (audit log) | 0 | **0** across 452 audited calls incl. voice and ticket policy checks |
| Latency | p50 / p95 end-to-end | report | cloud answers 13–25 s (router 2 s · retrieval 6 s · reasoner 4–12 s); format conversions 2–4 s; on-device answers 90–135 s (qwen3:4b on CPU) |

Full run: 51/56; the five misses were fixed deterministically (draft-email guard, conflict surfacing, router single-domain rule) or relaxed
(local routing legitimately triggered by restricted evidence) and re-ran green. Reasoner switched to `gpt-5-mini` (reasoning effort low)
after `gpt-4.1` misread the flattened IN12-B warranty table (generic 3-year electronics row vs the Intelligent-Toilet 5-year row).

---|---|---|
| Retrieval hit@5 | Expected doc appears in top-5 after rerank | ≥ 0.85 |
| Faithfulness | LLM-judge: every claim supported by cited excerpt | ≥ 0.90 |
| Answer relevance | LLM-judge 1–5 | ≥ 4.2 |
| Citation accuracy | Cited page contains the claim text (string/semantic match) | ≥ 0.85 |
| JSON schema validity | Pydantic validation pass rate (first try / after repair) | 100% after repair |
| Contradiction detection | Precision/recall on the 6 known conflict pairs | recall 1.0 |
| Access control | 0 internal/restricted chunks retrieved for the Customer persona across the test set | 0 |
| **Leak test** | 0 restricted chunks in any OpenAI request (audit log) | 0 |
| Latency | p50 / p95 end-to-end, per stage; cloud vs local | report |

---

## 8. Demo script (7 steps)

All steps run as India personas.
1. Employee: "What is our paternity leave entitlement?" → cited answer from India Leave Policy v2.0 (10 working
   days); conflict banner shows v1.0 (5 days) superseded; Handbook's global minimum shown as context only.
2. "Give me that as JSON matching this schema {…}" → validated JSON, no re-retrieval.
3. "Now an Excel summary" → download; "Draft an email to my manager requesting the leave" → ready-to-send email.
4. Employee: "Can I claim a ₹20,000 client dinner and does it comply with anti-bribery policy?" → Finance
   (India T&E Addendum v2.1) + Legal (Anti-Bribery Policy) synthesis; v1.4's ₹15,000 cap flagged superseded.
5. Internal team (Customer Care): "A customer's intelligent toilet electronics failed after 4 years — is it
   covered? Draft the reply." → real India Warranty IN12-B (5 years) with IN12-A (3 years) flagged superseded; internal escalation
   matrix used (🔒 on-device badge); email from the tone-guide template with the 1800-103-2244 line.
6. Customer: "Compare water use of Cimarron, Highline and Wellworth in litres and show yearly savings for a
   family of four" → Excel with real spec-sheet figures (4.8 / 6.0 / 4.8 lpf), savings formulas, litres first;
   follow-up "which of these carry a BIS star rating?" → certification register (illustrative) + standards matrix.
7. Internal team: "What's the FY26 salary band for a Grade 7 in Pune?" → 🔒 on-device answer (restricted
   evidence); switch to Customer and ask the same → no internal content retrieved, polite "not available", access
   note shows internal documents were withheld.
8. Customer: "Help with my product" → enters order KI-2025-0412 → *Claim warranty* → *Call me back* → the Sarvam
   agent calls, confirms the product (Hindi/English), checks eligibility via the backend, opens the claim; the
   internal Inbox shows the transcript and the auto-approved claim with its audit row.
Bonus (global documents): "Does Kohler still require ISO/TS 16949 from suppliers?" → Supplier Quality Manual
Rev 5.0 answer, Rev 2.0 flagged superseded (real revisions). Internal: "Is our India privacy policy DPDP-ready?" →
real policy (IT Act framing) + DPDP Readiness Note → `review_recommended`.

---

## 9. Out of scope (v1)
Real SSO, multi-tenant deployment, fine-tuning, voice, document upload by end-users, full RAGAS suite,
public hosting of the demo.

---

## 10. Build order (12 working days)
| Day | Deliverable |
|---|---|
| 1 | `AnswerIR` + config + ingestion (parse → chunk → embed → Qdrant) for all 90 docs |
| 2 | Retrieval service: hybrid + rerank + persona filters; retrieval eval |
| 3–4 | LangGraph: router → retrieval → gate → reasoner → IR; FastAPI SSE; NL answers with citations |
| 5 | Compiler: JSON(schema)/Excel/XML/Markdown/email; multi-turn IR reuse |
| 6 | Contradiction detector; cross-domain planner; access notes; standards normalisation tool |
| 7–8 | React UI (both modes), citation panel, badges, downloads, stage streaming |
| 9 | Eval harness + leak test; README results table; latency tuning (local model choice) |
| 10 | Demo rehearsal, architecture diagram, polish, buffer |
| 11 | Actions layer: `crm.db` + seeded orders, guarded tools, audit log, "Help with my product" panel, email → Inbox; light/dark theme |
| 12 | Sarvam voice agent via MCP: prompt, API tools over tunnel, attach number, test calls, Instant Outbound "call me back"; Inbox transcripts |
