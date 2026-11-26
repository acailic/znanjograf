// site/js/pages/diagnose.js - the diagnosis: where to start, the questions, the pause at
// the end of a block, and the result with its link, print and export.
//
// The page keeps no state of its own. Everything a session knows is its scope and its
// log (spec 10.1); after every answer both go to storage, and every screen is drawn
// again from what storage holds. So a reload, a second tab and a shared link all end in
// the same place: the log is replayed and the engine says what comes next.

import {
  announce, esc, focusHeading, fold, formatHash, initCommon, parseHash, renderError, renderLoading, replaceHash, selfHref, t,
} from "../common.js";
import { bankOf, loadGrades, loadIndex, loadOutcomes, mergeGrades, resolveAlias } from "../data.js";
import { decodeSession, encodeSession } from "../engine/encode.js";
import { buildIndex } from "../engine/graph.js";
import { apply, createSession, extend, next, reduce, summarise } from "../engine/session.js";
import { verdictOf } from "../engine/verdict.js";
import { KEYS, clearSession, loadHistory, loadSession, pushHistory, saveSession } from "../storage.js";
import { feedbackMarkup, renderQuestion, wireQuestion } from "../ui/question.js";
import { progressMarkup } from "../ui/progress.js";
import { mountResult, outcomeItemMarkup, shareBoxMarkup } from "../ui/result.js";

const BUDGET = 25; // questions in one block (spec 10.3)
const KINDS = ["topic", "unit", "grade", "grade-full"];

let main = null;
let script = "lat";
let index = null; // the data index
let graph = null; // what buildIndex makes of it
let byId = new Map(); // topic id -> record of the data index
let ticket = 0; // every screen has one; a screen that lost its ticket draws nothing
let run = null; // the live session: { scope, state, engine, log, history, extensions, finished }

// ----- boot ----------------------------------------------------------------------------------

async function boot() {
  const context = initCommon();
  if (!context) return;
  main = document.getElementById("zg-main") || document.body;
  script = context.script;
  window.addEventListener("hashchange", () => route());
  window.addEventListener("zg:cleared", () => route({ focus: true }));
  // Another tab answered or cleared the history: this tab shows what storage holds now.
  window.addEventListener("storage", (event) => {
    if (event.key === null || event.key === KEYS.session || event.key === KEYS.history) route();
  });
  renderLoading(main);
  try {
    index = await loadIndex(script);
    graph = buildIndex(index.topics, index.edges, index.aliases);
    byId = new Map((index.topics || []).map((topic) => [topic.id, topic]));
  } catch (error) {
    renderError(main, error);
    return;
  }
  await route();
}

/** Draws the screen the fragment and storage call for. */
async function route({ focus = false } = {}) {
  const my = ++ticket;
  run = null;
  const params = parseHash(location.hash);
  try {
    if (params.result) return showShared(params.result, my);
    const saved = loadSession();
    const wanted = scopeFromHash(params);
    let stale = false;
    if (saved && (!wanted || sameScope(saved.scope, wanted))) {
      const outcome = await resume(saved, my);
      if (outcome === "shown") return;
      stale = outcome === "stale";
    }
    if (my !== ticket) return;
    startScreen({
      wanted,
      focus,
      stale,
      missing: !wanted && (!!params.topic || params.grade !== undefined),
      other: saved && wanted && !sameScope(saved.scope, wanted) ? saved : null,
    });
  } catch (error) {
    if (my === ticket) renderError(main, error);
  }
}

// ----- scopes -------------------------------------------------------------------------------

function grades() {
  const declared = Array.isArray(index.grades) ? index.grades : [];
  return (declared.length > 0 ? declared : [...new Set((index.topics || []).map((topic) => topic.grade))]).filter(Number.isInteger).sort((a, b) => a - b);
}

/** The topics a scope covers (spec 10.3), as the engine sees them. */
function scopeTopics(scope) {
  if (!scope || !KINDS.includes(scope.kind)) return [];
  const ofGrade = (grade) => graph.topicIds.filter((id) => graph.gradeOf.get(id) === grade);
  switch (scope.kind) {
    case "topic":
      return graph.resolveAlias(scope.id);
    case "unit":
      return ofGrade(scope.grade).filter((id) => graph.unitOf.get(id) === scope.unit);
    case "grade":
      return graph.gradeExits(scope.grade);
    default:
      return ofGrade(scope.grade);
  }
}

