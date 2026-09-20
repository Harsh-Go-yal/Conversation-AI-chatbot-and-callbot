"""LLM clients: OpenAI (cloud) and Ollama (self-hosted). Both expose the same two calls:
  complete_json(system, user, schema) -> dict validated against a Pydantic model
  complete_text(system, user)         -> str  (streamed token callback optional)
The audit log records every call with which provider saw which chunk ids, feeding the leak test.
"""
from __future__ import annotations

import json
import time
import urllib.request
from typing import Callable, Iterator, Type, TypeVar

from openai import OpenAI
from pydantic import BaseModel, ValidationError

from app.config import settings

T = TypeVar("T", bound=BaseModel)

AUDIT: list[dict] = []  # in-memory routing audit; also appended to logs/routing_audit.jsonl


def _audit(provider: str, model: str, purpose: str, chunk_ids: list[str] | None, sensitivities: list[str] | None, ms: int):
    rec = {"ts": time.time(), "provider": provider, "model": model, "purpose": purpose,
           "chunk_ids": chunk_ids or [], "sensitivities": sorted(set(sensitivities or [])), "ms": ms}
    AUDIT.append(rec)
    try:
        (settings.raw_dir.parents[1] / "logs" / "routing_audit.jsonl").open("a", encoding="utf-8").write(json.dumps(rec) + "\n")
    except Exception:
        pass


# ───────────────────────── OpenAI ─────────────────────────
class OpenAIClient:
    provider = "openai"

    def __init__(self):
        self._c = OpenAI(api_key=settings.openai_api_key)

    def _is_gpt5(self, model: str) -> bool:
        return model.startswith("gpt-5")

    def complete_json(self, model: str, system: str, user: str, schema: Type[T], purpose: str = "",
                      chunk_ids=None, sensitivities=None, reasoning: str = "minimal") -> T:
        t = time.time()
        kwargs = dict(model=model, input=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                      text_format=schema)
        if self._is_gpt5(model):
            kwargs["reasoning"] = {"effort": reasoning}
        try:
            r = self._c.responses.parse(**kwargs)
            out = r.output_parsed
        except Exception as e:  # fall back to the non-reasoning model on any API/schema failure
            if model != settings.reasoner_fallback_model:
                r = self._c.responses.parse(model=settings.reasoner_fallback_model, input=kwargs["input"], text_format=schema)
                out = r.output_parsed
                model = settings.reasoner_fallback_model
            else:
                raise e
        _audit(self.provider, model, purpose, chunk_ids, sensitivities, int((time.time() - t) * 1000))
        return out

    def complete_text(self, model: str, system: str, user: str, purpose: str = "", chunk_ids=None, sensitivities=None,
                      on_token: Callable[[str], None] | None = None, reasoning: str = "minimal") -> str:
        t = time.time()
        kwargs = dict(model=model, input=[{"role": "system", "content": system}, {"role": "user", "content": user}])
        if self._is_gpt5(model):
            kwargs["reasoning"] = {"effort": reasoning}
        text = ""
        if on_token:
            with self._c.responses.stream(**kwargs) as stream:
                for ev in stream:
                    if ev.type == "response.output_text.delta":
                        text += ev.delta
                        on_token(ev.delta)
        else:
            text = self._c.responses.create(**kwargs).output_text
        _audit(self.provider, model, purpose, chunk_ids, sensitivities, int((time.time() - t) * 1000))
        return text


# ───────────────────────── Ollama (self-hosted) ─────────────────────────
class OllamaClient:
    provider = "local"

    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or settings.local_llm_base_url()).rstrip("/")

    def _post(self, path: str, body: dict, stream: bool = False):
        req = urllib.request.Request(f"{self.base_url}{path}", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        return urllib.request.urlopen(req, timeout=900)

    def complete_json(self, model: str, system: str, user: str, schema: Type[T], purpose: str = "",
                      chunk_ids=None, sensitivities=None, **_) -> T:
        t = time.time()
        body = {"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "format": schema.model_json_schema(), "stream": False, "think": False,
                "options": {"temperature": 0.1, "num_ctx": 8192, "num_predict": settings.local_max_tokens}}
        with self._post("/api/chat", body) as r:
            content = json.load(r)["message"]["content"]
        try:
            out = schema.model_validate_json(content)
        except ValidationError:
            # one repair attempt: ask the model to fix its own JSON
            body["messages"].append({"role": "assistant", "content": content})
            body["messages"].append({"role": "user", "content": "That JSON did not validate. Return only corrected JSON matching the schema."})
            with self._post("/api/chat", body) as r:
                out = schema.model_validate_json(json.load(r)["message"]["content"])
        _audit(self.provider, model, purpose, chunk_ids, sensitivities, int((time.time() - t) * 1000))
        return out

    def complete_text(self, model: str, system: str, user: str, purpose: str = "", chunk_ids=None, sensitivities=None,
                      on_token: Callable[[str], None] | None = None, **_) -> str:
        t = time.time()
        body = {"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "stream": bool(on_token), "think": False, "options": {"temperature": 0.2, "num_ctx": 8192, "num_predict": settings.local_max_tokens}}
        text = ""
        with self._post("/api/chat", body) as r:
            if on_token:
                for line in r:
                    d = json.loads(line)
                    tok = d.get("message", {}).get("content", "")
                    if tok:
                        text += tok
                        on_token(tok)
                    if d.get("done"):
                        break
            else:
                text = json.load(r)["message"]["content"]
        _audit(self.provider, model, purpose, chunk_ids, sensitivities, int((time.time() - t) * 1000))
        return text


_openai: OpenAIClient | None = None
_local: OllamaClient | None = None


def openai_client() -> OpenAIClient:
    global _openai
    if _openai is None:
        _openai = OpenAIClient()
    return _openai


def local_client() -> OllamaClient:
    global _local
    if _local is None:
        _local = OllamaClient()
    return _local
