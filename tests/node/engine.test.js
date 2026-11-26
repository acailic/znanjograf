// Behaviour of the diagnostic engine (site/js/engine) on the shared fixture corpus.
//
// The fixture (tests/fixtures/engine-fixture.json) is built by Python; the
// answer vectors (tests/fixtures/answer-vectors.json) are shared with the Python
// parser, so both implementations are held to the same cases.

import test from "node:test";
import assert from "node:assert/strict";
import { Buffer } from "node:buffer";

import { isCorrect, isStrongAnswer } from "../../site/js/engine/answer.js";
import { decodeSession, encodeSession } from "../../site/js/engine/encode.js";
import { buildIndex } from "../../site/js/engine/graph.js";
import { parseRat, rat } from "../../site/js/engine/rational.js";
import { statusesOf, summarise } from "../../site/js/engine/result.js";
import { apply, createSession, extend, next, reduce } from "../../site/js/engine/session.js";
import { STATUS, verdictOf } from "../../site/js/engine/verdict.js";

import {
  askedPerTopic,
  fixtureContext,
  guessingPupil,
  loadAnswerVectors,
  loadEngineFixture,
  mulberry32,
  pupilKnowing,
  pupilKnowingAll,
  pupilKnowingAllBut,
  pupilKnowingNothing,
  questionById,
  randomPupil,
  runSession,
  syntheticCorpus,
} from "./helpers.js";

const fixture = loadEngineFixture();
const expected = fixture.expected;
const index = buildIndex(fixture.topics, fixture.edges, fixture.aliases);

const GOAL = "mat-zadaci-sa-sabiranjem";
const SHAPES = "mat-geometrijski-oblici";
const COMPARISON = "mat-poredjenje-do-100";
const topicScope = (id = GOAL) => ({ kind: "topic", id });

const SCOPES = {
  topic: { kind: "topic", id: GOAL },
  unit: { kind: "unit", grade: 2, unit: "Brojevi" },
  grade: { kind: "grade", grade: 2 },
  "grade-full": { kind: "grade-full", grade: 2 },
  "grade 1": { kind: "grade", grade: 1 },
  "unit of grade 1": { kind: "unit", grade: 1, unit: "Brojevi" },
};

/** The topics a scope covers, read straight from the fixture (not from the engine). */
function topicsOf(scope) {
  if (scope.kind === "topic") return [scope.id];
  const ofGrade = fixture.topics.filter((topic) => topic.grade === scope.grade).map((topic) => topic.id);
  if (scope.kind === "grade-full") return ofGrade;
  if (scope.kind === "unit") return ofGrade.filter((id) => fixture.topics.find((topic) => topic.id === id).unit === scope.unit);
  return expected.gradeExits[String(scope.grade)];
}

/** What a user sees of a state: the log, what comes next and what has been found. */
function view(state) {
  return { log: state.log, next: next(state), summary: summarise(state), statuses: [...statusesOf(state)] };
}

const question = (id) => questionById(fixture.questions, id);

