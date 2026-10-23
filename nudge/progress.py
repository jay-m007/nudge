"""What the student has done so far, and when to bring things back for review.

Stored as one small JSON file (default ~/.nudge/progress.json, or $NUDGE_HOME).
Review follows the Leitner method: solve an exercise without needing a big hint and
it moves to a box with a longer wait; struggle and it returns to box 1.
"""
from __future__ import annotations

import json
import os
from datetime import date, timedelta
from pathlib import Path

INTERVALS = [1, 2, 4, 8, 16]  # days to wait in box 1..5
CLEAN_LEVEL = 2  # hints up to this level (where to look / what to think about) still count as "on your own"


def home() -> Path:
    return Path(os.environ.get("NUDGE_HOME") or Path.home() / ".nudge")


class Progress:
    def __init__(self, path: Path | None = None, today: date | None = None, data: dict | None = None):
        """With ``data`` the progress lives in memory only (the browser version keeps it in localStorage)."""
        self.memory = data is not None
        self.path = path or home() / "progress.json"
        self.today = today or date.today()
        self.data: dict = {"exercises": {}, "concept_trouble": {}}
        if self.memory:
            if isinstance(data.get("exercises"), dict):
                self.data.update(data)
        elif self.path.exists():
            try:
                loaded = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict) and isinstance(loaded.get("exercises"), dict):
                    self.data.update(loaded)
            except (OSError, ValueError):
                # A damaged file shouldn't block practice; keep a copy and start fresh.
                try:
                    self.path.replace(self.path.with_suffix(".broken"))
                except OSError:
                    pass

    # -- storage
    def save(self) -> None:
        if self.memory:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=1), encoding="utf-8")
        tmp.replace(self.path)

    def ex(self, exercise_id: str) -> dict:
        return self.data["exercises"].setdefault(
            exercise_id,
            {"attempts": 0, "fails": 0, "solved": False, "clean": False, "max_level": 0, "hint_level": 0, "hint_code": "", "solution_seen": False, "box": 0, "due": None, "solved_on": None, "reviews": 0},
        )

    # -- events
    def record_fail(self, exercise_id: str, top_code: str | None, concepts: list[str]) -> None:
        e = self.ex(exercise_id)
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

    def record_hint(self, exercise_id: str, level: int) -> None:
        e = self.ex(exercise_id)
        e["hint_level"] = max(e["hint_level"], level)
        e["max_level"] = max(e["max_level"], level)
        self.save()

    def record_solution_seen(self, exercise_id: str) -> None:
        self.ex(exercise_id)["solution_seen"] = True
        self.save()

    def record_pass(self, exercise_id: str) -> dict:
        """Returns what happened: {"first": bool, "clean": bool, "box": int, "due": str}."""
        e = self.ex(exercise_id)
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
        e["hint_level"], e["hint_code"], e["max_level"], e["solution_seen"] = 0, "", 0, False
        self.save()
        return {"first": first, "clean": clean, "box": e["box"], "due": e["due"]}

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
