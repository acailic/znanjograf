// answer.js — is a response correct, and is a correct answer "strong"?
//
// A response is {type: "numeric", value} or {type: "choice", choiceId}; "I
// don't know" is an empty value or a null choice and simply counts as wrong.
// Numeric questions carry `answerRational`, the expected value as decimal
// strings, because the `check` expression itself is only evaluated in Python.

import { parseRat, rat } from "./rational.js";

/** The expected value of a numeric question (from `answerRational`, else from `answer`). */
function expectedValue(question) {
  const [numerator, denominator] = question.answerRational ?? [];
  return numerator === undefined || denominator === undefined ? parseRat(question.answer) : rat(BigInt(numerator), BigInt(denominator));
}

/**
 * A strong answer is a correct typed number that cannot be guessed: its value
 * is not an integer between -10 and 10. A choice is never strong.
 */
export function isStrongAnswer(question, correct) {
  if (!correct || question.type !== "numeric") return false;
  const value = expectedValue(question);
  if (value === null) return false;
  return value.d !== 1n || value.n < -10n || value.n > 10n;
}

/** True when `response` is the right answer to `question`. */
export function isCorrect(question, response) {
  if (typeof question !== "object" || question === null) return false;
  if (typeof response !== "object" || response === null) return false;

  if (question.type === "choice") {
    return response.type === "choice" && typeof response.choiceId === "string" && response.choiceId === question.answer;
  }
  if (question.type === "numeric") {
    if (response.type !== "numeric") return false;
    const expected = expectedValue(question);
    const given = typeof response.value === "string" || typeof response.value === "number" ? parseRat(String(response.value)) : null;
    return expected !== null && given !== null && given.n === expected.n && given.d === expected.d;
  }
  return false;
}