test("buildIndex reproduces what Python expects of the fixture", async (t) => {
  await t.test("learning order", () => {
    assert.deepEqual(index.learningOrder(), expected.learningOrder);
    assert.deepEqual(index.topicIds, expected.learningOrder);
  });

  await t.test("grade exits", () => {
    assert.deepEqual(index.gradeExits(1), expected.gradeExits["1"]);
    assert.deepEqual(index.gradeExits(2), expected.gradeExits["2"]);
  });

  await t.test("hard ancestors", () => {
    assert.deepEqual([...index.topicIds].sort(), Object.keys(expected.hardAncestors).sort());
    for (const [id, ancestors] of Object.entries(expected.hardAncestors)) {
      assert.deepEqual([...index.hardAncestorsOf(id)].sort(), ancestors, id);
    }
  });

  await t.test("ancestors of any strength include the soft ones", () => {
    assert.deepEqual([...index.hardAncestorsOf(COMPARISON)], ["mat-brojevi-do-10"]);
    assert.deepEqual([...index.ancestorsOf(COMPARISON)].sort(), ["mat-brojevi-do-10", "mat-sabiranje-do-10"]);
  });

  await t.test("prerequisites keep the file order and the strength", () => {
    assert.deepEqual(index.prereqsOf(COMPARISON), [
      { id: "mat-brojevi-do-10", strength: "hard" },
      { id: "mat-sabiranje-do-10", strength: "soft" },
    ]);
    assert.deepEqual(index.gradeOf.get("mat-oduzimanje-do-100"), 2);
  });

  await t.test("a subset keeps the learning order", () => {
    assert.deepEqual(index.learningOrder([GOAL, "mat-sabiranje-do-20", "mat-brojevi-do-10", "mat-sabiranje-do-20"]), [
      "mat-brojevi-do-10",
      "mat-sabiranje-do-20",
      GOAL,
    ]);
  });

  await t.test("aliases resolve to the current ids", () => {
    assert.deepEqual(index.resolveAlias("mat-brojevi"), ["mat-brojevi-do-10"]);
    assert.deepEqual(index.resolveAlias("mat-brojevi-do-10"), ["mat-brojevi-do-10"]);
    assert.deepEqual(index.resolveAlias("mat-nepostoji"), []);
  });

  await t.test("a cycle or an unknown edge endpoint is refused", () => {
    const cycle = [...fixture.edges, ["mat-brojevi-do-10", "mat-sabiranje-do-10", "hard"]];
    const dangling = [...fixture.edges, ["mat-sabiranje-do-10", "mat-nepostoji", "hard"]];
    assert.throws(() => buildIndex(fixture.topics, cycle, fixture.aliases), /ZG_BAD_GRAPH/);
    assert.throws(() => buildIndex(fixture.topics, dangling, fixture.aliases), /ZG_BAD_GRAPH/);
  });
});

test("parseRat mirrors the Python answer parser", async (t) => {
  const vectors = loadAnswerVectors();

  await t.test("every valid vector parses to the expected rational", () => {
    assert.ok(vectors.valid.length >= 24);
    for (const { text, num, den } of vectors.valid) {
      assert.deepEqual(parseRat(text), { n: BigInt(num), d: BigInt(den) }, JSON.stringify(text));
    }
  });

  await t.test("every invalid vector gives null", () => {
    assert.ok(vectors.invalid.length >= 24);
    for (const text of vectors.invalid) {
      assert.equal(parseRat(text), null, JSON.stringify(text));
    }
  });

  await t.test("only strings can be an answer", () => {
    for (const value of [undefined, null, 7, 3.5, {}, ["3"]]) {
      assert.equal(parseRat(value), null, String(value));
    }
  });

  await t.test("rat normalises and keeps the denominator positive", () => {
    assert.deepEqual(rat(6n, -4n), { n: -3n, d: 2n });
    assert.deepEqual(rat(0n, -7n), { n: 0n, d: 1n });
    assert.deepEqual(rat(-12n, 18n), { n: -2n, d: 3n });
    assert.throws(() => rat(1n, 0n), RangeError);
  });
});

