// site/js/common.js - what every page shares: the header, the script switch, messages to
// the reader, and the helpers around the URL fragment.
//
// Importing the module touches no DOM. Only initCommon, setScript, announce, focusHeading,
// go and replaceHash read or change the page, and each checks that there is one.

import { DataError, currentScript, dataBase } from "./data.js";
import { clearAll, getPrefs, setPrefs } from "./storage.js";
import { strings } from "./strings.js";

const hasDom = () => typeof document !== "undefined" && !!document.body;
const hasLocation = () => typeof location !== "undefined";

// ----- text --------------------------------------------------------------------------------

/** Replaces {name} in a template with the value of that name; unknown names are left alone. */
function fill(template, params) {
  if (!params) return template;
  return template.replace(/\{([a-z][A-Za-z0-9]*)\}/g, (name) => {
    const key = name.slice(1, -1);
    return key in params ? String(params[key]) : name;
  });
}

/** A sentence from strings.js. The result is plain text: escape it before it goes into HTML. */
export function t(key, params) {
  const template = strings[key];
  return typeof template === "string" ? fill(template, params) : String(key);
}

/** Escapes text for HTML, attributes included. */
export function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
}

// Serbian alphabet order. Written as escapes so that this file stays ASCII.
const CYRILLIC = "\u0430\u0431\u0432\u0433\u0434\u0452\u0435\u0436\u0437\u0438\u0458\u043a\u043b\u0459\u043c\u043d\u045a\u043e\u043f\u0440\u0441\u0442\u045b\u0443\u0444\u0445\u0446\u0447\u045f\u0448";
const LATIN = ["a", "b", "v", "g", "d", "\u0111", "e", "\u017e", "z", "i", "j", "k", "l", "lj", "m", "n", "nj", "o", "p", "r", "s", "t", "\u0107", "u", "f", "h", "c", "\u010d", "d\u017e", "\u0161"];
const TO_LATIN = new Map([...CYRILLIC].map((letter, position) => [letter, LATIN[position]]));
const DIACRITIC = /[\u0111\u017e\u0161\u010d\u0107]/g;
const WITHOUT_DIACRITIC = { "\u0111": "dj", "\u017e": "z", "\u0161": "s", "\u010d": "c", "\u0107": "c" };

/** Lowercase ASCII, without diacritics, the same for both scripts. */
export function fold(text) {
  const latin = Array.from(String(text ?? "").toLowerCase(), (ch) => TO_LATIN.get(ch) ?? ch).join("");
  return latin.replace(DIACRITIC, (ch) => WITHOUT_DIACRITIC[ch]).replace(/\s+/g, " ").trim();
}

/**
 * A key for searching. On top of fold() it drops punctuation and the vowel that Latin
 * writes before lj and nj and Cyrillic leaves out (Latin "deljenje" is d + lj + e + nj + e
 * in Cyrillic), so that a query typed in either script finds names written in either.
 */
export function searchKey(text) {
  return fold(text).replace(/[ei](?=lj|nj)/g, "").replace(/[^a-z0-9]+/g, " ").trim();
}

// ----- the fragment -------------------------------------------------------------------------

// Internal name -> name in the fragment. A topic id stands alone, without a name.
const TOPIC_ID = /^[a-z][a-z0-9]*(?:-[a-z0-9]+)+$/;
const GRADE = /^[1-9]\d?$/;
const SCRIPTS = { lat: "lat", cir: "cyr", cyr: "cyr" };

/**
 * "#mat-sabiranje-do-20&pismo=cir" -> { topic: "mat-sabiranje-do-20", script: "cyr" }.
 * Names: razred (grade), sve (all), jedinica (unit), oblast (area), rezultat (result),
 * pismo (script). Whatever cannot be used is ignored.
 */
