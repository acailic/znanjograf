// Tests for site/js/strings.js and for the rules that keep the site translatable by the
// build: every sentence lives in strings.js in Serbian Latin, and nothing else carries text.
// The build transliterates only <title>, <noscript> and the string literals of strings.js, so
// every other byte of the pages must be ASCII.

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { strings } from "../../site/js/strings.js";

const root = new URL("../../", import.meta.url);
const read = (path) => readFileSync(new URL(path, root), "utf8");

const STRINGS = "site/js/strings.js";
const MODULES = [
  "site/js/data.js", "site/js/storage.js", "site/js/common.js",
  "site/js/ui/question.js", "site/js/ui/progress.js", "site/js/ui/result.js",
  "site/js/pages/home.js", "site/js/pages/map.js", "site/js/pages/diagnose.js", "site/js/pages/about.js",
];
const PAGES = ["site/index.html", "site/mapa/index.html", "site/dijagnostika/index.html", "site/o-projektu/index.html"];

const CYRILLIC = /[\u0400-\u04FF]/;
const NON_ASCII = /[^\u0000-\u007F]/g;
const LETTER = /[A-Za-z\u00C0-\u024F\u0400-\u04FF]/;
const ALLOWED = new Set(Array.from("čćšžđČĆŠŽĐ„“”–—…·"));
const KEY = /^[a-z0-9]+(?:\.[a-z0-9][A-Za-z0-9]*)+$/;
const KEY_LINE = /^  ("[A-Za-z0-9.]+"): "([^"\\\n]*)",?$/;
// The very pattern zg/build.py runs over strings.js to find the literals it transliterates.
const BUILD_LITERAL = /("(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*'|`(?:[^`\\]|\\.)*`)(\s*:)?/gs;
const TAG = /(<[^>]+>)/;
const SIMPLE_TAG = /^<\/?(?:a|strong|em|code|br)(?: [a-z-]+='[^']*')?\/?>$/i;
const NAMESPACES = "site|common|nav|script|home|map|diag|about|area|status|strength|match|progress|question|result";
const KEY_LITERAL = new RegExp(`"(${NAMESPACES})(\\.[A-Za-z0-9]+)+"`, "g");
const HTML_COMMENTS = /<!--[\s\S]*?-->/g;
const TITLE_OR_NOSCRIPT = /<(title|noscript)\b[^>]*>([\s\S]*?)<\/\1>/gi;

test("every value is a non-empty sentence in Serbian Latin", () => {
  const entries = Object.entries(strings);
  assert.ok(entries.length > 100, "the site has more than a hundred sentences");
  for (const [key, value] of entries) {
    assert.match(key, KEY, key);
    assert.equal(typeof value, "string", key);
    assert.ok(value.trim().length > 0, `${key} is empty`);
    assert.ok(value === value.trim(), `${key} has padding at the ends`);
    assert.doesNotMatch(value, CYRILLIC, `${key} holds Cyrillic; the build generates it`);
    for (const ch of value.match(NON_ASCII) || []) {
      assert.ok(ALLOWED.has(ch), `${key} holds a character outside Serbian Latin: ${ch}`);
    }
    for (const name of value.match(/\$?\{[^{}]*\}/g) || []) {
      assert.match(name, /^\$\{[a-z][A-Za-z0-9]*\}$/, `${key}: a placeholder is written ${"${name}"}, the one form the build leaves alone`);
    }
  }
});

test("the file is one flat object, one quoted key and one plain value per line", () => {
  const lines = read(STRINGS).split("\n");
  const first = lines.indexOf("export const strings = {");
  const last = lines.lastIndexOf("};");
  assert.ok(first > 0, "a comment header, then the object");
  assert.equal(lines.slice(last + 1).join("").trim(), "", "nothing follows the object");
  const inSource = [];
  for (const line of lines.slice(first + 1, last)) {
    if (line === "") continue; // a blank line between two groups of sentences
    const match = KEY_LINE.exec(line);
    assert.ok(match, `not a plain key and value: ${line}`);
    inSource.push(match[1].slice(1, -1));
  }
  assert.equal(new Set(inSource).size, inSource.length, "a key is written twice");
  assert.deepEqual(inSource, Object.keys(strings));
});

test("a placeholder survives the build the way zg/build.py transliterates it", () => {
  // What zg/build.py does to a value: the ${...} pieces are kept, the text between them transliterated.
  const interpolation = /(\$\{[^}]*\})/; // the capturing group keeps each piece in the split
  const cyrillic = (piece) => piece.replace(/[A-Za-z]/g, (ch) => String.fromCharCode(ch.charCodeAt(0) < 97 ? 0x410 + ch.charCodeAt(0) - 65 : 0x430 + ch.charCodeAt(0) - 97));
  for (const [key, value] of Object.entries(strings)) {
    const pieces = value.split(interpolation);
    const mirror = pieces.map((piece, index) => (index % 2 ? piece : cyrillic(piece))).join("");
    for (const piece of pieces.filter((_, index) => index % 2)) {
      if (!mirror.includes(piece)) assert.fail(`${key}: ${piece} would not survive the mirror`);
    }
  }
});

