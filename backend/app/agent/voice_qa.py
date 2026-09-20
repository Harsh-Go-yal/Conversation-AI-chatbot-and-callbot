"""Low-latency answer path for the voice agent.

A phone caller cannot wait for the full Router → Reasoner → Compiler chain (~12 s warm) and the Sarvam tool timeout
is 30 s, so the voice tool takes a shortcut that keeps the safety properties and drops the rest:
  * same hybrid retrieval with the *customer* persona filter (public-only) — nothing internal can be fetched;
  * no router call (the caller is always a customer asking about products / warranty / policies);
  * one small cloud call that writes a 1–2 sentence spoken answer, preferring the newest document version;
  * still audited (purpose="voice_qa") so the leak test covers voice traffic too.
The full pipeline (contradiction detector, AnswerIR, formats) stays for the chat UI.
"""
from __future__ import annotations

import time

from pydantic import BaseModel, Field

from app.agent.reasoner import _evidence_block
from app.config import settings
from app.llm.clients import openai_client
from app.models.ir import Persona
from app.retrieval.search import hybrid_search

SYSTEM = (
    "You are Kohler India's customer-care assistant answering on a phone call. Use ONLY the evidence given. "
    "Write a spoken answer of at most two short sentences in plain English (numbers in words are fine), no markdown, "
    "no citations in the text. If two documents disagree, follow the one with the newer version / effective date and "
    "say 'as per the current policy'. If the evidence does not answer the question, say so and suggest the caller ask "
    "for a call-back. Never mention internal documents."
)


class VoiceAnswer(BaseModel):
    answer: str = Field(description="At most two short spoken sentences")
    used_chunks: list[str] = Field(default_factory=list, description="chunk ids (k1..kn) the answer relies on")
    answered: bool = Field(description="false if the evidence did not contain the answer")


def voice_answer(question: str, k: int = 5) -> dict:
    t = time.time()
    chunks, stats = hybrid_search(question, Persona.customer, None, k=k, rerank_n=12)
    t_ret = int((time.time() - t) * 1000)
    if not chunks:
        return {"answer": "I could not find that in Kohler India's public information. I can ask the team to call you back.",
                "sources": "", "answered": False, "timings_ms": {"retrieval": t_ret, "llm": 0}}
    t = time.time()
    user = f"Question: {question}\n\nEVIDENCE:\n{_evidence_block(chunks, 1200, question)}\n\nReturn the structured answer."
    out = openai_client().complete_json(settings.reasoner_fallback_model, SYSTEM, user, VoiceAnswer, purpose="voice_qa",
                                        chunk_ids=[c.id for c in chunks],
                                        sensitivities=[str(getattr(c.meta.sensitivity, "value", c.meta.sensitivity)) for c in chunks])
    t_llm = int((time.time() - t) * 1000)
    used = {int(x[1:]) for x in out.used_chunks if x.startswith("k") and x[1:].isdigit()}
    cited = [chunks[i - 1] for i in sorted(used) if 0 < i <= len(chunks)] or chunks[:2]
    sources = "; ".join(sorted({c.meta.title + (f" v{c.meta.version}" if c.meta.version else "") for c in cited}))[:300]
    return {"answer": out.answer, "sources": sources, "answered": out.answered, "timings_ms": {"retrieval": t_ret, "llm": t_llm}}
