/* Nudge in the browser. The engine is the same Python as the command-line tool, running in a Web Worker. */
"use strict";

const $ = (id) => document.getElementById(id);
const STORE = "nudge.progress.v1";
const LABELS = ["Where to look", "What to think about", "The exact spot", "A worked example"];
const BASE = 4;

/* ---------- small helpers ---------- */
function el(tag, attrs, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k === "class") n.className = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else if (v !== false && v != null) n.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat()) if (kid != null) n.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
  return n;
}
const store = {
  get(k) { try { return localStorage.getItem(k); } catch { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch { /* private window: carry on without saving */ } },
  del(k) { try { localStorage.removeItem(k); } catch { /* ignore */ } },
};
function today() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
function niceDate(iso) {
  const d = new Date(iso + "T00:00:00");
  return isNaN(d) ? iso : d.toLocaleDateString(undefined, { day: "numeric", month: "short" });
}
function withCode(text) {  // `like this` becomes <code>; everything else stays text
  const frag = document.createDocumentFragment();
  String(text).split(/(`[^`]+`)/).forEach((part) => {
    if (part.length > 2 && part.startsWith("`") && part.endsWith("`")) frag.append(el("code", {}, part.slice(1, -1)));
    else if (part) frag.append(document.createTextNode(part));
  });
  return frag;
}
const clip = (s, n = 160) => (s.length > n ? s.slice(0, n - 1) + "…" : s);

/* ---------- the Python engine (a worker) ---------- */
class Engine {
  constructor(onStatus) {
    this.onStatus = onStatus;
    this.pending = new Map();
    this.next = 1;
    this.lines = null;
    this.boot();
  }
  boot() {
    this.ready = new Promise((resolve, reject) => { this._ok = resolve; this._fail = reject; });
    this.ready.catch(() => {});
    this.worker = new Worker("worker.js");
    this.worker.onmessage = (e) => {
      const m = e.data;
      if (m.type === "status") this.onStatus("loading", m.text);
      else if (m.type === "ready") { this.onStatus("ready", "Python is ready"); this._ok(); }
      else if (m.type === "fatal") { this.onStatus("failed", "Python could not start"); this._fail(new Error(m.text)); }
      else if (m.type === "line") { if (this.lines) { this.lines.push(m.line); if (this.onActivity) this.onActivity(); } }
      else if (m.id && this.pending.has(m.id)) {
        const { resolve, reject } = this.pending.get(m.id);
        this.pending.delete(m.id);
        m.error ? reject(new Error(m.error)) : resolve(m.result);
      }
    };
    this.worker.onerror = (e) => { this.onStatus("failed", "Python could not start"); this._fail(new Error(e.message || "worker error")); };
  }
  async call(fn, ...args) {
    await this.ready;
    return new Promise((resolve, reject) => {
      const id = this.next++;
      this.pending.set(id, { resolve, reject });
      this.worker.postMessage({ id, fn, args });
    });
  }
  /* Run the student's code. If the worker goes quiet (a loop the trace hook can't interrupt), stop it and start a fresh one. */
  async run(exerciseId, source) {
    await this.ready;
    this.lines = [];
    const worker = this.worker;
    let timer;
    const stuck = new Promise((resolve) => {
      this.onActivity = () => { clearTimeout(timer); timer = setTimeout(() => resolve("stuck"), 5000); };
      this.onActivity();
    });
    let first;
    try {
      first = await Promise.race([this.call("run_check", exerciseId, source, 2.0).then((out) => ({ out })), stuck]);
    } finally {
      clearTimeout(timer);
      this.onActivity = null;
    }
    const partial = this.lines.join("");
    this.lines = null;
    if (first === "stuck") {
      worker.terminate();
      this.pending.clear();
      this.onStatus("loading", "Restarting Python…");
      this.boot();
      return { stdout: partial, timedOut: true };
    }
    return { stdout: first.out, timedOut: false };
  }
}

/* ---------- app state ---------- */
const S = {
  exercises: {}, order: [], id: null, progress: { exercises: {}, concept_trouble: {} },
  cm: null, busy: false, ready: false, hints: [], hintCode: "", solutionText: "", solutionNote: "", lastErrLine: null, armed: {},
};
let engine;

function loadProgress() {
  try { const p = JSON.parse(store.get(STORE) || "{}"); if (p && typeof p === "object" && !Array.isArray(p)) S.progress = p; } catch { /* start fresh */ }
  if (!S.progress.exercises || typeof S.progress.exercises !== "object") S.progress.exercises = {};
}
function saveProgress(p) { S.progress = p; store.set(STORE, JSON.stringify(p)); }
const entry = (id) => (S.progress.exercises && S.progress.exercises[id]) || {};
const ex = () => S.exercises[S.id];
const totalRungs = () => BASE + ex().hints.length;

/* ---------- sidebar ---------- */
function renderSidebar() {
  const solved = S.order.filter((i) => entry(i).solved).length;
  const t = today();
  $("summary").replaceChildren(
    `${solved} of ${S.order.length} solved`,
    el("div", { class: "bar", role: "img", "aria-label": `${solved} of ${S.order.length} solved` }, el("i", { style: `width:${(100 * solved) / S.order.length}%` })),
  );
  const list = $("list");
  list.replaceChildren();
  let last = null;
  for (const id of S.order) {
    const e = S.exercises[id];
    if (e.level !== last) { last = e.level; list.append(el("div", { class: "level" }, `Level ${last}`)); }
    const s = entry(id);
    const due = s.solved && s.due && s.due <= t;
    const cls = "ex" + (s.solved ? " solved" : "") + (due ? " due" : "");
    list.append(el("button", { class: cls, "aria-current": id === S.id ? "true" : "false", onclick: () => { openExercise(id); closeMenu(); } },
      el("span", { class: "st", "aria-hidden": "true" }, s.solved ? (due ? "↻" : "✓") : ""),
      el("span", {}, e.title),
      due ? el("span", { class: "due-tag" }, "review due") : null,
      el("span", { class: "sr", style: "position:absolute;left:-999px" }, s.solved ? (due ? "solved, review due" : "solved") : "not solved")));
  }
}
async function renderNext() {
  const box = $("next");
  if (!S.ready) { box.replaceChildren(); return; }
  const ov = JSON.parse(await engine.call("overview", JSON.stringify(S.progress), today()));
  if (!ov.next) { box.replaceChildren(el("p", { class: "note" }, "Everything is solved. Come back when reviews are due.")); return; }
  const target = S.exercises[ov.next.id];
  box.replaceChildren(el("button", { onclick: () => { openExercise(ov.next.id); closeMenu(); } }, el("b", {}, "Up next: " + target.title), el("span", {}, ov.next.why)));
}

/* ---------- opening an exercise ---------- */
function openExercise(id) {
  if (S.cm && S.id) store.set("nudge.code." + S.id, S.cm.getValue());
  S.id = id;
  store.set("nudge.last", id);
  const e = ex();
  $("title").textContent = e.title;
  $("meta").textContent = `Level ${e.level}. Practises: ${e.concepts.join(", ")}.`;
  const prompt = $("prompt");
  prompt.replaceChildren(...e.prompt.trim().split(/\n+/).map((para) => el("p", {}, withCode(para))));
  $("examples").textContent = (e.examples || []).join("\n");
  S.cm.setValue(store.get("nudge.code." + id) ?? e.starter);
  S.cm.clearHistory();
  clearErrLine();
  // restore hints shown earlier for this exercise
  let saved = null;
  try { saved = JSON.parse(store.get("nudge.hints." + id) || "null"); } catch { /* ignore */ }
  const lvl = entry(id).hint_level || 0;
  S.hints = saved && saved.code === (entry(id).hint_code || "") && lvl > 0 ? saved.list.slice(0, lvl) : [];
  S.hintCode = entry(id).hint_code || "";
  S.solutionText = entry(id).solution_seen ? e.solution.trimEnd() : "";
  S.solutionNote = "";
  S.armed = {};
  $("results").replaceChildren(el("h2", {}, "Test results"), el("p", { class: "empty" }, "Write your answer, then run the tests. You'll see what went wrong here."));
  renderSidebar();
  renderLadder();
  setTimeout(() => S.cm.refresh(), 0);
}

/* ---------- running tests ---------- */
function setBusy(text) {
  S.busy = !!text;
  $("busy").textContent = text || "";
  updateButtons();
}
function updateButtons() {
  const off = S.busy || !S.ready;
  $("run-btn").disabled = off;
  $("hint-btn").disabled = off || (entry(S.id).hint_level || 0) >= totalRungs();
  $("again-btn").disabled = off;
}
function clearErrLine() {
  if (S.lastErrLine != null && S.cm) S.cm.removeLineClass(S.lastErrLine, "background", "cm-errline");
  S.lastErrLine = null;
}
function markErrLine(n) {
  clearErrLine();
  if (n && n >= 1 && n <= S.cm.lineCount()) { S.lastErrLine = n - 1; S.cm.addLineClass(n - 1, "background", "cm-errline"); }
}
function persistCode() { if (S.id) store.set("nudge.code." + S.id, S.cm.getValue()); }

async function runTests() {
  if (S.busy || !S.ready) return;
  persistCode();
  const id = S.id, source = S.cm.getValue();
  setBusy("Running your tests…");
  try {
    const { stdout, timedOut } = await engine.run(id, source);
    const r = JSON.parse(await engine.call("finish_check", id, source, stdout, timedOut, JSON.stringify(S.progress), today()));
    saveProgress(r.progress);
    if (r.state.hint_level === 0 && S.hints.length) { S.hints = []; store.del("nudge.hints." + id); }
    if (r.passed) { S.hints = []; store.del("nudge.hints." + id); S.armed = {}; }
    if (id === S.id) { renderResults(r); renderLadder(); $("results").scrollIntoView({ block: "nearest" }); }
    renderSidebar();
    renderNext();
  } catch (err) {
    showBanner("Something went wrong while running your code: " + err.message);
  } finally {
    setBusy("");
  }
}

function caseView(c) {
  const kids = [el("div", { class: "call" }, `${ex().function}(${clip(c.call, 120)})`)];
  if (c.error) {
    const where = c.error.line ? ` on line ${c.error.line}` : "";
    const what = c.error.type === "Timeout" ? "Took too long. Look for a loop that never ends" : c.error.type;
    kids.push(el("div", { class: "line" }, el("b", {}, what), where, c.error.type !== "Timeout" && c.error.msg ? ": " + clip(c.error.msg, 140) : ""));
  } else if (c.mutated) {
    kids.push(el("div", { class: "line" }, "Your function changed the list it was given. Work on a copy and leave the original alone."));
  } else {
    kids.push(el("div", { class: "line" }, "Expected ", el("code", {}, clip(c.expected_repr)), ", got ", el("code", {}, clip(c.got_repr))));
    if (c.printed && c.printed.trim()) kids.push(el("div", { class: "tiny" }, `Your code printed ${clip(JSON.stringify(c.printed.trim()), 60)}, but the tests read what you return.`));
  }
  if (c.hidden) kids.push(el("div", { class: "tiny" }, "This was a hidden test."));
  return el("div", { class: "case" }, kids);
}

function renderResults(r) {
  const box = $("results");
  box.replaceChildren(el("h2", {}, "Test results"));
  clearErrLine();
  if (r.passed) {
    box.append(el("div", { class: "verdict pass" }, el("span", { class: "ic", "aria-hidden": "true" }, "✓"), `All ${r.total} tests pass`));
    const p = r.pass || {};
    let msg;
    if (p.not_due) msg = `You already solved this. The next review is on ${niceDate(p.due)}, so your schedule is unchanged.`;
    else if (p.first) msg = (p.clean ? "Solved on your own, with no big hints. " : "Solved, with help. It will come back for review sooner, which is how it sticks. ") + `Next review: ${niceDate(p.due)}.`;
    else msg = (p.clean ? "Review passed. " : "Passed, but you needed help, so it goes back to the start of the review cycle. ") + `Next review: ${niceDate(p.due)}.`;
    box.append(el("p", { class: "passinfo" }, msg));
    box.append(el("button", { class: "ghost go", onclick: goNext }, "What should I do next?"));
    return;
  }
  if (r.status === "ok" && r.cases.length) box.append(el("div", { class: "verdict fail" }, el("span", { class: "ic", "aria-hidden": "true" }, "✗"), `${r.ok_count} of ${r.total} tests pass`));
  else box.append(el("div", { class: "verdict fail" }, el("span", { class: "ic", "aria-hidden": "true" }, "✗"), "The tests could not run"));
  if (r.status === "syntax") {
    const line = r.info.line;
    box.append(el("p", { class: "detail" }, `Python could not read the file: ${r.info.msg || "invalid syntax"}`, line ? ` (line ${line})` : ""));
    markErrLine(line);
  } else if (r.status === "no_function") {
    const defined = (r.info.defined || []).filter((n) => n !== ex().function);
    box.append(el("p", { class: "detail" }, "I can't find a function called ", el("code", {}, ex().function), ". ",
      defined.length ? "Your code defines " + defined.join(", ") + ". Check the spelling of the name." : "Start with ", defined.length ? "" : el("code", {}, `def ${ex().function}(...):`), defined.length ? "" : "."));
  } else if (r.status === "load_error") {
    const err = r.info.error || {};
    box.append(el("p", { class: "detail" }, `Running the file raised ${err.type}: ${clip(err.msg || "", 140)}`, err.line ? ` (line ${err.line})` : ""));
    markErrLine(err.line);
  } else {
    r.cases.forEach((c) => box.append(caseView(c)));
    if (r.more_failing) box.append(el("p", { class: "tiny" }, `…and ${r.more_failing} more failing.`));
    const first = r.cases.find((c) => c.error && c.error.line);
    if (first) markErrLine(first.error.line);
  }
}

async function goNext() {
  const ov = JSON.parse(await engine.call("overview", JSON.stringify(S.progress), today()));
  if (ov.next) openExercise(ov.next.id);
}

/* ---------- the ladder ---------- */
function rungName(i) {
  if (i < BASE) return LABELS[i];
  return `Approach ${i - BASE + 1} of ${ex().hints.length}`;
}
function hintBody(h) {
  if (h.level === BASE && /\n\n/.test(h.text)) {
    const cut = h.text.indexOf("\n\n");
    return el("div", { class: "rung-text" }, el("p", {}, withCode(h.text.slice(0, cut))), el("pre", {}, h.text.slice(cut + 2)));
  }
  return el("div", { class: "rung-text" }, withCode(h.text));
}
function renderLadder() {
  const e = entry(S.id), level = e.hint_level || 0, total = totalRungs();
  const ready = level === 0 || e.hint_ready;
  const ol = $("ladder");
  ol.replaceChildren();
  for (let i = 0; i < total; i++) {
    const n = i + 1;
    const shown = S.hints.find((h) => h.level === n);
    let cls = "rung ", state = "", body = null, title = rungName(i);
    if (n <= level) {
      cls += "revealed";
      if (shown) { title = shown.title; body = hintBody(shown); }
      else body = el("div", { class: "rung-text" }, "You've seen this one. Use “Show the current hint again” if you need it back.");
    } else if (n === level + 1) {
      cls += ready ? "next" : "next locked";
      state = ready ? "Next. Press the button below." : "Locked until you run your tests again.";
    } else cls += "future";
    ol.append(el("li", { class: cls }, el("span", { class: "node", "aria-hidden": "true" }, String(n)),
      el("div", { class: "rung-body" }, el("div", { class: "rung-title" }, title), state ? el("div", { class: "rung-state" }, state) : null, body)));
  }
  // the last rung is the solution
  const solved = S.solutionText;
  const sol = el("li", { class: "rung solution " + (solved ? "revealed" : "future") }, el("span", { class: "node", "aria-hidden": "true" }, solved ? "★" : "🔒"),
    el("div", { class: "rung-body" }, el("div", { class: "rung-title" }, "The solution"),
      solved ? el("div", { class: "rung-text" }, el("pre", {}, S.solutionText), el("p", {}, "Read it, close it, then write it again from memory. It will come back for review.")) : el("div", { class: "rung-state" }, "Opens up after a few real attempts and the hints above."),
      S.solutionNote ? el("div", { class: "sol-note" }, S.solutionNote, " ", S.armed.force ? el("button", { class: "linkish", onclick: () => askSolution(true) }, "Yes, show it anyway") : el("button", { class: "linkish", onclick: () => { S.armed.force = true; renderLadder(); } }, "Show it anyway")) : null,
      solved ? null : el("div", { class: "ladder-actions" }, el("button", { class: "ghost", onclick: () => askSolution(false) }, "Ask for the solution"))));
  ol.append(sol);
  $("hint-btn").textContent = level >= total ? "That was every hint" : (level === 0 ? "Give me a hint" : "Give me the next hint");
  $("again-btn").hidden = level === 0;
  updateButtons();
}

async function askHint(again) {
  if (S.busy || !S.ready) return;
  persistCode();
  const id = S.id, source = S.cm.getValue();
  let note = "";
  setBusy("Looking at your code…");
  try {
    const { stdout, timedOut } = await engine.run(id, source);
    const r = JSON.parse(await engine.call("finish_hint", id, source, stdout, timedOut, JSON.stringify(S.progress), today(), !!again));
    saveProgress(r.progress);
    if (id !== S.id) return;
    if (r.passes) { renderResults({ passed: true, total: ex().cases.length, pass: { not_due: true, due: entry(id).due || today() } }); $("results").querySelector(".passinfo").textContent = "Your code already passes every test, so there is nothing to hint at."; }
    else if (r.waiting) { note = "You've seen the current hint. Change your code and run the tests, then ask for the next one."; }
    else {
      if (r.code !== S.hintCode) { S.hints = []; S.hintCode = r.code; }
      const h = r.hint;
      S.hints = S.hints.filter((x) => x.level !== h.level).concat([h]).sort((a, b) => a.level - b.level);
      store.set("nudge.hints." + id, JSON.stringify({ code: entry(id).hint_code || "", list: S.hints }));
    }
    renderLadder();
    const all = $("ladder").querySelectorAll(".rung.revealed:not(.solution)");
    if (all.length && r.hint) all[all.length - 1].scrollIntoView({ block: "nearest", behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  } catch (err) {
    showBanner("Something went wrong while looking at your code: " + err.message);
  } finally {
    setBusy("");
  }
  if (note) flash(note);
}

async function askSolution(force) {
  if (S.busy || !S.ready) return;
  const r = JSON.parse(await engine.call("solution", S.id, JSON.stringify(S.progress), today(), !!force));
  saveProgress(r.progress);
  if (r.locked) { S.solutionNote = r.locked.replace(/^Try a bit more first: /, "Not yet. ") + " "; }
  else { S.solutionText = r.solution; S.solutionNote = ""; S.armed = {}; }
  renderLadder();
  renderSidebar();
}

function flash(msg) {
  const b = $("busy");
  b.textContent = msg;
  setTimeout(() => { if (b.textContent === msg) b.textContent = ""; }, 6000);
}
function showBanner(msg) { const b = $("banner"); b.textContent = msg; b.hidden = false; }

/* ---------- backup and restore ---------- */
function backupNote(msg) { $("backup-note").textContent = msg; }
function wireBackup() {
  $("export-btn").onclick = () => {
    const blob = new Blob([JSON.stringify(S.progress, null, 1)], { type: "application/json" });
    const a = el("a", { href: URL.createObjectURL(blob), download: `nudge-progress-${today()}.json` });
    document.body.append(a); a.click(); a.remove();
    backupNote("Backup downloaded.");
  };
  $("import-btn").onclick = () => $("import-file").click();
  $("import-file").onchange = async (e) => {
    const f = e.target.files[0];
    e.target.value = "";
    if (!f) return;
    try {
      const text = await f.text();
      JSON.parse(text);
      const clean = JSON.parse(await engine.call("sanitise_progress", text));
      saveProgress(clean);
      backupNote("Progress restored.");
      openExercise(S.id); renderNext();
    } catch { backupNote("That file isn't a Nudge backup."); }
  };
  let armed = false;
  $("wipe-btn").onclick = () => {
    if (!armed) { armed = true; $("wipe-btn").textContent = "Click again to clear everything"; setTimeout(() => { armed = false; $("wipe-btn").textContent = "Clear everything"; }, 4000); return; }
    armed = false; $("wipe-btn").textContent = "Clear everything";
    try { Object.keys(localStorage).filter((k) => k.startsWith("nudge.")).forEach((k) => localStorage.removeItem(k)); } catch { /* ignore */ }
    S.progress = { exercises: {}, concept_trouble: {} };
    backupNote("Everything cleared.");
    openExercise(S.id); renderNext();
  };
}

/* ---------- menu (small screens) ---------- */
function closeMenu() { $("side").classList.remove("open"); $("menu-btn").setAttribute("aria-expanded", "false"); }

/* ---------- start ---------- */
function setEngineStatus(kind, text) {
  const box = $("engine");
  box.className = "engine " + (kind === "ready" ? "ready" : kind === "failed" ? "failed" : "");
  $("engine-text").textContent = text;
  S.ready = kind === "ready";
  if (S.id) updateButtons();
  if (kind === "ready" && S.id) renderNext();
  if (kind === "failed") showBanner("Python could not start in this browser. Nudge needs a recent Chrome, Edge, Firefox or Safari, and the first visit needs an internet connection to download Python (about 10 MB).");
}

async function main() {
  loadProgress();
  S.cm = CodeMirror.fromTextArea($("code"), {
    mode: "python", lineNumbers: true, indentUnit: 4, matchBrackets: true, autoCloseBrackets: true, viewportMargin: Infinity,
    extraKeys: {
      Tab: (cm) => (cm.somethingSelected() ? cm.indentSelection("add") : cm.replaceSelection("    ", "end")),
      "Shift-Tab": (cm) => cm.indentSelection("subtract"),
      "Ctrl-Enter": () => runTests(), "Cmd-Enter": () => runTests(),
      Esc: () => $("run-btn").focus(),
    },
  });
  S.cm.on("change", () => { clearErrLine(); persistCode(); });
  $("run-btn").onclick = runTests;
  $("hint-btn").onclick = () => askHint(false);
  $("again-btn").onclick = () => askHint(true);
  $("restart-btn").onclick = (() => {
    let armed = false;
    return () => {
      if (!armed) { armed = true; $("restart-btn").textContent = "Click again to wipe your code"; setTimeout(() => { armed = false; $("restart-btn").textContent = "Start over"; }, 4000); return; }
      armed = false; $("restart-btn").textContent = "Start over";
      S.cm.setValue(ex().starter); persistCode(); clearErrLine();
    };
  })();
  $("menu-btn").onclick = () => { const open = $("side").classList.toggle("open"); $("menu-btn").setAttribute("aria-expanded", String(open)); };
  wireBackup();

  const res = await fetch("exercises.json");
  S.exercises = await res.json();
  S.order = Object.keys(S.exercises);
  const start = store.get("nudge.last");
  openExercise(S.exercises[start] ? start : S.order[0]);
  engine = new Engine(setEngineStatus);
  window.nudge = { S, engine: () => engine };  // handy for the browser tests
}
main().catch((err) => showBanner("The page could not start: " + err.message));
