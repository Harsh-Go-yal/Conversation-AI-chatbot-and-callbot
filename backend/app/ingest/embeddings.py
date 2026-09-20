"""Embedding clients. Dense = BGE-M3 (1024-d) via an Ollama-compatible server (laptop or RunPod GPU) or via
fastembed ONNX on CPU; sparse = BM25 via fastembed (always local, cheap); reranker = fastembed cross-encoder.
Selected by settings; the retrieval code only sees `embed_dense`, `embed_sparse`, `rerank`.
"""
from __future__ import annotations

import json
import threading
import urllib.request
from functools import lru_cache

import numpy as np

from app.config import settings


# ───────────────────────── dense ─────────────────────────
class OllamaDense:
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def embed(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            body = json.dumps({"model": self.model, "input": texts[i:i + batch_size]}).encode()
            req = urllib.request.Request(f"{self.base_url}/api/embed", data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=600) as r:
                out.extend(json.load(r)["embeddings"])
        return out


class FastembedDense:
    def __init__(self, model: str):
        from fastembed import TextEmbedding
        from fastembed.common.model_description import ModelSource, PoolingType
        already = any(d.model == "BAAI/bge-m3" for d in TextEmbedding._list_supported_models()) if hasattr(TextEmbedding, "_list_supported_models") else False
        if model == "BAAI/bge-m3" and not already:
            TextEmbedding.add_custom_model(model="BAAI/bge-m3", pooling=PoolingType.CLS, normalization=True,
                                           sources=ModelSource(hf="BAAI/bge-m3"), dim=1024,
                                           model_file="onnx/model.onnx", size_in_gb=2.3)
        self.m = TextEmbedding(model, cache_dir=settings.fastembed_cache, threads=10)

    def embed(self, texts: list[str], batch_size: int = 16) -> list[list[float]]:
        return [v.tolist() for v in self.m.embed(texts, batch_size=batch_size)]


_LOAD_LOCK = threading.Lock()  # model construction is not thread-safe (custom-model registration + ONNX session)


@lru_cache(maxsize=1)
def _dense_client_locked():
    if settings.embed_backend == "fastembed":
        return FastembedDense("BAAI/bge-m3" if settings.embed_model in ("bge-m3", "BAAI/bge-m3") else settings.embed_model)
    return OllamaDense(settings.embed_base_url(), settings.embed_model)


def dense_client():
    with _LOAD_LOCK:
        return _dense_client_locked()


def embed_dense(texts: list[str]) -> list[list[float]]:
    return dense_client().embed(texts)


# ───────────────────────── sparse (BM25) ─────────────────────────
@lru_cache(maxsize=1)
def sparse_client():
    from fastembed import SparseTextEmbedding
    return SparseTextEmbedding(settings.sparse_model, cache_dir=settings.fastembed_cache)


def embed_sparse(texts: list[str]) -> list[dict]:
    """Returns [{'indices': [...], 'values': [...]}] in Qdrant sparse-vector form."""
    return [{"indices": e.indices.tolist(), "values": e.values.tolist()} for e in sparse_client().embed(texts)]


def embed_sparse_query(text: str) -> dict:
    e = next(sparse_client().query_embed(text))
    return {"indices": e.indices.tolist(), "values": e.values.tolist()}


# ───────────────────────── rerank ─────────────────────────
@lru_cache(maxsize=1)
def reranker():
    from fastembed.rerank.cross_encoder import TextCrossEncoder
    return TextCrossEncoder(settings.rerank_model, cache_dir=settings.fastembed_cache)


def rerank(query: str, docs: list[str]) -> list[float]:
    return [float(s) for s in reranker().rerank(query, docs)]


def cosine(a: list[float], b: list[float]) -> float:
    a, b = np.asarray(a), np.asarray(b)
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))
