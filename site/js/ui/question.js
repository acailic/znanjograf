// site/js/ui/question.js - one question on screen: its text with the formulas typeset,
// its figure if it has one, and the controls to answer it.
//
// renderQuestion, renderPrompt, feedbackMarkup and displayAnswer return strings;
// wireQuestion is the only function here that touches the DOM. The right answer never
// enters the markup: wireQuestion hands the response to the engine and reports back.

import { esc, t } from "../common.js";
import { isCorrect } from "../engine/answer.js";
import { parseRat } from "../engine/rational.js";
import { renderFigure } from "../figure.js";
import { texToHtml } from "../katex.js";

const MATH = /\$([^$]*)\$/g;
let counter = 0;
const nextId = (name) => `zg-${name}-${(counter += 1)}`;

// ----- text with formulas -----------------------------------------------------------------

function formula(tex) {
  try {
    const html = texToHtml(tex);
    if (typeof html === "string" && html !== "") return html;
  } catch {
    // KaTeX missing or unhappy: the formula stays visible as it is written.
  }
  return `<code class="zg-tex-raw">${esc(tex)}</code>`;
}

/** `text` with every $formula$ typeset by KaTeX; everything else is escaped. */
export function renderMath(text) {
  const source = String(text ?? "");
  const out = [];
  let last = 0;
  for (const match of source.matchAll(MATH)) {
    out.push(esc(source.slice(last, match.index)), formula(match[1]));
    last = match.index + match[0].length;
  }
  out.push(esc(source.slice(last)));
  return out.join("");
}

/** The right answer the way a pupil writes it: a choice by its text, a number with a decimal comma. */
export function displayAnswer(question) {
  if (!question) return "";
  if (question.type === "choice") {
    const choice = (Array.isArray(question.choices) ? question.choices : []).find((item) => item && item.id === question.answer);
    return choice ? String(choice.text ?? "") : "";
  }
  return String(question.answer ?? "").replace(/(\d)\.(\d)/g, "$1,$2");
}

// ----- the figure -------------------------------------------------------------------------

function figureMarkup(figure) {
  if (!figure || typeof figure !== "object") return ""; // no figure: no markup, and so no empty box
  let drawn = null;
  try {
    drawn = figure ? renderFigure(figure) : null;
  } catch {
    drawn = null; // the figure cannot be drawn: its description has to be enough (spec 12.3)
  }
  const alt = String(drawn?.alt ?? figure?.alt ?? "");
  if (typeof drawn?.svg !== "string") return `<p class="zg-note">${esc(alt)}</p>`;
  // The svg already carries the description for assistive technology, so the visible
  // copy of it is hidden from that technology to keep it from being read twice.
  return `<div class="zg-fig">${drawn.svg}${alt ? `<p class="zg-fig-cap" aria-hidden="true">${esc(alt)}</p>` : ""}</div>`;
}

// ----- markup -----------------------------------------------------------------------------

/** The text of a question and its figure, without any controls: what a page shows as a sample. */
export function renderPrompt(question) {
  return `<div class="zg-prompt">${figureMarkup(question?.figure)}<p class="zg-prompt-text">${renderMath(question?.prompt)}</p></div>`;
}

const topicCache = new WeakMap();

function topicName(index, topicId) {
  if (!index || typeof index !== "object" || !Array.isArray(index.topics)) return "";
  let names = topicCache.get(index);
  if (!names) {
    names = new Map(index.topics.map((topic) => [topic?.id, topic?.name]));
    topicCache.set(index, names);
  }
  return names.get(topicId) ?? "";
}

/** Whether the expected answer needs a comma or a slash, so that the pupil is told how to write it. */
const needsHint = (question) => /[^0-9 ]/.test(String(question?.answer ?? ""));
const inputMode = (question) => (needsHint(question) ? "text" : "decimal");

function numericMarkup(question) {
  const id = nextId("answer");
  const hint = needsHint(question) ? ` aria-describedby="${id}-hint"` : "";
  return `<div class="zg-field">
  <label for="${id}">${esc(t("question.answer.label"))}</label>
  <div class="zg-answer-line">
    <input class="zg-input zg-input-lg" id="${id}" name="answer" type="text" inputmode="${inputMode(question)}" autocomplete="off" autocapitalize="off" spellcheck="false" enterkeyhint="go" placeholder="${esc(t("question.answer.placeholder"))}"${hint}>
    <button type="submit" class="zg-btn zg-btn-primary">${esc(t("question.answer.submit"))}</button>
  </div>
  ${needsHint(question) ? `<p class="zg-hint" id="${id}-hint">${esc(t("question.answer.hint"))}</p>` : ""}
</div>`;
}

