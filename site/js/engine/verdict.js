// verdict.js — the verdict on one topic from the questions asked on it.
//
// The rules (spec 10.2), in the order the questions are asked:
//   1. the first standard question; wrong -> a basic question:
//      wrong again is weak, right is shaky.
//   2. right and strong -> mastered at once.
//   3. right but not strong -> the second standard question:
//      right is mastered, wrong is shaky.
//
// While the verdict is still open the status is `untested` and `done` is false,
// so the caller knows the topic needs another question.

import { isStrongAnswer } from "./answer.js";

export const STATUS = Object.freeze({
  UNTESTED: "untested",
  MASTERED: "mastered",
  SHAKY: "shaky",
  WEAK: "weak",
  INFERRED: "inferred",
});

/**
 * Decide a topic from its evidence: [{question, correct}] in asked order.
 * Returns {status, done}.
 */
export function verdictOf(evidence) {
  const first = evidence?.[0];
  const second = evidence?.[1];

  if (first === undefined) return { status: STATUS.UNTESTED, done: false };

  if (!first.correct) {
    if (second === undefined) return { status: STATUS.UNTESTED, done: false };
    return { status: second.correct ? STATUS.SHAKY : STATUS.WEAK, done: true };
  }

  if (isStrongAnswer(first.question, true)) return { status: STATUS.MASTERED, done: true };

  if (second === undefined) return { status: STATUS.UNTESTED, done: false };
  return { status: second.correct ? STATUS.MASTERED : STATUS.SHAKY, done: true };
}
