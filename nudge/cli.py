"""Command line: nudge list | show | start | check | hint | solution | next | stats | reset | validate"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__, exercises as exlib
from .diagnose import Finding, diagnose
from .hints import BASE_LEVELS, hint_at, next_hint, solution_locked, total_levels
from .progress import Progress
from .runner import RunResult, run

SHOW_FAILS = 3


def out(*a) -> None:
    print(*a)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return path.read_text(encoding="cp1252")


def resolve(target: str | None, exercise_id_hint: str | None = None) -> tuple[dict, Path]:
    """`nudge check sum_list`, `nudge check sum_list.py` and `nudge check some/dir/sum_list.py` all work."""
    if not target:
        raise exlib.ExerciseError("say which exercise, for example: nudge check sum_list")
    p = Path(target)
    if p.suffix == ".py" or p.exists():
        ex = exlib.get(p.stem)
        if not p.exists():
            raise exlib.ExerciseError(f"{p} doesn't exist yet. Create it with: nudge start {ex['id']}")
        return ex, p
    ex = exlib.get(target)
    path = Path.cwd() / f"{ex['id']}.py"
    if not path.exists():
        raise exlib.ExerciseError(f"there is no {path.name} in this folder yet. Create it with: nudge start {ex['id']}")
    return ex, path


def _show_case(ex: dict, c, limit: int = 120) -> None:
    args = ", ".join(repr(a) for a in c.args)
    label = "hidden test" if c.hidden else "test"
    out(f"  [FAIL] {ex['function']}({args})"[:limit + 20] + ("  (hidden test)" if c.hidden else ""))
    if c.error:
        e = c.error
        where = f" on line {e['line']}" if e.get("line") else ""
        out(f"         {e['type']}{where}: {e.get('msg', '')}"[:limit + 20])
    else:
        out(f"         expected {c.expected!r}, got {c.got!r}")
        if c.printed.strip():
            out(f"         (your code printed {c.printed.strip()[:60]!r}, but tests read what you return)")
    del label


def _diagnose_file(ex: dict, path: Path) -> tuple[RunResult, list[Finding], str]:
    source = _read(path)
    result = run(source, ex)
    findings = [] if result.passed else diagnose(source, ex, result)
    return result, findings, source


def cmd_list(args, prog: Progress) -> int:
    exs = exlib.load_all()
    due = set(prog.due(exs))
    solved = prog.solved_ids()
    last = None
    for eid, ex in exs.items():
        if ex["level"] != last:
            last = ex["level"]
            out(f"\nLevel {last}")
        mark = "review due" if eid in due else ("solved" if eid in solved else "")
        out(f"  {eid:<22} {ex['title']:<44} {mark}")
    out(f"\n{len(solved)} of {len(exs)} solved. Start one with: nudge start <name>")
    return 0


def cmd_show(args, prog: Progress) -> int:
    ex = exlib.get(args.exercise)
    out(f"{ex['title']}   (level {ex['level']}; practises: {', '.join(ex['concepts'])})\n")
    out(ex["prompt"].strip() + "\n")
    shown = [c for c in ex["cases"] if not c.get("hidden")][:3]
    out("Examples:")
    for c in shown:
        out(f"  {ex['function']}({', '.join(repr(a) for a in c['args'])})  ->  {c['expected']!r}")
    out(f"\nWrite your answer in {ex['id']}.py, then run: nudge check {ex['id']}")
    return 0


def cmd_start(args, prog: Progress) -> int:
    ex = exlib.get(args.exercise)
    path = Path.cwd() / f"{ex['id']}.py"
    if path.exists():
        out(f"{path.name} already exists, so I left it alone.\n")
    else:
        path.write_text(ex["starter"], encoding="utf-8")
        out(f"Created {path.name}. Open it and write your answer.\n")
    cmd_show(args, prog)
    return 0


def cmd_check(args, prog: Progress) -> int:
    ex, path = resolve(args.exercise)
    result, findings, _ = _diagnose_file(ex, path)
    if result.passed:
        info = prog.record_pass(ex["id"])
        n = len(result.cases)
        out(f"[PASS] {ex['id']}: all {n} tests pass.")
        if info["first"]:
            out("Solved on your own: no big hints needed." if info["clean"] else "Solved, with help. It will come back for review sooner, which is how it sticks.")
        else:
            out("Review passed." if info["clean"] else "Passed, but you needed help, so it goes back to the start of the review cycle.")
        out(f"Next review: {info['due']}.   Run `nudge next` for what to do now.")
        return 0

    top = findings[0] if findings else None
    prog.record_fail(ex["id"], top.code if top else None, sorted({f.concept for f in findings[:2]}))
    e = prog.ex(ex["id"])
    ok = sum(c.ok for c in result.cases)
    out(f"[FAIL] {ex['id']}: {ok} of {len(result.cases)} tests pass.\n")
    if result.status == "syntax":
        out(f"  Python could not read the file: {result.info.get('msg')} (line {result.info.get('line')})")
    elif result.status == "no_function":
        out(f"  No function called {ex['function']} found.")
    elif result.status == "load_error":
        err = result.info.get("error", {})
        out(f"  Running the file raised {err.get('type')}: {err.get('msg')}")
    else:
        for c in result.failing[:SHOW_FAILS]:
            _show_case(ex, c)
        if len(result.failing) > SHOW_FAILS:
            out(f"  ... and {len(result.failing) - SHOW_FAILS} more failing")
    out(f"\nStuck? Run: nudge hint {ex['id']}      (attempt {e['fails']})")
    return 1


def cmd_hint(args, prog: Progress) -> int:
    ex, path = resolve(args.exercise)
    result, findings, _ = _diagnose_file(ex, path)
    if result.passed:
        out("Your file already passes every test. Nothing to hint at.")
        return 0
    top = findings[0] if findings else None
    prog.set_hint_target(ex["id"], top.code if top else None)
    e = prog.ex(ex["id"])
    level = e["hint_level"] if args.again and e["hint_level"] else next_hint(e["hint_level"], top, ex).level
    h = hint_at(level, top, ex)
    prog.record_hint(ex["id"], h.level)
    out(f"Hint {h.level} of {h.of}: {h.title}\n")
    out(h.text)
    if h.level < h.of:
        out(f"\nStill stuck? Fix what you can, run `nudge check {ex['id']}`, then `nudge hint {ex['id']}` for the next step.")
    else:
        out("\nThat's every hint. If you're still stuck, `nudge solution` may be unlocked.")
    return 0


def cmd_solution(args, prog: Progress) -> int:
    ex = exlib.get(args.exercise)
    e = prog.ex(ex["id"])
    why = solution_locked(e["fails"], e["max_level"])
    if why and not args.force:
        out(why)
        return 1
    prog.record_solution_seen(ex["id"])
    out(f"One way to solve {ex['id']}:\n")
    out(ex["solution"].rstrip())
    out("\nRead it, close it, and write it again from memory. That is what makes it stick. It will come back for review.")
    return 0


def cmd_next(args, prog: Progress) -> int:
    exs = exlib.load_all()
    pick = prog.next_up(exs)
    if not pick:
        out("You've solved everything. Come back when reviews are due.")
        return 0
    eid, why = pick
    out(f"Next: {eid}  ({why})\n")
    args.exercise = eid
    return cmd_start(args, prog)


def cmd_stats(args, prog: Progress) -> int:
    exs = exlib.load_all()
    solved = prog.solved_ids()
    clean = sum(1 for i in solved if prog.ex(i)["clean"])
    out(f"Solved: {len(solved)} of {len(exs)}   ({clean} on your own)")
    due = prog.due(exs)
    out(f"Reviews due today: {', '.join(due) if due else 'none'}")
    by: dict[str, list[int]] = {}
    for eid, ex in exs.items():
        for c in ex["concepts"]:
            by.setdefault(c, [0, 0])
            by[c][1] += 1
            by[c][0] += eid in solved
    out("\nBy topic (solved/total):")
    for c, (s, t) in sorted(by.items()):
        out(f"  {c:<18} {s}/{t}  {'#' * s}{'.' * (t - s)}")
    weak = prog.weakest_concepts()
    if weak:
        out("\nWhere you've had the most trouble: " + ", ".join(f"{c} ({n})" for c, n in weak))
    return 0


def cmd_reset(args, prog: Progress) -> int:
    ex = exlib.get(args.exercise)
    prog.reset(ex["id"])
    out(f"Progress for {ex['id']} cleared (your file is untouched).")
    return 0


def cmd_validate(args, prog: Progress) -> int:
    """For exercise authors: every reference solution must pass, every starter must fail."""
    bad = 0
    for eid, ex in exlib.load_all().items():
        sol = run(ex["solution"], ex)
        start = run(ex["starter"], ex)
        problems = []
        if not sol.passed:
            problems.append("reference solution fails: " + ", ".join(f"case {c.index}" for c in sol.failing[:3]))
        if start.passed:
            problems.append("starter already passes")
        if problems:
            bad += 1
            out(f"[BAD] {eid}: {'; '.join(problems)}")
        elif args.verbose:
            out(f"[ok]  {eid}")
    out(f"\n{'All exercises valid.' if not bad else str(bad) + ' problem(s).'}")
    return 1 if bad else 0


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(prog="nudge", description="Practise Python. Get hints that nudge, not answers that spoil.")
    ap.add_argument("--version", action="version", version=f"nudge {__version__}")
    sub = ap.add_subparsers(dest="cmd")
    for name, fn, helptext in (
        ("list", cmd_list, "show all exercises"),
        ("next", cmd_next, "what to practise now"),
        ("stats", cmd_stats, "your progress by topic"),
    ):
        sub.add_parser(name, help=helptext).set_defaults(fn=fn)
    for name, fn, helptext in (
        ("show", cmd_show, "read an exercise"),
        ("start", cmd_start, "create the starter file for an exercise"),
        ("check", cmd_check, "run the tests on your file"),
        ("hint", cmd_hint, "get the next hint"),
        ("solution", cmd_solution, "see a solution (unlocks after real attempts)"),
        ("reset", cmd_reset, "forget your progress on one exercise"),
    ):
        p = sub.add_parser(name, help=helptext)
        p.add_argument("exercise", help="exercise name, or your file (for example sum_list.py)")
        if name == "hint":
            p.add_argument("--again", action="store_true", help="show the current hint again")
        if name == "solution":
            p.add_argument("--force", action="store_true", help="skip the unlock rule (not recommended)")
        p.set_defaults(fn=fn)
    p = sub.add_parser("validate", help="(for authors) check every exercise's tests")
    p.add_argument("-v", "--verbose", action="store_true")
    p.set_defaults(fn=cmd_validate)

    args = ap.parse_args(argv)
    if not getattr(args, "fn", None):
        ap.print_help()
        return 0
    try:
        return args.fn(args, Progress())
    except exlib.ExerciseError as e:
        print(f"nudge: {e}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130
