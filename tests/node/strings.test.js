// Tests for site/js/strings.js and for the rules that keep the site translatable by the
// build: every sentence lives in strings.js in Serbian Latin, and nothing else carries text.
// The build transliterates only <title>, <noscript> and the string literals of strings.js, so
// every other byte of the pages must be ASCII.

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
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
const KEY = /^[a-z0-9]+(?:\.[a-z0-9]+)+$/;
const KEY_LINE = /^  ("[a-z0-9.]+"): "([^"\\\n]*)",?$/;
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
    for (const name of value.match(/\{[^{}]*\}/g) || []) {
      assert.match(name, /^\{[a-z][A-Za-z0-9]*\}$/, `${key}: odd placeholder ${name}`);
    }
  }
});

test("the file is one flat object, one quoted key and one plain value per line", () => {
  const lines = read(STRINGS).split("\n");
  assert.equal(lines[0], "export const strings = {");
  assert.equal(lines.at(-2), "};", "the object closes on its own line");
  const inSource = [];
  for (const line of lines.slice(1, -2)) {
    const match = KEY_LINE.exec(line);
    assert.ok(match, `not a plain key and value: ${line}`);
    inSource.push(match[1].slice(1, -1));
  }
  assert.equal(new Set(inSource).size, inSource.length, "a key is written twice");
  assert.deepEqual(inSource, Object.keys(strings));
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
    assert.equal(html.replace(TITLE_OR_NOSCRIPT, "").match(NON_ASCII), null, `${path}: text outside <title> and <noscript> stays Latin in the mirror`);
    assert.match(html, /<html lang="sr-Latn">/, `${path}: the build rewrites exactly this`);
    assert.match(html, /data-pismo="lat"/, `${path}: the build rewrites exactly this`);
    assert.match(html, /<meta name="viewport" content="width=device-width, initial-scale=1">/, path);
    assert.match(html, /<script type="module" src="[^"]*js\/pages\/[a-z]+\.js"><\/script>/, path);
    assert.match(html, /<link rel="stylesheet" href="[^"]*css\/zg\.css">/, path);
  }
  assert.match(read("site/index.html"), /data-podaci="podaci\/"/);
  for (const path of PAGES.slice(1)) assert.match(read(path), /data-podaci="\.\.\/podaci\/"/, path);
});

test("everything but strings.js is pure ASCII", () => {
  for (const path of [...MODULES, "site/css/zg.css"]) {
    assert.equal(read(path).match(NON_ASCII), null, `${path}: use escapes, keep text in strings.js`);
  }
});
