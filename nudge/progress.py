"""What the student has done so far, and when to bring things back for review.

Stored as one small JSON file (default ~/.nudge/progress.json, or $NUDGE_HOME).
Review follows the Leitner method: solve an exercise without needing a big hint and
it moves to a box with a longer wait; struggle and it returns to box 1.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

INTERVALS = [1, 2, 4, 8, 16]  # days to wait in box 1..5
CLEAN_LEVEL = 2  # hints up to this level (where to look / what to think about) still count as "on your own"


def _default_entry() -> dict:
    return {"attempts": 0, "fails": 0, "solved": False, "clean": False, "max_level": 0, "hint_level": 0, "hint_code": "", "solution_seen": False, "box": 0, "due": None, "solved_on": None, "reviews": 0, "last_hash": "", "hint_ready": True}


def _int(v, default=0) -> int:
    try:
        return max(0, int(v))
    except (TypeError, ValueError):
        return default


def sanitise(raw) -> dict:
    """Whatever is in the file, return something safe to use (a damaged or hand-edited file must not crash practice)."""
    out: dict = {"exercises": {}, "concept_trouble": {}}
    if not isinstance(raw, dict):
        return out
    ex = raw.get("exercises")
    if isinstance(ex, dict):
        for eid, e in ex.items():
            if not isinstance(e, dict):
                continue
            d = _default_entry()
            for k in ("attempts", "fails", "max_level", "hint_level", "reviews"):
                d[k] = _int(e.get(k))
            d["box"] = min(5, _int(e.get("box")))
            for k in ("solved", "clean", "solution_seen", "hint_ready"):
                d[k] = bool(e.get(k, d[k]))
            for k in ("hint_code", "last_hash"):
                d[k] = e.get(k) if isinstance(e.get(k), str) else ""
            for k in ("due", "solved_on"):
                v = e.get(k)
                try:
                    date.fromisoformat(v)
                    d[k] = v
                except (TypeError, ValueError):
                    d[k] = None
            if d["solved"] and not d["due"]:
                d["due"] = date.today().isoformat()
            if d["solved"] and d["box"] < 1:
                d["box"] = 1
            out["exercises"][str(eid)] = d
    ct = raw.get("concept_trouble")
    if isinstance(ct, dict):
        out["concept_trouble"] = {str(k): _int(v) for k, v in ct.items() if _int(v) > 0}
    return out


def home() -> Path:
    return Path(os.environ.get("NUDGE_HOME") or Path.home() / ".nudge")


class Progress:
    def __init__(self, path: Path | None = None, today: date | None = None, data: dict | None = None):
        """With ``data`` the progress lives in memory only and is never written (used by tests)."""
        self.memory = data is not None
        self._warned = False
        self.path = path or home() / "progress.json"
        self.today = today or date.today()
        self.data: dict = {"exercises": {}, "concept_trouble": {}}
        if self.memory:
            self.data = sanitise(data)
        elif self.path.exists():
            try:
                loaded = json.loads(self.path.read_text(encoding="utf-8-sig"))
            except (OSError, ValueError):
                loaded = None
            if isinstance(loaded, dict) and isinstance(loaded.get("exercises", {}), dict):
                self.data = sanitise(loaded)
            else:
                # Not something we wrote. Keep a copy and start fresh instead of silently overwriting it.
                try:
                    self.path.replace(self.path.with_suffix(".broken"))
                except OSError:
                    pass

    # -- storage
    def save(self) -> None:
        if self.memory:
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.data, indent=1), encoding="utf-8")
            tmp.replace(self.path)
        except OSError as e:
            if not self._warned:
                print(f"nudge: could not save your progress to {self.path} ({e.strerror or e})", file=sys.stderr)
                self._warned = True

    def ex(self, exercise_id: str) -> dict:
        return self.data["exercises"].setdefault(exercise_id, _default_entry())

    # -- events
    def record_fail(self, exercise_id: str, top_code: str | None, concepts: list[str], source_hash: str = "") -> None:
        """A failed check. Running the same unchanged file again is not a new attempt (it can't unlock the solution)."""
        e = self.ex(exercise_id)
        e["hint_ready"] = True
        if source_hash and source_hash == e["last_hash"]:
            self.save()
            return
        e["last_hash"] = source_hash
        e["attempts"] += 1
        e["fails"] += 1
        if top_code and top_code != e["hint_code"]:
            e["hint_code"], e["hint_level"] = top_code, 0  # a different problem now: start the ladder again
        for c in concepts:
            self.data["concept_trouble"][c] = self.data["concept_trouble"].get(c, 0) + 1
        self.save()

    def set_hint_target(self, exercise_id: str, top_code: str | None) -> None:
        """The ladder belongs to one problem at a time; a different top problem starts it again."""
        e = self.ex(exercise_id)
        if top_code and top_code != e["hint_code"]:
            e["hint_code"], e["hint_level"] = top_code, 0
            self.save()

    def hint_allowed(self, exercise_id: str) -> bool:
        """The next rung needs a check in between (and so a chance to change the code)."""
        e = self.ex(exercise_id)
        return e["hint_level"] == 0 or e["hint_ready"]

    def record_hint(self, exercise_id: str, level: int) -> None:
        e = self.ex(exercise_id)
        e["hint_ready"] = False
        e["hint_level"] = max(e["hint_level"], level)
        e["max_level"] = max(e["max_level"], level)
        self.save()

    def record_solution_seen(self, exercise_id: str) -> None:
        self.ex(exercise_id)["solution_seen"] = True
        self.save()

    def record_pass(self, exercise_id: str) -> dict:
        """Returns what happened: {"first": bool, "clean": bool, "box": int, "due": str}."""
        e = self.ex(exercise_id)
        if e["solved"] and e["due"] and e["due"] > self.today.isoformat():
            # Passing again before it is due is fine, but it is not a review: don't move the box.
            return {"first": False, "clean": True, "box": e["box"], "due": e["due"], "not_due": True}
        e["attempts"] += 1
        clean = e["max_level"] <= CLEAN_LEVEL and not e["solution_seen"]
        first = not e["solved"]
        if first:
            e["solved"], e["solved_on"] = True, self.today.isoformat()
            e["clean"] = clean
            e["box"] = 2 if clean else 1
        else:
            e["reviews"] += 1
            e["box"] = min(5, e["box"] + 1) if clean else 1
        e["due"] = (self.today + timedelta(days=INTERVALS[e["box"] - 1])).isoformat()
        e["hint_level"], e["hint_code"], e["max_level"], e["solution_seen"], e["last_hash"], e["hint_ready"] = 0, "", 0, False, "", True
        self.save()
        return {"first": first, "clean": clean, "box": e["box"], "due": e["due"], "not_due": False}

    def reset(self, exercise_id: str) -> None:
        self.data["exercises"].pop(exercise_id, None)
        self.save()

    # -- queries
    def due(self, exercises: dict[str, dict]) -> list[str]:
        out = []
        for eid, e in self.data["exercises"].items():
            if eid in exercises and e.get("solved") and e.get("due") and e["due"] <= self.today.isoformat():
                out.append(eid)
        return sorted(out, key=lambda i: self.data["exercises"][i]["due"])

    def solved_ids(self) -> set[str]:
        return {i for i, e in self.data["exercises"].items() if e.get("solved")}

    def weakest_concepts(self, n: int = 3) -> list[tuple[str, int]]:
        t = self.data["concept_trouble"]
        return sorted(((c, k) for c, k in t.items() if k > 0), key=lambda kv: -kv[1])[:n]

    def next_up(self, exercises: dict[str, dict]) -> tuple[str, str] | None:
        """(exercise id, reason): a due review first, else a new exercise on a shaky concept, else the next one in order."""
        due = self.due(exercises)
        if due:
            return due[0], "due for review"
        solved = self.solved_ids()
        todo = [i for i in exercises if i not in solved]
        if not todo:
            return None
        weak = [c for c, _ in self.weakest_concepts(3)]
        # Only lean on weak concepts once the student has done a few; early on, just go in order.
        if len(solved) >= 3 and weak:
            lowest = min(exercises[i]["level"] for i in todo)
            pool = [i for i in todo if exercises[i]["level"] <= lowest + 1]
            for c in weak:
                for i in pool:
                    if c in exercises[i]["concepts"]:
                        return i, f"practises '{c}', which has been tricky"
        return todo[0], "next in order"
