/* Runs Python (Pyodide) off the page's main thread, so a student's infinite loop can never freeze the page. */
importScripts("vendor/pyodide/pyodide.js");

let api = null;

async function boot() {
  postMessage({ type: "status", text: "Loading Python…" });
  const py = await loadPyodide({ indexURL: "vendor/pyodide/" });
  postMessage({ type: "status", text: "Loading the hint engine…" });
  const names = await (await fetch("py-files.json")).json();
  py.FS.mkdirTree("/home/pyodide/nudge");
  for (const name of names) {
    const text = await (await fetch("py/" + name)).text();
    py.FS.writeFile("/home/pyodide/nudge/" + name, text);
  }
  const exercises = await (await fetch("exercises.json")).text();
  py.runPython('import sys\nsys.path.insert(0, "/home/pyodide")');
  api = py.pyimport("nudge.web_api");
  api.init(exercises);
  api.set_emitter((line) => postMessage({ type: "line", line }));
  postMessage({ type: "ready" });
}

onmessage = (e) => {
  const { id, fn, args } = e.data;
  try {
    const result = api[fn](...args);
    postMessage({ id, result });
  } catch (err) {
    postMessage({ id, error: String(err && err.message ? err.message : err) });
  }
};

boot().catch((err) => postMessage({ type: "fatal", text: String(err && err.message ? err.message : err) }));
