"""Run a student's file against an exercise and collect what happened."""
from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

HARNESS = Path(__file__).with_name("_harness.py")
OVERALL_TIMEOUT = 20.0


@dataclass
class CaseResult:
    index: int
    tag: str
    args: list
    expected: object
    ok: bool
    got: object = None
    got_type: str = ""
    error: dict | None = None  # {"type", "msg", "line"}
    printed: str = ""
    mutated: bool = False
    hidden: bool = False


@dataclass
class RunResult:
    status: str  # "ok" | "syntax" | "load_error" | "no_function" | "crashed"
    cases: list[CaseResult] = field(default_factory=list)
    info: dict = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.status == "ok" and bool(self.cases) and all(c.ok for c in self.cases)

    @property
    def failing(self) -> list[CaseResult]:
        return [c for c in self.cases if not c.ok]


def run(source: str, exercise: dict, limit: float = 2.0) -> RunResult:
    cases = exercise["cases"]
    job = {
        "source": source,
        "function": exercise["function"],
        "cases": [{"args": c["args"], "expected": c["expected"], "tag": c.get("tag", "")} for c in cases],
        "limit": limit,
        "approx": exercise.get("approx", False),
        "allow_mutation": exercise.get("allow_mutation", False),
    }
    try:
        proc = subprocess.run(
            [sys.executable, "-I", str(HARNESS)],
            input=json.dumps(job),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=OVERALL_TIMEOUT,
        )
        stdout, stderr, timed_out = proc.stdout, proc.stderr, False
    except subprocess.TimeoutExpired as e:
        out = e.stdout or ""
        stdout = out.decode("utf-8", "replace") if isinstance(out, bytes) else out
        stderr, timed_out = "", True
    return collect(stdout, stderr, timed_out, exercise)


def collect(stdout: str, stderr: str, timed_out: bool, exercise: dict) -> RunResult:
    """Turn the harness's output lines into a RunResult."""
    cases = exercise["cases"]

    result = RunResult("ok")
    seen: set[int] = set()
    stopped = False
    for line in stdout.splitlines():
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        kind = msg.get("kind")
        if kind == "stopped":
            stopped = True
        if kind in ("syntax", "load_error", "no_function"):
            result.status, result.info = kind, msg
            return result
        if kind == "case":
            i = msg["i"]
            seen.add(i)
            c = cases[i]
            result.cases.append(
                CaseResult(
                    index=i,
                    tag=c.get("tag", ""),
                    args=c["args"],
                    expected=c["expected"],
                    ok=bool(msg.get("ok")),
                    got=msg.get("got"),
                    got_type=msg.get("type", ""),
                    error=msg.get("error"),
                    printed=msg.get("printed", ""),
                    mutated=bool(msg.get("mutated")),
                    hidden=bool(c.get("hidden")),
                )
            )
    # Anything that never reported (Windows, where a hung loop can't be interrupted per case, or a hard crash).
    for i, c in enumerate(cases):
        if i not in seen and not stopped:
            if timed_out:
                err = {"type": "Timeout", "msg": "took too long", "line": None}
            else:
                err = {"type": "Crashed", "msg": (stderr.strip().splitlines() or ["the program stopped"])[-1][:200], "line": None}
            result.cases.append(CaseResult(i, c.get("tag", ""), c["args"], c["expected"], False, error=err, hidden=bool(c.get("hidden"))))
            if not timed_out:
                result.status = "crashed" if not seen else result.status
            break  # later cases would only repeat the same failure
    result.cases.sort(key=lambda c: c.index)
    return result
