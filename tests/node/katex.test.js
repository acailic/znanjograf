// Tests for site/js/katex.js: the KaTeX wrapper and its raw-LaTeX fallback.
import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

// KaTeX is a UMD bundle. In Node it is loaded with require and put where the
// wrapper looks for it, exactly as a <script> tag would define window.katex.
globalThis.katex = createRequire(import.meta.url)("../../site/vendor/katex/katex.min.js");
const { texToHtml, renderInto } = await import("../../site/js/katex.js");

const FALLBACK = /<code class="zg-tex-raw">[\s\S]*<\/code>/;

test("a valid formula is rendered by KaTeX with MathML for screen readers", () => {
  const html = texToHtml("3{,}5+\\frac{1}{2}");
  assert.match(html, /class="katex"/);
  assert.match(html, /<math[\s>]/);
  assert.match(html, /<mfrac>/);
  assert.doesNotMatch(html, FALLBACK);
});

test("\\text{…} is accepted only for unit symbols", () => {
  for (const tex of [
    "5\\text{ cm}",
    "60\\,\\text{km/h}",
    "12\\,\\text{m/s}",
    "\\text{kg}",
    "\\text {ml}",
    "3\\text{h}",
    "25\\,\\text{cl}",
    "3\\text{ hl}",
    "\\text{ha}",
    "150\\text{ din}",
    "6\\text{a}",
  ]) {
    assert.match(texToHtml(tex), /class="katex"/, tex);
  }
});

test("\\text{…} with anything but a unit falls back to raw TeX", () => {
  for (const tex of ["\\text{abc}", "\\text{}", "\\text{Mila ima}", "\\text{°C}", "\\text a", "x\\text{metara}"]) {
    assert.match(texToHtml(tex), FALLBACK, tex);
  }
});

test("a formula KaTeX cannot parse falls back to raw TeX", () => {
  assert.match(texToHtml("\\unknowncmd"), FALLBACK);
  assert.match(texToHtml("\\frac{1}"), FALLBACK);
  assert.match(texToHtml("x^"), FALLBACK);
});

test("the fallback keeps the TeX visible and HTML-escaped", () => {
  const html = texToHtml("\\text{a<b&c}");
  assert.match(html, /^<code class="zg-tex-raw">/);
  assert.match(html, /\\text\{a&lt;b&amp;c\}<\/code>$/);
  assert.doesNotMatch(html, /<b&/);
});

test("only the \\text command is inspected, not letters that follow a line break or a comment", () => {
  // "\\\\text{abc}" is a line break followed by the variables t,e,x,t; the
  // comment is dropped by KaTeX and shows nothing.
  assert.match(texToHtml("\\\\text{abc}"), /class="katex"/);
  assert.match(texToHtml("x % \\text{abc}\n"), /class="katex"/);
});

test("texToHtml falls back when KaTeX is not loaded or the input is not a string", () => {
  const saved = globalThis.katex;
  try {
    delete globalThis.katex;
    assert.match(texToHtml("1+1"), FALLBACK);
  } finally {
    globalThis.katex = saved;
  }
  assert.match(texToHtml(undefined), FALLBACK);
});

test("renderInto puts the markup into the element", () => {
  const el = { innerHTML: "" };
  renderInto(el, "7 \\cdot 8");
  assert.match(el.innerHTML, /class="katex"/);
  renderInto(el, "\\text{abc}");
  assert.match(el.innerHTML, FALLBACK);
});
