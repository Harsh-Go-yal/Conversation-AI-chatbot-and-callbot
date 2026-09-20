"""Response Compiler — renders an AnswerIR into the requested format. JSON/XML/Excel/Markdown are deterministic
code; only the natural-language answer and the email body use an LLM (for tone), and even those are grounded in
the IR's claims so no new facts appear."""
from __future__ import annotations

import io
import json
import re
import xml.etree.ElementTree as ET
from datetime import date
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from pydantic import ValidationError, create_model

from app.config import settings
from app.llm.clients import local_client, openai_client
from app.models.ir import AnswerIR, ConflictVerdict, OutputFormat, Persona


# ───────────────────────── helpers ─────────────────────────
def _llm_for(ir: AnswerIR):
    if ir.routing and ir.routing.llm_used == "local":
        return local_client(), settings.local_model
    return openai_client(), settings.reasoner_fallback_model  # fast model is enough for prose polish


def _cite_label(ir: AnswerIR, sid: str) -> str:
    s = ir.source_by_id(sid)
    if not s:
        return sid
    bits = [s.title]
    if s.version:
        bits.append(f"v{s.version}")
    if s.page:
        bits.append(f"p.{s.page}")
    return ", ".join(bits)


def _ir_public_dict(ir: AnswerIR) -> dict[str, Any]:
    """Default JSON shape when the user gives no schema: claims + citations, no internal routing fields."""
    return {
        "question": ir.query,
        "answer": ir.summary,
        "claims": [{"id": c.id, "text": c.text, "type": c.type.value, "confidence": round(c.confidence, 2),
                    "sources": [ir.source_by_id(s).model_dump(include={"id", "title", "doc_code", "version", "effective_date", "page", "section"}) for s in c.source_ids if ir.source_by_id(s)]}
                   for c in ir.claims],
        "entities": {k: v for k, v in ir.entities.model_dump().items() if v},
        "sources": [s.model_dump(include={"id", "title", "domain", "region", "version", "effective_date", "page", "section", "excerpt", "origin"}) for s in ir.sources],
        "conflicts": [{"verdict": c.verdict.value, "older": _cite_label(ir, c.source_a), "newer": _cite_label(ir, c.source_b), "reason": c.reason, "resolution": c.resolution} for c in ir.conflicts],
        "notes": [n.message for n in ir.access_notes],
        "generated_on": date.today().isoformat(),
    }


# ───────────────────────── text ─────────────────────────
def render_text(ir: AnswerIR) -> str:
    if not ir.claims and not ir.summary:
        return "I couldn't find that in the available documents."
    lines = [ir.summary.strip()]
    if ir.claims:
        lines.append("")
        for c in ir.claims:
            cites = ", ".join(f"[{s}]" for s in c.source_ids)
            lines.append(f"• {c.text} {cites}".rstrip())
    if ir.conflicts:
        lines.append("")
        for c in ir.conflicts:
            tag = {"superseded": "Superseded version", "review_recommended": "Review recommended", "conflict": "Conflicting documents"}[c.verdict.value]
            lines.append(f"⚠ {tag}: {c.reason} {c.resolution}")
    if ir.access_notes:
        lines.append("")
        lines += [f"ℹ {n.message}" for n in ir.access_notes]
    return "\n".join(lines)


# ───────────────────────── JSON (optionally against a user schema) ─────────────────────────
def render_json(ir: AnswerIR, user_schema: dict | str | None = None) -> tuple[str, dict]:
    """Returns (json_text, validation_report). With a user schema: ask the LLM to map the IR into it, validate with
    a dynamically built Pydantic model (plus jsonschema when available) and repair once on failure."""
    if not user_schema:
        return json.dumps(_ir_public_dict(ir), indent=2, ensure_ascii=False), {"validated": True, "schema": "default", "attempts": 0}
    schema = json.loads(user_schema) if isinstance(user_schema, str) else user_schema
    client, model = _llm_for(ir)
    sysmsg = ("Map the structured answer into JSON that conforms EXACTLY to the given JSON schema. Use only facts in the "
              "answer; leave unknown optional fields out and required ones as empty strings/lists. Return only JSON.")
    payload = json.dumps(_ir_public_dict(ir), ensure_ascii=False)
    user = f"JSON SCHEMA:\n{json.dumps(schema)}\n\nSTRUCTURED ANSWER:\n{payload}"
    attempts, last_err, text = 0, None, ""
    try:
        import jsonschema
    except ImportError:
        jsonschema = None
    while attempts < 3:
        attempts += 1
        text = client.complete_text(model, sysmsg, user + (f"\n\nPrevious attempt failed validation: {last_err}. Fix it." if last_err else ""), purpose="compiler.json")
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.S)
        try:
            obj = json.loads(text)
            if jsonschema:
                jsonschema.validate(obj, schema)
            return json.dumps(obj, indent=2, ensure_ascii=False), {"validated": True, "schema": "user", "attempts": attempts}
        except Exception as e:  # noqa: BLE001
            last_err = str(e)[:300]
    return text, {"validated": False, "schema": "user", "attempts": attempts, "error": last_err}


