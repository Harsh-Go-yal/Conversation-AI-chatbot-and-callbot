"""OCR image-only PDFs into Markdown text sidecars so they can be ingested like any other document.

Uses RapidOCR (ONNX runtime, CPU-only, no system dependencies) — consistent with the project's
fastembed/ONNX choice. Output: <pdf path>.ocr.md next to the PDF, with per-page markers so
citations can still point at a page number.

Usage:
    python scripts/ocr_scanned.py                       # OCR every source tagged `needs-ocr` in data/sources.yaml
    python scripts/ocr_scanned.py path/to/file.pdf ...  # OCR specific PDFs
    python scripts/ocr_scanned.py --dpi 300 --min-conf 0.5
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

import numpy as np
import pymupdf
import wordsegment
import yaml
from rapidocr_onnxruntime import RapidOCR

wordsegment.load()
_MERGED = re.compile(r"[A-Za-z]{11,}")
_CAMEL = re.compile(r"([a-z])([A-Z][a-z])")


def split_merged_words(text: str) -> str:
    """RapidOCR often drops spaces between tightly kerned words ("beundertakenspecified").
    Re-insert them with a unigram/bigram segmenter, keeping the original casing, and leave
    genuine long words (present in the segmenter's dictionary) untouched."""

    def fix(m: re.Match) -> str:
        w = m.group(0)
        if w.lower() in wordsegment.UNIGRAMS:
            return w
        parts = wordsegment.segment(w)
        if len(parts) < 2 or any(len(x) < 2 and x not in ("a", "i", "s") for x in parts):
            return w
        out, i = [], 0
        for x in parts:  # re-slice the original string so case is preserved
            out.append(w[i:i + len(x)])
            i += len(x)
        return " ".join(out)

    text = _CAMEL.sub(lambda m: m.group(1) + " " + m.group(2), text)  # "theBoard" -> "the Board", "CSRPolicy" -> "CSR Policy"
    return _MERGED.sub(fix, text)

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "data" / "sources.yaml"
RAW = ROOT / "data" / "raw"


def page_image(page: pymupdf.Page, dpi: int) -> np.ndarray:
    pix = page.get_pixmap(dpi=dpi)
    return np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)[:, :, :3]


def boxes_to_lines(boxes: list, min_conf: float) -> list[str]:
    """Group OCR boxes into reading-order lines: sort by y, merge boxes whose vertical centres overlap."""
    items = []
    for box, text, conf in boxes:
        if float(conf) < min_conf or not text.strip():
            continue
        ys = [p[1] for p in box]
        xs = [p[0] for p in box]
        items.append((min(ys), max(ys), min(xs), text.strip()))
    items.sort(key=lambda t: (t[0], t[2]))
    lines: list[list[tuple]] = []
    for it in items:
        if lines:
            top, bottom = lines[-1][0][0], lines[-1][0][1]
            h = max(bottom - top, 1)
            if abs(it[0] - top) < 0.6 * h:  # same visual line
                lines[-1].append(it)
                continue
        lines.append([it])
    return [" ".join(t[3] for t in sorted(line, key=lambda t: t[2])) for line in lines]


def ocr_pdf(pdf: Path, engine: RapidOCR, dpi: int, min_conf: float) -> Path:
    doc = pymupdf.open(pdf)
    out = pdf.with_suffix(".ocr.md")
    parts = [
        f"<!-- OCR extraction of {pdf.name} ({len(doc)} pages) via RapidOCR @ {dpi} dpi, min confidence {min_conf}.",
        "     Image-only source; text below is machine-read and may contain recognition errors.",
        "     © original publisher. Unmodified apart from OCR; non-commercial research use. -->",
        "",
    ]
    confs: list[float] = []
    t0 = time.time()
    for i, page in enumerate(doc, 1):
        native = page.get_text().strip()
        if len(native) > 40:  # page already has a text layer — keep it verbatim
            parts += [f"\n<!-- page {i} (native text) -->\n", native]
            continue
        result, _ = engine(page_image(page, dpi))
        result = result or []
        confs += [float(r[2]) for r in result]
        lines = [split_merged_words(line) for line in boxes_to_lines(result, min_conf)]
        parts += [f"\n<!-- page {i} (OCR, {len(lines)} lines) -->\n", "\n".join(lines)]
        print(f"    page {i}/{len(doc)}: {len(result)} boxes, {len(lines)} lines", flush=True)
    out.write_text("\n".join(parts).strip() + "\n", encoding="utf-8")
    mean_conf = sum(confs) / len(confs) if confs else 0.0
    print(f"  -> {out.relative_to(ROOT)}  ({len(confs)} boxes, mean confidence {mean_conf:.2f}, {time.time()-t0:.0f}s)")
    return out


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("pdfs", nargs="*", help="specific PDFs; default = sources tagged needs-ocr")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--min-conf", type=float, default=0.5)
    args = ap.parse_args()

    if args.pdfs:
        targets = [Path(p) for p in args.pdfs]
    else:
        srcs = yaml.safe_load(SOURCES.read_text(encoding="utf-8"))["sources"]
        targets = [RAW / s["path"] for s in srcs if "needs-ocr" in s.get("tags", [])]
    if not targets:
        print("nothing to OCR")
        return 0

    engine = RapidOCR()
    for pdf in targets:
        if not pdf.exists():
            print(f"missing: {pdf}")
            continue
        print(f"OCR {pdf.relative_to(ROOT)}")
        ocr_pdf(pdf, engine, args.dpi, args.min_conf)
    return 0


if __name__ == "__main__":
    sys.exit(main())