test("the build finds every value and nothing else to transliterate", () => {
  const values = [];
  for (const match of read(STRINGS).matchAll(BUILD_LITERAL)) {
    if (match[2] || match[1][0] !== '"') continue; // a quoted key, or a quote inside a comment
    values.push(JSON.parse(match[1]));
  }
  assert.deepEqual(values, Object.values(strings));
});

test("only *Html keys hold markup, and only simple inline tags", () => {
  for (const [key, value] of Object.entries(strings)) {
    if (!value.includes("<")) continue;
    assert.ok(key.endsWith("Html"), `${key} holds markup but does not say so`);
    const open = [];
    for (const piece of value.split(TAG).filter((part) => part.startsWith("<"))) {
      assert.match(piece, SIMPLE_TAG, `${key}: ${piece} is not a simple inline tag`);
      const name = piece.replace(/^<\/?([a-z]+)[\s/>].*$/i, "$1").toLowerCase();
      if (piece.startsWith("</")) assert.equal(open.pop(), name, `${key}: unexpected </${name}>`);
      else if (!piece.endsWith("/>")) open.push(name);
    }
    assert.deepEqual(open, [], `${key}: a tag is left open`);
  }
});

function keysUsedBy(path) {
  return [...read(path).matchAll(KEY_LITERAL)].map((match) => match[0].slice(1, -1));
}

test("every key the site asks for exists", () => {
  const missing = [];
  for (const path of MODULES) {
    for (const key of keysUsedBy(path)) {
      if (!(key in strings)) missing.push(`${path}: ${key}`);
    }
  }
  assert.deepEqual(missing, []);
});

test("every sentence is actually shown somewhere", () => {
  const used = new Set(MODULES.flatMap(keysUsedBy));
  assert.deepEqual(Object.keys(strings).filter((key) => !used.has(key)), [], "sentences nobody shows");
});

test("a page carries text only in its title and its noscript sentence", () => {
  for (const path of PAGES) {
    const html = read(path).replace(HTML_COMMENTS, "");
    const texts = [...html.matchAll(TITLE_OR_NOSCRIPT)].map((match) => match[2]);
    assert.equal(texts.length, 2, `${path}: one title and one noscript`);
    for (const text of texts) {
      assert.match(text, LETTER, `${path}: empty title or noscript`);
      assert.doesNotMatch(text, CYRILLIC, `${path}: Cyrillic is generated by the build`);
    }
    // The one exception: a static hint for a page opened from a file, shown only when the
    // page module never ran (inline code below main un-hides it after load).
    const inside = /<main\b[^>]*>([\s\S]*?)<\/main>/.exec(html)?.[1] ?? "";
    assert.match(inside, /^<p class="zg-noscript" id="zg-fallback" hidden>[^<]*<\/p>$/, `${path}: nothing in main but the file hint`);
    assert.match(html, /getElementById\("zg-fallback"\)/, `${path}: the hint is un-hidden only if nothing replaced main`);
    assert.equal(html.replace(TITLE_OR_NOSCRIPT, "").replace(/<main\b[^>]*>[\s\S]*?<\/main>/, "").match(NON_ASCII), null, `${path}: text outside <title>, <noscript> and the file hint stays Latin in the mirror`);
    assert.match(html, /<html lang="sr-Latn">/, `${path}: the build rewrites exactly this`);
    assert.match(html, /data-pismo="lat"/, `${path}: the build rewrites exactly this`);
    assert.match(html, /<meta name="viewport" content="width=device-width, initial-scale=1">/, path);
    assert.match(html, /<script type="module" src="[^"]*js\/pages\/[a-z]+\.js"><\/script>/, path);
    assert.match(html, /<link rel="stylesheet" href="[^"]*css\/zg\.css">/, path);
    // An icon inside the page: the browser would otherwise ask for /favicon.ico on every page.
    const icon = /<link rel="icon" type="image\/svg\+xml" href="data:image\/svg\+xml,([^"]*)">/.exec(html);
    assert.ok(icon, `${path}: an inline icon`);
  }
  assert.match(read("site/index.html"), /data-podaci="podaci\/"/);
  for (const path of PAGES.slice(1)) assert.match(read(path), /data-podaci="\.\.\/podaci\/"/, path);
});