function shuffled(items) {
  const out = [...items];
  for (let i = out.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out; // the offers are shuffled every time a question is shown (spec 10.2)
}

function choicesMarkup(question) {
  const choices = shuffled((Array.isArray(question.choices) ? question.choices : []).filter((choice) => choice && typeof choice.id === "string"));
  return `<div class="zg-field" role="group" aria-label="${esc(t("question.choices.label"))}">
  <ul class="zg-choices">${choices.map((choice) => `<li><button type="button" class="zg-choice" data-zg-choice="${esc(choice.id)}">${renderMath(choice.text)}</button></li>`).join("")}</ul>
</div>`;
}

/**
 * A question as a card. `index` is the data index (the question then says which topic it
 * is from); a number in its place is taken as the number of the question, which is what
 * `position` says otherwise.
 */
export function renderQuestion(question, index, position = 0) {
  const numeric = question?.type === "numeric";
  const choice = question?.type === "choice";
  const number = Number.isInteger(index) ? index : Number.isInteger(position) && position > 0 ? position : 0;
  const topic = topicName(index, question?.topic);
  const titleId = nextId("question");
  return `<article class="zg-card zg-question" data-zg-question>
  ${topic ? `<p class="zg-eyebrow">${esc(topic)}</p>` : ""}
  <h2 class="zg-question-title" id="${titleId}" data-zg-focus>${esc(t("diag.question.heading", { n: number }))}</h2>
  ${renderPrompt(question)}
  <form class="zg-answer" novalidate>
    ${choice ? choicesMarkup(question) : ""}
    ${numeric ? numericMarkup(question) : ""}
    <div class="zg-actions"><button type="button" class="zg-btn zg-btn-secondary" data-zg-dontknow>${esc(t("question.dontKnow"))}</button></div>
  </form>
</article>`;
}

/**
 * What is said right after an answer: right, wrong or "I don't know", never more. The
 * explanation is passed in only once the engine has settled the topic (spec 10.2).
 */
export function feedbackMarkup({ correct = false, dontKnow = false, explanation = "" } = {}) {
  const tone = dontKnow ? "" : correct ? " zg-feedback-ok" : " zg-feedback-bad";
  const verdict = t(dontKnow ? "question.feedback.dontKnow" : correct ? "question.feedback.correct" : "question.feedback.wrong");
  const note = explanation
    ? `<div class="zg-explain"><p class="zg-explain-title">${esc(t("question.explanation"))}</p><p>${renderMath(explanation)}</p></div>`
    : "";
  return `<div class="zg-feedback${tone}" data-zg-feedback tabindex="-1">
  <p class="zg-feedback-verdict">${esc(verdict)}</p>${note}
  <div class="zg-actions"><button type="button" class="zg-btn zg-btn-primary" data-zg-next>${esc(t("question.next"))}</button></div>
</div>`;
}

// ----- behaviour ----------------------------------------------------------------------------

function isNumber(value) {
  try {
    return parseRat(value) !== null;
  } catch {
    return true; // without the parser nothing is refused before the engine sees it
  }
}

/** Stops the form from taking a second answer and marks the offer that was chosen. */
function lock(form, picked, correct) {
  for (const control of form.querySelectorAll("input, button")) control.disabled = true;
  if (picked?.choice) picked.choice.classList.add("zg-picked", correct ? "zg-right" : "zg-wrong");
}

function complain(input, form, message) {
  let line = form.querySelector("[data-zg-error]");
  if (!line) {
    form.querySelector("input")?.insertAdjacentHTML("afterend", '<p class="zg-error" data-zg-error role="alert"></p>');
    line = form.querySelector("[data-zg-error]");
  }
  line.textContent = message;
  if (input) {
    input.classList.add("zg-invalid");
    input.setAttribute("aria-invalid", "true");
    if (document.activeElement !== input) input.focus();
  }
}

/**
 * Makes the controls of a rendered question work. `onAnswer` hears { correct, value,
 * dontKnow } once, with the engine's verdict on the response; the controls are then
 * disabled until the page draws the next question. The question is the third argument,
 * or was left on the container as `zgQuestion`.
 */
export function wireQuestion(container, onAnswer, question = container?.zgQuestion) {
  const form = container?.querySelector("form");
  if (!form || !question || typeof question !== "object") return;
  let answered = false;

  const finish = (response, picked) => {
    if (answered) return;
    answered = true;
    let correct = false;
    if (!picked?.dontKnow) {
      try {
        correct = isCorrect(question, response) === true;
      } catch (error) {
        console.error(error);
      }
    }
    lock(form, picked, correct);
    onAnswer({ correct, value: picked?.dontKnow ? null : (response.value ?? response.choiceId ?? null), dontKnow: picked?.dontKnow === true });
  };

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (answered || question.type !== "numeric") return;
    const input = form.querySelector("input");
    const value = input ? input.value.trim() : "";
    if (value === "") return complain(input, form, t("question.answer.empty"));
    if (!isNumber(value)) return complain(input, form, t("question.answer.invalid"));
    finish({ type: "numeric", value });
  });
  form.querySelector("[data-zg-dontknow]")?.addEventListener("click", () => finish({ type: "choice", choiceId: null }, { dontKnow: true }));
  for (const button of form.querySelectorAll("[data-zg-choice]")) {
    button.addEventListener("click", () => finish({ type: "choice", choiceId: button.dataset.zgChoice }, { choice: button }));
  }
}
