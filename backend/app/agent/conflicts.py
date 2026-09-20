"""Contradiction / staleness detector — engineered, not prompted.

Trigger: among the retrieved chunks (plus sibling versions of the same policy_key that the persona may see), two
documents share a policy_key but differ in version / effective_date. The newer one is preferred; the LLM is only
asked to DESCRIBE the difference. Also detects `review_recommended` cases from a small registry of known
regulatory-change pairs (e.g. India Privacy Policy vs the DPDP Readiness Note)."""
from __future__ import annotations

from dataclasses import dataclass

from app.models.ir import ConflictVerdict, Persona, RetrievedChunk
from app.retrieval.search import fetch_doc_chunks, sibling_versions

# doc_id pairs where a newer internal note recommends reviewing a still-current public document
REVIEW_PAIRS = {
    ("privacy_in_policy", "legal_in_dpdp_readiness_note"): "The public India Privacy Policy is framed on the IT Act 2000 / SPDI Rules; the DPDP Readiness Note records the obligations that will apply when the DPDP Rules commence and recommends a revision.",
}


@dataclass
class ConflictCandidate:
    older_doc_id: str
    newer_doc_id: str
    policy_key: str | None
    verdict: ConflictVerdict
    older_label: str
    newer_label: str
    older_text: str
    newer_text: str
    system_reason: str


def _ver_num(v) -> tuple:
    import re as _re
    nums = [int(x) for x in _re.findall(r"\d+", str(v or ""))]
    return tuple(nums) if nums else ()


def _ver_key(p: dict) -> tuple:
    """Newest wins. Numeric version first (Rev 5.0 > Rev 3.0 even without dates), then effective date, then the raw string
    (handles IN12-A < IN12-B)."""
    return (_ver_num(p.get("version")), p.get("effective_date") or "", str(p.get("version") or ""))


def find_conflicts(chunks: list[RetrievedChunk], persona: Persona, max_pairs: int = 2) -> list[ConflictCandidate]:
    out: list[ConflictCandidate] = []
    seen_keys: set[str] = set()
    doc_ids_present = {c.meta.doc_id for c in chunks}

    for c in chunks:
        pk = c.meta.policy_key
        if not pk or pk in seen_keys:
            continue
        seen_keys.add(pk)
        sibs = sibling_versions(pk, persona)
        if len(sibs) < 2:
            continue
        sibs.sort(key=_ver_key)
        newest = sibs[-1]
        for older in sibs[:-1]:
            if _ver_key(older) == _ver_key(newest):
                continue
            # only flag when the retrieved evidence actually touches the older version OR the newest is missing
            if older["doc_id"] not in doc_ids_present and newest["doc_id"] in doc_ids_present and len(sibs) > 2:
                continue
            older_chunks = [x.meta for x in chunks if x.meta.doc_id == older["doc_id"]] or fetch_doc_chunks(older["doc_id"])[:3]
            newer_chunks = [x.meta for x in chunks if x.meta.doc_id == newest["doc_id"]]
            if not newer_chunks:
                # pull the newest version's matching section(s) so the reasoner sees the preferred text
                newer_chunks = fetch_doc_chunks(newest["doc_id"])
                sec = {x.section for x in older_chunks if x.section}
                newer_chunks = [m for m in newer_chunks if m.section in sec][:3] or newer_chunks[:3]
            out.append(ConflictCandidate(
                older_doc_id=older["doc_id"], newer_doc_id=newest["doc_id"], policy_key=pk,
                verdict=ConflictVerdict.superseded,
                older_label=f"{older.get('title')} v{older.get('version')} ({older.get('effective_date') or 'no date'})",
                newer_label=f"{newest.get('title')} v{newest.get('version')} ({newest.get('effective_date') or 'no date'})",
                older_text="\n".join(m.text[:900] for m in older_chunks[:2]),
                newer_text="\n".join(m.text[:900] for m in newer_chunks[:2]),
                system_reason=f"Same policy_key '{pk}': version {older.get('version')} is superseded by version {newest.get('version')}.",
            ))
            if len(out) >= max_pairs:
                return out

    for (public_doc, note_doc), why in REVIEW_PAIRS.items():
        if public_doc in doc_ids_present and persona == Persona.internal:
            note = fetch_doc_chunks(note_doc)
            if note:
                out.append(ConflictCandidate(
                    older_doc_id=public_doc, newer_doc_id=note_doc, policy_key=None,
                    verdict=ConflictVerdict.review_recommended,
                    older_label=next(x.meta.title for x in chunks if x.meta.doc_id == public_doc),
                    newer_label=note[0].title, older_text="", newer_text="\n".join(m.text[:700] for m in note[:2]),
                    system_reason=why,
                ))
    return out[:max_pairs + 1]