test("answers and verdicts follow the rules for one topic", async (t) => {
  await t.test("a strong answer is a correct number that cannot be guessed", () => {
    assert.equal(isStrongAnswer(question("mat-sabiranje-do-20-q3"), true), true); // 15
    assert.equal(isStrongAnswer(question("mat-brojevi-do-10-q4"), true), false); // 6
    assert.equal(isStrongAnswer(question("mat-brojevi-do-10-q3"), true), false); // a choice
    assert.equal(isStrongAnswer(question("mat-sabiranje-do-20-q3"), false), false);
  });

  await t.test("isCorrect compares exact values in every accepted spelling", () => {
    const half = { type: "numeric", answer: "0.5", answerRational: ["1", "2"] };
    for (const value of ["0,5", "0.5", "1/2", "2/4", " 1/2 "]) {
      assert.equal(isCorrect(half, { type: "numeric", value }), true, value);
    }
    for (const value of ["", "0,6", "1/3", "abc", "1 000"]) {
      assert.equal(isCorrect(half, { type: "numeric", value }), false, JSON.stringify(value));
    }
    assert.equal(isCorrect(half, { type: "choice", choiceId: "a" }), false);
  });

  await t.test("a choice is correct only by the id of the right option", () => {
    const shapes = question(`${SHAPES}-q1`); // the answer is "b"
    assert.equal(isCorrect(shapes, { type: "choice", choiceId: "b" }), true);
    assert.equal(isCorrect(shapes, { type: "choice", choiceId: "a" }), false);
    assert.equal(isCorrect(shapes, { type: "choice", choiceId: null }), false); // "I don't know"
    assert.equal(isCorrect(shapes, { type: "numeric", value: "b" }), false);
    assert.equal(isCorrect(shapes, undefined), false);
  });

  await t.test("verdictOf decides from the evidence in asked order", () => {
    const guessable = question("mat-brojevi-do-10-q3"); // a choice, never strong
    const strong = question("mat-sabiranje-do-20-q3"); // 15
    const basic = question("mat-brojevi-do-10-q1");
    const right = (asked) => ({ question: asked, correct: true });
    const wrong = (asked) => ({ question: asked, correct: false });

    assert.deepEqual(verdictOf([]), { status: STATUS.UNTESTED, done: false });
    assert.deepEqual(verdictOf([wrong(guessable)]), { status: STATUS.UNTESTED, done: false });
    assert.deepEqual(verdictOf([wrong(guessable), right(basic)]), { status: STATUS.SHAKY, done: true });
    assert.deepEqual(verdictOf([wrong(guessable), wrong(basic)]), { status: STATUS.WEAK, done: true });
    assert.deepEqual(verdictOf([right(strong)]), { status: STATUS.MASTERED, done: true });
    assert.deepEqual(verdictOf([right(guessable)]), { status: STATUS.UNTESTED, done: false });
    assert.deepEqual(verdictOf([right(guessable), right(question("mat-brojevi-do-10-q4"))]), { status: STATUS.MASTERED, done: true });
    assert.deepEqual(verdictOf([right(guessable), wrong(question("mat-brojevi-do-10-q4"))]), { status: STATUS.SHAKY, done: true });
  });

  await t.test("STATUS carries the five exact strings", () => {
    assert.deepEqual({ ...STATUS }, { UNTESTED: "untested", MASTERED: "mastered", SHAKY: "shaky", WEAK: "weak", INFERRED: "inferred" });
    assert.ok(Object.isFrozen(STATUS));
  });
});

test("a single missing topic is reported as the confirmed root", async (t) => {
  // The fixture's hard chain into the goal, in learning order.
  const CHAIN = ["mat-brojevi-do-10", "mat-sabiranje-do-10", "mat-sabiranje-do-20", "mat-sabiranje-do-100", GOAL];
  const reachable = new Set(CHAIN);

  for (const missing of index.topicIds) {
    await t.test(missing, () => {
      const run = runSession(fixtureContext(fixture, topicScope()), pupilKnowingAllBut(index, [missing]));
      if (!reachable.has(missing)) {
        assert.deepEqual(run.summary.roots, []);
        assert.deepEqual(run.summary.path, []);
        return;
      }
      assert.deepEqual(run.summary.roots, [{ id: missing, confirmed: true, missed: [`${missing}-q3`, `${missing}-q1`] }]);
      assert.deepEqual(
        run.summary.path,
        CHAIN.slice(CHAIN.indexOf(missing)).map((id) => ({ id, status: STATUS.WEAK })),
      );
      // Every topic on the path was asked two questions, and nothing else was asked.
      assert.equal(run.log.length, 2 * run.summary.path.length);
      assert.deepEqual(run.pauses, []);
    });
  }

  await t.test("a topic off the chain is weak but stays out of the path", () => {
    const run = runSession(fixtureContext(fixture, topicScope()), pupilKnowingAllBut(index, ["mat-brojevi-do-10"]));
    assert.equal(run.statuses.get("mat-oduzimanje-do-100"), STATUS.WEAK);
    assert.equal(run.summary.path.some((entry) => entry.id === "mat-oduzimanje-do-100"), false);
    assert.deepEqual(run.summary.shaky, []);
  });

  await t.test("a shaky topic on the path is listed as a step to consolidate", () => {
    const pupil = pupilKnowingAllBut(index, ["mat-sabiranje-do-20"]);
    pupil.shaky = new Set(["mat-sabiranje-do-20"]); // it passes the basic question after all
    const run = runSession(fixtureContext(fixture, topicScope()), pupil);
    assert.deepEqual(run.summary.roots, [{ id: "mat-sabiranje-do-100", confirmed: true, missed: ["mat-sabiranje-do-100-q3", "mat-sabiranje-do-100-q1"] }]);
    assert.deepEqual(run.summary.path, [
      { id: "mat-sabiranje-do-20", status: STATUS.SHAKY },
      { id: "mat-sabiranje-do-100", status: STATUS.WEAK },
      { id: GOAL, status: STATUS.WEAK },
    ]);
    assert.deepEqual(run.summary.shaky, ["mat-sabiranje-do-20"]);
    assert.deepEqual(run.summary.counts, { mastered: 1, shaky: 1, weak: 2, inferred: 1, untested: 0 });
  });

  await t.test("a weak soft prerequisite is a root when the hard ones are fine", () => {
    const pupil = pupilKnowing(index, index.topicIds.filter((id) => ![GOAL, COMPARISON].includes(id)));
    const run = runSession(fixtureContext(fixture, topicScope()), pupil);

    // The goal is weak too and has no weak hard ancestor, so it is a root of its own.
    assert.deepEqual(run.summary.roots, [
      { id: COMPARISON, confirmed: true, missed: [`${COMPARISON}-q3`, `${COMPARISON}-q1`] },
      { id: GOAL, confirmed: true, missed: [`${GOAL}-q3`, `${GOAL}-q1`] },
    ]);
    assert.deepEqual(run.summary.path, [
      { id: COMPARISON, status: STATUS.WEAK },
      { id: GOAL, status: STATUS.WEAK },
    ]);
  });
});

