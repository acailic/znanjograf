// site/js/pages/map.js - the map of knowledge: every topic, grouped by grade and unit,
// with a search and filters; the graph around the selected topic; and what that topic
// is about, what it asks of the pupil, what comes before it and what is built on it.

import { esc, formatHash, go, hrefTo, initCommon, parseHash, renderError, renderLoading, replaceHash, searchKey, t, withScript } from "../common.js";
import { findOutcome, loadGrade, loadIndex, loadOutcomes, resolveAlias, topicOfQuestion } from "../data.js";
import { buildIndex } from "../engine/graph.js";
import { mount as mountGraph } from "../graph-view.js";
import { layout } from "../layout.js";
import { displayAnswer, renderMath, renderPrompt } from "../ui/question.js";
import { outcomeItemMarkup } from "../ui/result.js";

const GRAPH_LIMIT = 60; // above this many topics around the selection only a list is shown
const LEVELS_UP = 2; // hard prerequisites are followed this many levels up
const ISSUES_URL = "https://github.com/acailic/znanjograf/issues/new?title=";
const DOT = " \u00b7 "; // a spaced middle dot, written as an escape to keep this file ASCII

const AREA_KEYS = { numbers: "area.numbers", geometry: "area.geometry", data: "area.data" };
const STRENGTH_KEYS = { hard: "strength.hard", soft: "strength.soft" };
const MATCH_KEYS = { exact: "match.exact", partial: "match.partial" };

let main = null;
let script = "lat";
let index = null; // the data index
let graph = null; // what buildIndex makes of it
let byId = new Map(); // topic id -> record of the data index
let params = {}; // what the fragment says now
let query = ""; // what the search box holds
let opened = new Map(); // groups of the list the reader opened or closed by hand
let ticket = 0; // guards the parts of the panel that arrive later

// ----- boot ----------------------------------------------------------------------------------

async function boot() {
  const context = initCommon();
  if (!context) return;
  main = document.getElementById("zg-main") || document.body;
  script = context.script;
  renderLoading(main);
  try {
    index = await loadIndex(script);
    graph = buildIndex(index.topics, index.edges, index.aliases);
    byId = new Map((index.topics || []).map((topic) => [topic.id, topic]));
  } catch (error) {
    renderError(main, error);
    return;
  }
  window.addEventListener("hashchange", () => render(true));
  render(false);
}

// ----- reading the data -----------------------------------------------------------------------

function gradesOf() {
  return [...new Set((index.topics || []).map((topic) => topic.grade))].filter(Number.isInteger).sort((a, b) => a - b);
}

function areasOf() {
  const declared = Array.isArray(index.areas) ? index.areas : [];
  return declared.length > 0 ? declared : [...new Set((index.topics || []).map((topic) => topic.area))].filter(Boolean);
}

const searching = () => query.trim() !== "";
const filtering = () => searching() || params.grade !== undefined || !!params.area;

function filtered() {
  const tokens = searchKey(query).split(" ").filter(Boolean);
  return (index.topics || []).filter((topic) => {
    if (params.grade !== undefined && topic.grade !== params.grade) return false;
    if (filteringByArea() && topic.area !== params.area) return false;
    if (tokens.length === 0) return true;
    const key = `${searchKey(topic.name)} ${searchKey(topic.id)}`;
    return tokens.every((token) => key.includes(token));
  });
}

const filteringByArea = () => !!params.area && areasOf().includes(params.area);

/** The topic the fragment names, through an alias if it is one; null when there is none. */
function selectedId() {
  return params.topic ? resolveAlias(index, params.topic).find((id) => byId.has(id)) ?? null : null;
}

/** A link to a topic of this page: the fragment keeps the filters and the script. */
function topicHref(id) {
  return formatHash(withScript({ topic: id, grade: params.grade, area: params.area }));
}

// ----- the page -------------------------------------------------------------------------------