/** The grades whose bundles the session can ask from: its topics and everything behind them. */
function gradesNeeded(topicIds) {
  const needed = new Set();
  for (const id of topicIds) {
    for (const related of [id, ...graph.ancestorsOf(id)]) {
      if (Number.isInteger(graph.gradeOf.get(related))) needed.add(graph.gradeOf.get(related));
    }
  }
  return [...needed];
}

function unitsOfGrade(grade) {
  const declared = index.units?.[grade];
  if (Array.isArray(declared) && declared.length > 0) return declared;
  return [...new Set((index.topics || []).filter((topic) => topic.grade === grade).map((topic) => topic.unit))];
}

/** The unit of `grade` whose name matches in either script; undefined when there is none. */
function unitNamed(grade, name) {
  return unitsOfGrade(grade).find((unit) => fold(unit) === fold(name ?? ""));
}

/** The scope the fragment names, or null when it names none or one that does not exist. */
function scopeFromHash(params) {
  if (params.topic) {
    const id = resolveAlias(index, params.topic).find((candidate) => byId.has(candidate));
    return id ? { kind: "topic", id } : null;
  }
  if (params.grade === undefined || !grades().includes(params.grade)) return null;
  if (params.unit) {
    const unit = unitNamed(params.grade, params.unit);
    return unit ? { kind: "unit", grade: params.grade, unit } : null;
  }
  return params.all ? { kind: "grade-full", grade: params.grade } : { kind: "grade", grade: params.grade };
}

function scopeParams(scope) {
  switch (scope?.kind) {
    case "topic":
      return { topic: scope.id };
    case "unit":
      return { grade: scope.grade, unit: scope.unit };
    case "grade-full":
      return { grade: scope.grade, all: true };
    default:
      return { grade: scope?.grade };
  }
}

function sameScope(a, b) {
  if (!a || !b || a.kind !== b.kind) return false;
  if (a.kind === "topic") return a.id === b.id;
  if (a.kind === "unit") return a.grade === b.grade && fold(a.unit ?? "") === fold(b.unit ?? "");
  return a.grade === b.grade;
}

function scopeLabel(scope) {
  switch (scope?.kind) {
    case "topic": {
      const topic = byId.get(scope.id);
      return t("diag.scope.topic", { name: topic?.name ?? scope.id, grade: topic?.grade ?? "?" });
    }
    case "unit":
      return t("diag.scope.unit", { unit: scope.unit, grade: scope.grade });
    case "grade":
      return t("diag.scope.grade", { grade: scope.grade });
    default:
      return t("diag.scope.gradeFull", { grade: scope?.grade ?? "?" });
  }
}

// ----- the engine and the log ------------------------------------------------------------------

async function makeEngine(grades) {
  const gradeData = mergeGrades(await loadGrades(grades, script));
  const curriculum = {};
  for (const [id, topic] of Object.entries(gradeData.topics)) curriculum[id] = Array.isArray(topic?.curriculum) ? topic.curriculum : [];
  return { gradeData, bank: bankOf(gradeData), curriculum };
}

/**
 * The history the engine must see to ask exactly the questions the log holds. It replays
 * strictly: an event whose question it would not pick ends the replay there. A logged
 * question is given the lowest counter there is, so it is the one picked at every step,
 * on this device as on the one the log came from; every other question keeps its count.
 */
function replayHistory(log, history) {
  const forced = {};
  for (const event of Array.isArray(log) ? log : []) {
    if (event && typeof event.questionId === "string") forced[event.questionId] = -1;
  }
  return { ...(history && typeof history === "object" ? history : loadHistory()), ...forced };
}

function replay(log, scope, engine, history) {
  return reduce(log, { scope, index: graph, bank: engine.bank, budget: BUDGET, history: replayHistory(log, history), curriculum: engine.curriculum });
}

function save() {
  if (!run) return;
  saveSession({ v: 1, scope: run.scope, log: run.log, history: run.history, extensions: run.extensions, finished: run.finished, updated: Date.now() });
}

// ----- starting and resuming -------------------------------------------------------------------

function note(key, tone = "warn") {
  return `<p class="zg-note zg-note-${tone}" role="status">${esc(t(key))}</p>`;
}

function resumeMarkup(saved) {
  return `<section class="zg-card" aria-labelledby="zg-resume-title">
  <h2 class="zg-subtitle" id="zg-resume-title">${esc(t("diag.resume.title"))}</h2>
  <p>${esc(t("diag.resume.text", { scope: scopeLabel(saved.scope) }))}</p>
  <a class="zg-btn zg-btn-secondary" href="${esc(selfHref(scopeParams(saved.scope)))}">${esc(t("diag.resume.link"))}</a>
</section>`;
}

