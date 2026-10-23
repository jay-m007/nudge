"""Does Nudge help on realistic mistakes? Break each reference solution in small,
typical ways (mutation testing) and measure what the engine does with the result.

Mutations: flip a comparison, change a number by 1, swap + and -, drop a return
value, delete a statement, swap and/or, remove a `not`, negate a condition.

For every mutant we ask:
  killed      do the tests notice it? (survivors are either harmless or a hole in the tests)
  specific    does the top hint name a concrete cause, not the generic "trace it by hand"?
  line hit    when a hint points at a line, is it the line that was changed?
  leak        does any hint at levels 1-4 repeat a line of the reference solution?

Run:  python tools/evaluate.py [--json out.json] [--dump mutants.json]
"""
from __future__ import annotations

import argparse
import ast
import copy
import difflib
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nudge import exercises as exlib  # noqa: E402
from nudge.diagnose import diagnose  # noqa: E402
from nudge.hints import BASE_LEVELS, hint_at  # noqa: E402
from nudge.runner import run  # noqa: E402

GENERIC = {"wrong_answer", "runtime_other", "syntax_other", "crashed"}


# ---------------------------------------------------------------- mutation operators

def _flip_compare(n):
    if isinstance(n, ast.Compare) and len(n.ops) == 1:
        swap = {ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt, ast.Eq: ast.NotEq, ast.NotEq: ast.Eq}
        t = type(n.ops[0])
        if t in swap:
            n.ops[0] = swap[t]()
            return "flip-compare"


def _const_pm1(n):
    if isinstance(n, ast.Constant) and type(n.value) is int and not isinstance(n.value, bool):
        n.value += 1
        return "constant+1"


def _const_m1(n):
    if isinstance(n, ast.Constant) and type(n.value) is int and not isinstance(n.value, bool) and n.value > 0:
        n.value -= 1
        return "constant-1"


def _swap_arith(n):
    if isinstance(n, ast.BinOp):
        swap = {ast.Add: ast.Sub, ast.Sub: ast.Add, ast.FloorDiv: ast.Div, ast.Mod: ast.FloorDiv, ast.Mult: ast.Add}
        t = type(n.op)
        if t in swap:
            n.op = swap[t]()
            return "swap-arithmetic"
    if isinstance(n, ast.AugAssign):
        swap = {ast.Add: ast.Sub, ast.Sub: ast.Add, ast.FloorDiv: ast.Div}
        t = type(n.op)
        if t in swap:
            n.op = swap[t]()
            return "swap-arithmetic"


def _drop_return_value(n):
    if isinstance(n, ast.Return) and n.value is not None:
        n.value = None
        return "drop-return-value"


def _swap_boolop(n):
    if isinstance(n, ast.BoolOp):
        n.op = ast.Or() if isinstance(n.op, ast.And) else ast.And()
        return "swap-and-or"


def _remove_not(n):
    if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.Not):
        return "remove-not"


def _negate_if(n):
    if isinstance(n, (ast.If, ast.While)):
        n.test = ast.UnaryOp(op=ast.Not(), operand=n.test)
        return "negate-condition"


def _delete_stmt(n):
    return "delete-statement" if isinstance(n, (ast.Assign, ast.AugAssign, ast.Expr)) else None


OPS = [_flip_compare, _const_pm1, _const_m1, _swap_arith, _drop_return_value, _swap_boolop, _remove_not, _negate_if, _delete_stmt]


def sites(tree):
    """(operator, node index in walk order) for every place a mutation can apply."""
    out = []
    nodes = list(ast.walk(tree))
    for op in OPS:
        for i, n in enumerate(nodes):
            probe = copy.deepcopy(n)
            if op is _remove_not or op is _delete_stmt:
                ok = op(probe)
            else:
                ok = op(probe)
            if ok:
                out.append((op, i))
    return out


def apply(tree, op, index):
    tree = copy.deepcopy(tree)
    nodes = list(ast.walk(tree))
    target = nodes[index]
    if op is _remove_not:
        parent = next(p for p in nodes for c in ast.iter_child_nodes(p) if c is target)
        for field, value in ast.iter_fields(parent):
            if value is target:
                setattr(parent, field, target.operand)
            elif isinstance(value, list):
                for k, v in enumerate(value):
                    if v is target:
                        value[k] = target.operand
        kind = "remove-not"
    elif op is _delete_stmt:
        parent = next(p for p in nodes for c in ast.iter_child_nodes(p) if c is target)
        for field, value in ast.iter_fields(parent):
            if isinstance(value, list) and any(v is target for v in value):
                value[:] = [v for v in value if v is not target] or [ast.Pass()]
        kind = "delete-statement"
    else:
        kind = op(target)
    ast.fix_missing_locations(tree)
    return tree, kind


