import json
from datetime import date, timedelta

import pytest

from nudge import exercises as exlib
from nudge.cli import main
from nudge.diagnose import diagnose, input_features
from nudge.hints import BASE_LEVELS, MIN_FAILS, hint_at, solution_locked, total_levels
from nudge.progress import Progress
from nudge.runner import run

EXS = exlib.load_all()
TOTAL = EXS["total"]


# ---------------------------------------------------------------- exercises

def test_every_reference_solution_passes_and_every_starter_fails():
    for eid, ex in EXS.items():
        assert run(ex["solution"], ex).passed, eid
        assert not run(ex["starter"], ex).passed, eid


def test_exercise_files_are_complete():
    assert len(EXS) >= 25
    for eid, ex in EXS.items():
        assert len(ex["hints"]) >= 3, eid
        assert any(c.get("hidden") for c in ex["cases"]), f"{eid} has no hidden test"
        assert len({c.get("tag") for c in ex["cases"]}) >= 2, eid
        assert ex["function"] in ex["starter"], eid


def test_bad_exercise_name_suggests_a_close_one():
    with pytest.raises(exlib.ExerciseError, match="tot"):
        exlib.get("tota")


# ---------------------------------------------------------------- runner

def test_runner_reports_syntax_error_with_line():
    r = run("def total(numbers)\n    return 0\n", TOTAL)
    assert r.status == "syntax" and r.info["line"] == 1


def test_runner_reports_missing_function():
    r = run("def totl(numbers):\n    return 0\n", TOTAL)
    assert r.status == "no_function" and "totl" in r.info["defined"]


def test_runner_catches_exceptions_per_case_and_keeps_going():
    r = run("def total(numbers):\n    return numbers[0]\n", TOTAL)
    assert r.status == "ok" and len(r.cases) == len(TOTAL["cases"])
    empty = next(c for c in r.cases if c.tag == "empty")
    assert empty.error["type"] == "IndexError" and empty.error["line"] == 2


def test_infinite_loop_is_stopped_and_attributed():
    r = run("def total(numbers):\n    while True:\n        pass\n", TOTAL, limit=0.3)
    assert r.cases and all(c.error and c.error["type"] == "Timeout" for c in r.cases[:1])


def test_input_call_does_not_hang():
    r = run("def total(numbers):\n    return input()\n", TOTAL)
    assert all(c.error and c.error["type"] == "EOFError" for c in r.cases)


def test_modifying_the_input_fails_the_case():
    ex = EXS["merge_sorted"]
    r = run("def merge_sorted(a, b):\n    a.extend(b)\n    a.sort()\n    return a\n", ex)
    assert any(c.mutated for c in r.cases)


def test_bool_is_not_accepted_for_int_and_vice_versa():
    ex = EXS["is_prime"]
    r = run("def is_prime(n):\n    return 1 if n > 1 else 0\n", ex)
    assert not r.passed


def test_print_is_captured_not_leaked():
    r = run("def total(numbers):\n    print('hi')\n    return 0\n", TOTAL)
    assert r.cases[0].printed.strip() == "hi"


# ---------------------------------------------------------------- diagnosis

def test_input_features():
    assert "empty input" in input_features([[]])
    assert {"capital letters", "spaces"} <= input_features(["Ab c"])
    assert "negative numbers" in input_features([[1, -2]])
    assert "repeated values" in input_features([[1, 1]])


def test_diagnosis_never_empty_for_a_failing_submission():
    for eid, ex in EXS.items():
        src = ex["starter"]
        res = run(src, ex)
        assert diagnose(src, ex, res), eid


def test_hints_never_contain_solution_lines():
    for eid, ex in EXS.items():
        sol_lines = {l.strip() for l in ex["solution"].splitlines() if len(l.strip()) >= 14 and not l.strip().startswith("def ")}
        res = run(ex["starter"], ex)
        top = diagnose(ex["starter"], ex, res)[0]
        for lvl in range(1, BASE_LEVELS + 1):
            text = hint_at(lvl, top, ex).text
            assert not any(l in text for l in sol_lines), (eid, lvl)
        for lvl in range(BASE_LEVELS + 1, total_levels(ex) + 1):
            text = hint_at(lvl, top, ex).text
            assert not any(l in text for l in sol_lines), (eid, lvl)


# ---------------------------------------------------------------- hint ladder and solution lock

def test_ladder_has_the_documented_shape():
    src = "def total(numbers):\n    for n in numbers:\n        return n\n"
    top = diagnose(src, TOTAL, run(src, TOTAL))[0]
    titles = [hint_at(i, top, TOTAL).title for i in range(1, total_levels(TOTAL) + 1)]
    assert titles[:4] == ["Where to look", "What to think about", "The exact spot", "A similar example"]
    assert titles[4].startswith("Approach hint 1")
    assert hint_at(99, top, TOTAL).level == total_levels(TOTAL)  # clamped, never past the end


