// session.js — the diagnostic session: which question comes next, as a pure
// function of the log.
//
// A state is {scope, index, bank, budget, history, curriculum, extensions,
// log}. Nothing is remembered beyond the log: `next` replays the log through
// the diagnostic script and returns the question the script asks once the log
// runs out. A state is therefore a fold over its log, which is what makes
// continuing, saving and sharing a session all the same operation.
//
// Pure: no DOM, no storage, no fetch.

import { STATUS, verdictOf } from "./verdict.js";

// C7 lists summarise with the session functions; it lives in result.js.
export { summarise } from "./result.js";

const SCOPE_KINDS = ["topic", "unit", "grade", "grade-full"];

/** What `next` asks for when a question is not a scope topic itself. */
const ROLE_SCOPE = "scope";
const ROLE_PREREQUISITE = "prerequisite";

function isEvent(event) {
  return typeof event === "object" && event !== null && typeof event.questionId === "string" && typeof event.correct === "boolean";
}

/** Create the opening state of a session. */
export function createSession({ scope, index, bank, budget = 25, history = {}, curriculum = {} } = {}) {
  if (!SCOPE_KINDS.includes(scope?.kind)) {
    throw new TypeError(`ZG_BAD_SCOPE: ${JSON.stringify(scope?.kind)} is not a scope kind`);
  }
  if (!Number.isInteger(budget) || budget < 1) {
    throw new TypeError("ZG_BAD_BUDGET: the budget must be a positive whole number of questions");
  }
  return Object.freeze({ scope, index, bank, budget, history, curriculum, extensions: 0, log: Object.freeze([]) });
}

/**
 * What the session wants now:
 *   {kind: "question", topicId, question, role}  role is "scope" or "prerequisite"
 *   {kind: "paused", asked}                       the block budget is used up
 *   {kind: "done"}                                every topic has a status
 */
export function next(state) {
  return replay(state).pending;
}

/** Answer the question `next` asks. Throws Error("ZG_OUT_OF_SYNC") for any other question. */
export function apply(state, event) {
  const pending = next(state);
  const questionId = pending.kind === "question" ? pending.question.id : null;
  if (questionId === null || !isEvent(event) || event.questionId !== questionId) {
    throw new Error("ZG_OUT_OF_SYNC");
  }
  const answer = Object.freeze({ questionId, correct: event.correct });
  return Object.freeze({ ...state, log: Object.freeze([...state.log, answer]) });
}

/** Allow one more block of `budget` questions. */
export function extend(state) {
  return Object.freeze({ ...state, extensions: state.extensions + 1 });
}

/**
 * Rebuild a session from a log. An event that does not answer the question the
 * engine asks at that point is dropped, and so is everything after it.
 */
export function reduce(log, ctx) {
  const events = Array.isArray(log) ? log : [];
  let state = createSession(ctx);
  for (const event of events) {
    const pending = next(state);
    if (pending.kind !== "question" || !isEvent(event) || event.questionId !== pending.question.id) break;
    state = apply(state, event);
  }
  return state;
}

// ----- replaying the log --------------------------------------------------------------

/** How many questions the session may ask before it pauses. */
function questionLimit(state) {
  // A log longer than one block shows that the block was extended, so a
  // restored session continues in the right block without being told.
  const proven = 1 + Math.floor((state.log.length - 1) / state.budget);
  return Math.max(1 + state.extensions, proven) * state.budget;
}

/**
 * Run the diagnostic script and feed it the log. Returns what the script
 * learned and what it wants once the log runs out. A log entry that does not
 * answer the question asked at that point ends the replay there.
 *
 *   {scopeIds, world: {status, missed, used, queue}, pending}
 *
 * This is the only place the script is run; result.js builds on it.
 */
export function replay(state) {
  const scopeIds = topicsInScope(state.scope, state.index);
  const world = {
    index: state.index,
    bank: state.bank,
    history: state.history,
    status: new Map(), // topic id → status; a topic without an entry is untested
    missed: new Map(), // topic id → questions answered wrong while judging it
    used: new Set(), // question ids asked in this session
    queue: [], // weak topics whose prerequisites still have to be examined
  };

  const script = diagnose(world, scopeIds);
  const log = state.log;
  let taken = 0;
  let step = script.next();
  while (!step.done && isEvent(log[taken]) && log[taken].questionId === step.value.question.id) {
    step = script.next(log[taken].correct);
    taken += 1;
  }

  let pending;
  if (step.done) pending = { kind: "done" };
  else if (taken >= questionLimit(state)) pending = { kind: "paused", asked: taken };
  else pending = { kind: "question", topicId: step.value.topicId, question: step.value.question, role: step.value.role };
  return { scopeIds, world, pending };
}