test("a pupil who knows everything finishes every scope topic in at most two questions", async (t) => {
  const pupil = pupilKnowingAll(index);

  for (const [name, scope] of Object.entries(SCOPES)) {
    await t.test(name, () => {
      const run = runSession(fixtureContext(fixture, scope), pupil);
      const topics = index.learningOrder(topicsOf(scope));

      // A scope topic that another scope topic builds on is implied by that
      // topic: it becomes `inferred` and is never asked (spec 10.3, step 2).
      const implied = new Set(topics.flatMap((id) => [...index.hardAncestorsOf(id)]).filter((id) => topics.includes(id)));

      for (const id of topics) {
        assert.equal(run.statuses.get(id), implied.has(id) ? STATUS.INFERRED : STATUS.MASTERED, `${id}`);
      }
      for (const [id, count] of askedPerTopic(fixture.questions, run.log)) {
        assert.ok(count <= 2, `${id} was asked ${count} questions`);
      }
      assert.deepEqual(
        [...new Set(run.questions.map((step) => step.topicId))].sort(),
        topics.filter((id) => !implied.has(id)).sort(),
      );
      assert.deepEqual(run.summary.roots, []);
      assert.deepEqual(run.summary.untested, []);
      assert.deepEqual(run.pauses, []);
      assert.equal(run.summary.counts.mastered, topics.length - implied.size);
      assert.equal(run.summary.counts.weak + run.summary.counts.shaky, 0);
    });
  }

  await t.test("a single topic is mastered outright, in at most two questions", () => {
    for (const id of index.topicIds) {
      const run = runSession(fixtureContext(fixture, topicScope(id)), pupil);

      assert.equal(run.statuses.get(id), STATUS.MASTERED, id);
      assert.ok(run.log.length >= 1 && run.log.length <= 2, `${id} took ${run.log.length} questions`);
      assert.ok(run.log.every((event) => question(event.questionId).topic === id), id);
    }
  });

  await t.test("a grade scope asks only the exit topics when nothing leads back", () => {
    const run = runSession(fixtureContext(fixture, SCOPES.grade), pupil);
    const asked = [...new Set(run.questions.map((step) => step.topicId))].sort();

    assert.deepEqual(asked, [...expected.gradeExits["2"]].sort());
    assert.equal(run.log.length, 2); // both exit topics have a strong standard question
    assert.ok(run.questions.every((step) => step.role === "scope"));
    assert.equal(run.statuses.get("mat-sabiranje-do-100"), STATUS.INFERRED);
    assert.equal(run.statuses.has(COMPARISON), false); // a soft prerequisite is not inferred
  });
});