def test_solution_stays_locked_until_tried_and_hinted():
    assert solution_locked(0, 0)
    assert solution_locked(MIN_FAILS, 1)
    assert solution_locked(MIN_FAILS, BASE_LEVELS) is None


# ---------------------------------------------------------------- progress and spaced review

def make_progress(tmp_path, day):
    return Progress(tmp_path / "p.json", today=day)


def test_clean_first_solve_goes_to_box_2_and_comes_back_in_four_days(tmp_path):
    d0 = date(2026, 1, 1)
    p = make_progress(tmp_path, d0)
    info = p.record_pass("total")
    assert info["first"] and info["clean"] and info["box"] == 2
    assert info["due"] == (d0 + timedelta(days=2)).isoformat()


def test_solve_with_big_hint_starts_in_box_1(tmp_path):
    p = make_progress(tmp_path, date(2026, 1, 1))
    p.record_fail("total", "x", ["loops"])
    p.record_hint("total", 3)
    info = p.record_pass("total")
    assert info["box"] == 1 and not info["clean"]


def test_review_moves_up_and_a_struggle_moves_back(tmp_path):
    d0 = date(2026, 1, 1)
    make_progress(tmp_path, d0).record_pass("total")  # box 2, due in 2 days
    p = Progress(tmp_path / "p.json", today=d0 + timedelta(days=3))
    assert p.record_pass("total")["box"] == 3  # a real review, passed
    p = Progress(tmp_path / "p.json", today=d0 + timedelta(days=9))
    p.record_hint("total", 4)
    assert p.record_pass("total")["box"] == 1  # needed help: back to the start


def test_passing_again_before_it_is_due_does_not_move_the_box(tmp_path):
    p = make_progress(tmp_path, date(2026, 1, 1))
    p.record_pass("total")
    for _ in range(5):
        info = p.record_pass("total")
        assert info["not_due"] and info["box"] == 2
    assert p.ex("total")["reviews"] == 0


def test_rerunning_an_unchanged_file_is_not_a_new_attempt(tmp_path):
    p = make_progress(tmp_path, date(2026, 1, 1))
    for _ in range(6):
        p.record_fail("total", "x", [], "abc123")
    assert p.ex("total")["fails"] == 1
    p.record_fail("total", "x", [], "def456")
    assert p.ex("total")["fails"] == 2


def test_next_hint_needs_a_check_in_between(tmp_path):
    p = make_progress(tmp_path, date(2026, 1, 1))
    assert p.hint_allowed("total")  # the first hint is always available
    p.record_hint("total", 1)
    assert not p.hint_allowed("total")
    p.record_fail("total", "x", [], "h1")
    assert p.hint_allowed("total")


@pytest.mark.parametrize("raw", [
    None, [], "text", {"exercises": []}, {"exercises": {"total": None}}, {"exercises": {"total": {}}},
    {"exercises": {"total": {"fails": "3", "due": 5, "solved": True, "box": "x"}}},
    {"exercises": {}, "concept_trouble": []}, {"exercises": {}, "concept_trouble": {"loops": "x"}},
    {"exercises": {"gone": {"solved": True}}},
])
def test_any_progress_shape_is_usable(raw, tmp_path):
    p = Progress(data=raw, today=date(2026, 1, 1))
    p.due(EXS), p.next_up(EXS), p.weakest_concepts(), p.solved_ids()
    p.record_fail("total", "x", ["loops"], "h")
    p.record_pass("total")


def test_cli_survives_wrongly_shaped_progress_file(workdir, capsys):
    (workdir / "home").mkdir()
    (workdir / "home" / "progress.json").write_text('{"exercises": {"total": null, "x": {"solved": true}}, "concept_trouble": []}', encoding="utf-8")
    for cmd in (["list"], ["stats"], ["next"], ["solution", "total"]):
        assert main(cmd) in (0, 1)


def test_solution_stays_locked_when_nothing_changes(workdir, capsys):
    main(["start", "digit_sum"])
    for _ in range(4):
        main(["check", "digit_sum"])
    for _ in range(6):
        main(["hint", "digit_sum"])
    capsys.readouterr()
    assert main(["solution", "digit_sum"]) == 1
    assert "more failed check" in capsys.readouterr().out


def test_cli_odd_files_do_not_crash(workdir, capsys):
    for data in (b"# caf\xe9 \x81\ndef total(n): return 0\n", b"def total(n):\n    return 0\x00\n", b"", b"\xff\xfe\x00"):
        (workdir / "total.py").write_bytes(data)
        assert main(["check", "total"]) in (0, 1)
    (workdir / "total.py").unlink()
    (workdir / "average").mkdir()
    assert main(["check", "average"]) == 2


