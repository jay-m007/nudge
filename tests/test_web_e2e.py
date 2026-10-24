"""Drives the real page in a real browser (Chromium via Playwright). Skipped unless the site is built
(python tools/build_web.py) and Playwright is installed."""
import functools
import http.server
import json
import threading
from pathlib import Path

import pytest

pw = pytest.importorskip("playwright.sync_api")
SITE = Path(__file__).resolve().parent.parent / "site"
pytestmark = pytest.mark.skipif(not (SITE / "index.html").exists(), reason="run tools/build_web.py first")

GOOD_TOTAL = "def total(numbers):\n    s = 0\n    for n in numbers:\n        s += n\n    return s\n"


@pytest.fixture(scope="module")
def base():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a, **k):
            pass

    handler = functools.partial(Quiet, directory=str(SITE))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}/"
    srv.shutdown()


@pytest.fixture(scope="module")
def browser():
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.fixture()
def page(browser, base):
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
    pg = ctx.new_page()
    pg.errors = []
    pg.on("pageerror", lambda e: pg.errors.append(str(e)))
    pg.goto(base)
    pg.wait_for_selector("#engine.ready", timeout=90000)
    yield pg
    assert not pg.errors, pg.errors
    ctx.close()


def open_ex(pg, title):
    if pg.viewport_size["width"] <= 1180:
        pg.click("#menu-btn")
    pg.click(f".ex:has-text('{title}')")
    pg.wait_for_function("(t) => document.querySelector('#title').textContent.includes(t)", arg=title)


def set_code(pg, src):
    pg.evaluate("(s) => nudge.S.cm.setValue(s)", src)


def run(pg):
    pg.click("#run-btn")
    pg.wait_for_function("document.querySelector('#run-btn').disabled === false && document.querySelector('#results .verdict')", timeout=60000)


def test_fail_then_hints_need_a_run_in_between(page):
    open_ex(page, "Add up a list")
    set_code(page, "def total(numbers):\n    return None\n")
    run(page)
    assert "tests pass" in page.inner_text("#results .verdict") and "All" not in page.inner_text("#results .verdict")
    page.click("#hint-btn")
    page.wait_for_selector(".rung.revealed .rung-text")
    assert page.locator(".rung.revealed").count() == 1
    assert page.locator(".rung.next.locked").count() == 1
    page.click("#hint-btn")  # nothing new without a run
    page.wait_for_function("document.querySelector('#hint-btn').disabled === false")
    assert page.locator(".rung.revealed").count() == 1
    set_code(page, "def total(numbers):\n    return None  # still the same mistake\n")
    run(page)
    page.click("#hint-btn")
    page.wait_for_function("document.querySelectorAll('.rung.revealed').length === 2")


def test_infinite_loop_is_reported_and_the_page_survives(page):
    open_ex(page, "Add up a list")
    set_code(page, "def total(numbers):\n    while True:\n        pass\n")
    run(page)
    txt = page.inner_text("#results")
    assert "Took too long" in txt and "line 3" in txt
    assert page.locator(".cm-errline").count() == 1
    set_code(page, GOOD_TOTAL)
    run(page)
    assert "All 7 tests pass" in page.inner_text("#results .verdict")


def test_a_hang_inside_one_builtin_call_is_stopped_and_python_restarts(page):
    open_ex(page, "Add up a list")
    set_code(page, "def total(numbers):\n    return len(str(10 ** 10 ** 8))\n")
    run(page)
    assert "Took too long" in page.inner_text("#results")
    page.wait_for_selector("#engine.ready", timeout=90000)
    set_code(page, GOOD_TOTAL)
    run(page)
    assert "All 7 tests pass" in page.inner_text("#results .verdict")


def test_solving_is_remembered_across_reload(page, base):
    open_ex(page, "Add up a list")
    set_code(page, GOOD_TOTAL)
    run(page)
    assert "Solved on your own" in page.inner_text("#results")
    assert page.locator(".ex.solved:has-text('Add up a list')").count() == 1
    page.reload()
    page.wait_for_selector("#engine.ready", timeout=90000)
    assert "1 of 27 solved" in page.inner_text("#summary")
    assert "def total" in page.evaluate("nudge.S.cm.getValue()")


def test_solution_is_locked_until_real_attempts(page):
    open_ex(page, "Add up a list")
    set_code(page, "def total(numbers):\n    return None\n")
    page.click(".rung.solution button:has-text('Ask for the solution')")
    page.wait_for_selector(".sol-note")
    assert "Not yet" in page.inner_text(".sol-note")
    assert "return s" not in page.inner_text("#ladder")
    page.click(".sol-note .linkish")  # arm
    page.click(".sol-note .linkish")  # confirm
    page.wait_for_selector(".rung.solution.revealed")
    assert "def total" in page.inner_text(".rung.solution")


def test_syntax_error_marks_the_line(page):
    open_ex(page, "Add up a list")
    set_code(page, "def total(numbers)\n    return 1\n")
    run(page)
    assert "could not read" in page.inner_text("#results")
    assert page.locator(".cm-errline").count() == 1


def test_input_call_does_not_hang(page):
    open_ex(page, "Add up a list")
    set_code(page, "def total(numbers):\n    return input()\n")
    run(page)
    assert "EOFError" in page.inner_text("#results")


def test_backup_and_restore_round_trip(page, tmp_path):
    open_ex(page, "Add up a list")
    set_code(page, GOOD_TOTAL)
    run(page)
    with page.expect_download() as dl:
        page.click("#export-btn")
    f = tmp_path / "b.json"
    dl.value.save_as(str(f))
    assert json.loads(f.read_text())["exercises"]["total"]["solved"]
    page.click("#wipe-btn")
    page.click("#wipe-btn")
    page.wait_for_function("document.querySelector('#summary').textContent.startsWith('0 of')")
    page.set_input_files("#import-file", str(f))
    page.wait_for_function("document.querySelector('#summary').textContent.startsWith('1 of')")
    f.write_text("not json")
    page.set_input_files("#import-file", str(f))
    page.wait_for_function("document.querySelector('#backup-note').textContent.includes('isn')")


def test_phone_width_has_no_sideways_scroll(browser, base):
    ctx = browser.new_context(viewport={"width": 390, "height": 800})
    pg = ctx.new_page()
    pg.goto(base)
    pg.wait_for_selector("#engine.ready", timeout=90000)
    assert pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    pg.click("#menu-btn")
    assert pg.locator("#side.open").count() == 1
    ctx.close()
