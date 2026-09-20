"""AnswerIR — the structured, format-neutral answer produced by the reasoner and consumed by the compiler.

Users never see this object directly; the Response Compiler renders it as NL / JSON / Excel / XML / Markdown /
email. Sources attach at claim level so every rendering carries the same document/version/page citations.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Domain(str, Enum):
    hr = "hr"
    finance = "finance"
    legal = "legal"
    privacy = "privacy"
    support = "support"
    sustainability = "sustainability"


class Region(str, Enum):
    global_ = "global"
    IN = "IN"


class Sensitivity(str, Enum):
    public = "public"
    internal = "internal"
    restricted = "restricted"


class Persona(str, Enum):
    customer = "customer"
    internal = "internal"


class Intent(str, Enum):
    retrieval_question = "retrieval_question"
    format_conversion = "format_conversion"
    follow_up = "follow_up"
    action_request = "action_request"
    out_of_scope = "out_of_scope"


class OutputFormat(str, Enum):
    text = "text"
    json = "json"
    excel = "excel"
    xml = "xml"
    markdown_table = "markdown_table"
    email = "email"


class ClaimType(str, Enum):
    fact = "fact"
    policy = "policy"
    number = "number"
    recommendation = "recommendation"


class ConflictVerdict(str, Enum):
    superseded = "superseded"            # newer version of the same policy exists → prefer it
    review_recommended = "review_recommended"  # document predates newer guidance / regulation → flag, don't judge
    conflict = "conflict"                # two current documents disagree → surface both


# ───────────────────────── retrieval-side objects ─────────────────────────
class ChunkMeta(BaseModel):
    """Payload stored on every Qdrant point. Also the single source of truth for access control and routing."""
    doc_id: str
    title: str
    domain: Domain
    region: Region
    audience: Literal["public", "internal"]
    sensitivity: Sensitivity
    origin: Literal["original", "synthetic"]
    tags: list[str] = Field(default_factory=list)
    doc_code: str | None = None
    version: str | None = None
    effective_date: str | None = None  # ISO date
    policy_key: str | None = None
    supersedes: str | None = None
    source_path: str
    source_url: str | None = None
    page: int | None = None
    section: str | None = None
    chunk_index: int = 0
    chunk_kind: Literal["prose", "table_card", "table_rows"] = "prose"
    text: str


class RetrievedChunk(BaseModel):
    id: str
    score: float
    rerank_score: float | None = None
    meta: ChunkMeta


# ───────────────────────── AnswerIR ─────────────────────────
class Source(BaseModel):
    id: str = Field(description="Short citation id used inline, e.g. 's1'")
    chunk_id: str
    doc_id: str
    title: str
    domain: Domain
    region: Region
    sensitivity: Sensitivity
    origin: Literal["original", "synthetic"]
    doc_code: str | None = None
    version: str | None = None
    effective_date: str | None = None
    policy_key: str | None = None
    page: int | None = None
    section: str | None = None
    excerpt: str = Field(description="Verbatim excerpt (≤ 400 chars) supporting the claims that cite this source")
    source_path: str | None = None


class Claim(BaseModel):
    id: str = Field(description="c1, c2, …")
    text: str
    type: ClaimType = ClaimType.fact
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    source_ids: list[str] = Field(default_factory=list, description="Ids of Source entries supporting this claim")


class Entities(BaseModel):
    amounts: list[str] = Field(default_factory=list)      # "₹20,000", "5,000 INR"
    durations: list[str] = Field(default_factory=list)    # "10 working days", "5 years"
    dates: list[str] = Field(default_factory=list)
    products: list[str] = Field(default_factory=list)     # "Cimarron K-3609"
    roles: list[str] = Field(default_factory=list)
    thresholds: list[str] = Field(default_factory=list)   # "pre-approval above ₹10,000"
    standards: list[str] = Field(default_factory=list)    # "IS 17953", "WaterSense"


class Conflict(BaseModel):
    source_a: str = Field(description="Source id of the older / superseded / conflicting document")
    source_b: str = Field(description="Source id of the newer / preferred document")
    verdict: ConflictVerdict
    resolution: str = Field(description="One sentence: which document the answer follows and why")
    reason: str = Field(description="What differs, concretely (e.g. '5 days → 10 days paternity leave')")


class AccessNote(BaseModel):
    kind: Literal["withheld_internal", "withheld_restricted", "no_evidence", "region_override"]
    message: str
    count: int | None = None


class RoutingInfo(BaseModel):
    llm_used: Literal["openai", "local"]
    model: str
    reason: str
    restricted_chunks: int = 0
    stage_timings_ms: dict[str, int] = Field(default_factory=dict)


class AnswerIR(BaseModel):
    """The one object that flows from reasoner to compiler."""
    query: str
    intent: Intent = Intent.retrieval_question
    persona: Persona
    region: Region = Region.IN
    domains: list[Domain] = Field(default_factory=list)
    requested_format: OutputFormat = OutputFormat.text
    claims: list[Claim] = Field(default_factory=list)
    entities: Entities = Field(default_factory=Entities)
    sources: list[Source] = Field(default_factory=list)
    conflicts: list[Conflict] = Field(default_factory=list)
    access_notes: list[AccessNote] = Field(default_factory=list)
    summary: str = Field(default="", description="2–4 sentence natural-language answer with inline [s1] citations")
    routing: RoutingInfo | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # ── helpers used by the compiler ──
    def source_by_id(self, sid: str) -> Source | None:
        return next((s for s in self.sources if s.id == sid), None)

    def preferred_sources(self) -> list[Source]:
        """Sources not marked as superseded by a conflict."""
        superseded = {c.source_a for c in self.conflicts if c.verdict == ConflictVerdict.superseded}
        return [s for s in self.sources if s.id not in superseded]


# ───────────────────────── what the reasoner LLM is asked to emit ─────────────────────────
class ReasonerOutput(BaseModel):
    """Structured output schema for the reasoning LLM. Sources are referenced by chunk id and mapped to
    Source objects by code afterwards, so the model cannot invent citations."""
    claims: list[Claim]
    entities: Entities = Field(default_factory=Entities)
    summary: str
    used_chunk_ids: list[str] = Field(description="Chunk ids actually used as evidence; ids not in the evidence set are dropped")
    conflict_explanations: list[Conflict] = Field(default_factory=list,
                                                  description="Only for conflict pairs the system pre-identified")