test("everything but strings.js is pure ASCII", () => {
  for (const path of [...MODULES, "site/css/zg.css"]) {
    assert.equal(read(path).match(NON_ASCII), null, `${path}: use escapes, keep text in strings.js`);
  }
});

// ----- what the pages draw ------------------------------------------------------------------
// The renderers are string builders that need no DOM, so they are held to the same fixture
// the engine is tested on. KaTeX is loaded the way katex.test.js loads it.

const fixture = JSON.parse(read("tests/fixtures/engine-fixture.json"));
globalThis.katex = createRequire(import.meta.url)("../../site/vendor/katex/katex.min.js");
const { displayAnswer, feedbackMarkup, renderMath, renderQuestion } = await import("../../site/js/ui/question.js");
const { progressMarkup } = await import("../../site/js/ui/progress.js");
const { outcomeItemMarkup, resultSections } = await import("../../site/js/ui/result.js");
const { apply, createSession, next, summarise } = await import("../../site/js/engine/session.js");
const { buildIndex } = await import("../../site/js/engine/graph.js");

const MISSING = "mat-sabiranje-do-10"; // what the pupil below does not know
const OUTCOME = { id: "g1-2026-002", text: "sabira dva jednocifrena broja", page: 12 };
const edition = { edition: "g1-2026", outcomes: [OUTCOME] };

test("an outcome is found from either shape a caller may hold", () => {
  // A grade bundle keeps a topic's curriculum as { edition, outcome, match }; the map passes that on.
  const fromBundle = { edition: "g1-2026", outcome: "g1-2026-002", match: "exact" };
  // The engine's summary lists outcomes as { edition, id }; the result screen passes that on.
  const fromSummary = { edition: "g1-2026", id: "g1-2026-002" };
  for (const entry of [fromBundle, fromSummary]) {
    const html = outcomeItemMarkup(entry, edition);
    assert.match(html, /sabira dva jednocifrena broja/, "the text of the outcome");
    assert.match(html, /g1-2026-002/, "its id");
    assert.match(html, /strana 12/, "and the page it is printed on");
  }
  assert.match(outcomeItemMarkup(fromSummary, null), /g1-2026-002/, "without the edition file the id is shown");
  assert.equal(outcomeItemMarkup(null, edition), "", "no outcome, no markup, no empty box");
});