function quickMarkup(scope, count) {
  return `<section class="zg-card" aria-labelledby="zg-quick-title">
  <h2 class="zg-subtitle" id="zg-quick-title">${esc(t("diag.result.scope", { scope: scopeLabel(scope) }))}</h2>
  <p class="zg-hint">${esc(t("diag.topics.count", { n: count }))}</p>
  <p class="zg-hint">${esc(t("diag.block.note", { n: BUDGET }))}</p>
  <div class="zg-actions"><button type="button" class="zg-btn zg-btn-primary" data-zg-quick>${esc(t("diag.start"))}</button></div>
</section>`;
}

const option = (value, label, current) => `<option value="${esc(value)}"${String(value) === String(current) ? " selected" : ""}>${esc(label)}</option>`;

const KIND_FIELDS = [
  ["topic", "diag.kind.topic", "diag.kind.hint.topic"],
  ["unit", "diag.kind.unit", "diag.kind.hint.unit"],
  ["grade", "diag.kind.grade", "diag.kind.hint.grade"],
  ["grade-full", "diag.kind.gradeFull", "diag.kind.hint.gradeFull"],
];

function formMarkup(preset) {
  const grade = preset?.grade ?? byId.get(preset?.id)?.grade ?? grades()[0];
  const kind = preset?.kind ?? "grade";
  const radios = KIND_FIELDS.map(([value, label, hint]) => `<label class="zg-radio"><input type="radio" name="zg-kind" value="${value}"${value === kind ? " checked" : ""}><span class="zg-radio-text"><span>${esc(t(label))}</span><span class="zg-hint">${esc(t(hint))}</span></span></label>`);
  const field = (name, labelKey) => `<div class="zg-field" data-zg-for="${name}"${kind === name ? "" : " hidden"}>
  <label for="zg-${name}">${esc(t(labelKey))}</label>
  <select class="zg-select" id="zg-${name}" data-zg-${name}></select>
</div>`;
  return `<form data-zg-form novalidate>
  <fieldset class="zg-fieldset">
    <legend>${esc(t("diag.form.legend"))}</legend>
    <div class="zg-field">
      <label for="zg-grade">${esc(t("diag.grade.label"))}</label>
      <select class="zg-select" id="zg-grade" data-zg-grade>${grades().map((n) => option(n, t("common.grade.n", { n }), grade)).join("")}</select>
    </div>
    <div class="zg-field">
      <span class="zg-label" id="zg-kind-label">${esc(t("diag.kind.label"))}</span>
      <div role="radiogroup" aria-labelledby="zg-kind-label">${radios.join("")}</div>
    </div>
    ${field("topic", "diag.topic.label")}
    ${field("unit", "diag.unit.label")}
  </fieldset>
  <p class="zg-hint" data-zg-count role="status"></p>
  <div class="zg-actions"><button type="submit" class="zg-btn zg-btn-primary">${esc(t("diag.start"))}</button></div>
</form>`;
}

function groupBy(items, keyOf) {
  const groups = new Map();
  for (const item of items) {
    if (!groups.has(keyOf(item))) groups.set(keyOf(item), []);
    groups.get(keyOf(item)).push(item);
  }
  return groups;
}

