// Spec §6.1: CI parses every formula of the data with the vendored KaTeX; a broken one fails the build.
import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { texToHtml } from "../../site/js/katex.js";

const require = createRequire(import.meta.url);
const katex = require("../../site/vendor/katex/katex.min.js");
// The wrapper calls the global, exactly as a page's <script> tag defines it.
globalThis.katex = katex;
const OPTIONS = { throwOnError: true, output: "htmlAndMathml" };
const ROOT = new URL("../../", import.meta.url).pathname;
const MATH = /\$([^$]+)\$/g;
const TEXT = new RegExp(`\\$((?:(?!\\$).)+)\\$`, "g");

function jsonFiles(folder) {
  return readdirSync(folder)
    .map((name) => join(folder, name))
    .filter((path) => (statSync(path).isDirectory() ? jsonFiles(path).length > 0 : path.endsWith(".json")))
    .flatMap((path) => (statSync(path).isDirectory() ? jsonFiles(path) : [path]));
}

function* strings(value, key) {
  if (typeof value === "string") {
    if (!["id", "check", "points_to"].includes(key)) yield [key, value];
  } else if (Array.isArray(value)) {
    for (const item of value) yield* strings(item, key);
  } else if (value && typeof value === "object") {
    for (const [name, item] of Object.entries(value)) yield* strings(item, name);
  }
}

function* formulas() {
  const files = [...jsonFiles(join(ROOT, "data")), join(ROOT, "tests/fixtures/engine-fixture.json")].filter((p) => {
    try { statSync(p); return true; } catch { return false; }
  });
  for (const file of files) {
    if (file.endsWith("ledger.json")) continue;
    const parsed = JSON.parse(readFileSync(file, "utf8"));
    for (const [key, text] of strings(parsed, "")) {
      for (const match of text.matchAll(TEXT)) yield [relative(ROOT, file), key, match[1]];
    }
  }
}

test("every formula of the data parses with the vendored KaTeX", () => {
  const problems = [];
  let count = 0;
  for (const [file, key, tex] of formulas()) {
    count += 1;
    try {
      katex.renderToString(tex, OPTIONS);
    } catch (error) {
      problems.push(`${file} ${key}: $${tex}$: ${error.message.split("\n")[0]}`);
    }
    // What the page shows: the wrapper refuses a formula whose \text{…} holds anything but a unit.
    if (texToHtml(tex).includes('class="zg-tex-raw"')) {
      problems.push(`${file} ${key}: $${tex}$ does not render on the site (\\text{…} holds what the wrapper does not take for a unit)`);
    }
  }
  assert.deepEqual(problems, []);
  assert.ok(count > 10, `only ${count} formulas were checked`);
});
