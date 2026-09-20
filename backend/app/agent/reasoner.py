"""Reasoner — builds the AnswerIR from evidence. Runs on OpenAI unless any evidence chunk is `restricted`, in which
case it runs on the self-hosted model (sensitivity gate). Citations are mapped by chunk id in code, so the model
cannot invent a source."""
from __future__ import annotations

import re

from app.agent.conflicts import ConflictCandidate
from app.config import settings
from app.llm.clients import local_client, openai_client
from app.models.ir import (AccessNote, AnswerIR, Claim, Conflict, ConflictVerdict, Domain, Entities, Intent, OutputFormat,
                           Persona, ReasonerOutput, Region, RetrievedChunk, RoutingInfo, Source)

SYSTEM = """You are Kohler India's enterprise assistant. Answer ONLY from the evidence chunks provided. Every claim must
cite the chunk ids it comes from. If the evidence does not answer the question, say so in the summary and return no
claims rather than guessing.

Rules:
- India-specific documents (region IN) take precedence over global documents on the same topic; global documents
  fill gaps. Say which applied when both are present.
- If a "superseded version" pair is listed, base the answer on the NEWER version and explain the difference in
  conflict_explanations (verdict superseded). Never call anything "non-compliant"; use "superseded" or
  "review recommended".
- Quote numbers, durations, thresholds and product figures exactly as written (₹ with Indian grouping, litres first
  with gallons in brackets where both exist).
- Warranty / rate tables: pick the row whose sub-category names the product asked about (e.g. "Intelligent Toilet*
  — Mechanical, Electronics & Electrical Components: 5 Years / 1 Year") and quote THAT row; a generic component row
  (e.g. "Electronics & Electrical Components – Steam Generator & Electronic Bidet seat: 3 Years") belongs to the
  products it names, not to the product asked about. When a product has a footnoted/specific row and a generic row,
  the specific row applies and the answer must not present the generic figure as the product's figure.
- summary: 2–4 sentences, plain language, with inline citations like [k3] using the chunk ids.
- claims: 3–8 atomic statements, each with chunk ids in source_ids (use the chunk ids exactly as given).
- used_chunk_ids: only chunks you actually relied on.
- Do not mention internal documents to a customer persona beyond what the evidence shows.
- Fictional documents are marked origin=synthetic; treat them as authoritative company policy for this exercise."""


SYSTEM_LOCAL = """You are Kohler India's internal assistant. Answer ONLY from the evidence chunks. Cite chunk ids like [k1] in the
summary and put them in each claim's source_ids. Quote numbers exactly (₹ with Indian grouping). If the evidence does
not answer the question, say so. Return the structured answer."""


def _evidence_block(chunks: list[RetrievedChunk], limit: int = 1800, query: str = "") -> str:
    from app.retrieval.search import _query_tokens, focus_table_rows
    toks = _query_tokens(query) if query else []
    parts = []
    for i, c in enumerate(chunks, 1):
        m = c.meta
        hdr = (f"[k{i}] doc={m.title} | region={m.region} | sensitivity={m.sensitivity} | origin={m.origin}"
               + (f" | version={m.version}" if m.version else "") + (f" | effective={m.effective_date}" if m.effective_date else "")
               + (f" | page={m.page}" if m.page else "") + (f" | section={m.section}" if m.section else ""))
        body = focus_table_rows(m.text, toks, limit) if (m.chunk_kind == "table_rows" and toks) else m.text.split("———\n", 1)[-1][:limit]
        parts.append(hdr + "\n" + body)
    return "\n\n".join(parts)


def _conflict_block(cands: list[ConflictCandidate]) -> str:
    if not cands:
        return ""
    lines = ["\nPRE-IDENTIFIED VERSION RELATIONSHIPS (explain each in conflict_explanations):"]
    for i, c in enumerate(cands, 1):
        lines.append(f"P{i}: {c.verdict.value} — OLDER: {c.older_label} → NEWER: {c.newer_label}. {c.system_reason}")
        if c.older_text:
            lines.append(f"  older excerpt: {c.older_text[:700]}")
        lines.append(f"  newer excerpt: {c.newer_text[:700]}")
    return "\n".join(lines)


def _excerpt(text: str, n: int = 380) -> str:
    body = text.split("———\n", 1)[-1]
    body = re.sub(r"\s+", " ", body).strip()
    return body[:n] + ("…" if len(body) > n else "")


