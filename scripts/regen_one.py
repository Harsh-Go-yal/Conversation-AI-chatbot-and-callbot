"""Regenerate ONE synthetic document (after a content/metadata change) and patch its manifest entry.

    python scripts/regen_one.py support_escalation_matrix_sla

Then re-index just that document:  cd backend && python -m app.ingest.run --only <doc_id>
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_synthetic import ALL_DOCS, META_KEYS, RAW, RENDERERS, SYN_MANIFEST, build_inventory, sha256_of  # noqa: E402


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    doc_id = sys.argv[1]
    doc = next(d for d in ALL_DOCS if d["id"] == doc_id)
    manifest = yaml.safe_load(SYN_MANIFEST.read_text(encoding="utf-8"))
    old = next(r for r in manifest["documents"] if r["id"] == doc_id)
    old_path = RAW / old["path"]
    out = RAW / doc["path"]
    out.parent.mkdir(parents=True, exist_ok=True)
    RENDERERS[doc["format"]](doc, out)
    if old_path != out and old_path.exists():
        old_path.unlink()
        print(f"removed old file {old_path.relative_to(RAW)}")
    rec = {k: doc[k] for k in META_KEYS if k in doc}
    rec.update(origin="synthetic", fictional=True, size=out.stat().st_size, sha256=sha256_of(out))
    manifest["documents"] = [rec if r["id"] == doc_id else r for r in manifest["documents"]]
    head = SYN_MANIFEST.read_text(encoding="utf-8").splitlines()[0]
    SYN_MANIFEST.write_text(head + "\n" + yaml.safe_dump({"generated": manifest["generated"], "documents": manifest["documents"]}, sort_keys=False, allow_unicode=True), encoding="utf-8")
    build_inventory(manifest["documents"])
    print(f"regenerated {doc_id}: {doc['path']} ({doc['sensitivity']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
