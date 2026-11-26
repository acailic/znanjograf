// site/js/data.js - reads the bundles the build writes under podaci/ (plan C9):
//
//   index.{lat|cyr}.json       topics, edges, aliases, units, counts
//   g{N}.{lat|cyr}.json        { topics: { id: { summary, mastery, curriculum, review } },
//                                questions: { questionId: { level, type, prompt, ... } } }
//   ishodi/{edition}.{lat|cyr}.json   outcomes of one curriculum edition
//
// Nothing here touches the DOM at import time; the page is read only when a function runs.

const DEFAULT_BASE = "podaci/";
const cache = new Map();

/** A bundle that could not be read. `url` says which one, `status` the HTTP status if any. */
export class DataError extends Error {
  constructor(url, reason, status = null, cause = undefined) {
    super(`ZG_DATA ${reason}: ${url}`);
    this.name = "DataError";
    this.url = url;
    this.reason = reason;
    this.status = status;
    if (cause !== undefined) this.cause = cause;
  }
}

// ----- where the page is -----------------------------------------------------------------

/** "lat" or "cyr", from <body data-pismo>. */
export function currentScript() {
  const value = typeof document !== "undefined" && document.body && document.body.dataset ? document.body.dataset.pismo : "";
  return value === "cyr" ? "cyr" : "lat";
}

/** The bundle folder as the page declares it in <body data-podaci>. */
export function dataBase() {
  const value = typeof document !== "undefined" && document.body && document.body.dataset ? document.body.dataset.podaci : "";
  return typeof value === "string" && value ? value : DEFAULT_BASE;
}

/** The absolute URL of a bundle file, given relative to the bundle folder. */
export function dataUrl(file) {
  const base = dataBase().replace(/\/+$/, "") + "/";
  let resolved = base;
  if (typeof document !== "undefined" && document.baseURI) {
    try {
      resolved = new URL(base, document.baseURI).href;
    } catch {
      resolved = base;
    }
  }
  return resolved + file;
}

// ----- loading ---------------------------------------------------------------------------

function ofScript(script) {
  if (script !== "lat" && script !== "cyr") throw new DataError(String(script), "script");
  return script;
}

function loadBundle(file) {
  const url = dataUrl(file);
  if (!cache.has(url)) {
    const pending = fetchJson(url).catch((error) => {
      cache.delete(url);
      throw error;
    });
    cache.set(url, pending);
  }
  return cache.get(url);
}

async function fetchJson(url) {
  let response;
  try {
    response = await fetch(url);
  } catch (cause) {
    throw new DataError(url, "network", null, cause);
  }
  if (!response || !response.ok) throw new DataError(url, "http", response ? response.status : null);
  try {
    return await response.json();
  } catch (cause) {
    throw new DataError(url, "json", response.status, cause);
  }
}

/** Forgets every bundle, so that the next load asks the network again. */
export function resetDataCache() {
  cache.clear();
}

/** { subject, name, grades, areas, topics, edges, aliases, units, counts } */
export async function loadIndex(script) {
  return loadBundle(`index.${ofScript(script)}.json`);
}

/** One grade bundle. */
export async function loadGrade(grade, script) {
  ofScript(script);
  if (!Number.isInteger(grade) || grade < 1) throw new DataError(String(grade), "grade");
  return loadBundle(`g${grade}.${script}.json`);
}

/** The grade bundles for the given grades, in ascending order. */
export async function loadGrades(grades, script) {
  const wanted = [...new Set(grades)].filter((grade) => Number.isInteger(grade) && grade >= 1).sort((a, b) => a - b);
  return Promise.all(wanted.map((grade) => loadGrade(grade, script)));
}

/** { edition, grade, applies_from, themes, outcomes: [{ id, text, page, ... }] } */
export async function loadOutcomes(edition, script) {
  ofScript(script);
  if (!/^g[1-8]-\d{4}$/.test(String(edition))) throw new DataError(String(edition), "edition");
  return loadBundle(`ishodi/${edition}.${script}.json`);
}

/** The outcome record with that id, wherever the edition file keeps it. */
export function findOutcome(outcomesData, id) {
  if (!outcomesData || typeof outcomesData !== "object") return null;
  if (Array.isArray(outcomesData)) return outcomesData.find((outcome) => outcome && outcome.id === id) || null;
  if (Array.isArray(outcomesData.outcomes)) return outcomesData.outcomes.find((outcome) => outcome && outcome.id === id) || null;
  return isRecord(outcomesData[id]) ? outcomesData[id] : null;
}

const isRecord = (value) => value !== null && typeof value === "object" && !Array.isArray(value);

// ----- shapes the pages and the engine need ------------------------------------------------

/**
 * The ids a name in a link stands for today. An old id (see data/aliases.json) opens onto
 * the topics it was merged or split into; anything else is an id and stands for itself.
 */
export function resolveAlias(index, id) {
  const aliases = index && isRecord(index.aliases) ? index.aliases : {};
  const seen = new Set();
  const expand = (name) => {
    const targets = Array.isArray(aliases[name]) ? aliases[name] : [];
    if (targets.length === 0 || seen.has(name)) return [name];
    seen.add(name);
    const out = [];
    for (const target of targets) {
      for (const hit of expand(target)) {
        if (!out.includes(hit)) out.push(hit);
      }
    }
    return out.length > 0 ? out : [name];
  };
  if (id === null || id === undefined) return [];
  return expand(String(id));
}

/** Many grade bundles as one { topics, questions }; the first bundle wins on an id. */
export function mergeGrades(bundles) {
  const topics = {};
  const questions = {};
  for (const bundle of Array.isArray(bundles) ? bundles : [bundles]) {
    if (!isRecord(bundle)) continue;
    for (const [id, topic] of Object.entries(isRecord(bundle.topics) ? bundle.topics : {})) {
      if (!(id in topics)) topics[id] = topic;
    }
    for (const [id, question] of Object.entries(isRecord(bundle.questions) ? bundle.questions : {})) {
      if (!(id in questions)) questions[id] = question;
    }
  }
  return { topics, questions };
}

/** The bundle stores questions by id; the id ends in the topic id: `<topic id>-q<n>`. */
export function topicOfQuestion(questionId) {
  return String(questionId).replace(/-q\d+$/, "");
}

/**
 * The question bank the engine takes: { topicId: [question, ...] } in file order, each
 * question carrying the `id` and `topic` the bundle leaves out.
 */
export function bankOf(gradeData) {
  const bank = {};
  const questions = isRecord(gradeData) && isRecord(gradeData.questions) ? gradeData.questions : {};
  for (const [id, question] of Object.entries(questions)) {
    const topic = topicOfQuestion(id);
    (bank[topic] ||= []).push({ ...question, id, topic });
  }
  return bank;
}