def changed_lines(before: str, after: str) -> set[int]:
    a, b = before.splitlines(), after.splitlines()
    out = set()
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
        if tag != "equal":
            out.update(range(j1 + 1, max(j2, j1 + 1) + 1))
            out.add(i1 + 1)
    return out


# ---------------------------------------------------------------- evaluation

def leak_lines(solution: str) -> set[str]:
    return {ln.strip() for ln in solution.splitlines() if len(ln.strip()) >= 14 and not ln.strip().startswith("def ")}


def evaluate(limit_per_ex: int, seed: int, dump: list | None = None):
    rng = random.Random(seed)
    rows = []
    per_op = defaultdict(lambda: Counter())
    for eid, ex in exlib.load_all().items():
        base_src = ast.unparse(ast.parse(ex["solution"]))
        tree = ast.parse(base_src)
        found = sites(tree)
        rng.shuffle(found)
        seen_src = {base_src}
        mutants = []
        for op, idx in found:
            try:
                mt, kind = apply(tree, op, idx)
                src = ast.unparse(mt)
            except Exception:
                continue
            if src in seen_src:
                continue
            seen_src.add(src)
            mutants.append((kind, src))
            if len(mutants) >= limit_per_ex:
                break
        leaks = leak_lines(base_src)
        for kind, src in mutants:
            res = run(src, ex, limit=0.3)
            killed = not res.passed
            row = dict(exercise=eid, kind=kind, killed=killed)
            per_op[kind]["total"] += 1
            if killed:
                per_op[kind]["killed"] += 1
                fs = diagnose(src, ex, res)
                top = fs[0]
                row["top"] = top.code
                row["specific"] = top.code not in GENERIC
                lines = changed_lines(base_src, src)
                row["origin"] = top.origin
                # Only code-shape hints claim to name the cause. A traceback line is where Python
                # *crashed*, which can be well after the mistake, so it is not scored here.
                row["has_line"] = top.line is not None and top.origin == "lint"
                row["line_hit"] = bool(row["has_line"] and (top.line in lines or top.line - 1 in lines or top.line + 1 in lines))
                texts = []
                for lvl in range(1, BASE_LEVELS + 1):
                    texts.append(hint_at(lvl, top, ex).text)
                row["leak"] = any(l in t for l in leaks for t in texts)
                if row["specific"] is False:
                    per_op[kind]["generic"] += 1
            if dump is not None:
                dump.append(dict(row, source=src))
            rows.append(row)
    return rows, per_op


def summarize(rows, per_op):
    total = len(rows)
    killed = [r for r in rows if r["killed"]]
    spec = [r for r in killed if r["specific"]]
    lined = [r for r in killed if r["has_line"]]
    hit = [r for r in lined if r["line_hit"]]
    leak = [r for r in killed if r["leak"]]
    tops = Counter(r["top"] for r in killed)
    return dict(
        mutants=total, killed=len(killed), survived=total - len(killed),
        kill_rate=len(killed) / total if total else 0,
        specific_rate=len(spec) / len(killed) if killed else 0,
        line_given=len(lined), line_hit_rate=len(hit) / len(lined) if lined else 0,
        leaks=len(leak),
        top_codes=dict(tops.most_common()),
        by_operator={k: dict(v) for k, v in sorted(per_op.items())},
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-exercise", type=int, default=18)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--json")
    ap.add_argument("--dump")
    a = ap.parse_args()
    dump: list | None = [] if a.dump else None
    rows, per_op = evaluate(a.per_exercise, a.seed, dump)
    s = summarize(rows, per_op)
    print(f"mutants: {s['mutants']}   killed by tests: {s['killed']} ({s['kill_rate']:.0%})   survived: {s['survived']}")
    print(f"top hint names a specific cause: {s['specific_rate']:.0%} of killed mutants")
    print(f"code-shape hints that name a line: {s['line_given']}; of those, the line is the changed one (+/-1): {s['line_hit_rate']:.0%}")
    print(f"hints (levels 1-4) that repeat a line of the solution: {s['leaks']}")
    print("\nby mutation:")
    for k, v in s["by_operator"].items():
        print(f"  {k:<20} total {v['total']:>3}  killed {v.get('killed', 0):>3}  generic hint {v.get('generic', 0):>3}")
    print("\ntop hint given:")
    for c, n in s["top_codes"].items():
        print(f"  {c:<22} {n}")
    if a.json:
        Path(a.json).write_text(json.dumps(s, indent=1), encoding="utf-8")
    if dump is not None:
        Path(a.dump).write_text(json.dumps(dump, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
