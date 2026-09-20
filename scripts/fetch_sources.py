"""Fetch the real, publicly published documents listed in data/sources.yaml into data/raw/.

Rules enforced here (see NOTICE.md):
  * Only entries with method == "script" are fetched. Manual entries are listed for the user.
  * Exactly one request per document, sequential, with a polite delay. No crawling.
  * Standard browser User-Agent (the CDN drops anything else); behaviour is identical to a manual download.
  * Existing files are skipped unless --force is given.
  * A manifest (data/raw/_manifest.json) records url, path, size, sha256 and fetch time
    so the corpus can be reproduced without ever committing the files.

Usage:
    python scripts/fetch_sources.py            # fetch missing files
    python scripts/fetch_sources.py --force    # re-download everything
    python scripts/fetch_sources.py --list     # print the manual-download checklist only
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import html2text
import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "data" / "sources.yaml"
RAW = ROOT / "data" / "raw"
MANIFEST = RAW / "_manifest.json"

# Kohler's CDN/WAF silently drops requests carrying a non-standard User-Agent (the connection hangs with
# no HTTP response). A standard browser UA is therefore required; it is exactly what a manual download
# from a browser sends. Nothing else about the request differs from clicking the link.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0 Safari/537.36"
)
DELAY_SECONDS = 2.0
TIMEOUT = 90


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def html_to_markdown(html: str) -> str:
    """Strip navigation chrome and convert the main content to Markdown for ingestion."""
    body = html
    m = re.search(r"<main.*?</main>", html, flags=re.S | re.I)
    if m:
        body = m.group(0)
    body = re.sub(r"<(script|style|nav|footer|header)\b.*?</\1>", "", body, flags=re.S | re.I)
    conv = html2text.HTML2Text()
    conv.ignore_links = False
    conv.ignore_images = True
    conv.body_width = 0
    return conv.handle(body).strip()


def load_sources() -> tuple[dict, list[dict]]:
    doc = yaml.safe_load(SOURCES.read_text(encoding="utf-8"))
    defaults = doc.get("defaults", {})
    sources = [{**defaults, **s} for s in doc["sources"]]
    return defaults, sources


def fetch_one(session: requests.Session, src: dict, force: bool) -> dict:
    target = RAW / src["path"]
    target.parent.mkdir(parents=True, exist_ok=True)
    record = {"id": src["id"], "title": src["title"], "url": src["url"], "path": src["path"]}

    if target.exists() and not force:
        record.update(status="skipped (exists)", size=target.stat().st_size, sha256=sha256_of(target))
        return record

    resp = session.get(src["url"], timeout=TIMEOUT, allow_redirects=True)
    record["http_status"] = resp.status_code
    if resp.status_code != 200:
        record["status"] = f"failed (HTTP {resp.status_code})"
        return record

    ctype = resp.headers.get("Content-Type", "").lower()
    if src["kind"] == "pdf" and "pdf" not in ctype and not resp.content.startswith(b"%PDF"):
        record["status"] = f"failed (expected PDF, got {ctype or 'unknown'})"
        return record

    target.write_bytes(resp.content)
    if src["kind"] == "html":
        md_path = target.with_suffix(".md")
        text = resp.content.decode(resp.encoding or "utf-8", errors="replace")
        md_path.write_text(
            f"<!-- Source: {src['url']}\n     Fetched: {datetime.now(timezone.utc).isoformat()}\n"
            f"     © Kohler Co. / original publisher. Unmodified extraction for non-commercial research use. -->\n\n"
            + html_to_markdown(text),
            encoding="utf-8",
        )
        record["markdown"] = str(md_path.relative_to(RAW))

    record.update(
        status="ok",
        size=target.stat().st_size,
        sha256=sha256_of(target),
        fetched_at=datetime.now(timezone.utc).isoformat(),
        content_type=ctype,
    )
    return record


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):  # Windows consoles default to cp1252
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="re-download files that already exist")
    ap.add_argument("--list", action="store_true", help="only print the manual-download checklist")
    args = ap.parse_args()

    _, sources = load_sources()
    scripted = [s for s in sources if s["method"] == "script"]
    manual = [s for s in sources if s["method"] == "manual"]

    if not args.list:
        RAW.mkdir(parents=True, exist_ok=True)
        session = requests.Session()
        session.headers["User-Agent"] = USER_AGENT
        records = []
        for i, src in enumerate(scripted, 1):
            try:
                rec = fetch_one(session, src, args.force)
            except requests.RequestException as e:  # network error: record and continue
                rec = {"id": src["id"], "url": src["url"], "path": src["path"], "status": f"failed ({e.__class__.__name__})"}
            records.append(rec)
            size = rec.get("size")
            size_s = f"{size/1024:8.0f} KB" if size else "        -"
            print(f"[{i:2d}/{len(scripted)}] {rec['status']:<28} {size_s}  {src['path']}")
            if rec["status"] == "ok":
                time.sleep(DELAY_SECONDS)

        manifest = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "notice": "Files under data/raw are © their publishers, fetched for non-commercial research use, never committed.",
            "documents": records,
            "manual_present": [
                {"id": s["id"], "title": s["title"], "url": s["url"], "path": s["path"],
                 "size": (RAW / s["path"]).stat().st_size, "sha256": sha256_of(RAW / s["path"]),
                 "method": s["method"]}
                for s in sources
                if s["method"] in ("manual", "covered") and (RAW / s["path"]).exists()
            ],
            "manual_pending": [
                {"id": s["id"], "title": s["title"], "url": s["url"], "path": s["path"], "notes": s.get("notes", "")}
                for s in manual
                if not (RAW / s["path"]).exists()
            ],
        }
        MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        ok = sum(r["status"] == "ok" for r in records)
        skipped = sum(r["status"].startswith("skipped") for r in records)
        failed = [r for r in records if r["status"].startswith("failed")]
        total = sum(r.get("size", 0) for r in records)
        print(f"\nfetched {ok}, skipped {skipped}, failed {len(failed)}  |  {total/1e6:.1f} MB on disk  |  manifest: {MANIFEST.relative_to(ROOT)}")
        for r in failed:
            print(f"  FAILED {r['id']}: {r['status']}  {r['url']}")

    pending = [s for s in manual if not (RAW / s["path"]).exists()]
    if pending:
        print(f"\nManual downloads still needed ({len(pending)}) — open in a browser, save to the path shown:")
        for s in pending:
            print(f"  - {s['title']}\n      {s['url']}\n      -> data/raw/{s['path']}   ({s.get('notes', '')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
