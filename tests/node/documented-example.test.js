// The worked example at the end of docs/dijagnostika.md, held by the engine.
//
// When a test here fails, the text and the engine have drifted apart: either the engine
// changed (then rewrite the example) or the example was written without running it.

import test from "node:test";
import assert from "node:assert/strict";

import { buildIndex } from "../../site/js/engine/graph.js";
import { apply, createSession, extend, next } from "../../site/js/engine/session.js";
import { summarise } from "../../site/js/engine/result.js";
import { loadEngineFixture } from "./helpers.js";

const fixture = loadEngineFixture();
const A = "mat-brojevi-do-10", B = "mat-sabiranje-do-10", C = "mat-sabiranje-do-20";
const D = "mat-sabiranje-do-100", E = "mat-zadaci-sa-sabiranjem", P = "mat-poredjenje-do-100";
const NAME = { [A]: "A", [B]: "B", [C]: "C", [D]: "D", [E]: "E", [P]: "P" };

// The curriculum of the fixture (tests/fixtures/raw.py), as the page hands it to the session.
const curriculum = {
  [A]: [{ edition: "g1-2026", outcome: "g1-2026-001", match: "exact" }, { edition: "g1-2026", outcome: "g1-2026-005", match: "exact" }],
  [B]: [{ edition: "g1-2026", outcome: "g1-2026-002", match: "exact" }],
  [C]: [{ edition: "g1-2026", outcome: "g1-2026-003", match: "exact" }],
  [D]: [{ edition: "g2-2026", outcome: "g2-2026-001", match: "exact" }],
  [P]: [{ edition: "g2-2026", outcome: "g2-2026-002", match: "exact" }, { edition: "g2-2026", outcome: "g2-2026-005", match: "partial" }],
  [E]: [{ edition: "g2-2026", outcome: "g2-2026-004", match: "exact" }],
};

/** „E-q3“, the label the example gives a question. */
const label = (id) => {
  const [slug, number] = id.replace(/^mat-/, "").split("-q");
  return `${NAME[`mat-${slug}`]}-q${number}`;
};

/** Plays the example from E, answering correctly only what is in `right`. */
function play(right = []) {
  const context = {
    scope: { kind: "topic", id: E },
    index: buildIndex(fixture.topics, fixture.edges, fixture.aliases),
    bank: fixture.questions,
    budget: 25,
    history: {},
    curriculum,
  };
  const good = new Set(right);
  let state = createSession(context);
  const asked = [];
  for (;;) {
    const step = next(state);
    if (step.kind !== "question") return { asked, end: step, summary: summarise(state) };
    asked.push(`${label(step.question.id)}:${step.role}`);
    state = apply(state, { questionId: step.question.id, correct: good.has(step.question.id) });
  }
}

test("the example: „Ne znam“ to everything walks the whole line in ten questions", () => {
  const { asked, end, summary } = play();
  assert.equal(end.kind, "done");
  assert.deepEqual(asked, [
    "E-q3:scope", "E-q1:scope", "D-q3:prerequisite", "D-q1:prerequisite", "C-q3:prerequisite", "C-q1:prerequisite",
    "B-q3:prerequisite", "B-q1:prerequisite", "A-q3:prerequisite", "A-q1:prerequisite",
  ]);
  assert.deepEqual(summary, {
    roots: [{ id: A, confirmed: true, missed: [`${A}-q3`, `${A}-q1`] }],
    path: [[A, "weak"], [B, "weak"], [C, "weak"], [D, "weak"], [E, "weak"]].map(([id, status]) => ({ id, status })),
    shaky: [],
    counts: { mastered: 0, shaky: 0, weak: 5, inferred: 0, untested: 0 },
    untested: [],
    outcomes: [
      { edition: "g1-2026", id: "g1-2026-001" }, { edition: "g1-2026", id: "g1-2026-005" },
      { edition: "g1-2026", id: "g1-2026-002" }, { edition: "g1-2026", id: "g1-2026-003" },
      { edition: "g2-2026", id: "g2-2026-001" }, { edition: "g2-2026", id: "g2-2026-004" },
    ],
  });
});

test("the example: a strong first answer masters the topic and infers the line", () => {
  const { asked, summary } = play([`${E}-q3`]);
  assert.deepEqual(asked, ["E-q3:scope"]);
  assert.deepEqual(summary.counts, { mastered: 1, shaky: 0, weak: 0, inferred: 4, untested: 0 });
  assert.deepEqual([summary.roots, summary.path, summary.shaky], [[], [], []]);
});

test("the example: a mastered hard prerequisite sends the walk to the soft one", () => {
  const { asked, summary } = play([`${D}-q3`]);
  assert.deepEqual(asked, ["E-q3:scope", "E-q1:scope", "D-q3:prerequisite", "P-q3:prerequisite", "P-q1:prerequisite"]);
  assert.deepEqual(summary.roots, [
    { id: P, confirmed: true, missed: [`${P}-q3`, `${P}-q1`] },
    { id: E, confirmed: true, missed: [`${E}-q3`, `${E}-q1`] },
  ]);
  assert.deepEqual(summary.path.map(({ id, status }) => [NAME[id], status]), [["P", "weak"], ["E", "weak"]]);
  assert.deepEqual(summary.counts, { mastered: 1, shaky: 0, weak: 2, inferred: 3, untested: 0 });
});

test("the example: a right basic answer leaves the topic shaky and ends the diagnosis", () => {
  const { asked, end, summary } = play([`${E}-q1`]);
  assert.deepEqual(asked, ["E-q3:scope", "E-q1:scope"]);
  assert.equal(end.kind, "done");
  assert.deepEqual([summary.roots, summary.path, summary.shaky], [[], [], [E]]);
  assert.deepEqual(summary.counts, { mastered: 0, shaky: 1, weak: 0, inferred: 0, untested: 0 });
});

test("the example: a line of thirteen topics needs two blocks of twenty-five questions", () => {
  const topics = [], edges = [], bank = {};
  for (let i = 1; i <= 13; i += 1) {
    const id = `t${i}`;
    topics.push({ id, grade: 1 + Math.floor((i - 1) / 2), area: "numbers", unit: "Brojevi", kind: "procedure", name: `Tema ${i}` });
    if (i > 1) edges.push([id, `t${i - 1}`, "hard"]);
    // The bank is grouped by topic: two standard and two basic questions each.
    bank[id] = ["standard", "basic"].flatMap((level) => [1, 2].map((n) => (
      { id: `${id}-${level[0]}${n}`, topic: id, level, type: "numeric", answer: "100" }
    )));
  }
  const context = { scope: { kind: "topic", id: "t13" }, index: buildIndex(topics, edges, {}), bank, budget: 25, history: {}, curriculum: {} };
  let state = createSession(context);
  const answerWrong = () => {
    const step = next(state);
    if (step.kind === "question") state = apply(state, { questionId: step.question.id, correct: false });
    return step;
  };
  for (let i = 0; i < 25; i += 1) assert.equal(answerWrong().kind, "question");
  assert.deepEqual(next(state), { kind: "paused", asked: 25 });
  const [root] = summarise(state).roots;
  assert.equal(root.id, "t2");  // t1 is the topic whose first question was the twenty-fifth
  assert.equal(root.confirmed, false);
  state = extend(state);
  assert.equal(answerWrong().kind, "question");
  assert.equal(state.log.length, 26);
  assert.deepEqual(next(state), { kind: "done" });
  assert.deepEqual(summarise(state).roots, [{ id: "t1", confirmed: true, missed: ["t1-s1", "t1-b1"] }]);
});