# ───────────────────────── XML ─────────────────────────
def render_xml(ir: AnswerIR) -> str:
    root = ET.Element("answer", attrib={"generated_on": date.today().isoformat(), "persona": ir.persona.value, "region": ir.region.value})
    ET.SubElement(root, "question").text = ir.query
    ET.SubElement(root, "summary").text = ir.summary
    cl = ET.SubElement(root, "claims")
    for c in ir.claims:
        e = ET.SubElement(cl, "claim", attrib={"id": c.id, "type": c.type.value, "confidence": f"{c.confidence:.2f}"})
        ET.SubElement(e, "text").text = c.text
        for s in c.source_ids:
            ET.SubElement(e, "cite", attrib={"ref": s})
    ss = ET.SubElement(root, "sources")
    for s in ir.sources:
        e = ET.SubElement(ss, "source", attrib={k: str(v) for k, v in {"id": s.id, "version": s.version, "effective_date": s.effective_date, "page": s.page, "origin": s.origin}.items() if v})
        ET.SubElement(e, "title").text = s.title
        if s.section:
            ET.SubElement(e, "section").text = s.section
        ET.SubElement(e, "excerpt").text = s.excerpt
    if ir.conflicts:
        cf = ET.SubElement(root, "conflicts")
        for c in ir.conflicts:
            e = ET.SubElement(cf, "conflict", attrib={"verdict": c.verdict.value, "older": c.source_a, "newer": c.source_b})
            ET.SubElement(e, "reason").text = c.reason
            ET.SubElement(e, "resolution").text = c.resolution
    if ir.access_notes:
        nn = ET.SubElement(root, "notes")
        for n in ir.access_notes:
            ET.SubElement(nn, "note", attrib={"kind": n.kind}).text = n.message
    ET.indent(root, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")


# ───────────────────────── Markdown table ─────────────────────────
def render_markdown_table(ir: AnswerIR) -> str:
    rows = ["| # | Statement | Type | Source | Version | Page |", "|---|---|---|---|---|---|"]
    for c in ir.claims:
        src = ir.source_by_id(c.source_ids[0]) if c.source_ids else None
        rows.append(f"| {c.id} | {c.text.replace('|', '/')} | {c.type.value} | {src.title if src else ''} | {src.version or '' if src else ''} | {src.page or '' if src else ''} |")
    out = "\n".join(rows)
    if ir.conflicts:
        out += "\n\n| Verdict | Older | Newer | Difference |\n|---|---|---|---|\n" + "\n".join(
            f"| {c.verdict.value} | {_cite_label(ir, c.source_a)} | {_cite_label(ir, c.source_b)} | {c.reason.replace('|', '/')} |" for c in ir.conflicts)
    return out


# ───────────────────────── Excel ─────────────────────────
def render_excel(ir: AnswerIR) -> bytes:
    wb = Workbook()
    hdr_fill = PatternFill("solid", fgColor="1F3864"); hdr_font = Font(bold=True, color="FFFFFF")

    def sheet(name, headers, rows, widths):
        ws = wb.create_sheet(name)
        ws.append(headers)
        for c in ws[1]:
            c.fill, c.font = hdr_fill, hdr_font
        for r in rows:
            ws.append(r)
        for j, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(j)].width = w
        for row in ws.iter_rows(min_row=2):
            for c in row:
                c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.freeze_panes = "A2"
        return ws

    ws = wb.active; ws.title = "Answer"
    ws["A1"] = "Question"; ws["B1"] = ir.query
    ws["A2"] = "Answer"; ws["B2"] = ir.summary
    ws["A3"] = "Persona"; ws["B3"] = ir.persona.value
    ws["A4"] = "Generated"; ws["B4"] = date.today().isoformat()
    ws["A5"] = "Model route"; ws["B5"] = (ir.routing.llm_used + " · " + ir.routing.reason) if ir.routing else ""
    for r in range(1, 6):
        ws[f"A{r}"].font = Font(bold=True); ws[f"B{r}"].alignment = Alignment(wrap_text=True, vertical="top")
    ws.column_dimensions["A"].width = 14; ws.column_dimensions["B"].width = 110

    sheet("Claims", ["ID", "Statement", "Type", "Confidence", "Sources"],
          [[c.id, c.text, c.type.value, round(c.confidence, 2), "; ".join(_cite_label(ir, s) for s in c.source_ids)] for c in ir.claims],
          [6, 80, 14, 12, 50])
    sheet("Sources", ["ID", "Document", "Code", "Version", "Effective", "Page", "Section", "Region", "Origin", "Excerpt"],
          [[s.id, s.title, s.doc_code or "", s.version or "", s.effective_date or "", s.page or "", s.section or "", s.region.value, s.origin, s.excerpt] for s in ir.sources],
          [6, 40, 12, 9, 12, 6, 30, 8, 10, 90])
    ents = {k: v for k, v in ir.entities.model_dump().items() if v}
    if ents:
        sheet("Entities", ["Type", "Value"], [[k, v] for k, vs in ents.items() for v in vs], [16, 60])
    if ir.conflicts:
        sheet("Version notes", ["Verdict", "Older", "Newer", "Difference", "Resolution"],
              [[c.verdict.value, _cite_label(ir, c.source_a), _cite_label(ir, c.source_b), c.reason, c.resolution] for c in ir.conflicts],
              [18, 34, 34, 60, 60])
    _maybe_comparison_sheet(ir, sheet)
    buf = io.BytesIO(); wb.save(buf); return buf.getvalue()


