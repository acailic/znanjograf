// site/js/ui/result.js - what a diagnosis found: where the knowledge most likely broke
// (the roots), the repair path, the shaky topics, the tallies, the topics that stayed
// untested, and the curriculum outcomes behind it all.
//
// resultSections and its companions return strings; mountResult is the only function
// here that touches the DOM. Everything can be shown at any moment of a session.
//
//   summary    what the engine's summarise(state) returns
//   index      the data index (index.*.json): topic names, grades and units
//   gradeData  { topics, questions } of the grades in play, as data.js mergeGrades gives
//              them, and optionally outcomes: { edition: the edition file }, without
//              which the outcomes are listed by their ids

import { esc, hrefTo, t } from "../common.js";
import { findOutcome } from "../data.js";
import { displayAnswer, renderMath, renderPrompt } from "./question.js";

const DOT = "\u00b7"; // a middle dot, written as an escape to keep this file ASCII
const STATUS_KEYS = {
  mastered: "status.mastered",
  shaky: "status.shaky",
  weak: "status.weak",
  inferred: "status.inferred",
  untested: "status.untested",
};
const TONES = { mastered: " zg-badge-ok", shaky: " zg-badge-warn", weak: " zg-badge-bad" };

let counter = 0;
const nextId = (name) => `zg-${name}-${(counter += 1)}`;

const topicCache = new WeakMap();

/** id -> topic record of the data index. */
function topicsOf(index) {
  if (!index || typeof index !== "object") return new Map();
  let topics = topicCache.get(index);
  if (!topics) {
    topics = new Map((Array.isArray(index.topics) ? index.topics : []).map((topic) => [topic?.id, topic]));
    topicCache.set(index, topics);
  }
  return topics;
}

const list = (value) => (Array.isArray(value) ? value : []);

function section(name, title, body) {
  const id = nextId(name);
  return `<section class="zg-card" aria-labelledby="${id}"><h2 class="zg-subtitle" id="${id}">${title}</h2>${body}</section>`;
}

function badge(status) {
  return STATUS_KEYS[status] ? `<span class="zg-badge${TONES[status] ?? ""}">${esc(t(STATUS_KEYS[status]))}</span>` : "";
}

/** A topic as a link to its place on the map, with its status when it has one. */
function topicLink(id, index, status) {
  const name = topicsOf(index).get(id)?.name ?? id;
  return `<a class="zg-topiclink" href="${esc(hrefTo("mapa/", { topic: id }))}">${esc(name)}</a>${badge(status)}`;
}

/** "2. razred" and the unit of a topic, for the reader who does not know the graph. */
function placeOf(id, index) {
  const topic = topicsOf(index).get(id);
  if (!topic) return "";
  return [Number.isInteger(topic.grade) ? t("common.grade.n", { n: topic.grade }) : "", topic.unit].filter(Boolean).join(DOT);
}

const questionOf = (gradeData, id) => gradeData?.questions?.[id] ?? null;

// ----- the sections -----------------------------------------------------------------------

function countsMarkup(counts) {
  const row = (key, label) => `<div><dt>${esc(t(label))}</dt><dd>${Math.max(0, Number(counts?.[key]) || 0)}</dd></div>`;
  const body = `<dl class="zg-counts">${row("mastered", "result.counts.mastered")}${row("shaky", "result.counts.shaky")}${row("weak", "result.counts.weak")}${row("inferred", "result.counts.inferred")}${row("untested", "result.counts.untested")}</dl>`;
  return section("counts", esc(t("result.counts.title")), body);
}

function missedItem(question, id) {
  if (!question) return `<li><p class="zg-muted">${esc(id)}</p></li>`;
  const lines = [renderPrompt(question), `<p class="zg-hint">${esc(t("result.answer", { answer: displayAnswer(question) }))}</p>`];
  if (question.explanation) lines.push(`<p class="zg-hint">${renderMath(question.explanation)}</p>`);
  return `<li>${lines.join("")}</li>`;
}

function rootMarkup(root, index, gradeData) {
  const missed = list(root?.missed).map((id) => missedItem(questionOf(gradeData, id), id)).join("");
  const place = placeOf(root?.id, index);
  return `<li class="zg-root${root?.confirmed ? "" : " zg-root-unconfirmed"}">
  <h3>${topicLink(root?.id, index)}</h3>
  <div class="zg-root-meta">
    <span class="zg-badge${root?.confirmed ? " zg-badge-ok" : " zg-badge-warn"}">${esc(t(root?.confirmed ? "result.root.confirmed" : "result.root.unconfirmed"))}</span>
    ${place ? `<span class="zg-muted">${esc(place)}</span>` : ""}
  </div>
  ${root?.confirmed ? "" : `<p class="zg-hint">${esc(t("result.root.unconfirmed.text"))}</p>`}
  ${missed ? `<div class="zg-missed-wrap"><p class="zg-label">${esc(t("result.missed"))}</p><ul class="zg-missed">${missed}</ul></div>` : ""}
</li>`;
}

function rootsMarkup(summary, index, gradeData) {
  const roots = list(summary?.roots);
  if (roots.length === 0) {
    const key = list(summary?.untested).length > 0 ? "result.roots.partial" : "result.roots.none";
    return section("roots", esc(t("result.roots.title")), `<p class="zg-hint">${esc(t(key))}</p>`);
  }
  return section("roots", esc(t("result.roots.title")), `<ul class="zg-roots">${roots.map((root) => rootMarkup(root, index, gradeData)).join("")}</ul>`);
}