function wireForm(preset) {
  const form = main.querySelector("[data-zg-form]");
  if (!form) return;
  const gradeSelect = form.querySelector("[data-zg-grade]");
  const topicSelect = form.querySelector("[data-zg-topic]");
  const unitSelect = form.querySelector("[data-zg-unit]");
  const count = form.querySelector("[data-zg-count]");
  let preselected = preset;

  const grade = () => Number(gradeSelect.value);
  const kind = () => form.querySelector("input[name=zg-kind]:checked")?.value ?? "grade";
  const picked = () => {
    if (!grades().includes(grade())) return null;
    switch (kind()) {
      case "topic":
        return byId.has(topicSelect.value) ? { kind: "topic", id: topicSelect.value } : null;
      case "unit":
        return unitSelect.value ? { kind: "unit", grade: grade(), unit: unitSelect.value } : null;
      case "grade-full":
        return { kind: "grade-full", grade: grade() };
      default:
        return { kind: "grade", grade: grade() };
    }
  };
  const sync = () => {
    for (const field of form.querySelectorAll("[data-zg-for]")) field.hidden = field.dataset.zgFor !== kind();
    const scope = picked();
    count.textContent = scope ? t("diag.topics.count", { n: scopeTopics(scope).length }) : "";
  };

  const rebuild = () => {
    const ofGrade = (index.topics || []).filter((topic) => topic.grade === grade());
    const groups = [...groupBy(ofGrade, (topic) => topic.unit)].map(([unit, items]) => `<optgroup label="${esc(unit)}">${items.map((topic) => option(topic.id, topic.name, preselected?.kind === "topic" ? preselected.id : "")).join("")}</optgroup>`);
    topicSelect.innerHTML = option("", t("diag.topic.any"), "") + groups.join("");
    unitSelect.innerHTML = option("", t("diag.unit.any"), "") + unitsOfGrade(grade()).map((unit) => option(unit, unit, preselected?.kind === "unit" && fold(unit) === fold(preselected.unit ?? "") ? unit : "")).join("");
    sync();
  };

  gradeSelect.addEventListener("change", () => {
    preselected = null; // another grade: what the link named no longer applies
    rebuild();
  });
  for (const radio of form.querySelectorAll("input[name=zg-kind]")) radio.addEventListener("change", sync);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const scope = picked();
    if (!scope) {
      const target = { topic: topicSelect, unit: unitSelect }[kind()] ?? gradeSelect;
      target.focus();
      return;
    }
    start(scope, form.querySelector("button[type=submit]"));
  });
  rebuild();
}

/** Where a session starts: the picker, and first a single button when the fragment already names a scope. */
function startScreen({ wanted = null, other = null, stale = false, missing = false, focus = false } = {}) {
  const topics = wanted ? scopeTopics(wanted) : [];
  const quick = topics.length > 0;
  main.innerHTML = `<div class="zg-wrap zg-narrow">
  <h1 class="zg-title" data-zg-focus>${esc(t("diag.title"))}</h1>
  <p class="zg-lead">${esc(t("diag.lead"))}</p>
  ${stale ? note("diag.stale") : ""}
  ${missing ? note("diag.missing") : ""}
  ${other ? resumeMarkup(other) : ""}
  ${quick ? quickMarkup(wanted, topics.length) : ""}
  ${quick ? `<details class="zg-card zg-scope"><summary>${esc(t("diag.change"))}</summary>${formMarkup(wanted)}</details>` : `<section class="zg-card">${formMarkup(wanted)}</section>`}
  ${quick ? "" : `<p class="zg-hint">${esc(t("diag.block.note", { n: BUDGET }))}</p>`}
</div>`;
  wireForm(wanted);
  main.querySelector("[data-zg-quick]")?.addEventListener("click", (event) => start(wanted, event.currentTarget));
  if (focus) focusHeading(main);
}

async function start(scope, button) {
  const my = ++ticket;
  if (button) button.disabled = true;
  try {
    const engine = await makeEngine(gradesNeeded(scopeTopics(scope)));
    if (my !== ticket) return;
    const history = loadHistory();
    run = {
      scope,
      engine,
      history,
      log: [],
      extensions: 0,
      finished: false,
      state: createSession({ scope, index: graph, bank: engine.bank, budget: BUDGET, history, curriculum: engine.curriculum }),
    };
    save();
    replaceHash(scopeParams(scope)); // a reload finds the session again
    advance(run);
  } catch (error) {
    if (my === ticket) renderError(main, error);
  }
}

/** Draws the saved session again. Returns "shown", or "stale" when the data no longer fits it. */
async function resume(saved, my) {
  const scope = saved.scope;
  const topics = scopeTopics(scope);
  if (topics.length === 0) {
    clearSession();
    return "stale";
  }
  renderLoading(main);
  const engine = await makeEngine(gradesNeeded(topics));
  if (my !== ticket) return "shown";
  let state;
  try {
    state = replay(saved.log, scope, engine, saved.history);
  } catch (error) {
    console.error(error);
    clearSession();
    return "stale";
  }
  // "Continue" pressed at a pause, then the tab was closed: the block is still extended.
  const extensions = Math.max(0, Number(saved.extensions) || 0);
  while (state.extensions < extensions) state = extend(state);
  const history = saved.history && typeof saved.history === "object" ? saved.history : loadHistory();
  run = { scope, engine, history, log: [...state.log], extensions: state.extensions, finished: saved.finished === true, state };
  if (run.finished) return showResult(run);
  advance(run);
  return "shown";
}

