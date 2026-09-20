"""Qdrant collection management: one collection, named dense (1024-d cosine) + sparse (BM25) vectors, payload
indexes on the fields used for filtering (domain, region, audience, sensitivity, policy_key, doc_id)."""
from __future__ import annotations

import hashlib
import uuid

from qdrant_client import QdrantClient, models

from app.config import settings

DENSE = "dense"
SPARSE = "sparse"


def client() -> QdrantClient:
    return QdrantClient(url=settings.qdrant_url, timeout=120)


def ensure_collection(recreate: bool = False) -> None:
    c = client()
    name = settings.qdrant_collection
    exists = c.collection_exists(name)
    if exists and recreate:
        c.delete_collection(name)
        exists = False
    if not exists:
        c.create_collection(
            collection_name=name,
            vectors_config={DENSE: models.VectorParams(size=settings.embed_dim, distance=models.Distance.COSINE)},
            sparse_vectors_config={SPARSE: models.SparseVectorParams(modifier=models.Modifier.IDF)},
            optimizers_config=models.OptimizersConfigDiff(indexing_threshold=1000),
        )
        for field, ftype in [("domain", "keyword"), ("region", "keyword"), ("audience", "keyword"),
                             ("sensitivity", "keyword"), ("policy_key", "keyword"), ("doc_id", "keyword"),
                             ("origin", "keyword"), ("tags", "keyword"), ("page", "integer")]:
            c.create_payload_index(name, field_name=field, field_schema=ftype)


def point_id(doc_id: str, chunk_index: int) -> str:
    return str(uuid.UUID(hashlib.md5(f"{doc_id}#{chunk_index}".encode()).hexdigest()))


def delete_doc(doc_id: str) -> None:
    client().delete(collection_name=settings.qdrant_collection,
                    points_selector=models.FilterSelector(filter=models.Filter(must=[models.FieldCondition(key="doc_id", match=models.MatchValue(value=doc_id))])))


def upsert(points: list[models.PointStruct]) -> None:
    c = client()
    for i in range(0, len(points), 64):
        c.upsert(collection_name=settings.qdrant_collection, points=points[i:i + 64], wait=True)


def count() -> int:
    return client().count(settings.qdrant_collection, exact=True).count
