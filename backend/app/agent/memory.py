"""Conversation memory: per-session history + the last AnswerIR (for format conversions / follow-ups).
In-memory with a JSON spill to logs/sessions/ so a restart doesn't lose the demo state."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from app.config import ROOT
from app.models.ir import AnswerIR

_HIST: dict[str, list[dict]] = defaultdict(list)
_IR: dict[str, AnswerIR] = {}
_DIR = ROOT / "logs" / "sessions"


def history(session_id: str) -> list[dict]:
    return _HIST[session_id][-12:]


def append(session_id: str, role: str, content: str) -> None:
    _HIST[session_id].append({"role": role, "content": content})
    try:
        _DIR.mkdir(parents=True, exist_ok=True)
        (_DIR / f"{session_id}.json").write_text(json.dumps({"history": _HIST[session_id][-40:],
                                                            "last_ir": _IR[session_id].model_dump(mode="json") if session_id in _IR else None},
                                                           ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


def store_ir(session_id: str, ir: AnswerIR) -> None:
    _IR[session_id] = ir


def last_ir(session_id: str) -> AnswerIR | None:
    if session_id in _IR:
        return _IR[session_id]
    p = _DIR / f"{session_id}.json"
    if p.exists():
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            if d.get("last_ir"):
                _IR[session_id] = AnswerIR.model_validate(d["last_ir"])
                _HIST[session_id] = d.get("history", [])
                return _IR[session_id]
        except Exception:
            return None
    return None


# ── full transcript for the UI (what the user saw: stages, output, IR) ──
_TURNS: dict[str, list[dict]] = defaultdict(list)
_TDIR = ROOT / "logs" / "transcripts_ui"


def _tpath(session_id: str) -> Path:
    return _TDIR / f"{session_id}.json"


def record_turn(session_id: str, turn: dict) -> None:
    """Append one UI turn ({role, text, stages?, output?, ir?, ts}) and spill to disk so a reload / restart restores it."""
    _TURNS[session_id].append(turn)
    try:
        _TDIR.mkdir(parents=True, exist_ok=True)
        _tpath(session_id).write_text(json.dumps(_TURNS[session_id][-60:], ensure_ascii=False, default=str), encoding="utf-8")
    except Exception:
        pass


def update_last_assistant(session_id: str, **fields) -> None:
    """Format conversions rewrite the previous answer in place (same as the UI does)."""
    for t in reversed(_TURNS[session_id]):
        if t.get("role") == "assistant":
            t.update(fields)
            break
    try:
        _TDIR.mkdir(parents=True, exist_ok=True)
        _tpath(session_id).write_text(json.dumps(_TURNS[session_id][-60:], ensure_ascii=False, default=str), encoding="utf-8")
    except Exception:
        pass


def turns(session_id: str) -> list[dict]:
    if session_id not in _TURNS and _tpath(session_id).exists():
        try:
            _TURNS[session_id] = json.loads(_tpath(session_id).read_text(encoding="utf-8"))
        except Exception:
            _TURNS[session_id] = []
    return _TURNS[session_id]


def reset(session_id: str) -> None:
    _HIST.pop(session_id, None)
    _IR.pop(session_id, None)
    _TURNS.pop(session_id, None)
    try:
        _tpath(session_id).unlink(missing_ok=True)
    except Exception:
        pass
