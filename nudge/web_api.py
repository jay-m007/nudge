"""The glue between the web page and the engine. Runs inside Pyodide (Python in the browser),
but nothing here needs a browser, so the tests import it too.

Every function takes and returns plain JSON strings. The page keeps the progress JSON in
localStorage and hands it in on each call; nothing is sent anywhere.
"""
from __future__ import annotations

import hashlib
import io
import json
import sys

from . import _harness
from .diagnose import diagnose
from .hints import hint_at, next_hint, solution_locked
from .progress import Progress
from .runner import collect

_exercises: dict[str, dict] = {}
_emit = None  # optional callback that receives each output line as it is produced


def init(exercises_json: str) -> str:
    _exercises.clear()
    _exercises.update(json.loads(exercises_json))
    return json.dumps({"count": len(_exercises)})


def set_emitter(fn) -> None:
    global _emit
    _emit = fn


class _Out(io.StringIO):
    def write(self, s):
        if _emit and s:
            _emit(s)
        return super().write(s)


def run_check(exercise_id: str, source: str, limit: float = 2.0) -> str:
    """Run the student's code against the tests. Returns the raw harness output (JSON lines)."""
    ex = _exercises[exercise_id]
    job = {
        "source": source,
        "function": ex["function"],
        "cases": [{"args": c["args"], "expected": c["expected"], "tag": c.get("tag", "")} for c in ex["cases"]],
        "limit": limit,
        "approx": ex.get("approx", False),
        "allow_mutation": ex.get("allow_mutation", False),
    }
    out = _Out()
    old_stdin = sys.stdin
    sys.stdin = io.StringIO("")  # input() raises EOFError instead of waiting for a keyboard that isn't there
    try:
        _harness.run_job(job, out, use_trace=True)
    finally:
        sys.stdin = old_stdin
        sys.settrace(None)
    return out.getvalue()


def _digest(source: str) -> str:
    return hashlib.sha1(source.encode("utf-8", "replace")).hexdigest()[:12]


def _case_dict(c) -> dict:
    return {
        "index": c.index, "tag": c.tag, "args": c.args, "expected": c.expected, "ok": c.ok, "got": c.got,
        "error": c.error, "printed": c.printed, "mutated": c.mutated, "hidden": c.hidden,
        # Python's own repr, so 2 and 2.0 (or 'a' and "a") are never confused on the page
        "call": ", ".join(repr(a) for a in c.args), "expected_repr": repr(c.expected), "got_repr": repr(c.got),
    }


def _progress(progress_json: str, today: str) -> Progress:
    from datetime import date

    try:
        data = json.loads(progress_json) if progress_json else {}
    except ValueError:
        data = {}
    return Progress(data=data if isinstance(data, dict) else {}, today=date.fromisoformat(today))


def _state(prog: Progress, exercise_id: str) -> dict:
    e = prog.ex(exercise_id)
    return {"fails": e["fails"], "hint_level": e["hint_level"], "max_level": e["max_level"], "hint_ready": e["hint_ready"],
            "solved": e["solved"], "due": e["due"], "box": e["box"], "hint_code": e["hint_code"]}


def finish_check(exercise_id: str, source: str, stdout: str, timed_out: bool, progress_json: str, today: str) -> str:
    """Turn a run into what the page shows, and record it in the progress (a pass, or a failed attempt)."""
    ex = _exercises[exercise_id]
    prog = _progress(progress_json, today)
    result = collect(stdout, "", timed_out, ex)
    findings = [] if result.passed else diagnose(source, ex, result)
    reply: dict = {
        "status": result.status, "info": result.info, "total": len(ex["cases"]),
        "ok_count": sum(c.ok for c in result.cases), "passed": result.passed,
        "cases": [_case_dict(c) for c in result.failing[:3]], "more_failing": max(0, len(result.failing) - 3),
    }
    if result.passed:
        reply["pass"] = prog.record_pass(exercise_id)
    else:
        top = findings[0] if findings else None
        prog.record_fail(exercise_id, top.code if top else None, sorted({f.concept for f in findings[:2]}), _digest(source))
    reply["state"] = _state(prog, exercise_id)
    reply["progress"] = prog.data
    return json.dumps(reply)


def finish_hint(exercise_id: str, source: str, stdout: str, timed_out: bool, progress_json: str, today: str, again: bool = False) -> str:
    """Like the CLI's `nudge hint`: look at the current code, and reveal the next rung (or show the current one again)."""
    ex = _exercises[exercise_id]
    prog = _progress(progress_json, today)
    result = collect(stdout, "", timed_out, ex)
    if result.passed:
        return json.dumps({"passes": True, "state": _state(prog, exercise_id), "progress": prog.data})
    findings = diagnose(source, ex, result)
    top = findings[0] if findings else None
    prog.set_hint_target(exercise_id, top.code if top else None)
    e = prog.ex(exercise_id)
    again = bool(again and e["hint_level"])
    if not again and not prog.hint_allowed(exercise_id):
        return json.dumps({"waiting": True, "state": _state(prog, exercise_id), "progress": prog.data})
    level = e["hint_level"] if again else next_hint(e["hint_level"], top, ex).level
    h = hint_at(level, top, ex)
    prog.record_hint(exercise_id, h.level)
    return json.dumps({
        "hint": {"level": h.level, "of": h.of, "title": h.title, "text": h.text},
        "code": top.code if top else "", "state": _state(prog, exercise_id), "progress": prog.data,
    })


def solution(exercise_id: str, progress_json: str, today: str, force: bool = False) -> str:
    ex = _exercises[exercise_id]
    prog = _progress(progress_json, today)
    e = prog.ex(exercise_id)
    why = solution_locked(e["fails"], e["max_level"])
    if why and not force:
        return json.dumps({"locked": why.replace("`nudge hint`", "the hint button"), "state": _state(prog, exercise_id), "progress": prog.data})
    prog.record_solution_seen(exercise_id)
    return json.dumps({"solution": ex["solution"].rstrip(), "state": _state(prog, exercise_id), "progress": prog.data})


def overview(progress_json: str, today: str) -> str:
    """Everything the sidebar needs: per-exercise status, what is due, what to do next, and where help is needed."""
    prog = _progress(progress_json, today)
    due = prog.due(_exercises)
    solved = prog.solved_ids() & set(_exercises)
    pick = prog.next_up(_exercises)
    items = []
    for eid, ex in _exercises.items():
        e = prog.data["exercises"].get(eid, {})
        items.append({"id": eid, "solved": eid in solved, "due": eid in due, "due_on": e.get("due", ""), "box": e.get("box", 0)})
    return json.dumps({
        "items": items, "solved": len(solved), "total": len(_exercises),
        "clean": sum(1 for i in solved if prog.data["exercises"][i].get("clean")),
        "due": due, "next": {"id": pick[0], "why": pick[1]} if pick else None,
        "weak": prog.weakest_concepts(),
        "progress": prog.data,
    })


def reset(exercise_id: str, progress_json: str, today: str) -> str:
    prog = _progress(progress_json, today)
    prog.reset(exercise_id)
    return json.dumps({"progress": prog.data})


def sanitise_progress(progress_json: str) -> str:
    """Used when restoring a backup: coerce any file shape into a valid progress."""
    return json.dumps(_progress(progress_json, "2000-01-01").data)