function restart() {
  clearSession();
  run = null;
  replaceHash({});
  route({ focus: true });
}

// ----- questions --------------------------------------------------------------------------------

function progressOf(session) {
  const total = scopeTopics(session.scope).length;
  let done = 0;
  try {
    done = total - summarise(session.state).counts.untested;
  } catch {
    done = 0; // the bar still says how many questions were answered
  }
  return { asked: session.log.length, done, total };
}

function advance(session) {
  const step = next(session.state);
  if (step.kind === "question") return questionScreen(session, step);
  if (step.kind === "paused") return pauseScreen(session, step.asked);
  session.finished = true;
  save();
  showResult(session);
}

function questionScreen(session, step) {
  main.innerHTML = `<div class="zg-wrap zg-narrow">
  <h1 class="zg-visually-hidden">${esc(t("diag.title"))}</h1>
  ${progressMarkup(progressOf(session))}
  ${renderQuestion(step.question, index, session.log.length + 1)}
</div>`;
  wireQuestion(main.querySelector("[data-zg-question]"), (answer) => answerReceived(session, step.question, answer), step.question);
  focusHeading(main);
}

/** True once the engine has settled the topic these answers belong to. */
function settled(session, topicId) {
  const bank = session.engine.bank[topicId] ?? [];
  const evidence = [];
  for (const event of session.state.log) {
    const question = bank.find((item) => item.id === event.questionId);
    if (question) evidence.push({ question, correct: event.correct });
  }
  try {
    return verdictOf(evidence).done === true;
  } catch {
    return false;
  }
}

function answerReceived(session, question, { correct, dontKnow }) {
  if (run !== session) return route();
  try {
    session.state = apply(session.state, { questionId: question.id, correct });
  } catch (error) {
    console.error(error);
    return route(); // out of step with the engine: draw again from what storage holds
  }
  session.log = [...session.state.log];
  pushHistory([question.id]);
  save();
  main.querySelector("[data-zg-feedback]")?.remove();
  // Right or wrong only; the explanation comes once the topic is settled (spec 10.2).
  main.querySelector("[data-zg-question]").insertAdjacentHTML("afterend", feedbackMarkup({ correct, dontKnow, explanation: settled(session, question.topic) ? question.explanation : "" }));
  const box = main.querySelector("[data-zg-feedback]");
  box.querySelector("[data-zg-next]").addEventListener("click", () => {
    if (run === session) advance(session);
  });
  box.focus();
}

function pauseScreen(session, asked) {
  main.innerHTML = `<div class="zg-wrap zg-narrow">
  <h1 class="zg-visually-hidden">${esc(t("diag.title"))}</h1>
  ${progressMarkup(progressOf(session))}
  <section class="zg-card zg-stack">
    <h2 class="zg-subtitle" data-zg-focus>${esc(t("diag.pause.title"))}</h2>
    <p>${esc(t("diag.pause.text", { n: asked }))}</p>
    <div class="zg-actions">
      <button type="button" class="zg-btn zg-btn-primary" data-zg-extend>${esc(t("diag.pause.extend"))}</button>
      <button type="button" class="zg-btn zg-btn-secondary" data-zg-stop>${esc(t("diag.pause.result"))}</button>
    </div>
  </section>
</div>`;
  main.querySelector("[data-zg-extend]").addEventListener("click", () => {
    session.extensions += 1;
    session.state = extend(session.state);
    save();
    advance(session);
  });
  main.querySelector("[data-zg-stop]").addEventListener("click", () => {
    session.finished = true;
    save();
    showResult(session);
  });
  focusHeading(main);
}

// ----- the result --------------------------------------------------------------------------------

function brokenLink() {
  main.innerHTML = `<div class="zg-wrap zg-narrow">
  <h1 class="zg-title" data-zg-focus>${esc(t("diag.result.shared.title"))}</h1>
  <p class="zg-note zg-note-bad" role="alert">${esc(t("diag.result.shared.broken"))}</p>
  <p><a class="zg-btn zg-btn-secondary" href="${esc(selfHref())}">${esc(t("diag.start"))}</a></p>
</div>`;
  focusHeading(main);
}

