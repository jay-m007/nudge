"""Run Nudge on tests/heldout.json (buggy submissions written by someone who had not seen
the hint rules) and save the hints it gives, for grading.

  python tools/heldout.py out.json
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nudge import exercises as exlib  # noqa: E402
from nudge.diagnose import diagnose  # noqa: E402
from nudge.hints import hint_at  # noqa: E402
from nudge.runner import run  # noqa: E402

GENERIC = {"wrong_answer", "runtime_other", "syntax_other", "crashed"}


def main(out_path: str) -> None:
    items = json.loads((Path(__file__).resolve().parent.parent / "tests" / "heldout.json").read_text(encoding="utf-8"))
    exs = exlib.load_all()
    rows = []
    for i, it in enumerate(items):
        ex = exs[it["exercise"]]
        res = run(it["source"], ex, limit=0.5)
        if res.passed:
            rows.append(dict(id=i, **it, passed=True))
            continue
        fs = diagnose(it["source"], ex, res)
        top = fs[0]
        rows.append(dict(
            id=i, exercise=it["exercise"], kind=it["kind"], cause=it["cause"], source=it["source"], passed=False,
            top=top.code, generic=top.code in GENERIC, others=[f.code for f in fs[1:4]],
            hints=[hint_at(l, top, ex).text for l in (1, 2, 3)],
        ))
    Path(out_path).write_text(json.dumps(rows, indent=1), encoding="utf-8")
    failed = [r for r in rows if not r["passed"]]
    print(f"{len(rows)} submissions, {len(failed)} fail the tests")
    print(f"specific top hint: {sum(not r['generic'] for r in failed)} / {len(failed)}")
    print(Counter(r["top"] for r in failed).most_common())


if __name__ == "__main__":
    main(sys.argv[1])
