"""Build the browser version into ./site (ready to host as static files, e.g. on GitHub Pages).

    python tools/build_web.py

Needs Node/npm once, to fetch Pyodide (Python in the browser), the CodeMirror editor and two fonts.
Everything is copied into the site, so the finished page loads nothing from any other server.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
sys.path.insert(0, str(ROOT))

NPM = ["pyodide@0.26.4", "codemirror@5.65.21", "@fontsource/atkinson-hyperlegible@5.1.0", "@fontsource/jetbrains-mono@5.1.0"]
PYODIDE_FILES = ["pyodide.js", "pyodide.asm.js", "pyodide.asm.wasm", "python_stdlib.zip", "pyodide-lock.json"]
PY_FILES = ["__init__.py", "_harness.py", "concepts.py", "diagnose.py", "hints.py", "progress.py", "runner.py", "web_api.py"]


def main() -> int:
    from nudge import exercises as exlib

    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir()
    for name in ("index.html", "style.css", "app.js", "worker.js"):
        shutil.copy(ROOT / "web" / name, SITE / name)

    py = SITE / "py"
    py.mkdir()
    for name in PY_FILES:
        shutil.copy(ROOT / "nudge" / name, py / name)
    (SITE / "py-files.json").write_text(json.dumps(PY_FILES))
    exercises = exlib.load_all()
    for ex in exercises.values():  # what the page shows under the problem statement (Python's own repr)
        shown = [c for c in ex["cases"] if not c.get("hidden")][:3]
        ex["examples"] = [f"{ex['function']}({', '.join(repr(a) for a in c['args'])})  ->  {c['expected']!r}" for c in shown]
    (SITE / "exercises.json").write_text(json.dumps(exercises, separators=(",", ":")), encoding="utf-8")

    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["npm", "init", "-y"], cwd=tmp, check=True, capture_output=True)
        subprocess.run(["npm", "install", "--silent", *NPM], cwd=tmp, check=True)
        nm = Path(tmp) / "node_modules"
        vendor = SITE / "vendor"
        (vendor / "pyodide").mkdir(parents=True)
        for f in PYODIDE_FILES:
            shutil.copy(nm / "pyodide" / f, vendor / "pyodide" / f)
        cm = vendor / "codemirror"
        (cm / "mode").mkdir(parents=True)
        (cm / "addon").mkdir()
        shutil.copy(nm / "codemirror/lib/codemirror.js", cm)
        shutil.copy(nm / "codemirror/lib/codemirror.css", cm)
        shutil.copy(nm / "codemirror/mode/python/python.js", cm / "mode")
        shutil.copy(nm / "codemirror/addon/edit/matchbrackets.js", cm / "addon")
        shutil.copy(nm / "codemirror/addon/edit/closebrackets.js", cm / "addon")
        fonts = vendor / "fonts"
        fonts.mkdir()
        for pkg, files in (("atkinson-hyperlegible", ("400", "700")), ("jetbrains-mono", ("400", "600"))):
            for w in files:
                n = f"{pkg}-latin-{w}-normal.woff2"
                shutil.copy(nm / "@fontsource" / pkg / "files" / n, fonts / n)
    (SITE / ".nojekyll").write_text("")
    size = sum(f.stat().st_size for f in SITE.rglob("*") if f.is_file()) / 1e6
    print(f"Built {SITE} ({size:.1f} MB). Try it: python -m http.server -d site 8000")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