def reason(query: str, chunks: list[RetrievedChunk], persona: Persona, domains: list[Domain], intent: Intent,
           requested_format: OutputFormat, conflicts: list[ConflictCandidate], withheld: int,
           timings: dict[str, int]) -> AnswerIR:
    restricted = [c for c in chunks if c.meta.sensitivity == "restricted"]
    use_local = bool(restricted)
    if use_local:  # CPU model: keep the prompt small — top chunks only, restricted ones first
        chunks = sorted(chunks, key=lambda c: (c.meta.sensitivity != "restricted", -(c.rerank_score or 0)))[: settings.local_max_chunks]
    chunk_ids = [c.id for c in chunks]
    sens = [c.meta.sensitivity.value if hasattr(c.meta.sensitivity, "value") else str(c.meta.sensitivity) for c in chunks]

    user = (f"Persona: {persona.value}\nQuestion: {query}\n\nEVIDENCE:\n{_evidence_block(chunks, settings.local_chunk_chars if use_local else 1800, query)}\n"
            f"{_conflict_block(conflicts)}\n\nReturn the structured answer.")
    if use_local:
        model = settings.local_model
        user += "\n(Keep it short: summary of at most 2 sentences and at most 4 claims.)"
        out: ReasonerOutput = local_client().complete_json(model, SYSTEM_LOCAL, user, ReasonerOutput, purpose="reasoner",
                                                           chunk_ids=chunk_ids, sensitivities=sens)
        routing = RoutingInfo(llm_used="local", model=model, restricted_chunks=len(restricted),
                              reason=f"{len(restricted)} restricted chunk(s) in evidence → reasoning kept on the self-hosted model")
    else:
        model = settings.reasoner_model
        out = openai_client().complete_json(model, SYSTEM, user, ReasonerOutput, purpose="reasoner",
                                            chunk_ids=chunk_ids, sensitivities=sens, reasoning="low")
        routing = RoutingInfo(llm_used="openai", model=model, restricted_chunks=0,
                              reason="no restricted evidence → cloud model")

    # ── map k-ids → Source objects (code-controlled citations) ──
    kmap = {f"k{i}": c for i, c in enumerate(chunks, 1)}
    used = [k for k in out.used_chunk_ids if k in kmap]
    for cl in out.claims:  # any cited id not declared as used still counts
        used += [k for k in cl.source_ids if k in kmap and k not in used]
    if not used:
        used = list(kmap)[:3]
    sid_of: dict[str, str] = {}
    sources: list[Source] = []
    for n, k in enumerate(used, 1):
        c = kmap[k]; m = c.meta
        sid = f"s{n}"; sid_of[k] = sid
        sources.append(Source(id=sid, chunk_id=c.id, doc_id=m.doc_id, title=m.title, domain=m.domain, region=m.region,
                              sensitivity=m.sensitivity, origin=m.origin, doc_code=m.doc_code, version=m.version,
                              effective_date=m.effective_date, policy_key=m.policy_key, page=m.page, section=m.section,
                              excerpt=_excerpt(m.text), source_path=m.source_path))
    claims = []
    for i, cl in enumerate(out.claims, 1):
        sids = [sid_of[k] for k in cl.source_ids if k in sid_of]
        claims.append(Claim(id=f"c{i}", text=cl.text, type=cl.type, confidence=cl.confidence, source_ids=sids or [sources[0].id] if sources else []))
    summary = out.summary
    for k, sid in sid_of.items():
        summary = re.sub(rf"\[{k}\]", f"[{sid}]", summary)
    summary = re.sub(r"\[k\d+\]", "", summary)

    # ── conflicts: system-identified pairs + LLM explanation ──
    ir_conflicts: list[Conflict] = []
    doc_sid = {}
    for s in sources:
        doc_sid.setdefault(s.doc_id, s.id)
    # docs behind the strongest evidence (top-3 by rerank score) count as "relied on" even if the model did not cite
    # them — a small local model often cites a single chunk, and a superseded warranty table must still be flagged
    strong = [c for c in sorted(chunks, key=lambda c: c.rerank_score or 0, reverse=True)[:3]]
    strong_doc = {c.meta.doc_id: c for c in strong}
    for i, cand in enumerate(conflicts):
        # only surface a version relationship when the answer actually relies on one of the two documents
        relied = (cand.older_doc_id in doc_sid or cand.newer_doc_id in doc_sid
                  or cand.older_doc_id in strong_doc or cand.newer_doc_id in strong_doc)
        if not relied:
            continue
        for did in (cand.older_doc_id, cand.newer_doc_id):  # make sure the banner can point at a real source
            if did not in doc_sid and did in strong_doc:
                c = strong_doc[did]; m = c.meta
                sid = f"s{len(sources) + 1}"
                sources.append(Source(id=sid, chunk_id=c.id, doc_id=m.doc_id, title=m.title, domain=m.domain, region=m.region,
                                      sensitivity=m.sensitivity, origin=m.origin, doc_code=m.doc_code, version=m.version,
                                      effective_date=m.effective_date, policy_key=m.policy_key, page=m.page, section=m.section,
                                      excerpt=_excerpt(m.text), source_path=m.source_path))
                doc_sid[did] = sid
        expl = out.conflict_explanations[i] if i < len(out.conflict_explanations) else None
        a = doc_sid.get(cand.older_doc_id, f"doc:{cand.older_doc_id}")
        b = doc_sid.get(cand.newer_doc_id, f"doc:{cand.newer_doc_id}")
        ir_conflicts.append(Conflict(
            source_a=a, source_b=b, verdict=cand.verdict,
            resolution=(expl.resolution if expl else f"The answer follows {cand.newer_label}."),
            reason=(expl.reason if expl else cand.system_reason)))

    notes: list[AccessNote] = []
    if persona == Persona.customer and withheld:
        notes.append(AccessNote(kind="withheld_internal", count=withheld,
                                message=f"{withheld} internal document section(s) relate to this question but are not available to external customers."))
    if not chunks:
        notes.append(AccessNote(kind="no_evidence", message="No matching documents were found for this question."))

    routing.stage_timings_ms = timings
    return AnswerIR(query=query, intent=intent, persona=persona, region=Region.IN, domains=domains,
                    requested_format=requested_format, claims=claims, entities=out.entities, sources=sources,
                    conflicts=ir_conflicts, access_notes=notes, summary=summary.strip(), routing=routing)
