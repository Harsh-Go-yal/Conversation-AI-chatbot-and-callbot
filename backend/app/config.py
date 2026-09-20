"""Central settings — everything comes from `.env` (never committed) with safe defaults for a laptop-only run."""
from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", env_file_encoding="utf-8", extra="ignore")

    # ── keys ──
    openai_api_key: str = ""
    sarvam_api_key: str = ""
    sarvam_agent_id: str = ""        # Sarvam Voice Agents app id (set after the agent is deployed)
    sarvam_phone_number: str = ""    # number the agent answers on / dials from, E.164
    sarvam_deployment_id: str = ""
    sarvam_voice_api_key: str = ""   # Voice Agents platform key (dashboard → Settings → API Key); not the subscription key
    sarvam_org_id: str = ""
    sarvam_workspace_id: str = ""
    sarvam_connection_id: str = ""   # telephony connection the number belongs to
    sarvam_agent_version: int = 0    # committed version to dial with (0 = latest deployed)
    public_base_url: str = ""
    customer_demo_password: str = "1234"  # prototype login: any mobile number + this password (replace with OTP/SSO)
    voice_tool_key: str = ""              # optional shared secret the voice platform sends as X-Voice-Key        # tunnel URL the voice platform calls back into (cloudflared)
    runpod_api_key: str = ""

    # ── cloud LLM (router + non-restricted reasoning) ──
    router_provider: str = "openai"  # openai | local — where the intent router runs
    router_model: str = "gpt-5-mini"
    reasoner_model: str = "gpt-4.1"          # gpt-5 gives slightly richer answers but ~5x slower; switch via .env
    reasoner_fallback_model: str = "gpt-4.1-mini"

    # ── self-hosted LLM (restricted reasoning). Local laptop Ollama by default; a RunPod Ollama URL when set ──
    ollama_url: str = "http://localhost:11434"
    local_llm_url: str = ""  # e.g. https://<pod>-11434.proxy.runpod.net ; falls back to ollama_url when empty
    local_model: str = "qwen3:4b"
    local_model_fallback: str = "ministral-3:8b"
    local_max_chunks: int = 4        # CPU model: cap evidence to keep prompt processing fast
    local_chunk_chars: int = 800
    local_max_tokens: int = 700      # hard cap on local-model output so a verbose answer cannot run for minutes

    # ── embeddings: "ollama" (bge-m3 via Ollama, local or RunPod) | "fastembed" (ONNX on CPU) ──
    embed_backend: str = "ollama"
    embed_model: str = "bge-m3"
    embed_url: str = ""  # Ollama-compatible /api/embed base URL; falls back to local_llm_url, then ollama_url
    embed_dim: int = 1024

    # ── sparse + rerank (fastembed, CPU) ──
    sparse_model: str = "Qdrant/bm25"
    rerank_model: str = "BAAI/bge-reranker-base"  # best quality/speed on CPU among fastembed rerankers (MiniLM is faster but buries table rows)
    rerank_chars: int = 700                       # candidate text passed to the cross-encoder
    phrase_boost: float = 0.6                      # added when a 2-3 word phrase from the query appears verbatim in the chunk
    fastembed_cache: str = str(ROOT / ".fastembed_cache")

    # ── vector store ──
    qdrant_url: str = "http://localhost:6343"
    qdrant_collection: str = "kohler_kb"

    # ── corpus ──
    raw_dir: Path = ROOT / "data" / "raw"
    sources_yaml: Path = ROOT / "data" / "sources.yaml"
    synthetic_manifest: Path = ROOT / "data" / "synthetic_manifest.yaml"

    # ── chunking ──
    chunk_target_tokens: int = 320
    chunk_max_tokens: int = 480
    chunk_overlap_tokens: int = 50
    chunk_min_merge_tokens: int = 120   # keep merging small sections until a chunk reaches this size
    chunk_rows_max_tokens: int = 450    # table_rows chunks: header + as many rows as fit

    # ── retrieval ──
    region_boost: float = 0.15  # added to rerank score for region == IN (India overrides global)
    top_k: int = 8
    rerank_n: int = 16
    domain_soft: bool = True        # router domains act as a rerank boost (robust to router misses) instead of a hard filter
    domain_boost: float = 1.0
    evidence_margin: float = 5.0   # drop chunks scoring this far below the top reranked chunk
    evidence_min: int = 3

    def embed_base_url(self) -> str:
        return self.embed_url or self.local_llm_url or self.ollama_url

    def local_llm_base_url(self) -> str:
        return self.local_llm_url or self.ollama_url


settings = Settings()
