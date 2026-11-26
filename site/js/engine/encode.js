// encode.js — a session in a form that fits into the `#` fragment of an address.
//
// The text is "v1." followed by base64url (the URL-safe alphabet, no padding)
// of UTF-8 JSON {"scope", "log"}. It carries nothing but the scope and the log,
// so a shared link reveals only which questions were answered and how.
//
// Only standard web APIs are used (TextEncoder, TextDecoder), so the same code
// runs in the browser and under Node.

const PREFIX = "v1.";
const ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";
const VALUES = new Map([...ALPHABET].map((char, value) => [char, value]));

// The keys of each scope kind, in the order they are written out.
const SCOPE_KEYS = {
  topic: ["kind", "id"],
  unit: ["kind", "grade", "unit"],
  grade: ["kind", "grade"],
  "grade-full": ["kind", "grade"],
};

/** A copy of `scope` with exactly the keys of its kind. */
function pick(scope) {
  const copy = {};
  for (const key of SCOPE_KEYS[scope.kind]) copy[key] = scope[key];
  return copy;
}

function isScope(scope) {
  if (typeof scope !== "object" || scope === null || !Object.hasOwn(SCOPE_KEYS, scope.kind)) return false;
  if (scope.kind === "topic") return typeof scope.id === "string";
  if (!Number.isInteger(scope.grade)) return false;
  return scope.kind !== "unit" || typeof scope.unit === "string";
}

function isLog(log) {
  return (
    Array.isArray(log) &&
    log.every((event) => typeof event === "object" && event !== null && typeof event.questionId === "string" && typeof event.correct === "boolean")
  );
}

/** The session as text for a URL fragment. */
export function encodeSession({ scope, log }) {
  if (!isScope(scope)) throw new TypeError(`ZG_BAD_SCOPE: ${JSON.stringify(scope?.kind)} is not a scope`);
  if (!isLog(log)) throw new TypeError("ZG_BAD_LOG: the log must be a list of {questionId, correct}");

  const payload = { scope: pick(scope), log: log.map((event) => ({ questionId: event.questionId, correct: event.correct })) };
  return PREFIX + encodeBase64Url(new TextEncoder().encode(JSON.stringify(payload)));
}

/** The session a shared text carries, or null when the text is not one. */
export function decodeSession(text) {
  if (typeof text !== "string" || !text.startsWith(PREFIX)) return null;
  const bytes = decodeBase64Url(text.slice(PREFIX.length));
  if (bytes === null) return null;

  let data;
  try {
    data = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
  } catch (error) {
    return null; // not UTF-8, or not JSON
  }
  if (typeof data !== "object" || data === null || !isScope(data.scope) || !isLog(data.log)) return null;

  return {
    scope: pick(data.scope),
    log: data.log.map((event) => ({ questionId: event.questionId, correct: event.correct })),
  };
}

// ----- base64url ----------------------------------------------------------------------

/** Three bytes become four characters; the last group is cut short, without padding. */
function encodeBase64Url(bytes) {
  let text = "";
  for (let i = 0; i < bytes.length; i += 3) {
    const first = bytes[i];
    const hasSecond = i + 1 < bytes.length;
    const hasThird = i + 2 < bytes.length;
    const second = hasSecond ? bytes[i + 1] : 0;
    const third = hasThird ? bytes[i + 2] : 0;

    text += ALPHABET[first >> 2];
    text += ALPHABET[((first & 3) << 4) | (second >> 4)];
    if (hasSecond) text += ALPHABET[((second & 15) << 2) | (third >> 6)];
    if (hasThird) text += ALPHABET[third & 63];
  }
  return text;
}

/** The bytes behind base64url text, or null when a character or the length is wrong. */
function decodeBase64Url(text) {
  if (text.length % 4 === 1) return null;

  const bytes = new Uint8Array(Math.floor((text.length * 3) / 4));
  let at = 0;
  for (let i = 0; i < text.length; i += 4) {
    const values = [];
    for (let j = i; j < Math.min(i + 4, text.length); j += 1) {
      const value = VALUES.get(text[j]);
      if (value === undefined) return null;
      values.push(value);
    }

    bytes[at] = (values[0] << 2) | (values[1] >> 4);
    at += 1;
    if (values.length > 2) {
      bytes[at] = ((values[1] & 15) << 4) | (values[2] >> 2);
      at += 1;
    }
    if (values.length > 3) {
      bytes[at] = ((values[2] & 3) << 6) | values[3];
      at += 1;
    }
  }
  return bytes;
}