/** A result somebody shared: the link carries the scope and the log, nothing else (spec 10.5). */
async function showShared(text, my) {
  let scope = null;
  let log = null;
  try {
    const decoded = decodeSession(text);
    scope = decoded?.scope;
    log = decoded?.log;
  } catch {
    scope = null; // a link that cannot be read is a broken link
  }
  if (!scope || !KINDS.includes(scope.kind) || !Array.isArray(log)) return brokenLink();
  const topics = scopeTopics(scope);
  if (topics.length === 0) return brokenLink();
  renderLoading(main);
  const engine = await makeEngine(gradesNeeded(topics));
  if (my !== ticket) return;
  run = null;
  showResult({ scope, engine, log, finished: true, state: replay(log, scope, engine, {}) }, { shared: true });
}

function showResult(session, { shared = false } = {}) {
  const summary = summarise(session.state);
  // Stopped at a pause: the diagnosis can be taken up again where it left off.
  const resumable = !shared && next(session.state).kind === "paused";
  const disclaimer = t(session.log.length === 1 ? "diag.result.disclaimer.one" : "diag.result.disclaimer.many", { n: session.log.length });
  main.innerHTML = `<div class="zg-wrap">
  <h1 class="zg-title" data-zg-focus>${esc(t(shared ? "diag.result.shared.title" : "diag.result.title"))}</h1>
  <p class="zg-lead">${esc(t("diag.result.scope", { scope: scopeLabel(session.scope) }))}</p>
  <p class="zg-hint">${esc(disclaimer)}</p>
  ${shared ? `<p class="zg-note">${esc(t("diag.result.shared.text"))}</p>` : ""}
  ${resumable ? note("diag.result.stopped") : ""}
  <div class="zg-section" data-zg-result></div>
  <div class="zg-actions">
    ${resumable ? `<button type="button" class="zg-btn zg-btn-primary" data-zg-resume>${esc(t("diag.result.resume"))}</button>` : ""}
    ${shared ? "" : `<button type="button" class="zg-btn zg-btn-secondary" data-zg-again>${esc(t("diag.result.again"))}</button>`}
  </div>
</div>`;
  mountResult(main.querySelector("[data-zg-result]"), summary, index, session.engine.gradeData, {
    onShare: () => share(session),
    onPrint: () => window.print(),
    onExport: () => exportJson(session, summary),
  });
  main.querySelector("[data-zg-resume]")?.addEventListener("click", () => {
    session.finished = false;
    session.extensions += 1;
    session.state = extend(session.state);
    save();
    advance(session);
  });
  main.querySelector("[data-zg-again]")?.addEventListener("click", restart);
  focusHeading(main);
  fillOutcomes(session, summary);
}

/** The outcome texts come from their edition files; until then each outcome shows its id. */
async function fillOutcomes(session, summary) {
  const my = ticket;
  const editions = {};
  await Promise.all([...new Set((summary.outcomes ?? []).map((entry) => entry.edition))].map(async (edition) => {
    editions[edition] = await loadOutcomes(edition, script).catch(() => null);
  }));
  if (my !== ticket) return;
  session.engine.gradeData.outcomes = editions;
  for (const item of main.querySelectorAll("[data-zg-outcome]")) {
    const [edition, id] = item.dataset.zgOutcome.split("/");
    if (editions[edition]) item.innerHTML = outcomeItemMarkup({ edition, id }, editions[edition]);
  }
}

function shareUrl(session) {
  return location.href.split("#")[0] + formatHash({ result: encodeSession({ scope: session.scope, log: session.log }), script });
}

function share(session) {
  let url;
  try {
    url = shareUrl(session);
  } catch (error) {
    console.error(error);
    return;
  }
  const box = main.querySelector("[data-zg-share-box]");
  box.hidden = false;
  box.innerHTML = shareBoxMarkup(url);
  const input = box.querySelector("input");
  copy(url).then((copied) => {
    announce(t(copied ? "result.share.done" : "result.share.manual"));
    input.focus();
    input.select();
  });
}

async function copy(text) {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    // Not allowed here (an insecure address, a refused permission): the old way may still work.
  }
  try {
    const field = document.createElement("textarea");
    field.value = text;
    field.setAttribute("readonly", "");
    field.className = "zg-visually-hidden";
    document.body.append(field);
    field.select();
    const copied = document.execCommand("copy");
    field.remove();
    return copied;
  } catch {
    return false;
  }
}

function exportJson(session, summary) {
  const payload = { format: "znanjograf-rezultat", version: 1, exported: new Date().toISOString(), script, scope: session.scope, log: session.log, summary };
  const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = "znanjograf-rezultat.json";
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

boot();
