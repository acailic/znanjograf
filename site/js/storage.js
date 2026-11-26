// site/js/storage.js - session, question rotation and preferences in window.localStorage.
//
// Every call is wrapped: in a private window, or on an origin where storage is blocked,
// localStorage throws, and the site has to keep working without it (spec 10.5). Nothing
// here touches the DOM at import time.

export const KEYS = Object.freeze({
  session: "zg.session.v1",
  history: "zg.history.v1",
  prefs: "zg.prefs.v1",
});

const isRecord = (value) => value !== null && typeof value === "object" && !Array.isArray(value);

/** The storage object, or null when there is none or reading it is not allowed. */
function backend() {
  try {
    const store = globalThis.localStorage;
    return store && typeof store.getItem === "function" ? store : null;
  } catch {
    return null;
  }
}

function readJson(key) {
  const store = backend();
  if (!store) return null;
  try {
    const text = store.getItem(key);
    return typeof text === "string" ? JSON.parse(text) : null;
  } catch {
    return null;
  }
}

function writeJson(key, value) {
  const store = backend();
  if (!store) return false;
  try {
    store.setItem(key, JSON.stringify(value));
    return true;
  } catch {
    return false;
  }
}

function remove(key) {
  const store = backend();
  if (!store) return;
  try {
    store.removeItem(key);
  } catch {
    // Nothing stored, or removing is not allowed: either way there is nothing to do.
  }
}

function isSession(value) {
  return isRecord(value)
    && isRecord(value.scope)
    && typeof value.scope.kind === "string"
    && Array.isArray(value.log)
    && value.log.every((entry) => isRecord(entry) && typeof entry.questionId === "string" && typeof entry.correct === "boolean");
}

/** The saved session ({ scope, log, ... }), or null. Never throws. */
export function loadSession() {
  const value = readJson(KEYS.session);
  return isSession(value) ? value : null;
}

/** Keeps the session; null or undefined ends it. Returns false when nothing could be written. */
export function saveSession(session) {
  if (session === null || session === undefined) {
    remove(KEYS.session);
    return true;
  }
  return writeJson(KEYS.session, session);
}

/** Ends the session and leaves the rotation history and the script choice alone. */
export function clearSession() {
  remove(KEYS.session);
}

/** Forgets everything the site stored: session, rotation history and preferences. */
export function clearAll() {
  for (const key of Object.values(KEYS)) remove(key);
}

/** The preferences as a plain object; {} when there are none. */
export function getPrefs() {
  const value = readJson(KEYS.prefs);
  return isRecord(value) ? { ...value } : {};
}

/** Merges `prefs` into the stored preferences. */
export function setPrefs(prefs) {
  if (!isRecord(prefs)) return false;
  return writeJson(KEYS.prefs, { ...getPrefs(), ...prefs });
}

/** { questionId: times it was shown } */
export function loadHistory() {
  const value = readJson(KEYS.history);
  if (!isRecord(value)) return {};
  const history = {};
  for (const [id, count] of Object.entries(value)) {
    if (typeof count === "number" && Number.isFinite(count) && count > 0) history[id] = Math.floor(count);
  }
  return history;
}

/** Counts the given questions as shown once, so that later sessions rotate them away. */
export function pushHistory(questionIds) {
  if (!Array.isArray(questionIds)) return false;
  const history = loadHistory();
  let counted = false;
  for (const id of questionIds) {
    if (typeof id !== "string" || !id) continue;
    history[id] = (history[id] || 0) + 1;
    counted = true;
  }
  return counted ? writeJson(KEYS.history, history) : false;
}
