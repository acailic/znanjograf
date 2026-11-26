// rational.js — exact rational numbers, and a typed answer turned into one.
//
// parseRat(text) mirrors `parse_answer` in zg/mathcheck.py line for line; the
// shared vectors in tests/fixtures/answer-vectors.json hold both to the same
// cases. Everything is BigInt, so no value is ever rounded.

function gcd(a, b) {
  let x = a < 0n ? -a : a;
  let y = b < 0n ? -b : b;
  while (y !== 0n) {
    [x, y] = [y, x % y];
  }
  return x;
}

/**
 * The rational num/den as {n, d}, reduced, with d > 0.
 * Throws RangeError when den is zero.
 */
export function rat(num, den) {
  const n = BigInt(num);
  const d = BigInt(den);
  if (d === 0n) throw new RangeError("ZG_ZERO_DENOMINATOR: the denominator of a rational is zero");

  const divisor = gcd(n, d);
  return d < 0n ? { n: -n / divisor, d: -d / divisor } : { n: n / divisor, d: d / divisor };
}

const MAX_LENGTH = 100; // the longest text that can still be one answer
const DIGITS = /^[0-9]+$/;
// Plain digits, or a first group of one to three digits and then groups of
// three, separated by single spaces: 7, 1234567, 1 000, 12 345 678.
const NATURAL = /^(?:[0-9]{1,3}(?: [0-9]{3})*|[0-9]+)$/;

// What Python's str.strip() removes. It is not quite JavaScript's trim():
// Python also strips U+001C-U+001F and U+0085, and never the byte-order mark.
const PY_WHITESPACE = "[\\u0009-\\u000D\\u001C-\\u0020\\u0085\\u00A0\\u1680\\u2000-\\u200A\\u2028\\u2029\\u202F\\u205F\\u3000]";
const LEADING_WHITESPACE = new RegExp(`^${PY_WHITESPACE}+`);
const TRAILING_WHITESPACE = new RegExp(`${PY_WHITESPACE}+$`);

/** `text` without the whitespace at both ends, exactly as Python strips it. */
function strip(text) {
  return text.replace(LEADING_WHITESPACE, "").replace(TRAILING_WHITESPACE, "");
}

/** `text` split at its first `separator`, as Python's str.partition. */
function partition(text, separator) {
  const at = text.indexOf(separator);
  return at === -1 ? [text, "", ""] : [text.slice(0, at), separator, text.slice(at + 1)];
}

/** `text` split at its last `separator`, as Python's str.rpartition. */
function rpartition(text, separator) {
  const at = text.lastIndexOf(separator);
  return at === -1 ? ["", "", text] : [text.slice(0, at), separator, text.slice(at + 1)];
}

/** A natural number, possibly with space-separated thousands. */
function natural(text) {
  return NATURAL.test(text) ? rat(BigInt(text.replace(/ /g, "")), 1n) : null;
}

/** whole + numerator/denominator, where `whole` is what `natural` returned. */
function addFraction(whole, numerator, denominator) {
  return rat(whole.n * denominator + numerator * whole.d, whole.d * denominator);
}

/** The number without its sign, or null when the text is not exactly one number. */
function parseUnsigned(body) {
  if (body.length === 0 || body.length > MAX_LENGTH) return null;

  if (body.includes("/")) {
    // A fraction, possibly mixed: 3/4, 2 3/4.
    const [head, , denominatorText] = partition(body, "/");
    const [integerText, space, rest] = rpartition(head, " ");
    const hasWhole = space !== "";
    const numeratorText = hasWhole ? rest : head;
    if (!DIGITS.test(numeratorText) || !DIGITS.test(denominatorText)) return null;

    const whole = hasWhole && integerText !== "" ? natural(integerText) : rat(0n, 1n);
    const denominator = BigInt(denominatorText);
    if (whole === null || denominator === 0n) return null;
    return addFraction(whole, BigInt(numeratorText), denominator);
  }

  let wholeText = body;
  let decimals = "";
  if (!body.includes(",")) {
    const dot = body.lastIndexOf(".");
    if (dot !== -1 && body.length - dot === 4) {
      // A dot and exactly three digits at the end: 1.000 is a thousand.
      return body.split(".").length > 2 ? null : natural(body.replace(".", " "));
    }
    [wholeText, , decimals] = partition(body, ".");
    if (decimals.includes(".")) return null; // a second decimal point
  } else {
    // A comma is always a decimal separator.
    [wholeText, , decimals] = partition(body, ",");
    if (decimals.includes(",")) return null; // a second decimal comma
  }

  if (decimals === "") return natural(body);
  if (!DIGITS.test(decimals)) return null;
  const whole = natural(wholeText);
  if (whole === null) return null;

  const scale = 10n ** BigInt(decimals.length);
  return addFraction(whole, BigInt(decimals), scale);
}

/**
 * Parse a typed answer: "15", "3,5", "3.5", "3/4", "2 3/4", "-7", "1 000",
 * "1.000". Returns {n, d} or null for anything else.
 */
export function parseRat(text) {
  if (typeof text !== "string") return null;

  const stripped = strip(text);
  const signed = stripped.startsWith("+") || stripped.startsWith("-");
  const body = signed ? stripped.slice(1) : stripped;

  const value = parseUnsigned(body);
  if (value === null) return null;
  return stripped.startsWith("-") ? { n: -value.n, d: value.d } : value;
}
