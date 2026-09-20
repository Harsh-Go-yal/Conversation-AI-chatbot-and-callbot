"""Ingest the whole corpus: catalog → parse → chunk → embed (dense + sparse) → Qdrant.

Usage (from backend/):
    python -m app.ingest.run                # incremental: skips docs whose content hash is already indexed
    python -m app.ingest.run --recreate     # drop and rebuild the collection
    python -m app.ingest.run --dry-run      # parse + chunk only; print stats, write chunks preview
    python -m app.ingest.run --only hr_in_leave_policy_v2
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

from qdrant_client import models

from app.config import settings
from app.ingest import index
from app.ingest.catalog import DocRecord, load_catalog
from app.ingest.chunker import DocContext, chunk_blocks, ntok
from app.ingest.embeddings import embed_dense, embed_sparse
from app.ingest.parsers import parse
from app.models.ir import ChunkMeta

STATE = settings.raw_dir / "_index_state.json"


def _ctx(d: DocRecord) -> DocContext:
    return DocContext(title=d.title, domain=d.domain, region=d.region, doc_code=d.doc_code, version=d.version, effective_date=d.effective_date)


def content_hash(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def build_points(doc: DocRecord) -> tuple[list[models.PointStruct], int]:
    blocks = parse(doc.parse_path, doc.parse_kind)
    chunks = chunk_blocks(blocks, _ctx(doc))
    if not chunks:
        return [], 0
    texts = [c.text for c in chunks]
    dense = embed_dense(texts)
    sparse = embed_sparse(texts)
    pts = []
    for c, dv, sv in zip(chunks, dense, sparse):
        meta = ChunkMeta(
            doc_id=doc.doc_id, title=doc.title, domain=doc.domain, region=doc.region, audience=doc.audience,
            sensitivity=doc.sensitivity, origin=doc.origin, tags=doc.tags, doc_code=doc.doc_code, version=doc.version,
            effective_date=doc.effective_date, policy_key=doc.policy_key, supersedes=doc.supersedes,
            source_path=str(doc.path.relative_to(settings.raw_dir)).replace("\\", "/"), source_url=doc.source_url,
            page=c.page, section=c.section, chunk_index=c.index, text=c.text, chunk_kind=c.kind,
        )
        pts.append(models.PointStruct(id=index.point_id(doc.doc_id, c.index),
                                      vector={index.DENSE: dv, index.SPARSE: models.SparseVector(**sv)},
                                      payload=meta.model_dump(mode="json")))
    return pts, sum(ntok(t) for t in texts)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--recreate", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", nargs="*", help="doc ids to (re)ingest")
    args = ap.parse_args()

    docs = load_catalog()
    # priority: fictional + India documents first (demo-critical), big global reports last
    docs.sort(key=lambda d: (d.origin != "synthetic", d.region != "IN", d.parse_path.stat().st_size))
    if args.only:
        docs = [d for d in docs if d.doc_id in set(args.only)]
    print(f"catalog: {len(docs)} documents | embed backend: {settings.embed_backend} @ {settings.embed_base_url() if settings.embed_backend == 'ollama' else 'cpu'}")

    if args.dry_run:
        total_chunks = total_tok = 0
        preview = []
        for d in docs:
            blocks = parse(d.parse_path, d.parse_kind)
            chunks = chunk_blocks(blocks, _ctx(d))
            toks = [ntok(c.text) for c in chunks]
            total_chunks += len(chunks); total_tok += sum(toks)
            kinds = {k: sum(1 for c in chunks if c.kind == k) for k in ("prose", "table_card", "table_rows")}
            print(f"  {len(chunks):4} chunks ({kinds['prose']}p/{kinds['table_card']}c/{kinds['table_rows']}r) {sum(toks):6} tok  max {max(toks) if toks else 0:4}  {d.doc_id}")
            preview += [{"doc_id": d.doc_id, "kind": c.kind, "page": c.page, "section": c.section, "tokens": ntok(c.text), "text": c.text[:400]} for c in chunks[:4]]
        (settings.raw_dir / "_chunks_preview.json").write_text(json.dumps(preview, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"\nTOTAL {total_chunks} chunks, {total_tok} tokens (avg {total_tok // max(total_chunks, 1)}); preview → data/raw/_chunks_preview.json")
        return 0

    index.ensure_collection(recreate=args.recreate)
    state = json.loads(STATE.read_text()) if STATE.exists() and not args.recreate else {}
    t0 = time.time()
    n_pts = 0
    for i, d in enumerate(docs, 1):
        h = content_hash(d.parse_path)
        if state.get(d.doc_id) == h and not args.only:
            continue
        t = time.time()
        index.delete_doc(d.doc_id)
        pts, toks = build_points(d)
        index.upsert(pts)
        state[d.doc_id] = h
        STATE.write_text(json.dumps(state, indent=1))
        n_pts += len(pts)
        print(f"[{i:2}/{len(docs)}] {len(pts):4} chunks {toks:6} tok {time.time() - t:5.1f}s  {d.doc_id}")
    print(f"\ndone: {n_pts} points upserted in {time.time() - t0:.0f}s; collection now holds {index.count()} points")
    return 0


if __name__ == "__main__":
    sys.exit(main())