/** The topics a scope covers (spec 10.3). */
function topicsInScope(scope, index) {
  const ofGrade = (grade) => index.topicIds.filter((id) => index.gradeOf.get(id) === grade);
  switch (scope.kind) {
    case "topic":
      return index.resolveAlias(scope.id);
    case "unit":
      return ofGrade(scope.grade).filter((id) => index.unitOf.get(id) === scope.unit);
    case "grade":
      return index.gradeExits(scope.grade);
    default:
      return ofGrade(scope.grade);
  }
}

// ----- the diagnostic script ---------------------------------------------------------

/**
 * Yields every question the engine wants to ask, in the order that follows
 * from the answers, and takes each answer back as `next(correct)`.
 */
function* diagnose(world, scopeIds) {
  // The scope itself, hardest first; a topic that already has a status is skipped.
  for (const topicId of world.index.learningOrder(scopeIds).reverse()) {
    if (!world.status.has(topicId)) yield* settle(world, topicId, ROLE_SCOPE);
  }

  // Walk back from every weak topic, in the order in which they became weak.
  for (let head = 0; head < world.queue.length; head += 1) {
    const weakId = world.queue[head];
    const hard = world.index.hardAncestorsOf(weakId);
    yield* examine(world, hard);

    // Only when no hard ancestor is weak can a soft prerequisite be the cause.
    if (![...hard].some((id) => world.status.get(id) === STATUS.WEAK)) {
      yield* examine(world, new Set([...world.index.ancestorsOf(weakId)].filter((id) => !hard.has(id))));
    }
  }
}

/** Judges every topic of `ids` that has no status yet, the nearest first. */
function* examine(world, ids) {
  for (const topicId of world.index.learningOrder([...ids]).reverse()) {
    if (!world.status.has(topicId)) yield* settle(world, topicId, ROLE_PREREQUISITE);
  }
}

/** Judges one topic in up to two questions and gives it a status (spec 10.2). */
function* settle(world, topicId, role) {
  const evidence = [];
  world.missed.set(topicId, []);

  // A topic with no question left of the needed level is weak.
  let status = STATUS.WEAK;
  const first = yield* ask(world, topicId, "standard", role, evidence);
  if (first !== null) {
    const verdict = verdictOf(evidence);
    if (verdict.done) {
      status = verdict.status;
    } else {
      const second = yield* ask(world, topicId, first.correct ? "standard" : "basic", role, evidence);
      status = second === null ? STATUS.WEAK : verdictOf(evidence).status;
    }
  }
  conclude(world, topicId, status);
}

/** Asks the first unused question of `level` and records the answer. */
function* ask(world, topicId, level, role, evidence) {
  const question = pickQuestion(world, topicId, level);
  if (question === null) return null;

  world.used.add(question.id);
  const correct = (yield { topicId, question, role }) === true;
  evidence.push({ question, correct });
  if (!correct) world.missed.get(topicId).push(question.id);
  return { question, correct };
}

/** The first unused question of the level: lowest history counter first, then file order. */
function pickQuestion(world, topicId, level) {
  let best = null;
  for (const question of world.bank[topicId] ?? []) {
    if (question.level !== level || world.used.has(question.id)) continue;
    const uses = Object.hasOwn(world.history, question.id) ? world.history[question.id] : 0;
    // Ties keep the question that comes first in the file.
    if (best === null || uses < best.uses) best = { question, uses };
  }
  return best === null ? null : best.question;
}

/** Gives the topic its status and does what follows from it (spec 10.3). */
function conclude(world, topicId, status) {
  world.status.set(topicId, status);
  if (status === STATUS.MASTERED) {
    // Mastering a topic implies its hard prerequisites: they are inferred.
    for (const ancestor of world.index.hardAncestorsOf(topicId)) {
      if (!world.status.has(ancestor)) world.status.set(ancestor, STATUS.INFERRED);
    }
  } else if (status === STATUS.WEAK) {
    world.queue.push(topicId);
  }
}
