# Nudge

**Practise Python and get hints that nudge, not answers that spoil. Offline, free, no AI model.**

```text
$ nudge check total
[FAIL] total: 2 of 7 tests pass.

  [FAIL] total([1, 2, 3])
         expected 6, got 1
  ...
Stuck? Run: nudge hint total      (attempt 1)

$ nudge hint total
Hint 1 of 7: Where to look
The answer is right only when the first item decides everything. Your loop may end too early.

$ nudge hint total          # a second ask goes one step further
Hint 2 of 7: What to think about
A return inside a loop ends the whole function the first time it runs.
```

## Why this exists

Coding schools such as WhiteHat Jr, Dev Bootcamp, The Iron Yard and Juni Learning died of the same thing: the help students needed came from human tutors, and tutors cost more than students paid. Nudge replaces the part of a tutor that answers "why does my code fail?" with rules that read the error, the wrong answers and the code, so it costs nothing to run and works without internet.

It does **not** replace a teacher for new ideas, and it has not been tested on real learners (see [Limits](#limits)).

## Install and use

Needs Python 3.9 or newer.

```bash
git clone https://github.com/jay-m007/nudge
cd nudge
python -m pip install -e .

mkdir practice && cd practice
nudge list                  # 27 exercises in 3 levels
nudge next                  # what to practise now (reviews first)
nudge start total           # creates total.py with a starter
#   ...edit total.py...
nudge check total           # run the tests
nudge hint total            # next hint
nudge solution total        # locked until you have really tried
nudge stats                 # progress by topic
```

If the `nudge` command isn't found, use `python -m nudge ...` instead. Your progress is stored in `~/.nudge/progress.json` (set `NUDGE_HOME` to move it).

## How the hints work

**1. Diagnosis from three kinds of evidence** (`nudge/diagnose.py`, all plain readable rules):

| Evidence | Examples of what it recognises |
|---|---|
| The Python error | syntax slips (missing colon, `=` for `==`, `else if`, `&&`), NameError with "did you mean", IndexError, KeyError, ZeroDivisionError, `None` has no attribute, infinite loop, recursion with no base case, exponential recursion |
| The pattern in the wrong answers | forgot `return`, printed instead of returning, always off by one, right items in wrong order, only capitals/spaces differ, answer stops early, answer never changes, changed the input list |
| The shape of the code, read with `ast` | `return` inside a loop, accumulator reset every pass, `range` off by one, changing a list while looping over it, shadowing a built-in, mutable default argument, result of `.lower()` thrown away, ignored parameter |

It also finds what the *failing inputs have in common* (for example: every failing input has capital letters, and almost none of the passing ones do) and points at that.

**2. A ladder, one rung per request** (`nudge/hints.py`): where to look, what to think about, the exact spot, a small worked example on a *different* problem, then the exercise author's own approach hints. When no rule matches, it teaches debugging by contrast: the smallest failing input, the closest passing one, and where the output first differs.

**3. The solution is locked** until you have failed at least 3 *different* versions of your file with `check` *and* reached the worked example. Re-running an unchanged file doesn't count, and the next hint needs a `check` in between, so the lock can't be opened by repeating commands. Looking at the solution marks the exercise as "needed help". (`--force` skips the lock, for teachers.)

**4. Spaced review** (`nudge/progress.py`): solving without a big hint moves an exercise to a longer review interval (1, 2, 4, 8, 16 days, the Leitner method); needing help sends it back. Passing again before the review is due is fine but doesn't move the schedule. `nudge next` brings due reviews first, then exercises on topics you struggled with.

## Does it work? What was measured

Two checks, both reproducible. Numbers are from this repository's code.

**A. Blind test on realistic beginner bugs.** A separate agent wrote 81 buggy submissions (3 per exercise) without seeing any hint rule, with a one-line true cause for each. Nudge produced hints levels 1-3 for each. A second agent, which only saw the code, the true cause and the hints, graded each:

| Grade | Meaning | First run | After fixes |
|---|---|---|---|
| A | leads to the real cause | 37 (46%) | 47 (58%) |
| B | relevant, not decisive | 10 (12%) | 10 (12%) |
| C | generic but harmless | 27 (33%) | 23 (28%) |
| D | misleading | 7 (9%) | 1 (1%) |

No hint revealed corrected code. **Read the second column carefully:** I fixed the rules after seeing which hints were misleading, so it is no longer a blind result and is optimistic. The first column is the honest estimate. Both gradings were done by an AI model, not by teachers or students.

**B. Mutation test** (`python tools/evaluate.py`). Each reference solution was broken automatically in 9 typical ways (flip a comparison, change a number by 1, swap + and -, drop a return value, delete a statement ...), giving 279 broken versions:

- the tests catch 96% (267); the 12 survivors are mostly harmless (for example `n >= best` in a maximum). One was a gap in the tests (binary search missed most positions), now covered; the tests still don't check speed, so a slow linear search passes;
- for 66% of caught versions the top hint names a specific cause rather than the generic "trace it by hand";
- 0 hints at levels 1-4 repeat a line of the reference solution (also enforced by a test).

`tests/corpus.py` holds 61 hand-written classic mistakes that must keep getting a fitting hint. They were written alongside the rules, so they work as a regression test, not as an accuracy figure.

## The exercises

27 exercises, three levels: loops, strings, lists, dictionaries, recursion, searching, stacks. Each has visible and hidden tests, hints written by hand for the special cases, and a reference solution. Hidden tests exist so a function that only works for the examples still fails.

Add your own: copy a file in `nudge/exercises/`, or add a definition to `tools/build_exercises.py` (expected values are computed from your solution) and run `nudge validate`: every reference solution must pass and every starter must fail.

## Limits

- **Rules only.** It recognises common mistakes. About a quarter of the held-out bugs got a generic hint (grade C), and unusual mistakes will too.
- **Not a security sandbox.** Submissions run in a separate process with a time limit (and a memory limit on Linux/macOS). That protects against your own infinite loop, not against hostile code. Use it for your own practice.
- **Windows:** a runaway loop is stopped after 20 seconds for the whole run instead of 2 seconds per test.
- **Python only**, functions that take and return plain data (numbers, text, lists, dictionaries).
- Float versus int slips inside a function (for example `n / 10` instead of `n // 10`) can go unnoticed when the final answer is the same.
- Anyone can read the solutions in `nudge/exercises/*.json`. The lock is a nudge, not a safe.
- The last approach hint of an exercise (level 7 in most) is a step-by-step plan in words, which for some exercises is close to pseudo-code. Levels 1-4 never contain a line of the solution; that is tested.
- No study with real learners has been done. Whether graded hints teach better than other feedback is untested here.

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest -q                      # 110 tests
python -m nudge validate                 # exercise sanity check
python tools/build_exercises.py          # regenerate exercises/*.json from the definitions
python tools/evaluate.py                 # mutation test
python tools/heldout.py out.json         # hints for tests/heldout.json (the blind set)
```

MIT license.
