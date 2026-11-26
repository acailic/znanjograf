// site/js/ui/progress.js - how far a diagnosis has come: the topics of the scope that
// already have a status, and the questions answered so far.

import { esc, t } from "../common.js";

/**
 * `asked` questions answered so far, `done` topics the engine has given a status,
 * `total` topics in the scope. The bar follows the topics; the text says both.
 */
export function progressMarkup({ asked = 0, done = 0, total = 0 } = {}) {
  const span = Math.max(0, Number(total) || 0);
  const shown = Math.max(0, Math.min(Number(done) || 0, span));
  const percent = span > 0 ? Math.round((shown / span) * 100) : 0;
  const topics = t("progress.topics", { done: shown, total: span });
  return `<div class="zg-progress" role="group" aria-label="${esc(t("progress.label"))}">
  <div class="zg-progress-track" role="progressbar" aria-valuemin="0" aria-valuemax="${span}" aria-valuenow="${shown}" aria-valuetext="${esc(topics)}"><span class="zg-progress-fill" style="width:${percent}%"></span></div>
  <p class="zg-progress-text">${esc(topics)}${DOT}${esc(t("progress.questions", { asked: Math.max(0, Number(asked) || 0) }))}</p>
</div>`;
}

// A middle dot between the two counts, written as an escape to keep this file ASCII.
const DOT = " \u00b7 ";
