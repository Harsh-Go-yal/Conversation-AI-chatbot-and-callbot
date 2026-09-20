"""Chunking strategy (adapted from the SecureGPT-v2 approach).

Three chunk kinds:
  prose       — section-based text, merged up to ~target tokens, never across pages
  table_card  — one summary chunk per table/sheet: title, columns, row count, sample rows (answers "which document
                has the table about X" and gives the reasoner the table's shape)
  table_rows  — the table body in row groups of ≤ rows_max_tokens, header repeated, "rows i–j of N" in the header

Every chunk starts with a context header so the embedding/BM25 see where the text lives:
    <kb>/<region> › <title> (<doc_code>, v<version>, effective <date>) › <section>
    ———
    <body>
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import tiktoken

from app.config import settings
from app.ingest.parsers import Block

_enc = tiktoken.get_encoding("cl100k_base")


def ntok(t: str) -> int:
    return len(_enc.encode(t))


@dataclass
class DocContext:
    title: str
    domain: str
    region: str
    doc_code: str | None = None
    version: str | None = None
    effective_date: str | None = None

    def header(self, section: str | None, extra: str | None = None) -> str:
        meta = ", ".join(x for x in [self.doc_code, f"v{self.version}" if self.version else None,
                                     f"effective {self.effective_date}" if self.effective_date else None] if x)
        h = f"{self.domain}/{self.region} › {self.title}" + (f" ({meta})" if meta else "")
        if section and section.strip() and section.strip() != self.title:
            h += f" › {section.strip()}"
        if extra:
            h += f" ({extra})"
        return h + "\n———\n"


@dataclass
class Chunk:
    text: str
    page: int | None
    section: str | None
    index: int
    kind: str = "prose"  # prose | table_card | table_rows
    meta: dict = field(default_factory=dict)


_SENT_RE = re.compile(r"(?<=[.!?;])\s+(?=[A-Z0-9₹(\[•])")


def _split_long(text: str, target: int, max_: int, overlap: int) -> list[str]:
    if ntok(text) <= max_:
        return [text]
    sents = _SENT_RE.split(text)
    out, cur = [], ""
    for s in sents:
        if cur and ntok(cur) + ntok(s) > target:
            out.append(cur.strip())
            tail = _enc.decode(_enc.encode(cur)[-overlap:]) if overlap else ""
            cur = (tail + " " + s).strip()
        else:
            cur = (cur + " " + s).strip()
    if cur:
        out.append(cur.strip())
    final = []
    for o in out:
        toks = _enc.encode(o)
        for i in range(0, len(toks), max_):
            final.append(_enc.decode(toks[i:i + max_]))
    return final


def _table_chunks(b: Block, ctx: DocContext, start_index: int) -> list[Chunk]:
    t = b.table
    cols = [c for c in t["columns"]]
    rows = t["rows"]
    title = t.get("title") or b.section or "Table"
    out: list[Chunk] = []
    # card
    sample = rows[:3]
    card = (f"Table: {title}\nColumns ({len(cols)}): " + ", ".join(cols) + f"\nRows: {len(rows)}\nSample rows:\n"
            + "\n".join(" | ".join(f"{c}: {v}" for c, v in zip(cols, r) if v) for r in sample))
    out.append(Chunk(ctx.header(b.section) + card, b.page, b.section, start_index + len(out), "table_card",
                     {"table_title": title, "n_rows": len(rows)}))
    # row groups
    row_lines = [" | ".join(f"{c}: {v}" for c, v in zip(cols, r) if c and v not in (None, "")) for r in rows]
    row_lines = [l for l in row_lines if l]
    i = 0
    while i < len(row_lines):
        j = i
        body = f"Table: {title}\nColumns: " + ", ".join(cols) + "\n"
        while j < len(row_lines) and ntok(body + row_lines[j]) <= settings.chunk_rows_max_tokens:
            body += row_lines[j] + "\n"
            j += 1
        if j == i:  # single giant row
            body += row_lines[j][: settings.chunk_rows_max_tokens * 3] + "\n"
            j += 1
        extra = f"rows {i + 1}–{j} of {len(row_lines)}"
        out.append(Chunk(ctx.header(b.section, extra) + body.strip(), b.page, b.section, start_index + len(out),
                         "table_rows", {"table_title": title, "row_start": i + 1, "row_end": j, "n_rows": len(row_lines)}))
        i = j
    return out


def chunk_blocks(blocks: list[Block], ctx: DocContext) -> list[Chunk]:
    target, max_, overlap = settings.chunk_target_tokens, settings.chunk_max_tokens, settings.chunk_overlap_tokens
    min_merge = settings.chunk_min_merge_tokens
    chunks: list[Chunk] = []
    buf: list[Block] = []

    def flush():
        if not buf:
            return
        sec, page = buf[0].section, buf[0].page
        text = "\n\n".join(b.text for b in buf)
        for piece in _split_long(text, target, max_, overlap):
            chunks.append(Chunk(ctx.header(sec) + piece, page, sec, len(chunks), "prose"))
        buf.clear()

    for b in blocks:
        if b.table:
            flush()
            chunks.extend(_table_chunks(b, ctx, len(chunks)))
            continue
        cur_tok = ntok("\n\n".join(x.text for x in buf)) if buf else 0
        page_break = buf and b.page != buf[0].page
        section_break = buf and b.section != buf[0].section and cur_tok >= min_merge
        if buf and (page_break or section_break or cur_tok + ntok(b.text) > target):
            flush()
        buf.append(b)
    flush()
    return chunks
