// site/js/pages/home.js - the promise, the three steps, the way in by grade or through
// the map, and how large the graph is. Every number comes from the data index.

import { esc, hrefTo, initCommon, t } from "../common.js";
import { currentScript, loadIndex } from "../data.js";

/** The grades the data covers, lowest first. */
function gradesOf(index) {
  const grades = Array.isArray(index?.grades) ? index.grades.filter((grade) => Number.isInteger(grade)) : [];
  return grades.length > 0 ? [...grades].sort((a, b) => a - b) : [];
}

/** The number of questions, wherever the index keeps its counts; null when it keeps none. */
function countQuestions(index) {
  const walk = (node) => {
    if (!node || typeof node !== "object") return null;
    if (typeof node.questions === "number") return node.questions;
    for (const child of Object.values(node)) {
      const found = walk(child);
      if (found !== null) return found;
    }
    return null;
  };
  return walk(index?.counts);
}

function markup() {
  // The three steps are marked up in strings.js (keys ending in Html), so they go in unescaped.
  const step = (key) => `<li><p>${t(key)}</p></li>`;
  return `<div class="zg-wrap">
  <section class="zg-hero">
    <h1 class="zg-title" data-zg-focus>${esc(t("home.title"))}</h1>
    <p class="zg-lead">${esc(t("home.lead"))}</p>
  </section>
  <section class="zg-section" aria-labelledby="zg-home-steps">
    <h2 class="zg-subtitle" id="zg-home-steps">${esc(t("home.steps.title"))}</h2>
    <ol class="zg-steps">${step("home.steps.pickHtml")}${step("home.steps.answerHtml")}${step("home.steps.seeHtml")}</ol>
  </section>
  <section class="zg-section" aria-labelledby="zg-home-grades">
    <h2 class="zg-subtitle" id="zg-home-grades">${esc(t("home.grades.title"))}</h2>
    <p>${esc(t("home.grades.text"))}</p>
    <ul class="zg-grades" data-zg-grades></ul>
  </section>
  <section class="zg-section" aria-labelledby="zg-home-map">
    <h2 class="zg-subtitle" id="zg-home-map">${esc(t("home.map.title"))}</h2>
    <p>${esc(t("home.map.text"))}</p>
    <p><a class="zg-btn zg-btn-secondary" href="${esc(hrefTo("mapa/"))}">${esc(t("home.map.link"))}</a></p>
  </section>
  <section class="zg-section" aria-labelledby="zg-home-stats">
    <h2 class="zg-subtitle" id="zg-home-stats">${esc(t("home.stats.title"))}</h2>
    <dl class="zg-stats" data-zg-stats></dl>
  </section>
</div>`;
}

function fill(root, index) {
  root.querySelector("[data-zg-grades]").innerHTML = gradesOf(index).map((grade) => {
    const label = t("home.grades.link", { n: grade });
    return `<li><a class="zg-grade" href="${esc(hrefTo("dijagnostika/", { grade }))}" aria-label="${esc(label)}">${esc(t("common.grade.n", { n: grade }))}</a></li>`;
  }).join("");

  const questions = countQuestions(index);
  const stat = (key, value) => `<div><dt>${esc(t(key))}</dt><dd>${esc(value)}</dd></div>`;
  root.querySelector("[data-zg-stats]").innerHTML = [
    stat("home.stats.topics", Array.isArray(index?.topics) ? index.topics.length : 0),
    stat("home.stats.edges", Array.isArray(index?.edges) ? index.edges.length : 0),
    questions === null ? "" : stat("home.stats.questions", questions),
    stat("home.stats.grades", gradesOf(index).length),
  ].join("");
}

/** What the two data-driven sections say when the index could not be read. */
function failed(root) {
  root.querySelector("[data-zg-stats]").innerHTML = "";
  root.querySelector("[data-zg-grades]").innerHTML = `<li class="zg-note zg-note-bad" role="alert">${esc(t("common.error.data"))}</li>`;
}

async function main() {
  const context = initCommon();
  if (!context) return;
  const root = document.getElementById("zg-main") || document.body;
  root.innerHTML = markup();
  try {
    fill(root, await loadIndex(context.script || currentScript()));
  } catch (error) {
    console.error(error);
    failed(root);
  }
}

main();