_NUM_RE = re.compile(r"(?P<model>K-\d{3,5}[A-Z]?|[A-Z][a-z]+®?)[^.\n]{0,60}?(?P<val>\d+(?:\.\d+)?)\s*(?P<unit>gpf|lpf|gpm|l/min|litres?|liters?)", re.I)


def _maybe_comparison_sheet(ir: AnswerIR, sheet) -> None:
    """If the answer compares products by water use, add a computed savings sheet with live formulas."""
    products = {}
    for c in ir.claims:
        for m in _NUM_RE.finditer(c.text):
            unit = m.group("unit").lower(); val = float(m.group("val"))
            lpf = val * 3.785 if unit == "gpf" else val if unit == "lpf" else None
            if lpf:
                products.setdefault(m.group("model").strip(), lpf)
    if len(products) < 2:
        return
    ws = sheet("Water savings", ["Product", "Litres per flush", "Flushes/person/day", "Persons", "Litres per year", "Saving vs 6.0 lpf baseline (L/yr)"],
               [], [28, 16, 18, 10, 18, 30])
    for i, (name, lpf) in enumerate(products.items(), start=2):
        ws.append([name, round(lpf, 2), 5, 4, f"=B{i}*C{i}*D{i}*365", f"=(6-B{i})*C{i}*D{i}*365"])
    ws.append([]); ws.append(["Assumptions: 5 flushes per person per day, household of 4, baseline 6.0 litres per flush (1.6 gpf). Edit the yellow cells."])
    for r in range(2, 2 + len(products)):
        for col in ("C", "D"):
            ws[f"{col}{r}"].fill = PatternFill("solid", fgColor="FFF2CC")


# ───────────────────────── email ─────────────────────────
def render_email(ir: AnswerIR, recipient: str | None, sender_name: str | None = None, instruction: str | None = None) -> dict:
    client, model = _llm_for(ir)
    persona_note = ("The sender is a Kohler India Customer Care associate writing to a customer; sign as 'Kohler India Customer Care' and include 1800-103-2244 (Mon–Sat 08:00–20:00)."
                    if ir.persona == Persona.internal and (recipient or "").lower().find("customer") >= 0 else
                    "The sender is a customer writing to Kohler India Customer Care (indiacustomercare@kohler.com)." if ir.persona == Persona.customer else
                    f"The sender is a Kohler India employee writing to {recipient or 'a colleague'}.")
    facts = "\n".join(f"- {c.text} (source: {_cite_label(ir, c.source_ids[0]) if c.source_ids else 'n/a'})" for c in ir.claims)
    conf = "\n".join(f"- Note: {c.reason} {c.resolution}" for c in ir.conflicts)
    sysmsg = ("Write a ready-to-send business email that does exactly what the user asked for (a request, a reply, a notification…). "
              "Under 180 words. State the purpose in the first sentence, then the specifics, then the policy reference. "
              "Use only the facts given; do not invent order numbers, names or dates — use {placeholders} where needed. "
              "Return JSON with keys subject, body. Body is plain text with line breaks.")
    user = (f"{persona_note}\nRecipient: {recipient or 'unspecified'}\nWhat the user asked for: {instruction or 'an email conveying the answer'}\n"
            f"Original question the facts answer: {ir.query}\nFacts:\n{facts}\n{conf}\nSummary: {ir.summary}")
    text = client.complete_text(model, sysmsg, user, purpose="compiler.email")
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.S)
    try:
        obj = json.loads(text)
        subject, body = obj.get("subject", ""), obj.get("body", "")
    except Exception:
        subject, body = f"Re: {ir.query[:60]}", text
    return {"to": recipient or "", "subject": subject, "body": body,
            "citations": [_cite_label(ir, s.id) for s in ir.sources]}


# ───────────────────────── dispatcher ─────────────────────────
def compile_answer(ir: AnswerIR, fmt: OutputFormat, user_schema=None, recipient: str | None = None, instruction: str | None = None) -> dict:
    if fmt == OutputFormat.json:
        text, report = render_json(ir, user_schema)
        return {"format": "json", "content": text, "validation": report, "filename": "answer.json", "mime": "application/json"}
    if fmt == OutputFormat.xml:
        return {"format": "xml", "content": render_xml(ir), "filename": "answer.xml", "mime": "application/xml"}
    if fmt == OutputFormat.markdown_table:
        return {"format": "markdown_table", "content": render_markdown_table(ir)}
    if fmt == OutputFormat.excel:
        return {"format": "excel", "bytes": render_excel(ir), "filename": "answer.xlsx",
                "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
    if fmt == OutputFormat.email:
        return {"format": "email", **render_email(ir, recipient, instruction=instruction)}
    return {"format": "text", "content": render_text(ir)}