function toolbarMarkup() {
  const option = (value, label, current) => `<option value="${esc(value)}"${value === current ? " selected" : ""}>${esc(label)}</option>`;
  return `<div class="zg-toolbar">
  <div class="zg-field">
    <label for="zg-search">${esc(t("map.search.label"))}</label>
    <input class="zg-input" id="zg-search" type="search" placeholder="${esc(t("map.search.placeholder"))}" autocomplete="off" autocapitalize="off" spellcheck="false" value="${esc(query)}">
  </div>
  <div class="zg-field">
    <label for="zg-filter-grade">${esc(t("map.grade.label"))}</label>
    <select class="zg-select" id="zg-filter-grade" data-zg-filter="grade">${option("", t("map.grade.any"), params.grade ?? "")}${gradesOf().map((grade) => option(grade, t("common.grade.n", { n: grade }), params.grade)).join("")}</select>
  </div>
  <div class="zg-field">
    <label for="zg-filter-area">${esc(t("map.area.label"))}</label>
    <select class="zg-select" id="zg-filter-area" data-zg-filter="area">${option("", t("map.area.any"), params.area ?? "")}${areasOf().map((area) => option(area, AREA_KEYS[area] ? t(AREA_KEYS[area]) : area, params.area)).join("")}</select>
  </div>
</div>`;
}

function render() {
  const before = selectedId();
  params = parseHash(location.hash);
  // The panel takes the focus when the fragment newly names a topic.
  const moveFocus = selectedId() !== null && selectedId() !== before;
  main.innerHTML = `<div class="zg-wrap">
  <h1 class="zg-title" data-zg-focus>${esc(t("map.title"))}</h1>
  <p class="zg-lead">${esc(t("map.lead"))}</p>
  ${toolbarMarkup()}
  <div class="zg-map-layout">
    <section class="zg-map-list" aria-labelledby="zg-map-list-title">
      <h2 class="zg-visually-hidden" id="zg-map-list-title">${esc(t("map.list.title"))}</h2>
      <p class="zg-hint" id="zg-map-count" role="status"></p>
      <div data-zg-list></div>
    </section>
    <section class="zg-map-detail" data-zg-detail aria-labelledby="zg-detail-title"></section>
  </div>
</div>`;

  const search = main.querySelector("#zg-search");
  search.addEventListener("input", () => {
    query = search.value;
    renderList();
  });
  for (const select of main.querySelectorAll("[data-zg-filter]")) {
    select.addEventListener("change", () => {
      const name = select.dataset.zgFilter === "grade" ? "grade" : "area";
      const next = { ...params };
      next[name] = select.value === "" ? undefined : name === "grade" ? Number(select.value) : select.value;
      replaceHash(next); // a filter is not a place one goes back to
      params = parseHash(location.hash);
      renderList();
    });
  }

  renderList();
  renderDetail(moveFocus);
}

// ----- the list --------------------------------------------------------------------------------

function groupBy(items, keyOf) {
  const groups = new Map();
  for (const item of items) {
    const key = keyOf(item);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(item);
  }
  return groups;
}

/** A group is open while searching, or when it holds the selected topic, unless the reader closed or opened it by hand. */
function isShown(key, holdsSelection) {
  return opened.has(key) ? opened.get(key) : searching() || holdsSelection;
}

function listMarkup(topics) {
  if (topics.length === 0) return `<p class="zg-note zg-note-warn">${esc(t("map.list.empty"))}</p>`;
  const current = selectedId();
  const blocks = [];
  for (const [grade, ofGrade] of groupBy(topics, (topic) => topic.grade)) {
    const gradeKey = `grade-${grade}`;
    const units = [];
    for (const [unit, inUnit] of groupBy(ofGrade, (topic) => topic.unit)) {
      const key = `${gradeKey}|${unit}`;
      const links = inUnit.map((topic) => `<li><a href="${esc(topicHref(topic.id))}"${topic.id === current ? ' aria-current="true"' : ""}>${esc(topic.name)}</a></li>`);
      units.push(`<details class="zg-group zg-group-inner" data-zg-key="${esc(key)}"${isShown(key, inUnit.some((topic) => topic.id === current)) ? " open" : ""}><summary>${esc(unit)}</summary><ul>${links.join("")}</ul></details>`);
    }
    const holds = ofGrade.some((topic) => topic.id === current);
    blocks.push(`<details class="zg-group" data-zg-key="${esc(gradeKey)}"${isShown(gradeKey, holds) ? " open" : ""}><summary>${esc(t("common.grade.n", { n: grade }))}</summary>${units.join("")}</details>`);
  }
  return blocks.join("");
}