export function parseHash(hash) {
  const params = {};
  const text = String(hash ?? "").replace(/^#/, "");
  for (const rawPart of text.split("&")) {
    if (!rawPart) continue;
    let part = rawPart;
    try {
      part = decodeURIComponent(rawPart.replace(/\+/g, " "));
    } catch {
      continue;
    }
    const eq = part.indexOf("=");
    if (eq === -1) {
      if (TOPIC_ID.test(part) && params.topic === undefined) params.topic = part;
      continue;
    }
    const name = part.slice(0, eq);
    const value = part.slice(eq + 1);
    if (name === "razred" && GRADE.test(value)) params.grade = Number(value);
    else if (name === "sve" && (value === "1" || value === "")) params.all = true;
    else if (name === "jedinica" && value) params.unit = value;
    else if (name === "oblast" && value) params.area = value;
    else if (name === "rezultat" && value) params.result = value;
    else if (name === "pismo" && value in SCRIPTS) params.script = SCRIPTS[value];
  }
  return params;
}

/** The inverse of parseHash: the topic first, then the named parameters in a fixed order. */
export function formatHash(params = {}) {
  const parts = [];
  if (typeof params.topic === "string" && TOPIC_ID.test(params.topic)) parts.push(params.topic);
  if (Number.isInteger(params.grade) && params.grade >= 1) parts.push(`razred=${params.grade}`);
  if (params.all) parts.push("sve=1");
  if (params.unit) parts.push(`jedinica=${encodeURIComponent(params.unit)}`);
  if (params.area) parts.push(`oblast=${encodeURIComponent(params.area)}`);
  if (params.result) parts.push(`rezultat=${encodeURIComponent(params.result)}`);
  if (params.script === "lat" || params.script === "cyr") parts.push(`pismo=${params.script === "cyr" ? "cir" : "lat"}`);
  return parts.length > 0 ? `#${parts.join("&")}` : "";
}

/**
 * Decides which tree the reader should be in. The fragment wins; without it the stored
 * choice of script; without that the page itself. `redirect` is true when that is the other
 * tree, `adopt` when the fragment names a script different from the stored one.
 */
export function resolveScript(page, hash, prefs) {
  const here = page === "cyr" ? "cyr" : "lat";
  const wanted = parseHash(hash).script;
  const stored = prefs && (prefs.script === "cyr" || prefs.script === "lat") ? prefs.script : null;
  const script = wanted || stored || here;
  return { script, redirect: script !== here, adopt: wanted === script && wanted !== stored };
}

/**
 * The path of the same page in the tree written in `target`. `rootPath` is the folder of the
 * tree the page is in now ("" for the Latin tree, ".../cir/" for the mirror). Null when the
 * page is not under that root.
 */
export function twinPath(pagePath, rootPath, target) {
  const page = String(pagePath ?? "");
  const root = String(rootPath ?? "/");
  const want = target === "cyr" ? "cyr" : "lat";
  if (!page.startsWith(root)) return null;
  const inside = page.slice(root.length);
  const mirror = /\/cir\/$/.test(root);
  if (want === "cyr") return mirror ? page : `${root.endsWith("/") ? root : `${root}/`}cir/${inside}`;
  return mirror ? root.replace(/cir\/$/, "") + inside : page;
}

// ----- links -------------------------------------------------------------------------------

/** The path from this page to `path` in the same tree: "../mapa/" from a subpage, "mapa/" from the root. */
export function pageHref(path = "") {
  return /^\.\.[/\\]/.test(dataBase()) ? `../${path}` : path;
}

/** The folder of the tree the page is in, taken from where the page says the bundles are. */
function treeRoot() {
  try {
    return new URL("../", new URL(dataBase(), document.baseURI)).pathname;
  } catch {
    return null;
  }
}

/** The same parameters plus the script the fragment already names, so links keep it. */
export function withScript(params) {
  return { ...params, script: parseHash(hasDom() ? location.hash : "").script };
}

/** A link to a page of this tree, with parameters in the fragment. */
export function hrefTo(path, params = {}) {
  return pageHref(path) + formatHash(withScript(params));
}

/** Shows the parameters in the fragment as a history entry; the page then hears "hashchange". */
export function go(params) {
  if (!hasDom()) return;
  const hash = formatHash(withScript(params));
  if (hash === "") {
    history.pushState(null, "", location.pathname + location.search);
    window.dispatchEvent(typeof HashChangeEvent === "function" ? new HashChangeEvent("hashchange") : new Event("hashchange"));
  } else {
    location.hash = hash;
  }
}

/** Shows the parameters in the fragment without adding a history entry. */
export function replaceHash(params) {
  if (!hasDom()) return;
  history.replaceState(null, "", location.pathname + location.search + formatHash(withScript(params)));
}

/** Moves to the same page in the other tree, keeping the fragment, and remembers the choice. */
export function setScript(script) {
  const target = script === "cyr" ? "cyr" : "lat";
  setPrefs({ script: target });
  if (!hasDom()) return false;
  const path = twinPath(location.pathname, treeRoot(), target);
  if (path === null) return false;
  const hash = formatHash({ ...parseHash(location.hash), script: target });
  location.href = location.origin === "null" ? path + hash : location.origin + path + hash;
  return true;
}

// ----- the page ------------------------------------------------------------------------------

function announceRegion() {
  let region = document.getElementById("zg-live");
  if (!region) {
    region = document.createElement("div");
    region.id = "zg-live";
    region.className = "zg-visually-hidden";
    region.setAttribute("role", "status");
    region.setAttribute("aria-live", "polite");
    document.body.append(region);
  }
  return region;
}

/** Says something to a screen reader without moving the focus. */
export function announce(message) {
  if (!hasDom()) return;
  const region = announceRegion();
  region.textContent = "";
  setTimeout(() => {
    region.textContent = message;
  }, 40);
}

/** Puts the focus on the heading of the new screen (the element marked data-zg-focus, or the first h1). */
export function focusHeading(root) {
  if (!hasDom() || !root) return;
  const target = root.querySelector("[data-zg-focus]") || root.querySelector("h1");
  if (!target) return;
  target.setAttribute("tabindex", "-1");
  try {
    target.focus({ preventScroll: false });
  } catch {
    target.focus();
  }
}

const NAV = [
  ["map", "mapa/", "nav.map"],
  ["diagnose", "dijagnostika/", "nav.diagnose"],
  ["about", "o-projektu/", "nav.about"],
];

function headerMarkup(script, pageId) {
  const home = pageHref("") || "./";
  const toCyr = script !== "cyr";
  const items = NAV.map(([id, path, key]) => {
    const current = id === pageId ? ' aria-current="page"' : "";
    return `<a href="${esc(hrefTo(path))}"${current}>${esc(t(key))}</a>`;
  });
  return `<div class="zg-wrap zg-header-row">
    <a class="zg-brand" href="${esc(home)}">${esc(t("site.name"))}</a>
    <div class="zg-tools">
      <button type="button" class="zg-btn zg-btn-quiet" data-zg-script aria-label="${esc(t(toCyr ? "script.toCyr" : "script.toLat"))}">${esc(t(toCyr ? "script.cyr" : "script.lat"))}</button>
      <button type="button" class="zg-btn zg-btn-quiet" data-zg-clear>${esc(t("common.clear"))}</button>
    </div>
  </div>
  <nav class="zg-nav" aria-label="${esc(t("nav.label"))}"><div class="zg-wrap zg-nav-row">${items.join("")}</div></nav>`;
}

function onClear() {
  if (typeof window.confirm === "function" && !window.confirm(t("common.clear.confirm"))) return;
  clearAll();
  announce(t("common.clear.done"));
  window.dispatchEvent(new Event("zg:cleared"));
}

function buildChrome(script, pageId) {
  const body = document.body;
  let main = document.getElementById("zg-main");
  if (!main) {
    main = document.createElement("main");
    main.id = "zg-main";
    main.className = "zg-main";
    body.append(main);
  }
  main.setAttribute("tabindex", "-1");
  let skip = document.getElementById("zg-skip");
  if (!skip) {
    skip = document.createElement("a");
    skip.id = "zg-skip";
    skip.href = "#zg-main";
    body.prepend(skip);
  }
  skip.className = "zg-skip";
  skip.textContent = t("common.skip");
  let header = document.getElementById("zg-header");
  if (!header) {
    header = document.createElement("header");
    header.id = "zg-header";
    body.insertBefore(header, skip.nextSibling);
  }
  header.className = "zg-header";
  header.innerHTML = headerMarkup(script, pageId);
  header.querySelector("[data-zg-script]").addEventListener("click", () => setScript(script === "cyr" ? "lat" : "cyr"));
  header.querySelector("[data-zg-clear]").addEventListener("click", onClear);
}

/**
 * Prepares a page: the script (moving once to the other tree when the fragment or the stored
 * choice asks for it), then the header. Returns { script, page } once the page is ready, or
 * null when the browser is on its way to the other tree: then the page must draw nothing.
 */
export function initCommon() {
  if (!hasDom()) return null;
  const page = currentScript();
  document.documentElement.lang = page === "cyr" ? "sr-Cyrl" : "sr-Latn";
  const plan = resolveScript(page, hasLocation() ? location.hash : "", getPrefs());
  if (plan.redirect && hasLocation()) {
    const path = twinPath(location.pathname, treeRoot(), plan.script);
    if (path !== null) {
      const hash = parseHash(location.hash).script ? location.hash : formatHash({ ...parseHash(location.hash), script: plan.script });
      location.replace(location.origin === "null" ? path + hash : location.origin + path + hash);
      return null;
    }
  }
  if (plan.adopt) setPrefs({ script: plan.script });
  buildChrome(page, document.body.dataset.page || "");
  return { script: page, page: document.body.dataset.page || "" };
}

/** Says that the data is on its way while a page waits for its bundles. */
export function renderLoading(container) {
  if (!container) return;
  container.innerHTML = `<p class="zg-note zg-muted" role="status">${esc(t("common.loading"))}</p>`;
}

/** What a page shows when its bundles cannot be read. */
export function renderError(container, error) {
  if (!container) return;
  console.error(error);
  const data = error instanceof DataError;
  container.innerHTML = `<div class="zg-wrap zg-narrow">
    <h1 class="zg-title" data-zg-focus>${esc(t("common.error.title"))}</h1>
    <p class="zg-note zg-note-bad" role="alert">${esc(t(data ? "common.error.data" : "common.error.generic"))}</p>
    <button type="button" class="zg-btn zg-btn-primary" data-zg-retry>${esc(t("common.retry"))}</button>
  </div>`;
  container.querySelector("[data-zg-retry]").addEventListener("click", () => location.reload());
  focusHeading(container);
}
