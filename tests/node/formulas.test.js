// Spec §6.1: CI parses every formula of the data with the vendored KaTeX; a broken one fails the build.
import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";

const require = createRequire(import.meta.url);
const katex = require("../../site/vendor/katex/katex.min.js");
const ROOT = new URL("../../", import.meta.url).pathname;
const UNITS = new Set(["mm", "cm", "dm", "km", "m", "kg", "g", "mg", "t", "l", "ml", "dl", "h", "min", "s"]);
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

const UNIT_IN_TEXT = /\\text\{([^{}]*)\}/g;

test("every formula of the data parses with the vendored KaTeX", () => {
  const problems = [];
  let count = 0;
  for (const [file, key, tex] of formulas()) {
    count += 1;
    for (const unit of tex.matchAll(UNIT_IN_TEXT)) {
      if (!UNITS.has(unit[1].trim())) problems.push(`${file} ${key}: \\text{${unit[1]}} is not a unit symbol`);
    }
    try {
      katex.renderToString(tex, { throwOnError: true, output: "htmlAndMathml" });
    } catch (error) {
      problems.push(`${file} ${key}: $${tex}$: ${error.message.split("\n")[0]}`);
    }
  }
  assert.deepEqual(problems, []);
  assert.ok(count > 10, `only ${count} formulas were checked`);
});