test("the result screen draws what the engine finds on the fixture", () => {
  const dataIndex = { topics: fixture.topics, edges: fixture.edges, aliases: fixture.aliases };
  const questions = {};
  for (const list of Object.values(fixture.questions)) for (const question of list) questions[question.id] = question;
  const curriculum = [{ edition: "g1-2026", outcome: "g1-2026-002", match: "exact" }];
  const gradeData = { topics: { [MISSING]: { summary: "Sabiranje do 10.", mastery: ["sabira dva broja"], curriculum } }, questions, outcomes: { "g1-2026": edition } };
  const graph = buildIndex(fixture.topics, fixture.edges, fixture.aliases);

  // A pupil who knows everything except what leads through the missing topic.
  let state = createSession({ scope: { kind: "topic", id: "mat-zadaci-sa-sabiranjem" }, index: graph, bank: fixture.questions, curriculum: { [MISSING]: curriculum } });
  for (let step = next(state); step.kind === "question"; step = next(state)) {
    state = apply(state, { questionId: step.question.id, correct: step.topicId !== MISSING && !graph.hardAncestorsOf(step.topicId).has(MISSING) });
  }
  const summary = summarise(state);
  assert.deepEqual(summary.roots.map((root) => root.id), [MISSING], "the engine reports the one missing topic");

  const html = resultSections(summary, dataIndex, gradeData);
  assert.match(html, /Najverovatnije ovde je puklo/);
  assert.match(html, /Sabiranje do 10/, "the root by its name");
  assert.match(html, /href="mapa\/#mat-sabiranje-do-10"/, "as a link to its place on the map");
  assert.match(html, /Put popravke/);
  assert.match(html, /Pregled/);
  assert.match(html, /sabira dva jednocifrena broja/, "the outcome text is looked up in its edition");
  assert.match(html, /class="katex"/, "the missed tasks are typeset");
  assert.match(html, /Tačan odgovor:/, "with the right answer");
  assert.doesNotMatch(html, /\$\{/, "no placeholder is left unfilled");
  assert.doesNotMatch(html, /<p class="zg-[^"]*"><\/p>/, "no empty paragraph that would show as an empty box");

  // Nothing found wrong: the reader is told so instead of being shown an empty list.
  const clean = resultSections({ ...summary, roots: [], path: [], shaky: [], untested: [] }, dataIndex, gradeData);
  assert.match(clean, /Nema rupe/);
  assert.match(clean, /Nema tema za popravku\./);
  assert.doesNotMatch(clean, /<h2[^>]*>Neproverene teme<\/h2>/, "no section for topics left untested when there are none");
});

test("a question is drawn with its controls and without its answer", () => {
  const dataIndex = { topics: fixture.topics, edges: fixture.edges, aliases: fixture.aliases };
  const typed = renderQuestion(fixture.questions["mat-sabiranje-do-20"][0], dataIndex, 3);
  assert.match(typed, /Pitanje 3/);
  assert.match(typed, /Sabiranje do 20/, "the question says which topic it is from");
  assert.match(typed, /class="katex"/, "the formula of the prompt is typeset");
  assert.match(typed, /data-zg-dontknow[^>]*>Ne znam</);
  assert.match(typed, /inputmode="decimal"/, "a whole number asks for a numeric keypad");
  assert.match(typed, /<label for="zg-answer-\d+">Odgovor<\/label>/, "the field is labelled");
  assert.doesNotMatch(typed, /zg-note/, "no empty box where a figure would be");
  assert.doesNotMatch(typed, /answerRational|>14</, "the right answer (14) is not in the markup");

  const picked = renderQuestion(fixture.questions["mat-geometrijski-oblici"][0], dataIndex, 1);
  assert.match(picked, /data-zg-choice="a"/);
  assert.match(picked, /trougao/);
  assert.match(picked, /Izaberi jedni? odgovor|Izaberi jedan odgovor/);

  assert.equal(displayAnswer({ type: "numeric", answer: "3.5" }), "3,5", "a decimal comma, as a pupil writes it");
  assert.equal(displayAnswer({ type: "choice", answer: "b", choices: [{ id: "a", text: "kvadrat" }, { id: "b", text: "trougao" }] }), "trougao");
  assert.match(feedbackMarkup({ correct: false }), /Netačno\./);
  assert.doesNotMatch(feedbackMarkup({ correct: false }), /Objašnjenje/, "no explanation until the topic is settled");
  assert.match(feedbackMarkup({ correct: true, explanation: "9 + 1 = 10." }), /Objašnjenje/);
  assert.match(feedbackMarkup({ dontKnow: true }), /idemo dalje/);
  assert.match(progressMarkup({ asked: 3, done: 2, total: 8 }), /aria-valuemax="8" aria-valuenow="2" aria-valuetext="Teme: 2 od 8"/);
  assert.match(progressMarkup({ asked: 3, done: 12, total: 8 }), /aria-valuenow="8"/, "never past the end");
  assert.match(renderMath("Koliko je $3 + 4$? A &amp; B"), /Koliko je <span class="katex"/);
  assert.match(renderMath("x < y"), /x &lt; y/, "text around a formula is escaped");
});
