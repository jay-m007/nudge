"""Loading exercises (one JSON file each, with tests, hints and a reference solution)."""
from __future__ import annotations

import json
from pathlib import Path

DIR = Path(__file__).with_name("exercises")
REQUIRED = ("id", "title", "level", "concepts", "function", "prompt", "starter", "cases", "hints", "solution")


class ExerciseError(ValueError):
    pass


def validate(ex: dict, where: str = "exercise") -> None:
    for key in REQUIRED:
        if key not in ex:
            raise ExerciseError(f"{where}: missing '{key}'")
    if not ex["cases"]:
        raise ExerciseError(f"{where}: no test cases")
    if len(ex["hints"]) < 3:
        raise ExerciseError(f"{where}: needs at least 3 approach hints")
    for i, c in enumerate(ex["cases"]):
        if "args" not in c or "expected" not in c:
            raise ExerciseError(f"{where}: case {i} needs args and expected")


def load_all() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for p in sorted(DIR.glob("*.json")):
        ex = json.loads(p.read_text(encoding="utf-8"))
        validate(ex, p.name)
        if ex["id"] in out:
            raise ExerciseError(f"duplicate id {ex['id']}")
        out[ex["id"]] = ex
    return dict(sorted(out.items(), key=lambda kv: (kv[1]["level"], kv[0])))


def get(exercise_id: str) -> dict:
    allx = load_all()
    if exercise_id in allx:
        return allx[exercise_id]
    close = [k for k in allx if exercise_id in k]
    hint = f" Did you mean: {', '.join(close[:3])}?" if close else " Run `nudge list` to see them."
    raise ExerciseError(f"no exercise called '{exercise_id}'.{hint}")
