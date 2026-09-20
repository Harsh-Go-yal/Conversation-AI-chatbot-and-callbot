"""Hybrid retrieval with persona/region/domain filters, reranking and India-precedence boost.

Pipeline: dense (BGE-M3) + sparse (BM25) prefetch in Qdrant → RRF fusion → payload filters applied inside Qdrant
(so nothing unauthorised is ever fetched) → cross-encoder rerank of the top-N → IN-over-global boost → top-k.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from qdrant_client import models

from app.config import settings
from app.ingest import index
from app.ingest.embeddings import embed_dense, embed_sparse_query, rerank
from app.models.ir import ChunkMeta, Persona, RetrievedChunk

# persona → what may be retrieved. Internal team sees everything; customers only public.
PERSONA_AUDIENCE = {Persona.customer: ["public"], Persona.internal: ["public", "internal"]}
PERSONA_SENSITIVITY = {Persona.customer: ["public"], Persona.internal: ["public", "internal", "restricted"]}


@dataclass
class SearchStats:
    prefetch: int
    filtered_out_for_persona: int
    reranked: int
    ms: dict


def build_filter(persona: Persona, domains: list[str] | None, regions: list[str] | None = None,
                 doc_ids: list[str] | None = None) -> models.Filter:
    must = [
        models.FieldCondition(key="audience", match=models.MatchAny(any=PERSONA_AUDIENCE[persona])),
        models.FieldCondition(key="sensitivity", match=models.MatchAny(any=PERSONA_SENSITIVITY[persona])),
        models.FieldCondition(key="region", match=models.MatchAny(any=regions or ["IN", "global"])),
    ]
    if domains:
        must.append(models.FieldCondition(key="domain", match=models.MatchAny(any=domains)))
    if doc_ids:
        must.append(models.FieldCondition(key="doc_id", match=models.MatchAny(any=doc_ids)))
    return models.Filter(must=must)


def hybrid_search(query: str, persona: Persona, domains: list[str] | None = None, k: int = 8,
                  prefetch: int = 60, rerank_n: int = 20, regions: list[str] | None = None,
                  doc_ids: list[str] | None = None) -> tuple[list[RetrievedChunk], SearchStats]:
    ms = {}
    t = time.time()
    dense = embed_dense([query])[0]
    sparse = embed_sparse_query(query)
    ms["embed"] = int((time.time() - t) * 1000)

    flt = build_filter(persona, None if settings.domain_soft else domains, regions, doc_ids)
    t = time.time()
    c = index.client()
    res = c.query_points(
        collection_name=settings.qdrant_collection,
        prefetch=[
            models.Prefetch(query=dense, using=index.DENSE, limit=prefetch, filter=flt),
            models.Prefetch(query=models.SparseVector(**sparse), using=index.SPARSE, limit=prefetch, filter=flt),
        ],
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        limit=rerank_n,
        with_payload=True,
    )
    ms["qdrant"] = int((time.time() - t) * 1000)
    cands = [RetrievedChunk(id=str(p.id), score=float(p.score), meta=ChunkMeta(**p.payload)) for p in res.points]

    # how much would the customer persona have missed? (for access notes) — only computed for customers
    withheld = 0
    if persona == Persona.customer:
        t = time.time()
        res_all = c.query_points(
            collection_name=settings.qdrant_collection,
            prefetch=[models.Prefetch(query=dense, using=index.DENSE, limit=prefetch,
                                      filter=build_filter(Persona.internal, domains, regions))],
            query=models.FusionQuery(fusion=models.Fusion.RRF), limit=rerank_n, with_payload=["sensitivity"],
        )
        withheld = sum(1 for p in res_all.points if p.payload.get("sensitivity") != "public")
        ms["withheld_probe"] = int((time.time() - t) * 1000)

    if cands:
        t = time.time()
        toks = _query_tokens(query)
        scores = rerank(query, [_rerank_snippet(x, toks) for x in cands])
        phrases = _query_phrases(query)
        for x, s in zip(cands, scores):
            low = x.meta.text.lower()
            pb = settings.phrase_boost if any(ph in low for ph in phrases) else 0.0
            if x.meta.chunk_kind == "table_rows" and any(t in low for t in toks if len(t) >= 2):
                pb += settings.phrase_boost * 0.5  # a table row that literally contains a query identifier (G7, K-3609, IS 2556)
            db = settings.domain_boost if (domains and settings.domain_soft and x.meta.domain.value in domains) else 0.0
            x.rerank_score = s + (settings.region_boost if x.meta.region == "IN" else 0.0) + pb + db
        cands.sort(key=lambda x: x.rerank_score, reverse=True)
        ms["rerank"] = int((time.time() - t) * 1000)

    top = cands[:k]
    return top, SearchStats(prefetch=len(res.points), filtered_out_for_persona=withheld, reranked=len(cands), ms=ms)


_STOP = {"what", "is", "the", "a", "an", "of", "on", "in", "for", "to", "and", "or", "my", "our", "do", "does", "i", "how", "are", "can", "with", "from", "at", "by", "kohler", "india", "india?"}


_GRADE_RE = None


def _query_tokens(query: str) -> list[str]:
    """Identifier-like tokens from the query plus normalised variants: 'Grade 7' -> 'g7', 'K 3609' -> 'k-3609'."""
    import re as _re
    q = query.lower()
    toks = set(t for t in _re.findall(r"[a-z0-9][a-z0-9\-]+", q) if t not in _STOP and len(t) > 1)
    for m in _re.finditer(r"grade\s*(\d+)", q):
        toks.add(f"g{m.group(1)}")
    for m in _re.finditer(r"\bk[\s\-]?(\d{3,5})\b", q):
        toks.add(f"k-{m.group(1)}")
    for m in _re.finditer(r"\bis[\s\-]?(\d{3,5})\b", q):
        toks.add(f"is {m.group(1)}")
    return sorted(toks, key=len, reverse=True)


def focus_table_rows(text: str, toks: list[str], limit: int) -> str:
    """Body of a table_rows chunk with the rows that mention a query token moved to the front, then truncated —
    so a relevant row deep in the group survives any character limit (used by the reranker and the reasoner)."""
    body = text.split("———\n", 1)[-1]
    lines = body.splitlines()
    head, rows = lines[:2], lines[2:]

    def score(line: str) -> float:  # identifier-like tokens (g7, k-3609, is 2556, 2024) count 4x
        low = line.lower()
        return sum((4.0 if any(ch.isdigit() for ch in t) else 1.0) for t in toks if t in low)

    ranked = sorted(range(len(rows)), key=lambda i: (-score(rows[i]), i))
    return "\n".join(head + [rows[i] for i in ranked])[:limit]


def _rerank_snippet(x: RetrievedChunk, toks: list[str]) -> str:
    """Text shown to the cross-encoder. For table rows: header + the rows that mention a query token, so a relevant
    row deep in the group is not hidden by truncation."""
    parts = x.meta.text.split("———\n", 1)
    ctx = (parts[0].strip() + "\n") if len(parts) == 2 else ""  # document/section context line helps the cross-encoder
    body = parts[-1]
    if x.meta.chunk_kind == "table_rows":
        body = focus_table_rows(x.meta.text, toks, 100000)
    return (ctx + body)[: settings.rerank_chars]


def _query_phrases(query: str) -> list[str]:
    """2–3 word content phrases from the query (e.g. 'intelligent toilet', 'client dinner') for the verbatim boost."""
    import re as _re
    toks = [t for t in _re.findall(r"[a-z0-9][a-z0-9\-]+", query.lower()) if t not in _STOP and len(t) > 2]
    out = set()
    for i in range(len(toks) - 1):
        out.add(f"{toks[i]} {toks[i + 1]}")
    return sorted(out)


def fetch_doc_chunks(doc_id: str, limit: int = 200) -> list[ChunkMeta]:
    """All chunks of one document in order (used by the contradiction detector and citations)."""
    c = index.client()
    pts, _ = c.scroll(collection_name=settings.qdrant_collection,
                      scroll_filter=models.Filter(must=[models.FieldCondition(key="doc_id", match=models.MatchValue(value=doc_id))]),
                      limit=limit, with_payload=True)
    metas = [ChunkMeta(**p.payload) for p in pts]
    return sorted(metas, key=lambda m: m.chunk_index)


def sibling_versions(policy_key: str, persona: Persona) -> list[dict]:
    """Distinct (doc_id, version, effective_date) for a policy_key, respecting the persona filter."""
    c = index.client()
    flt = build_filter(persona, None)
    flt.must.append(models.FieldCondition(key="policy_key", match=models.MatchValue(value=policy_key)))
    pts, _ = c.scroll(collection_name=settings.qdrant_collection, scroll_filter=flt, limit=500,
                      with_payload=["doc_id", "version", "effective_date", "title", "supersedes"])
    seen = {}
    for p in pts:
        seen.setdefault(p.payload["doc_id"], p.payload)
    return list(seen.values())
