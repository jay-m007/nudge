"""The hint ladder.

Each ask for a hint reveals one more step for the top finding:

  1  where to look (the failing input, the line of the error)
  2  what to think about (the idea behind the mistake)
  3  the exact spot (a line, a condition)
  4  a small worked example of the idea, on a different problem
  5+ the exercise author's own approach hints, one at a time

The solution is a separate command, locked until the student has really tried
(MIN_FAILS failed attempts) and has already seen the worked example.
"""
from __future__ import annotations

from dataclasses import dataclass

from .concepts import EXAMPLES
from .diagnose import Finding

MIN_FAILS = 3
BASE_LEVELS = 4


@dataclass
class Hint:
    level: int
    of: int
    title: str
    text: str


def total_levels(exercise: dict) -> int:
    return BASE_LEVELS + len(exercise["hints"])


def hint_at(level: int, finding: Finding | None, exercise: dict) -> Hint:
    """The hint text at a 1-based level. Levels beyond the finding's own use the exercise's approach hints."""
    n = total_levels(exercise)
    level = max(1, min(level, n))
    if level > BASE_LEVELS:
        i = level - BASE_LEVELS - 1
        return Hint(level, n, f"Approach hint {i + 1} of {len(exercise['hints'])}", exercise["hints"][i])
    if finding is None:
        approach = exercise["hints"][min(level - 1, len(exercise["hints"]) - 1)]
        return Hint(level, n, "Think about the approach", approach)
    if level == 1:
        return Hint(level, n, "Where to look", finding.look)
    if level == 2:
        return Hint(level, n, "What to think about", finding.think)
    if level == 3:
        return Hint(level, n, "The exact spot", finding.point)
    if finding.example and finding.example in EXAMPLES:
        title, code = EXAMPLES[finding.example]
        return Hint(level, n, "A similar example", f"{title}.\n\n{code}")
    return Hint(level, n, "The exercise's approach", exercise["hints"][0])


def next_hint(shown_level: int, finding: Finding | None, exercise: dict) -> Hint:
    return hint_at(shown_level + 1, finding, exercise)


def solution_locked(fails: int, max_level: int) -> str | None:
    """None if the solution may be shown, else the reason it is still locked."""
    if fails < MIN_FAILS:
        left = MIN_FAILS - fails
        return f"Try a bit more first: {left} more failed check{'s' if left != 1 else ''} to go. Hints are available with `nudge hint`."
    if max_level < BASE_LEVELS:
        return f"Ask for the hints first (you're at level {max_level} of {BASE_LEVELS}). Use `nudge hint`."
    return None