function renderList() {
  const box = main.querySelector("[data-zg-list]");
  if (!box) return;
  const topics = filtered();
  box.innerHTML = listMarkup(topics);
  // Only a reader's click opens or closes a group for good. (The toggle event also fires
  // when the list is drawn with groups already open, which would make them stick.)
  for (const summary of box.querySelectorAll("summary")) {
    summary.addEventListener("click", () => opened.set(summary.parentElement.dataset.zgKey, !summary.parentElement.open));
  }
  main.querySelector("#zg-map-count").textContent = filtering()
    ? t(topics.length === 0 ? "map.list.empty" : "map.list.found", { n: topics.length })
    : "";
}

// ----- the panel -------------------------------------------------------------------------------

function edgeList(edges, emptyKey) {
  if (edges.length === 0) return `<p class="zg-hint">${esc(t(emptyKey))}</p>`;
  const items = edges.map((edge) => `<li><a class="zg-topiclink" href="${esc(topicHref(edge.id))}">${esc(byId.get(edge.id)?.name ?? edge.id)}</a><span class="zg-badge">${esc(t(STRENGTH_KEYS[edge.strength] ?? "strength.soft"))}</span></li>`);
  return `<ul class="zg-linklist">${items.join("")}</ul>`;
}

function aliasMarkup(aliasFrom, targets) {
  // The names are links built here; the old id comes from the fragment, so it is escaped first.
  const names = targets.map((id) => `<a href="${esc(topicHref(id))}">${esc(byId.get(id)?.name ?? id)}</a>`).join(", ");
  return `<p class="zg-note" role="status">${t("map.detail.aliasHtml", { old: esc(aliasFrom), names })}</p>`;
}

function detailMarkup(topic, aliasFrom, targets) {
  const place = [Number.isInteger(topic.grade) ? t("common.grade.n", { n: topic.grade }) : "", topic.unit].filter(Boolean).join(DOT);
  return `<p class="zg-eyebrow">${esc(place)}</p>
  <h2 class="zg-subtitle" id="zg-detail-title" data-zg-focus tabindex="-1">${esc(topic.name)}</h2>
  <div class="zg-actions">
    <a class="zg-btn zg-btn-primary" href="${esc(hrefTo("dijagnostika/", { topic: topic.id }))}">${esc(t("map.detail.diagnose"))}</a>
    <a class="zg-btn zg-btn-quiet" href="${esc(ISSUES_URL + encodeURIComponent(`[${topic.id}] `))}" target="_blank" rel="noopener">${esc(t("map.detail.report"))}</a>
  </div>
  ${aliasFrom ? aliasMarkup(aliasFrom, targets) : ""}
  <section class="zg-detail-graph" aria-labelledby="zg-graph-title">
    <h3 class="zg-label" id="zg-graph-title">${esc(t("map.detail.graph.title"))}</h3>
    <p class="zg-hint">${esc(t("map.detail.graph.hint"))}</p>
    <div class="zg-graph-box" data-zg-graph role="region" aria-label="${esc(t("map.detail.graph.title"))}" tabindex="0"></div>
  </section>
  <dl class="zg-props">
    <dt>${esc(t("map.detail.summary"))}</dt><dd data-zg-slot="summary"><span class="zg-muted">${esc(t("common.loading"))}</span></dd>
    <dt>${esc(t("map.detail.mastery"))}</dt><dd data-zg-slot="mastery"></dd>
    <dt>${esc(t("map.detail.outcomes"))}</dt><dd data-zg-slot="outcomes"></dd>
    <dt>${esc(t("map.detail.sample"))}</dt><dd data-zg-slot="sample"></dd>
    <dd data-zg-slot="review"></dd>
    <dt>${esc(t("map.detail.prereq"))}</dt><dd>${edgeList(graph.prereqsOf(topic.id), "map.detail.prereq.none")}</dd>
    <dt>${esc(t("map.detail.required"))}</dt><dd>${edgeList(graph.dependentsOf(topic.id), "map.detail.required.none")}</dd>
  </dl>`;
}

