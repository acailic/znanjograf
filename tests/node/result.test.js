// The result screen: a correct answer that is a formula is drawn as a formula, never as raw TeX.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
globalThis.katex = require("../../site/vendor/katex/katex.min.js");

const { resultSections } = await import("../../site/js/ui/result.js");
const { buildIndex } = await import("../../site/js/engine/graph.js");
const fixture = JSON.parse(readFileSync(new URL("../fixtures/engine-fixture.json", import.meta.url), "utf8"));

const TOPIC = "mat-sabiranje-do-20";
const index = buildIndex(fixture.topics, fixture.edges, fixture.aliases);

function gradeDataWith(question) {
  return { topics: { [TOPIC]: { summary: "Sabiranje do 20.", mastery: ["sabira dva broja"], curriculum: [] } }, questions: { [question.id]: question } };
}

const summary = {
  roots: [{ id: TOPIC, confirmed: true, missed: ["mat-sabiranje-do-20-q3"] }],
  path: [{ id: TOPIC, status: "weak" }],
  shaky: [], untested: [], outcomes: [],
  counts: { mastered: 0, shaky: 0, weak: 1, inferred: 0, untested: 0 },
};

const CHOICE = {
  id: "mat-sabiranje-do-20-q3", type: "choice", answer: "b",
  choices: [{ id: "a", text: "$6$" }, { id: "b", text: "$\\frac{18}{2}$" }], explanation: "…",
};

test("the right choice, written as a formula, is drawn as a formula", () => {
  const html = resultSections(summary, index, gradeDataWith(CHOICE));
  assert.match(html, /Tačan odgovor: <span class="katex"/);
  assert.doesNotMatch(html, /Tačan odgovor: \$/);
  // KaTeX keeps the TeX in an invisible MathML annotation for screen readers; that is intended.
});

test("a number written the way a pupil writes it stays plain text", () => {
  const html = resultSections(summary, index, gradeDataWith({ id: "mat-sabiranje-do-20-q3", type: "numeric", answer: "3/4", explanation: "…" }));
  assert.match(html, /Tačan odgovor: 3\/4/);
});

test("a missed question whose data is gone shows its id and nothing crashes", () => {
  const html = resultSections(summary, index, { topics: {}, questions: {} });
  assert.match(html, /mat-sabiranje-do-20-q3/);
});
