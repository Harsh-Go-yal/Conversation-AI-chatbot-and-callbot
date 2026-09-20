"""Evaluation harness. Runs eval/questions.yaml through the agent (in-process) and scores:
  retrieval hit@k     expected doc cited in sources
  routing accuracy    expected LLM (openai/local) used
  conflict recall     expected verdict present in ir.conflicts
  access control      no forbidden doc ever cited (customer persona)
  answer hits         must_contain substrings present in the rendered answer
  intent/format       expected intent / requested_format
  JSON validity       every json output validates
  faithfulness        LLM-judge (gpt-4.1-mini): each claim supported by its cited excerpt (sampled)
  leak test           routing audit: zero restricted chunks in any OpenAI call
  latency             p50 / p95 end-to-end and per stage
Usage (from backend/):  python ../eval/run_eval.py [--ids hr01 fin02] [--no-judge] [--tag conflict]
Writes eval/results/<timestamp>.json and eval/results/latest.md
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.agent import graph, memory  # noqa: E402
from app.agent.compiler import render_json  # noqa: E402
from app.llm.clients import AUDIT, openai_client  # noqa: E402
from app.models.ir import Persona  # noqa: E402
from pydantic import BaseModel  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "eval" / "results"


class Judge(BaseModel):
    supported: list[bool]
    notes: str = ""


def judge_faithfulness(ir) -> float | None:
    if not ir.claims or not ir.sources:
        return None
    items = []
    from app.ingest import index as _index
    full = {}
    try:
        pts = _index.client().retrieve(collection_name=_index.settings.qdrant_collection,
                                       ids=[s.chunk_id for s in ir.sources], with_payload=["text"])
        full = {str(p.id): p.payload["text"] for p in pts}
    except Exception:
        pass
    for c in ir.claims[:6]:
        ex = " ".join((full.get(ir.source_by_id(s).chunk_id) or ir.source_by_id(s).excerpt) for s in c.source_ids if ir.source_by_id(s))[:2500]
        items.append(f"CLAIM: {c.text}\nEVIDENCE: {ex}")
    sysm = "For each CLAIM decide if it is supported by its EVIDENCE excerpt (true/false). Be strict but allow paraphrase and unit conversion. Return supported as a list in order."
    out = openai_client().complete_json("gpt-4.1-mini", sysm, "\n\n".join(items), Judge, purpose="judge")
    vals = out.supported[: len(items)]
    return sum(vals) / len(vals) if vals else None


def run_one(q: dict, session: str, no_judge: bool) -> dict:
    t = time.time()
    persona = Persona(q["persona"])
    final = graph.run(session, persona, q["q"])
    dt = time.time() - t
    ir = final["ir"]
    out = final["output"]
    text = (out.get("content") or "") + " " + (out.get("body") or "") + " " + ir.summary + " " + " ".join(c.text for c in ir.claims)
    cited = {s.doc_id for s in ir.sources}
    r = {"id": q["id"], "persona": q["persona"], "q": q["q"], "seconds": round(dt, 1), "intent": ir.intent.value,
         "format": out.get("format"), "llm": ir.routing.llm_used if ir.routing else None, "cited": sorted(cited),
         "conflicts": [c.verdict.value for c in ir.conflicts], "timings": ir.routing.stage_timings_ms if ir.routing else {}}
    checks = {}
    if q.get("expect_docs"):
        checks["retrieval_hit"] = bool(cited & set(q["expect_docs"]))
    if q.get("expect_llm") and ir.routing:
        checks["routing"] = ir.routing.llm_used == q["expect_llm"]
    if q.get("expect_conflict"):
        checks["conflict"] = q["expect_conflict"] in r["conflicts"]
    if q.get("forbid_docs"):
        checks["access"] = not (cited & set(q["forbid_docs"])) and all(s.sensitivity == "public" for s in ir.sources) if persona == Persona.customer else True
    if persona == Persona.customer:
        checks["customer_public_only"] = all(s.sensitivity.value == "public" for s in ir.sources)
    if q.get("must_contain"):
        hits = [m.lower() in text.lower() for m in q["must_contain"]]
        checks["answer_hit"] = any(hits) if q.get("any_contain") else all(hits)
    if q.get("expect_intent"):
        checks["intent"] = ir.intent.value == q["expect_intent"]
    if q.get("expect_format"):
        checks["format"] = out.get("format") == q["expect_format"]
    if out.get("format") == "json":
        checks["json_valid"] = bool(out.get("validation", {}).get("validated"))
        try:
            json.loads(out.get("content") or "")
        except Exception:
            checks["json_valid"] = False
    if not no_judge and ir.claims and persona and ir.routing and ir.routing.llm_used == "openai":
        try:
            r["faithfulness"] = judge_faithfulness(ir)
        except Exception as e:  # noqa: BLE001
            r["faithfulness_error"] = str(e)[:120]
    r["checks"] = checks
    r["pass"] = all(checks.values()) if checks else True
    return r


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", nargs="*")
    ap.add_argument("--tag")
    ap.add_argument("--no-judge", action="store_true")
    args = ap.parse_args()
    qs = yaml.safe_load((ROOT / "eval" / "questions.yaml").read_text(encoding="utf-8"))["questions"]
    if args.ids:
        qs = [q for q in qs if q["id"] in set(args.ids)]
    if args.tag:
        qs = [q for q in qs if args.tag in q.get("tags", [])]
    results = []
    audit_start = len(AUDIT)
    for i, q in enumerate(qs, 1):
        session = f"eval-{q.get('session') or q['id']}"
        if not q.get("session"):
            memory.reset(session)
        try:
            r = run_one(q, session, args.no_judge)
        except Exception as e:  # noqa: BLE001
            r = {"id": q["id"], "q": q["q"], "error": str(e)[:300], "pass": False, "checks": {}, "seconds": 0}
        results.append(r)
        flag = "PASS" if r["pass"] else "FAIL"
        print(f"[{i:2}/{len(qs)}] {flag} {r['id']:6} {r.get('seconds', 0):5.1f}s llm={r.get('llm')} fmt={r.get('format')} "
              f"conf={r.get('conflicts')} checks={ {k: v for k, v in r.get('checks', {}).items() if not v} or 'ok'} {r.get('error', '')}")

    # ── aggregate ──
    def rate(key):
        vals = [r["checks"][key] for r in results if key in r.get("checks", {})]
        return (sum(vals) / len(vals), len(vals)) if vals else (None, 0)
    calls = AUDIT[audit_start:]
    leaks = [c for c in calls if c["provider"] == "openai" and "restricted" in c["sensitivities"]]
    secs = [r["seconds"] for r in results if r.get("seconds")]
    faith = [r["faithfulness"] for r in results if r.get("faithfulness") is not None]
    stage = {}
    for r in results:
        for k, v in (r.get("timings") or {}).items():
            stage.setdefault(k, []).append(v)
    summary = {
        "n": len(results), "passed": sum(1 for r in results if r["pass"]),
        "retrieval_hit": rate("retrieval_hit"), "routing": rate("routing"), "conflict_recall": rate("conflict"),
        "access": rate("access"), "customer_public_only": rate("customer_public_only"), "answer_hit": rate("answer_hit"),
        "intent": rate("intent"), "format": rate("format"), "json_valid": rate("json_valid"),
        "faithfulness_mean": round(statistics.mean(faith), 3) if faith else None, "faithfulness_n": len(faith),
        "leak_restricted_to_cloud": len(leaks), "openai_calls": sum(1 for c in calls if c["provider"] == "openai"),
        "local_calls": sum(1 for c in calls if c["provider"] == "local"),
        "latency_p50_s": round(statistics.median(secs), 1) if secs else None,
        "latency_p95_s": round(sorted(secs)[int(len(secs) * 0.95) - 1], 1) if len(secs) >= 2 else None,
        "stage_median_ms": {k: int(statistics.median(v)) for k, v in stage.items()},
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    (RESULTS / f"{ts}.json").write_text(json.dumps({"summary": summary, "results": results}, indent=1, default=str), encoding="utf-8")
    md = ["# Evaluation results", f"Run: {ts} · {summary['n']} questions · {summary['passed']} passed", "",
          "| Metric | Value | n |", "|---|---|---|"]
    for k in ("retrieval_hit", "routing", "conflict_recall", "access", "customer_public_only", "answer_hit", "intent", "format", "json_valid"):
        v, n = summary[k]
        md.append(f"| {k} | {'' if v is None else f'{v:.2f}'} | {n} |")
    md += [f"| faithfulness (LLM-judge) | {summary['faithfulness_mean']} | {summary['faithfulness_n']} |",
           f"| leak test: restricted chunks sent to cloud | **{summary['leak_restricted_to_cloud']}** | {summary['openai_calls']} OpenAI calls / {summary['local_calls']} local |",
           f"| latency p50 / p95 (s) | {summary['latency_p50_s']} / {summary['latency_p95_s']} | {len(secs)} |",
           f"| stage medians (ms) | {summary['stage_median_ms']} | |", "", "## Per question", "",
           "| id | pass | s | llm | format | conflicts | failed checks |", "|---|---|---|---|---|---|---|"]
    for r in results:
        failed = [k for k, v in r.get("checks", {}).items() if not v]
        md.append(f"| {r['id']} | {'✅' if r['pass'] else '❌'} | {r.get('seconds', '')} | {r.get('llm', '')} | {r.get('format', '')} | {', '.join(r.get('conflicts', []))} | {', '.join(failed) or r.get('error', '')} |")
    (RESULTS / "latest.md").write_text("\n".join(md), encoding="utf-8")
    print("\n" + "\n".join(md[:14]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