test("a pupil who knows nothing masters nothing and bottoms out at the graph roots", async (t) => {
  const pupil = pupilKnowingNothing();
  const graphRoots = index.topicIds.filter((id) => index.prereqsOf(id).length === 0);

  for (const [name, scope] of Object.entries(SCOPES)) {
    await t.test(name, () => {
      const run = runSession(fixtureContext(fixture, scope), pupil);
      const topics = topicsOf(scope);
      const diagnosed = new Set([...topics, ...topics.flatMap((id) => [...index.hardAncestorsOf(id)])]);

      for (const id of index.topicIds) {
        assert.notEqual(run.statuses.get(id), STATUS.MASTERED, `${id} must not be mastered`);
      }
      assert.equal(run.summary.counts.mastered, 0);
      assert.deepEqual(run.summary.untested, []);
      assert.deepEqual(
        run.summary.roots,
        graphRoots.filter((id) => diagnosed.has(id)).map((id) => ({ id, confirmed: true, missed: [`${id}-q3`, `${id}-q1`] })),
      );
      // Everything on the diagnosed paths is weak, in learning order.
      assert.deepEqual(run.summary.path, index.learningOrder([...diagnosed]).map((id) => ({ id, status: STATUS.WEAK })));
    });
  }

  await t.test("a grade scope goes back behind the exit topics when it must", () => {
    const run = runSession(fixtureContext(fixture, SCOPES.grade), pupil);
    const asked = new Set(run.questions.map((step) => step.topicId));

    assert.ok(asked.has("mat-sabiranje-do-100"));
    assert.ok(asked.has("mat-brojevi-do-10"));
    assert.ok(run.questions.some((step) => step.role === "prerequisite"));
  });
});

test("guessing rarely passes the choice-only topic", async (t) => {
  const SESSIONS = 2000;
  let mastered = 0;
  let answers = 0;
  let right = 0;

  for (let seed = 1; seed <= SESSIONS; seed += 1) {
    const run = runSession(fixtureContext(fixture, topicScope(SHAPES)), guessingPupil(mulberry32(seed)));
    if (run.statuses.get(SHAPES) === STATUS.MASTERED) mastered += 1;
    answers += run.log.length;
    right += run.log.filter((event) => event.correct).length;
  }

  await t.test("the pupil really guesses among four options", () => {
    assert.ok(right / answers > 0.22 && right / answers < 0.28, `${right} of ${answers} answers were right`);
  });

  await t.test(`the mastered rate ${(mastered / SESSIONS).toFixed(3)} is below 10 %`, () => {
    assert.ok(mastered / SESSIONS < 0.1, `${mastered} of ${SESSIONS} sessions mastered the topic`);
  });
});

test("the budget pauses a session and a topic without questions ends weak", async (t) => {
  await t.test("paused after exactly budget questions; extend continues", () => {
    const run = runSession(fixtureContext(fixture, topicScope(), { budget: 5 }), pupilKnowingNothing());

    assert.equal(run.log.length, 10);
    assert.deepEqual(run.pauses, [5]);
    assert.equal(next(run.states[4]).kind, "question");
    assert.deepEqual(next(run.states[5]), { kind: "paused", asked: 5 });
    assert.deepEqual(next(extend(run.states[5])), run.questions[5]);
    // The second block ends exactly where the questions run out: done, not paused.
    assert.deepEqual(next(run.states[10]), { kind: "done" });
  });

  await t.test("the default budget is 25 questions per block", () => {
    const run = runSession(fixtureContext(fixture, SCOPES["grade-full"]), pupilKnowingNothing());
    assert.equal(createSession(fixtureContext(fixture, topicScope())).budget, 25);
    assert.ok(run.log.length < 25);
    assert.deepEqual(run.pauses, []);
  });

  await t.test("an interrupted session reports unconfirmed roots and untested topics", () => {
    const run = runSession(fixtureContext(fixture, SCOPES.grade, { budget: 3 }), pupilKnowingNothing(), { maxAnswers: 3 });
    const summary = summarise(run.state);

    assert.deepEqual(next(run.state), { kind: "paused", asked: 3 });
    assert.deepEqual(summary.roots, [{ id: GOAL, confirmed: false, missed: [`${GOAL}-q3`, `${GOAL}-q1`] }]);
    assert.deepEqual(summary.untested, ["mat-oduzimanje-do-100"]);
    assert.deepEqual(summary.counts, { mastered: 0, shaky: 0, weak: 1, inferred: 0, untested: 1 });
  });

  const withBank = (id, keep) => {
    const bank = structuredClone(fixture.questions);
    bank[id] = keep.map((suffix) => bank[id].find((entry) => entry.id.endsWith(`-${suffix}`)));
    return fixtureContext({ ...fixture, questions: bank }, topicScope(id));
  };

  await t.test("one non-strong standard question and nothing left: weak", () => {
    const run = runSession(withBank("mat-brojevi-do-10", ["q3"]), pupilKnowingAll(index));
    assert.equal(run.log.length, 1);
    assert.equal(run.statuses.get("mat-brojevi-do-10"), STATUS.WEAK);
    assert.deepEqual(run.summary.roots, [{ id: "mat-brojevi-do-10", confirmed: true, missed: [] }]);
  });

  await t.test("no standard question at all: weak without asking", () => {
    const ctx = withBank("mat-brojevi-do-10", ["q1", "q2"]);
    assert.deepEqual(next(createSession(ctx)), { kind: "done" });
    const run = runSession(ctx, pupilKnowingAll(index));
    assert.equal(run.log.length, 0);
    assert.deepEqual(run.summary.roots, [{ id: "mat-brojevi-do-10", confirmed: true, missed: [] }]);
  });

  await t.test("the standard question is wrong and no basic one is left: weak", () => {
    const run = runSession(withBank("mat-brojevi-do-10", ["q3", "q4"]), pupilKnowingNothing());
    assert.equal(run.log.length, 1);
    assert.deepEqual(run.summary.roots, [{ id: "mat-brojevi-do-10", confirmed: true, missed: ["mat-brojevi-do-10-q3"] }]);
  });

  await t.test("history rotates to the least used question of the level", () => {
    const ctx = fixtureContext(fixture, topicScope(), { history: { [`${GOAL}-q3`]: 2, [`${GOAL}-q1`]: 1 } });
    const state = createSession(ctx);

    assert.equal(next(state).question.id, `${GOAL}-q4`); // q3 was used more often
    assert.equal(next(apply(state, { questionId: `${GOAL}-q4`, correct: false })).question.id, `${GOAL}-q2`);
    assert.equal(next(apply(state, { questionId: `${GOAL}-q4`, correct: true })).kind, "done"); // 70 is strong
  });
});