/** The repair path, grade by grade from the lowest, numbered across the grades. */
function pathMarkup(summary, index) {
  const title = esc(t("result.path.title"));
  const steps = list(summary?.path);
  if (steps.length === 0) return section("path", title, `<p class="zg-hint">${esc(t("result.path.empty"))}</p>`);

  const groups = new Map();
  for (const step of steps) {
    const grade = topicsOf(index).get(step?.id)?.grade;
    if (!groups.has(grade)) groups.set(grade, []);
    groups.get(grade).push(step);
  }
  let number = 0;
  const blocks = [...groups].map(([grade, group]) => {
    const items = group.map((step) => {
      number += 1;
      return `<li>${topicLink(step?.id, index, step?.status)}</li>`;
    });
    return `<li class="zg-path-group"><h3>${Number.isInteger(grade) ? esc(t("common.grade.n", { n: grade })) : ""}</h3><ol class="zg-path-list" start="${number - items.length + 1}">${items.join("")}</ol></li>`;
  });
  return section("path", title, `<p class="zg-hint">${esc(t("result.path.text"))}</p><ul class="zg-path">${blocks.join("")}</ul>`);
}

function shakyMarkup(summary, index) {
  const shaky = list(summary?.shaky);
  const body = shaky.length === 0
    ? `<p class="zg-hint">${esc(t("result.shaky.empty"))}</p>`
    : `<ul class="zg-linklist">${shaky.map((id) => `<li>${topicLink(id, index)}</li>`).join("")}</ul>`;
  return section("shaky", esc(t("result.shaky.title")), body);
}

function untestedMarkup(summary, index) {
  const untested = list(summary?.untested);
  if (untested.length === 0) return "";
  const body = `<p class="zg-hint">${esc(t("result.untested.text"))}</p><ul class="zg-linklist">${untested.map((id) => `<li>${topicLink(id, index)}</li>`).join("")}</ul>`;
  return section("untested", esc(t("result.untested.title")), body);
}

/** One curriculum outcome: its text when the edition file is at hand, otherwise its id. */
export function outcomeItemMarkup(entry, editionData) {
  const outcome = findOutcome(editionData, entry?.id);
  const meta = [entry?.id, Number.isInteger(outcome?.page) ? t("map.detail.outcomes.page", { n: outcome.page }) : ""].filter(Boolean).join(DOT);
  return `${outcome?.text ? `<p>${renderMath(outcome.text)}</p>` : `<p class="zg-muted">${esc(entry?.id ?? "")}</p>`}${meta ? `<p class="zg-hint">${esc(meta)}</p>` : ""}`;
}

function outcomesMarkup(summary, gradeData) {
  const outcomes = list(summary?.outcomes);
  if (outcomes.length === 0) return "";
  const items = outcomes.map((entry) => `<li data-zg-outcome="${esc(entry?.edition)}/${esc(entry?.id)}">${outcomeItemMarkup(entry, gradeData?.outcomes?.[entry?.edition])}</li>`);
  return section("outcomes", esc(t("result.outcomes.title")), `<p class="zg-hint">${esc(t("result.outcomes.text"))}</p><ul class="zg-outcomes">${items.join("")}</ul>`);
}

/** The whole result as HTML: tallies, roots, repair path, shaky topics, untested topics, outcomes. */
export function resultSections(summary, index, gradeData = {}) {
  return [
    countsMarkup(summary?.counts),
    rootsMarkup(summary, index, gradeData),
    pathMarkup(summary, index),
    shakyMarkup(summary, index),
    untestedMarkup(summary, index),
    outcomesMarkup(summary, gradeData),
  ].join("");
}

const shareBoxId = nextId("share");

/** A read-only field that holds the link and can be selected by hand. */
export function shareBoxMarkup(url) {
  return `<div class="zg-share"><label class="zg-label" for="${shareBoxId}">${esc(t("result.share.label"))}</label><input class="zg-input" id="${shareBoxId}" type="text" readonly value="${esc(url)}"></div>`;
}

/**
 * Draws the result into `container` and wires its three buttons: share, print and
 * export. The page decides what each of them does.
 */
export function mountResult(container, summary, index, gradeData, { onShare, onPrint, onExport } = {}) {
  const actions = section("result-actions", esc(t("result.actions.title")), `<div class="zg-actions">
  <button type="button" class="zg-btn zg-btn-primary" data-zg-share>${esc(t("result.actions.share"))}</button>
  <button type="button" class="zg-btn zg-btn-secondary" data-zg-print>${esc(t("result.actions.print"))}</button>
  <button type="button" class="zg-btn zg-btn-secondary" data-zg-export>${esc(t("result.actions.export"))}</button>
</div>`);
  container.innerHTML = `<div class="zg-result">${resultSections(summary, index, gradeData)}${actions}<div data-zg-share-box hidden></div></div>`;
  const on = (selector, handler) => container.querySelector(selector)?.addEventListener("click", handler);
  on("[data-zg-share]", () => onShare?.());
  on("[data-zg-print]", () => onPrint?.());
  on("[data-zg-export]", () => onExport?.());
}
