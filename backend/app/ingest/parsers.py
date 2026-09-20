"""Turn a document into a list of Blocks: (page, section, text). Page numbers are preserved for citations.

PDF  → PyMuPDF, page by page; heading detection from font size; tables kept as pipe-separated rows.
DOCX → paragraphs (headings from style names) + tables (one block per table, rows joined).
XLSX → each sheet → header row + one block per data row ("Sheet: Register | SKU: K-3609 | Product: …"), so a row
       is retrievable on its own; the README sheet becomes a description block.
MD   → split on headings; fenced comment lines (<!-- … -->) stripped; OCR page markers restore page numbers.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pymupdf
from docx import Document
from openpyxl import load_workbook

FICTION_BANNER_RE = re.compile(r"FICTIONAL DOCUMENT[^\n]*?invented\.?", re.I | re.S)
FICTION_SHORT_RE = re.compile(r"FICTIONAL\s+—\s+EDUCATIONAL PURPOSES ONLY\s+—\s+NOT REAL DATA", re.I)
NAV_JUNK_RE = re.compile(r"Select Language.*?(?=#|\n\n|$)", re.S)


@dataclass
class Block:
    text: str
    page: int | None = None
    section: str | None = None
    kind: str = "text"  # text | table
    table: dict | None = None  # {"title": str, "columns": [..], "rows": [[..], ..]} for table blocks


def _table_block(title: str, columns: list[str], rows: list[list[str]], page, section) -> Block:
    columns = [str(c).strip() if c is not None else "" for c in columns]
    rows = [[("" if v is None else str(v).strip().replace("\n", " ")) for v in r] for r in rows]
    rows = [r for r in rows if any(r)]
    preview = "; ".join(" | ".join(v for v in r if v) for r in rows[:2])
    return Block(f"Table {title}: {', '.join(c for c in columns if c)}. {preview}", page, section, "table",
                 {"title": title, "columns": columns, "rows": rows})


def _clean(t: str) -> str:
    t = FICTION_BANNER_RE.sub("", t)
    t = FICTION_SHORT_RE.sub("", t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


# ───────────────────────── PDF ─────────────────────────
def parse_pdf(path: Path) -> list[Block]:
    doc = pymupdf.open(path)
    blocks: list[Block] = []
    section = None
    for pno, page in enumerate(doc, start=1):
        H = page.rect.height
        top_band, bottom_band = 46.0, H - 30.0  # running headers/footers (incl. the fiction banner) live here
        d = page.get_text("dict")
        tblocks = [b for b in d["blocks"] if b.get("lines")]
        spans = [(round(s["size"], 1), s["text"]) for b in tblocks for line in b["lines"] for s in line["spans"] if s["text"].strip()]
        if not spans:
            continue
        body_size = max({z for z, _ in spans}, key=lambda z: sum(1 for zz, _ in spans if zz == z))
        heading_sizes = {z for z, _ in spans if z >= body_size + 1.5}
        page_start_section = section  # carried over from the previous page (tables that continue across pages)
        headings_y: list[tuple[float, str]] = []  # (y, heading) in reading order, for table→section mapping
        buf: list[str] = []
        for b in sorted(tblocks, key=lambda b: (b["bbox"][1], b["bbox"][0])):
            y0, y1 = b["bbox"][1], b["bbox"][3]
            if y1 < top_band or y0 > bottom_band:
                continue  # header / footer band
            btxt = " ".join(s["text"] for line in b["lines"] for s in line["spans"]).strip()
            if not btxt or FICTION_SHORT_RE.search(btxt) or btxt.startswith("FICTIONAL DOCUMENT"):
                continue
            bsize = max((round(s["size"], 1) for line in b["lines"] for s in line["spans"]), default=body_size)
            numeric = re.fullmatch(r"[\d.,%$₹+\-–B ]+(?:in \d{4})?", btxt) is not None  # infographic numbers ("98.1B") are not headings
            is_heading = bsize in heading_sizes and len(btxt) < 120 and not numeric
            if is_heading:
                if buf:
                    blocks.append(Block(_clean("\n".join(buf)), pno, section))
                    buf = []
                section = btxt
                headings_y.append((y0, btxt))
                buf.append(btxt)
            else:
                buf.append(btxt)
        if buf:
            blocks.append(Block(_clean("\n".join(buf)), pno, section))
        try:
            for t in page.find_tables().tables:
                rows = [[(c or "").strip().replace("\n", " ") for c in r] for r in t.extract()]
                rows = [r for r in rows if any(r)]
                if len(rows) >= 2 and sum(1 for c in rows[0] if c) >= 2:
                    ty = t.bbox[1]
                    sec = next((h for y, h in reversed(headings_y) if y <= ty), page_start_section)
                    blocks.append(_table_block(sec or f"page {pno}", rows[0], rows[1:], pno, sec))
        except Exception:
            pass
    return _merge_short(blocks)


def _merge_short(blocks: list[Block], min_len: int = 40) -> list[Block]:
    """Short text blocks (a lone number, a caption) are merged into the previous text block on the same page instead
    of being dropped, so infographic figures stay attached to their label."""
    out: list[Block] = []
    for b in blocks:
        if b.kind == "text" and len(b.text) < min_len and out and out[-1].kind == "text" and out[-1].page == b.page:
            out[-1].text = out[-1].text + "\n" + b.text
            continue
        out.append(b)
    return [b for b in out if len(b.text) > 20 or b.kind == "table"]


# ───────────────────────── DOCX ─────────────────────────
def parse_docx(path: Path) -> list[Block]:
    d = Document(path)
    blocks: list[Block] = []
    section = None
    buf: list[str] = []
    for p in d.paragraphs:
        t = p.text.strip()
        if not t:
            continue
        if p.style.name.lower().startswith(("heading", "title")):
            if buf:
                blocks.append(Block(_clean("\n".join(buf)), None, section))
                buf = []
            section = t
            buf.append(t)
        else:
            buf.append(t)
    if buf:
        blocks.append(Block(_clean("\n".join(buf)), None, section))
    for t in d.tables:
        rows = [[c.text.strip().replace("\n", " ") for c in r.cells] for r in t.rows]
        rows = [r for r in rows if any(r)]
        if len(rows) >= 2:
            blocks.append(_table_block(section or "table", rows[0], rows[1:], None, section))
    return [b for b in blocks if len(b.text) > 20]


# ───────────────────────── XLSX ─────────────────────────
def parse_xlsx(path: Path) -> list[Block]:
    wb = load_workbook(path, data_only=True)
    blocks: list[Block] = []
    for ws in wb.worksheets:
        rows = [[c for c in r] for r in ws.iter_rows(values_only=True)]
        rows = [r for r in rows if any(v is not None and str(v).strip() for v in r)]
        if not rows:
            continue
        if ws.title.lower() == "readme":
            text = "\n".join(str(v) for r in rows for v in r if v is not None)
            blocks.append(Block(_clean(text), None, "README"))
            continue
        # first row is the banner in synthetic workbooks; header is the first row with ≥2 non-empty cells after it
        hdr_idx = next((i for i, r in enumerate(rows) if sum(1 for v in r if v not in (None, "")) >= 2 and not FICTION_SHORT_RE.search(str(r[0]))), 0)
        header = [str(h).strip() if h is not None else "" for h in rows[hdr_idx]]
        blocks.append(_table_block(f"sheet {ws.title}", header, rows[hdr_idx + 1:], None, ws.title))
    return blocks


# ───────────────────────── Markdown ─────────────────────────
PAGE_MARK_RE = re.compile(r"<!--\s*page\s+(\d+)[^>]*-->")


def parse_md(path: Path) -> list[Block]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    raw = NAV_JUNK_RE.sub("", raw)
    # OCR sidecars carry page markers; keep them as split points
    parts = PAGE_MARK_RE.split(raw)
    blocks: list[Block] = []
    if len(parts) > 1:
        head = parts[0]
        pairs = list(zip(parts[1::2], parts[2::2]))
        seq = [(None, head)] + [(int(p), t) for p, t in pairs]
    else:
        seq = [(None, raw)]
    for page, text in seq:
        text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
        text = re.sub(r"^\s*>\s*\*\*FICTIONAL.*$", "", text, flags=re.M)
        section = None
        buf: list[str] = []
        for line in text.splitlines():
            if re.match(r"^\s{0,3}#{1,4}\s+", line):
                if buf:
                    blocks.append(Block(_clean("\n".join(buf)), page, section))
                    buf = []
                section = re.sub(r"^\s{0,3}#{1,4}\s+", "", line).strip("* ")
                buf.append(section)
            else:
                buf.append(line)
        if buf:
            blocks.append(Block(_clean("\n".join(buf)), page, section))
    return [b for b in blocks if len(b.text) > 20]


PARSERS = {"pdf": parse_pdf, "docx": parse_docx, "xlsx": parse_xlsx, "md": parse_md}


def parse(path: Path, kind: str) -> list[Block]:
    return PARSERS[kind](path)