test("replaying the log rebuilds the live state", async (t) => {
  const corpus = syntheticCorpus(7);
  const ctx = { scope: { kind: "grade-full", grade: 4 }, index: corpus.index, bank: corpus.bank, history: {} };
  const run = runSession(ctx, randomPupil(mulberry32(11), 0.3), { maxAnswers: 60 });

  await t.test("the sample session is long and varied enough", () => {
    assert.equal(run.log.length, 60);
    assert.deepEqual(run.pauses, [25, 50]);
    assert.ok(run.summary.roots.length >= 1);
    assert.ok(run.summary.counts.mastered >= 1);
    assert.ok(run.summary.counts.shaky >= 1);
    assert.ok(run.summary.counts.weak >= 1);
    assert.ok(run.summary.counts.inferred >= 1);
    assert.ok(run.summary.untested.length >= 1);
  });

  await t.test("reduce of every prefix equals the live state after that prefix", () => {
    for (let length = 0; length <= 60; length += 1) {
      assert.deepEqual(view(reduce(run.log.slice(0, length), ctx)), view(run.states[length]), `after ${length} answers`);
    }
  });

  await t.test("the pauses sit exactly on the block boundaries", () => {
    assert.deepEqual(next(reduce(run.log.slice(0, 25), ctx)), { kind: "paused", asked: 25 });
    assert.deepEqual(next(reduce(run.log.slice(0, 50), ctx)), { kind: "paused", asked: 50 });
    assert.equal(next(reduce(run.log.slice(0, 26), ctx)).kind, "question");
  });

  await t.test("an event that does not fit is dropped together with everything after it", () => {
    const corrupted = [...run.log];
    corrupted[30] = { questionId: "syn-topic-00-q9", correct: true };
    corrupted[31] = { questionId: "not-even-a-question", correct: true };

    assert.deepEqual(view(reduce(corrupted, ctx)), view(reduce(run.log.slice(0, 30), ctx)));
    assert.equal(reduce(corrupted, ctx).log.length, 30);
  });

  await t.test("a log that is not a list gives a fresh session", () => {
    for (const log of [undefined, null, "abc", 5, { length: 3 }]) {
      assert.deepEqual(view(reduce(log, ctx)), view(createSession(ctx)));
    }
  });
});

