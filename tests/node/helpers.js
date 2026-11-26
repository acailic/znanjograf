// Shared helpers for the engine tests: the fixtures, simulated pupils and a
// session driver. Nothing here is used by the site.

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { isCorrect } from "../../site/js/engine/answer.js";
import { buildIndex } from "../../site/js/engine/graph.js";
import { parseRat } from "../../site/js/engine/rational.js";
import { statusesOf, summarise } from "../../site/js/engine/result.js";
import { apply, createSession, extend, next } from "../../site/js/engine/session.js";

const FIXTURES = join(dirname(fileURLToPath(import.meta.url)), "..", "fixtures");

// The engine fixture is dumped by tests/helpers.py (dump_engine_fixture). If it
// is ever missing, this is the one function to change.
function readJson(name) {
  return JSON.parse(readFileSync(join(FIXTURES, name), "utf8"));
}

export function loadEngineFixture() {
  return readJson("engine-fixture.json");
}

export function loadAnswerVectors() {
  return readJson("answer-vectors.json");
}

/** The fixture as a session context: graph index, question bank and the scope. */
export function fixtureContext(fixture, scope, options = {}) {
  return {
    scope,
    index: buildIndex(fixture.topics, fixture.edges, fixture.aliases),
    bank: fixture.questions,
    history: {},
    ...options,
  };
}

// ----- simulated pupils -----------------------------------------------------------

/** Every topic reachable from `ids` through hard edges (without the ids themselves). */
export function hardDescendants(index, ids) {
  const found = new Set();
  const queue = [...ids];
  while (queue.length > 0) {
    for (const edge of index.dependentsOf(queue.pop())) {
      if (edge.strength === "hard" && !found.has(edge.id)) {
        found.add(edge.id);
        queue.push(edge.id);
      }
    }
  }
  return found;
}

/**
 * A pupil whose knowledge is `known`, closed under hard prerequisites. A pupil
 * may also carry a `shaky` set of topics it answers as in a shaky verdict.
 */
export function pupilKnowing(index, known) {
  const closed = new Set(known);
  for (const id of closed) {
    for (const ancestor of index.hardAncestorsOf(id)) closed.add(ancestor);
  }
  return { known: closed };
}

export function pupilKnowingAll(index) {
  return { known: new Set(index.topicIds) };
}

export function pupilKnowingNothing() {
  return { known: new Set() };
}

/** Knows every topic except `missing` and their hard descendants. */
export function pupilKnowingAllBut(index, missing) {
  const gone = new Set([...missing, ...hardDescendants(index, missing)]);
  return { known: new Set(index.topicIds.filter((id) => !gone.has(id))) };
}

/** Answers every question at random: one of the options, or a number from 0 to 19. */
export function guessingPupil(rng) {
  return { rng, guessing: true };
}

/** Answers correctly with probability `probability`, otherwise wrongly. */
export function randomPupil(rng, probability) {
  return { rng, probability };
}

function pick(list, rng) {
  return list[Math.floor(rng() * list.length)];
}

/** A numeric value that is certainly not the answer of `question`. */
function wrongValue(question) {
  const expected = parseRat(question.answer);
  if (expected === null) return "0";
  return expected.d === 1n ? String(expected.n + 1n) : `${expected.n + expected.d}/${expected.d}`;
}

function isCorrectByNature(question, pupil) {
  if ("guessing" in pupil) return null; // the random pick decides
  if ("probability" in pupil) return pupil.rng() < pupil.probability;
  // A pupil marked `shaky` at a topic fails its standard questions and passes its basic ones.
  if (pupil.shaky !== undefined && pupil.shaky.has(question.topic)) return question.level === "basic";
  return pupil.known.has(question.topic);
}

/** The response object a pupil gives to `question`. */
export function answerQuestion(question, pupil) {
  const rng = pupil.rng;
  const correct = isCorrectByNature(question, pupil);
  if (question.type === "choice") {
    const ids = question.choices.map((option) => option.id);
    if (correct === null) return { type: "choice", choiceId: pick(ids, rng) };
    const options = correct ? [question.answer] : ids.filter((id) => id !== question.answer);
    return { type: "choice", choiceId: rng ? pick(options, rng) : options[0] };
  }
  if (correct === null) return { type: "numeric", value: String(Math.floor(rng() * 20)) };
  return { type: "numeric", value: correct ? question.answer : wrongValue(question) };
}