async function renderDetail(moveFocus) {
  const my = ++ticket;
  const panel = main.querySelector("[data-zg-detail]");
  if (!panel) return;
  const requested = params.topic;
  const targets = requested ? resolveAlias(index, requested) : [];
  const id = targets.find((candidate) => byId.has(candidate));
  if (!id) {
    const title = requested ? t("map.detail.missing.title") : t("map.detail.empty.title");
    const text = requested ? t("map.detail.missing.text", { id: requested }) : t("map.detail.empty.text");
    panel.innerHTML = `<h2 class="zg-subtitle" id="zg-detail-title" data-zg-focus tabindex="-1">${esc(title)}</h2><p class="${requested ? "zg-note zg-note-warn" : "zg-hint"}">${esc(text)}</p>`;
    if (requested) panel.querySelector("[data-zg-focus]").focus();
    return;
  }
  panel.innerHTML = detailMarkup(byId.get(id), requested !== id ? requested : null, targets);
  drawGraph(panel, byId.get(id));
  if (moveFocus) panel.querySelector("[data-zg-focus]").focus();
  await fillDetail(panel, byId.get(id), my);
}

function pickSample(questions) {
  return questions.find((question) => question.level === "standard") ?? questions[0] ?? null;
}

function sampleMarkup(question) {
  if (!question) return `<p class="zg-hint">${esc(t("map.detail.sample.none"))}</p>`;
  return `<div class="zg-sample">${renderPrompt(question)}<details><summary>${esc(t("map.detail.sample.answer"))}</summary><p>${renderMath(displayAnswer(question))}</p></details></div>`;
}

function outcomesMarkup(entries, editions) {
  if (entries.length === 0) return `<p class="zg-hint">${esc(t("map.detail.outcomes.none"))}</p>`;
  const items = entries.map((entry) => {
    const edition = editions[entry.edition];
    // An outcome the edition file does not hold is said so; a file that could not be read says nothing.
    const missing = edition && !findOutcome(edition, entry.outcome) ? `<p class="zg-hint">${esc(t("map.detail.outcomes.missing", { id: entry.outcome }))}</p>` : "";
    const meta = [
      `<span class="zg-badge">${esc(t(MATCH_KEYS[entry.match] ?? "match.partial"))}</span>`,
      typeof edition?.applies_from === "string" ? esc(t("map.detail.outcomes.edition", { year: edition.applies_from })) : "",
    ].filter(Boolean).join(DOT);
    return `<li>${outcomeItemMarkup({ edition: entry.edition, id: entry.outcome }, edition)}${missing}<p class="zg-hint">${meta}</p></li>`;
  });
  return `<ul class="zg-outcomes">${items.join("")}</ul>`;
}

function reviewMarkup(review) {
  if (typeof review?.name !== "string" || review.name === "") return "";
  // The key ends in Html: the label is marked up in strings.js; everything filled in is escaped.
  return `<p class="zg-note zg-note-ok">${t("map.detail.reviewHtml", { name: esc(review.name), role: esc(review.role ?? ""), date: esc(review.date ?? "") })}${review.note ? ` ${esc(review.note)}` : ""}</p>`;
}