test("apply refuses an answer to a question that was not asked", async (t) => {
  const ctx = fixtureContext(fixture, topicScope());
  const fresh = createSession(ctx);
  const asked = next(fresh).question.id;
  const outOfSync = { name: "Error", message: "ZG_OUT_OF_SYNC" };

  await t.test("a wrong question id throws ZG_OUT_OF_SYNC", () => {
    for (const event of [
      { questionId: `${asked}-x`, correct: true },
      { questionId: asked.toUpperCase(), correct: false },
      { questionId: "mat-brojevi-do-10-q1", correct: true },
      undefined,
    ]) {
      assert.throws(() => apply(fresh, event), outOfSync, JSON.stringify(event));
    }
  });

  await t.test("a refused answer leaves the state untouched", () => {
    assert.deepEqual(fresh, createSession(ctx));
  });

  await t.test("apply returns a new state that remembers only the answer", () => {
    const after = apply(fresh, { questionId: asked, correct: true, extra: "ignored" });

    assert.notEqual(after, fresh);
    assert.deepEqual(fresh.log, []);
    assert.deepEqual(after.log, [{ questionId: asked, correct: true }]);
  });

  await t.test("nothing can be answered while paused or done", () => {
    const paused = runSession(fixtureContext(fixture, SCOPES.grade, { budget: 3 }), pupilKnowingNothing(), { maxAnswers: 3 }).state;
    const done = runSession(ctx, pupilKnowingAll(index)).state;

    for (const state of [paused, done]) {
      assert.throws(() => apply(state, { questionId: asked, correct: true }), outOfSync);
    }
  });
});

test("a session survives the share link", async (t) => {
  const log = [
    { questionId: `${GOAL}-q3`, correct: false },
    { questionId: `${GOAL}-q1`, correct: false },
  ];
  const scopes = [
    ...Object.values(SCOPES),
    { kind: "topic", id: "mat-brojevi" },
    { kind: "unit", grade: 3, unit: "Geometrija i merenje – č, ć, š, ž, đ" },
  ];

  await t.test("round trip for every scope kind", () => {
    for (const scope of scopes) {
      const text = encodeSession({ scope, log });

      assert.match(text, /^v1\.[A-Za-z0-9_-]+$/, "must be safe inside a URL fragment");
      assert.deepEqual(decodeSession(text), { scope, log });
    }
    assert.deepEqual(decodeSession(encodeSession({ scope: SCOPES.topic, log: [] })), { scope: SCOPES.topic, log: [] });
  });

  await t.test("the payload is base64url of UTF-8 JSON", () => {
    for (const scope of scopes) {
      const payload = Buffer.from(encodeSession({ scope, log }).slice(3), "base64url");

      assert.deepEqual(JSON.parse(payload.toString("utf8")), { scope, log });
    }
  });

  await t.test("the same session always gives the same link", () => {
    assert.equal(encodeSession({ scope: SCOPES.unit, log }), encodeSession({ scope: SCOPES.unit, log }));
  });

  await t.test("garbage gives null", () => {
    const garbage = [undefined, null, 42, {}, "", "v1", "v1.", "v2.e30", "e30", "v1.e30=", "v1.e3/e", "v1.e3+e", "v1.a", "v1.YQ", "v1.eyJzY29wZSI6", "v1.Wy0xLDJd"];
    for (const text of garbage) {
      assert.equal(decodeSession(text), null, String(text));
    }
  });

  await t.test("well-formed base64 that is not a session gives null", () => {
    const pack = (value) => `v1.${Buffer.from(JSON.stringify(value), "utf8").toString("base64url")}`;
    const notSessions = [
      null,
      5,
      "x",
      [],
      {},
      { scope: SCOPES.topic },
      { log },
      { scope: { kind: "nope", id: "x" }, log },
      { scope: { kind: "topic" }, log },
      { scope: { kind: "unit", grade: "2", unit: "Brojevi" }, log },
      { scope: SCOPES.topic, log: "x" },
      { scope: SCOPES.topic, log: [{ questionId: 5, correct: true }] },
      { scope: SCOPES.topic, log: [{ questionId: "a", correct: "yes" }] },
    ];
    for (const value of notSessions) {
      assert.equal(decodeSession(pack(value)), null, JSON.stringify(value));
    }
  });

  await t.test("a decoded link rebuilds the session it was made from", () => {
    const run = runSession(fixtureContext(fixture, SCOPES["grade-full"]), pupilKnowingNothing());
    const restored = reduce(decodeSession(encodeSession({ scope: SCOPES["grade-full"], log: run.log })).log, fixtureContext(fixture, SCOPES["grade-full"]));

    assert.deepEqual(view(restored), view(run.state));
  });
});
