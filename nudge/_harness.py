"""Runs one student's file against an exercise's test cases. Started as a separate
process by runner.py; reads one JSON job on stdin and writes one JSON line per case.

This is a guard against *accidents* (infinite loops, huge memory, a stray input()),
not a security sandbox: it is meant for practising with your own code.
"""
import copy
import io
import json
import math
import os
import sys
import threading
import traceback

FILENAME = "<student>"


def norm(v):
    """JSON-comparable form: tuples become lists, sets become sorted lists."""
    if isinstance(v, (tuple, list)):
        return [norm(x) for x in v]
    if isinstance(v, (set, frozenset)):
        try:
            return sorted(norm(x) for x in v)
        except TypeError:
            return [norm(x) for x in v]
    if isinstance(v, dict):
        return {str(k): norm(x) for k, x in v.items()}
    return v


def same(got, want, approx):
    if approx and isinstance(got, (int, float)) and isinstance(want, (int, float)) and not isinstance(got, bool):
        return math.isclose(got, want, rel_tol=1e-9, abs_tol=1e-9)
    if isinstance(got, bool) != isinstance(want, bool):
        return False  # 1 == True in Python, but a student returning 1 for True should hear about it
    if isinstance(got, list) and isinstance(want, list):
        return len(got) == len(want) and all(same(a, b, approx) for a, b in zip(got, want))
    if isinstance(got, dict) and isinstance(want, dict):
        return got.keys() == want.keys() and all(same(got[k], want[k], approx) for k in got)
    return got == want and type(got) is type(want)


def emit(out, obj):
    out.write(json.dumps(obj) + "\n")
    out.flush()


def error_info(exc):
    tb = traceback.extract_tb(exc.__traceback__)
    line = None
    for frame in reversed(tb):
        if frame.filename == FILENAME:
            line = frame.lineno
            break
    return {"type": type(exc).__name__, "msg": str(exc)[:300], "line": line}


class CaseTimeout(Exception):
    pass


def main():
    job = json.loads(sys.stdin.read())
    sys.stdin = io.StringIO("")  # input() will raise EOFError instead of hanging
    try:
        import resource

        resource.setrlimit(resource.RLIMIT_AS, (768 * 1024 * 1024, 768 * 1024 * 1024))
    except Exception:
        pass
    run_job(job, sys.stdout, use_alarm=True)


def run_job(job, out, use_alarm=False):
    """Run one job, writing one JSON line per event to ``out``.

    Called as a script by runner.py: a separate process, with a per-case alarm where the OS has one.
    """
    prev_stdout = sys.stdout
    alarm = None
    try:
        import signal

        if use_alarm and hasattr(signal, "setitimer") and not os.environ.get("NUDGE_FORCE_WATCHDOG"):

            def on_alarm(signum, frame):
                raise CaseTimeout()

            signal.signal(signal.SIGALRM, on_alarm)
            alarm = signal

    except Exception:
        pass

    limit = job.get("limit", 2.0)
    watch = use_alarm and alarm is None  # no SIGALRM (Windows): a watchdog thread ends the run instead
    main_id = threading.get_ident()
    state = {"i": None, "timer": None, "tag": ""}

    def fire():
        line = None
        frame = sys._current_frames().get(main_id)
        while frame is not None:
            if frame.f_code.co_filename == FILENAME:
                line = frame.f_lineno
                break
            frame = frame.f_back
        err = {"type": "Timeout", "msg": "took too long", "line": line}
        if state["i"] is None:
            emit(out, {"kind": "load_error", "error": err})
        else:
            emit(out, {"kind": "case", "i": state["i"], "tag": state["tag"], "ok": False, "error": err, "printed": ""})
            emit(out, {"kind": "stopped"})
        out.flush()
        os._exit(0)

    def arm():
        if alarm:
            alarm.setitimer(alarm.ITIMER_REAL, limit)
        elif watch:
            t = threading.Timer(limit, fire)
            t.daemon = True
            state["timer"] = t
            t.start()

    def disarm():
        if alarm:
            alarm.setitimer(alarm.ITIMER_REAL, 0)
        elif state["timer"] is not None:
            state["timer"].cancel()
            state["timer"] = None

    buf = io.StringIO()
    sys.stdout = buf
    ns = {"__name__": "student"}
    try:
        code = compile(job["source"], FILENAME, "exec")
    except SyntaxError as e:
        sys.stdout = prev_stdout
        emit(out, {"kind": "syntax", "msg": e.msg, "line": e.lineno, "offset": e.offset, "text": (e.text or "").rstrip("\n")})
        return
    except (ValueError, RecursionError, MemoryError) as e:  # null bytes, absurdly deep expressions
        sys.stdout = prev_stdout
        emit(out, {"kind": "syntax", "msg": "Python could not read the file (" + (str(e)[:80] or type(e).__name__) + ")", "line": None, "offset": None, "text": ""})
        return
    try:
        arm()
        exec(code, ns)
        disarm()
    except CaseTimeout:
        sys.stdout = prev_stdout
        emit(out, {"kind": "load_error", "error": {"type": "Timeout", "msg": "the file never finished loading", "line": None}})
        return
    except BaseException as e:  # noqa: BLE001 - students can raise anything
        sys.stdout = prev_stdout
        emit(out, {"kind": "load_error", "error": error_info(e)})
        return
    fn = ns.get(job["function"])
    if not callable(fn):
        sys.stdout = prev_stdout
        names = [k for k, v in ns.items() if callable(v) and not k.startswith("__")]
        emit(out, {"kind": "no_function", "defined": names})
        return
    sys.stdout = prev_stdout
    emit(out, {"kind": "start"})
    for i, case in enumerate(job["cases"]):
        args = copy.deepcopy(case["args"])
        before = copy.deepcopy(args)
        buf.seek(0)
        buf.truncate()
        sys.stdout = buf
        res = {"kind": "case", "i": i, "tag": case.get("tag", "")}
        try:
            state["i"], state["tag"] = i, case.get("tag", "")
            arm()
            got = fn(*args)
            disarm()
            g = norm(got)
            res["got"] = g if _jsonable(g) else repr(got)
            res["type"] = type(got).__name__
            res["ok"] = same(g, case["expected"], job.get("approx", False))
            res["mutated"] = (not job.get("allow_mutation")) and norm(args) != norm(before)
            if res["mutated"]:
                res["ok"] = False
        except CaseTimeout:
            res.update(ok=False, error={"type": "Timeout", "msg": "took too long", "line": _current_line()})
        except RecursionError as e:
            disarm()
            res.update(ok=False, error=error_info(e))
        except BaseException as e:  # noqa: BLE001
            disarm()
            res.update(ok=False, error=error_info(e))
        printed = buf.getvalue()
        sys.stdout = prev_stdout
        res["printed"] = printed[:500]
        emit(out, res)
        if res.get("error", {}).get("type") == "Timeout":
            emit(out, {"kind": "stopped"})  # the rest would only repeat the wait
            break


def _current_line():
    tb = sys.exc_info()[2]
    line = None
    while tb is not None:
        if tb.tb_frame.f_code.co_filename == FILENAME:
            line = tb.tb_lineno
        tb = tb.tb_next
    return line


def _jsonable(v):
    try:
        json.dumps(v)
        return True
    except (TypeError, ValueError):
        return False


if __name__ == "__main__":
    main()