/** Fills what needs the grade bundle: summary, mastery, a sample question, the review, the outcomes. */
async function fillDetail(panel, topic, my) {
  const put = (slot, html) => {
    const element = panel.querySelector(`[data-zg-slot="${slot}"]`);
    if (element) element.innerHTML = html;
  };
  try {
    const bundle = await loadGrade(topic.grade, script);
    if (my !== ticket) return;
    const record = bundle?.topics?.[topic.id] ?? {};
    put("summary", record.summary ? renderMath(record.summary) : "");
    const mastery = Array.isArray(record.mastery) ? record.mastery : [];
    put("mastery", mastery.length === 0 ? "" : `<span class="zg-hint">${esc(t("map.detail.mastery.lead"))}</span><ul>${mastery.map((item) => `<li>${renderMath(item)}</li>`).join("")}</ul>`);
    const questions = Object.entries(bundle?.questions ?? {}).filter(([id]) => topicOfQuestion(id) === topic.id).map(([id, question]) => ({ ...question, id }));
    put("sample", sampleMarkup(pickSample(questions)));
    put("review", reviewMarkup(record.review));

    const entries = (Array.isArray(record.curriculum) ? record.curriculum : []).filter((entry) => entry && entry.edition && entry.outcome);
    const editions = {};
    await Promise.all([...new Set(entries.map((entry) => entry.edition))].map(async (edition) => {
      editions[edition] = await loadOutcomes(edition, script).catch(() => null);
    }));
    if (my !== ticket) return;
    put("outcomes", outcomesMarkup(entries, editions));
  } catch (error) {
    console.error(error);
    if (my === ticket) put("summary", `<p class="zg-note zg-note-bad" role="alert">${esc(t("common.error.data"))}</p>`);
  }
}

// ----- the graph --------------------------------------------------------------------------------

/** The selected topic, its hard prerequisites two levels up and what is built on it one level down. */
function neighbourhood(id) {
  const nodes = new Set([id]);
  let frontier = [id];
  for (let level = 0; level < LEVELS_UP; level += 1) {
    const next = [];
    for (const topicId of frontier) {
      for (const edge of graph.prereqsOf(topicId)) {
        if (edge.strength === "hard" && !nodes.has(edge.id)) {
          nodes.add(edge.id);
          next.push(edge.id);
        }
      }
    }
    frontier = next;
  }
  for (const edge of graph.dependentsOf(id)) nodes.add(edge.id);
  return {
    nodes: graph.learningOrder([...nodes]).map((topicId) => byId.get(topicId)).filter((topic) => Number.isInteger(topic?.grade)),
    edges: (index.edges || []).filter(([topic, requires]) => nodes.has(topic) && nodes.has(requires)),
  };
}

function select(id) {
  go({ topic: id, grade: params.grade, area: params.area });
}

/** Above the limit the graph gives way to a plain list of the same topics. */
function listInsteadOfGraph(box, nodes) {
  const note = document.createElement("div");
  note.className = "zg-hint";
  note.innerHTML = `<p>${esc(t("map.detail.graph.tooBig", { n: GRAPH_LIMIT }))}</p><ul class="zg-linklist">${nodes.map((node) => `<li><a class="zg-topiclink" href="${esc(topicHref(node.id))}">${esc(node.name)}</a></li>`).join("")}</ul>`;
  box.replaceWith(note);
}

function drawGraph(panel, topic) {
  const box = panel.querySelector("[data-zg-graph]");
  if (!box) return;
  const around = neighbourhood(topic.id);
  if (around.nodes.length === 0 || around.nodes.length > GRAPH_LIMIT) return listInsteadOfGraph(box, around.nodes);
  try {
    mountGraph(box, layout({ nodes: around.nodes, edges: around.edges, focus: topic.id }), {}, select);
  } catch (error) {
    console.error(error);
    box.hidden = true;
    return;
  }
  for (const node of box.querySelectorAll(".zg-node")) {
    if (!byId.has(node.dataset.id)) continue; // a "+N" box that stands for topics left out
    node.setAttribute("tabindex", "0");
    node.setAttribute("role", "link");
    node.setAttribute("aria-label", byId.get(node.dataset.id).name);
  }
  box.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    const node = event.target.closest?.(".zg-node");
    if (!node || !byId.has(node.dataset.id)) return;
    event.preventDefault();
    select(node.dataset.id);
  });
  // Centre the selected topic in the box without moving the page itself (a wide graph
  // scrolls sideways on a narrow screen).
  const focus = box.querySelector(".zg-node--focus");
  if (focus) {
    box.scrollLeft += focus.getBoundingClientRect().left - box.getBoundingClientRect().left - (box.clientWidth - focus.getBoundingClientRect().width) / 2;
  }
}

boot();
