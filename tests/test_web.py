"""The browser glue (nudge.web_api), driven the way the page drives it, but in plain Python."""
import json
import time
from datetime import date

import pytest

from nudge import exercises as exlib
from nudge import web_api as api

TODAY = date(2026, 1, 10).isoformat()


@pytest.fixture(autouse=True)
def loaded():
    api.init(json.dumps(exlib.load_all()))
    api.set_emitter(None)
    yield


def check(eid, src, prog="{}", limit=2.0):
    out = api.run_check(eid, src, limit)
    r = json.loads(api.finish_check(eid, src, out, False, prog, TODAY))
    return r, json.dumps(r["progress"])


def test_pass_and_fail():
    r, p = check("total", "def total(nums):\n    s = 0\n    for n in nums:\n        s += n\n    return s\n")
    assert r["passed"] and r["pass"]["first"] and r["state"]["solved"]
    r, _ = check("total", "def total(nums):\n    return None\n")
    assert not r["passed"] and r["ok_count"] < r["total"] and r["cases"]


def test_infinite_loop_is_stopped_with_a_line_number():
    t = time.time()
    r, _ = check("total", "def total(nums):\n    while True:\n        pass\n", limit=0.5)
    assert time.time() - t < 5
    err = r["cases"][0]["error"]
    assert err["type"] == "Timeout" and err["line"] == 3


def test_swallowing_except_cannot_hide_a_timeout():
    r, _ = check("total", "def total(nums):\n    try:\n        while True:\n            pass\n    except Exception:\n        return 0\n", limit=0.5)
    assert r["cases"][0]["error"]["type"] == "Timeout"


def test_syntax_error_and_missing_function():
    r, _ = check("total", "def total(nums)\n    return 1\n")
    assert r["status"] == "syntax"
    r, _ = check("total", "x = 1\n")
    assert r["status"] == "no_function"


def test_input_does_not_hang():
    r, _ = check("total", "def total(nums):\n    return input()\n")
    assert r["cases"][0]["error"]["type"] == "EOFError"


def test_hint_ladder_needs_a_check_between_rungs():
    src = "def total(nums):\n    return None\n"
    out = api.run_check("total", src)
    first = json.loads(api.finish_hint("total", src, out, False, "{}", TODAY))
    assert first["hint"]["level"] == 1
    again = json.loads(api.finish_hint("total", src, out, False, json.dumps(first["progress"]), TODAY))
    assert again.get("waiting")
    r, p = check("total", src + "# changed\n", json.dumps(first["progress"]))
    second = json.loads(api.finish_hint("total", src, out, False, p, TODAY))
    assert second["hint"]["level"] == 2


def test_solution_stays_locked_until_tried():
    src = "def total(nums):\n    return None\n"
    locked = json.loads(api.solution("total", "{}", TODAY))
    assert "locked" in locked and "nudge" not in locked["locked"]
    shown = json.loads(api.solution("total", "{}", TODAY, True))
    assert "def total" in shown["solution"]


def test_overview_and_reset():
    r, p = check("total", "def total(nums):\n    s = 0\n    for n in nums:\n        s += n\n    return s\n")
    ov = json.loads(api.overview(p, TODAY))
    assert ov["solved"] == 1 and ov["next"]
    p2 = json.loads(api.reset("total", p, TODAY))["progress"]
    assert json.loads(api.overview(json.dumps(p2), TODAY))["solved"] == 0


def test_garbage_progress_is_tolerated():
    for bad in ("", "nope", "[]", '{"exercises": 5}'):
        json.loads(api.overview(bad, TODAY))


def test_streaming_emitter_sees_lines():
    seen = []
    api.set_emitter(seen.append)
    api.run_check("total", "def total(nums):\n    return 0\n")
    assert any('"kind": "start"' in s for s in seen)
