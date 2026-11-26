// site/js/katex.js - the only place that calls KaTeX.
//
// The vendored KaTeX (`site/vendor/katex/katex.min.js`, loaded by the page as a
// plain script) defines the global `katex`. A formula that KaTeX rejects, or
// that uses `\text{...}` for anything but a unit, comes back as raw TeX inside
// `<code>`, never as an empty element (spec section 6.1).

const OPTIONS = Object.freeze({ throwOnError: true, output: "htmlAndMathml", strict: "warn" });

// Unit symbols allowed inside \text{...} (spec section 6.2), alone or as `km/h`.
// Every plain-letter unit of the curriculum (the list of zg/translit/protect.py); a Python test holds the two together.
const UNIT = "mm|cm|dm|km|m|kg|g|mg|t|l|ml|cl|dl|hl|h|min|s|ha|din|a";
const UNIT_RE = new RegExp(`^(?:${UNIT})(?:/(?:${UNIT}))*$`);

export function texToHtml(tex) {
  try {
    assertUnitsOnly(tex);
    return globalThis.katex.renderToString(tex, OPTIONS);
  } catch {
    return `<code class="zg-tex-raw">${escapeHtml(String(tex))}</code>`;
  }
}

export function renderInto(el, tex) {
  el.innerHTML = texToHtml(tex);
}

/** Throws unless every `\text{...}` group holds unit symbols only. */
function assertUnitsOnly(tex) {
  if (typeof tex !== "string") throw new Error("ZG_TEX");
  let i = 0;
  while (i < tex.length) {
    const ch = tex[i];
    if (ch === "%") {
      // A comment: KaTeX drops the rest of the line, so it shows nothing.
      const end = tex.indexOf("\n", i);
      i = end < 0 ? tex.length : end + 1;
    } else if (ch !== "\\") {
      i += 1;
    } else {
      const word = /^[a-zA-Z]+/.exec(tex.slice(i + 1));
      if (!word) {
        i += 2; // a control symbol such as `\\` or `\,`: the next character is no command name
      } else if (word[0] !== "text") {
        i += 1 + word[0].length;
      } else {
        const open = skipSpace(tex, i + 5);
        // `\text a` (a single letter, no braces) is not a unit group either.
        if (tex[open] !== "{") throw new Error("ZG_TEX");
        const [content, end] = readGroup(tex, open);
        if (!UNIT_RE.test(content.trim())) throw new Error("ZG_TEX");
        i = end;
      }
    }
  }
}

function skipSpace(text, i) {
  while (i < text.length && /\s/.test(text[i])) i += 1;
  return i;
}

/** `open` points at `{`; returns the group's content and the index after its `}`. */
function readGroup(text, open) {
  let depth = 0;
  for (let i = open; i < text.length; i += 1) {
    if (text[i] === "{") depth += 1;
    if (text[i] === "}" && (depth -= 1) === 0) return [text.slice(open + 1, i), i + 1];
  }
  return [text.slice(open + 1), text.length];
}

function escapeHtml(text) {
  return text.replace(/[&<>"]/g, (ch) => `&${{ "&": "amp", "<": "lt", ">": "gt", '"': "quot" }[ch]};`);
}