def test_a_hung_program_stops_after_the_first_timeout():
    r = run("def total(numbers):\n    while True:\n        pass\n", TOTAL, limit=0.3)
    assert len(r.cases) == 1 and r.cases[0].error["type"] == "Timeout"


def test_due_and_next_prefer_reviews(tmp_path):
    p = make_progress(tmp_path, date(2026, 1, 1))
    p.record_pass("total")
    later = Progress(tmp_path / "p.json", today=date(2026, 1, 10))
    assert later.due(EXS) == ["total"]
    assert later.next_up(EXS) == ("total", "due for review")


def test_next_follows_order_then_weak_topics(tmp_path):
    p = make_progress(tmp_path, date(2026, 1, 1))
    first = p.next_up(EXS)
    assert first[0] == next(iter(EXS))
    for eid in list(EXS)[:3]:
        p.record_pass(eid)
    p.data["concept_trouble"] = {"recursion": 5}
    pick = Progress(tmp_path / "p.json", today=date(2026, 1, 2))
    pick.data = p.data
    eid, why = pick.next_up(EXS)
    assert "recursion" in EXS[eid]["concepts"] and "recursion" in why


def test_ladder_restarts_when_the_top_problem_changes(tmp_path):
    p = make_progress(tmp_path, date(2026, 1, 1))
    p.record_fail("total", "a", [])
    p.record_hint("total", 3)
    p.record_fail("total", "b", [])
    assert p.ex("total")["hint_level"] == 0


def test_damaged_progress_file_is_set_aside_not_fatal(tmp_path):
    path = tmp_path / "p.json"
    path.write_text("{not json", encoding="utf-8")
    p = Progress(path, today=date(2026, 1, 1))
    assert p.data["exercises"] == {}
    assert path.with_suffix(".broken").exists()


# ---------------------------------------------------------------- command line

@pytest.fixture()
def workdir(tmp_path, monkeypatch):
    monkeypatch.setenv("NUDGE_HOME", str(tmp_path / "home"))
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_cli_full_session(workdir, capsys):
    assert main(["start", "total"]) == 0
    assert (workdir / "total.py").exists()
    assert main(["check", "total"]) == 1  # starter fails
    (workdir / "total.py").write_text("def total(numbers):\n    for n in numbers:\n        return n\n", encoding="utf-8")
    assert main(["check", "total"]) == 1
    capsys.readouterr()
    assert main(["hint", "total"]) == 0
    assert "Where to look" in capsys.readouterr().out
    assert main(["solution", "total"]) == 1  # locked
    assert "more failed check" in capsys.readouterr().out
    (workdir / "total.py").write_text(EXS["total"]["solution"], encoding="utf-8")
    assert main(["check", "total.py"]) == 0
    assert "PASS" in capsys.readouterr().out
    assert main(["stats"]) == 0
    assert "Solved: 1 of" in capsys.readouterr().out
    assert json.loads((workdir / "home" / "progress.json").read_text())["exercises"]["total"]["solved"]


def test_cli_start_never_overwrites_work(workdir, capsys):
    (workdir / "total.py").write_text("# my work\n", encoding="utf-8")
    main(["start", "total"])
    assert (workdir / "total.py").read_text() == "# my work\n"
    assert "already exists" in capsys.readouterr().out


def test_cli_unknown_exercise_and_missing_file(workdir, capsys):
    assert main(["show", "nope"]) == 2
    assert main(["check", "total"]) == 2
    assert "nudge start total" in capsys.readouterr().err


def test_cli_validate_and_list(workdir, capsys):
    assert main(["validate"]) == 0
    assert main(["list"]) == 0
    assert "0 of" in capsys.readouterr().out


def test_cli_reads_files_saved_with_a_bom(workdir, capsys):
    (workdir / "total.py").write_bytes(b"\xef\xbb\xbf" + EXS["total"]["solution"].encode())
    assert main(["check", "total"]) == 0


def test_watchdog_timer_stops_a_hung_program_like_the_alarm_does(monkeypatch):
    """Windows has no SIGALRM; force the thread-based path used there and check it behaves the same."""
    monkeypatch.setenv("NUDGE_FORCE_WATCHDOG", "1")
    r = run("def total(numbers):\n    while True:\n        pass\n", TOTAL, limit=0.4)
    assert len(r.cases) == 1 and r.cases[0].error["type"] == "Timeout" and r.cases[0].error["line"] in (2, 3)
    r = run("while True:\n    pass\ndef total(numbers):\n    return 0\n", TOTAL, limit=0.4)
    assert r.status == "load_error" and r.info["error"]["type"] == "Timeout"