/** mulberry32: a tiny seeded PRNG, good enough for reproducible simulations. */
export function mulberry32(seed) {
  let state = seed >>> 0;
  return function () {
    state = (state + 0x6d2b79f5) >>> 0;
    let t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// ----- driving a session ----------------------------------------------------------

/**
 * Runs a session to the end for `pupil`, continuing past every pause, and stops
 * early once `maxAnswers` answers are given. Returns the live state after every
 * answer (`states[k]` is the state after k answers) and the final summary.
 */
export function runSession(ctx, pupil, { maxAnswers = Infinity } = {}) {
  let state = createSession(ctx);
  const states = [state];
  const pauses = [];
  const questions = [];
  for (;;) {
    const step = next(state);
    if (step.kind === "done" || state.log.length >= maxAnswers) break;
    if (step.kind === "paused") {
      pauses.push(step.asked);
      state = extend(state);
      continue;
    }
    questions.push(step);
    const response = answerQuestion(step.question, pupil);
    state = apply(state, { questionId: step.question.id, correct: isCorrect(step.question, response) });
    states.push(state);
  }
  return { state, states, log: state.log, pauses, questions, summary: summarise(state), statuses: statusesOf(state) };
}

/** How often each topic was asked in `log`. */
export function askedPerTopic(bank, log) {
  const counts = new Map();
  for (const event of log) {
    const topic = questionById(bank, event.questionId).topic;
    counts.set(topic, (counts.get(topic) ?? 0) + 1);
  }
  return counts;
}

export function questionById(bank, questionId) {
  for (const questions of Object.values(bank)) {
    const question = questions.find((candidate) => candidate.id === questionId);
    if (question !== undefined) return question;
  }
  throw new Error(`no question ${questionId} in the bank`);
}

// ----- a corpus larger than the fixture --------------------------------------------

/**
 * A random corpus, larger than the fixture, so that one session can last 60
 * answers. Topics are numbered in learning order; every edge points backwards.
 */
export function syntheticCorpus(seed, { topics = 48, grades = 4 } = {}) {
  const rng = mulberry32(seed);
  const perGrade = topics / grades;
  const topicList = [];
  const edges = [];
  const bank = {};
  const seen = new Set();
  const addEdge = (topic, requires, strength) => {
    const key = `${topic}>${requires}`;
    if (topic === requires || seen.has(key)) return;
    seen.add(key);
    edges.push([topic, requires, strength]);
  };
  for (let i = 0; i < topics; i += 1) {
    const id = `syn-topic-${String(i).padStart(2, "0")}`;
    const grade = Math.floor(i / perGrade) + 1;
    topicList.push({ id, grade, area: "numbers", unit: `Jedinica ${grade}`, kind: "procedure", name: `Tema ${i}` });
    if (i > 0 && rng() < 0.85) addEdge(id, topicList[i - 1].id, "hard");
    for (let extra = 0; extra < 2; extra += 1) {
      if (i > 1 && rng() < 0.3) addEdge(id, topicList[Math.floor(rng() * i)].id, rng() < 0.6 ? "hard" : "soft");
    }
    bank[id] = syntheticQuestions(id, rng);
  }
  return { topics: topicList, edges, bank, index: buildIndex(topicList, edges, {}) };
}

const SMALL_ANSWERS = ["3", "7", "10", "0"];
const LARGE_ANSWERS = ["25", "48", "150", "237", "1000", "2500"];

/** Two basic and two standard questions; answers mix guessable and strong values. */
function syntheticQuestions(topicId, rng) {
  const pickFrom = (list) => list[Math.floor(rng() * list.length)];
  const choice = {
    id: `${topicId}-q3`,
    topic: topicId,
    level: "standard",
    type: "choice",
    prompt: `${topicId} standard choice`,
    choices: [{ id: "a", text: "12" }, { id: "b", text: "25" }, { id: "c", text: "48" }, { id: "d", text: "150" }],
    answer: "c",
  };
  const basic = (n, answer) => ({ id: `${topicId}-q${n}`, topic: topicId, level: "basic", type: "numeric", prompt: `${topicId} q${n}`, answer, answerRational: [answer, "1"] });
  const standard = (n, answer) => ({ id: `${topicId}-q${n}`, topic: topicId, level: "standard", type: "numeric", prompt: `${topicId} q${n}`, answer, answerRational: [answer, "1"] });
  return [
    basic(1, pickFrom(LARGE_ANSWERS)),
    basic(2, pickFrom(SMALL_ANSWERS)),
    rng() < 0.25 ? choice : standard(3, pickFrom(rng() < 0.5 ? SMALL_ANSWERS : LARGE_ANSWERS)),
    standard(4, pickFrom(rng() < 0.5 ? SMALL_ANSWERS : LARGE_ANSWERS)),
  ];
}
