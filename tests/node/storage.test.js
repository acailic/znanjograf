// Tests for site/js/storage.js: nothing here needs a DOM, only a storage object in place of
// window.localStorage. The spec (10.5) asks for exactly three keys and for every write to be
// wrapped so that a private window or a blocked origin cannot break the page.

import test from "node:test";
import assert from "node:assert/strict";
import {
  KEYS, clearAll, clearSession, getPrefs, loadHistory, loadSession, pushHistory, saveSession, setPrefs,
} from "../../site/js/storage.js";

function memoryStorage() {
  const data = new Map();
  return {
    getItem: (key) => (data.has(key) ? data.get(key) : null),
    setItem: (key, value) => data.set(key, String(value)),
    removeItem: (key) => data.delete(key),
    dump: () => Object.fromEntries(data),
  };
}

const boom = () => {
  throw new Error("QuotaExceededError");
};

function useStorage(value) {
  Object.defineProperty(globalThis, "localStorage", { value, configurable: true, writable: true });
}

useStorage(undefined);

test("the keys are the ones the spec names", () => {
  assert.deepEqual(KEYS, { session: "zg.session.v1", history: "zg.history.v1", prefs: "zg.prefs.v1" });
  assert.ok(Object.isFrozen(KEYS));
});

test("a storage that throws on everything (private mode) still gives the defaults", () => {
  useStorage({ getItem: boom, setItem: boom, removeItem: boom });
  assert.equal(loadSession(), null);
  assert.deepEqual(loadHistory(), {});
  assert.deepEqual(getPrefs(), {});
  assert.equal(saveSession({ scope: { kind: "topic", id: "mat-brojevi-do-10" }, log: [] }), false);
  assert.doesNotThrow(() => setPrefs({ script: "cyr" }));
  assert.doesNotThrow(() => pushHistory(["mat-brojevi-do-10-q1"]));
  assert.doesNotThrow(clearSession);
  assert.doesNotThrow(clearAll);
  assert.equal(loadSession(), null);
  assert.deepEqual(loadHistory(), {});
  assert.deepEqual(getPrefs(), {});
});

test("reading the storage property itself may throw (blocked origin)", () => {
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    get() {
      throw new Error("SecurityError");
    },
  });
  assert.equal(loadSession(), null);
  assert.deepEqual(getPrefs(), {});
  assert.doesNotThrow(() => saveSession({ scope: {}, log: [] }));
  assert.doesNotThrow(clearAll);
});

test("no storage at all gives the defaults", () => {
  useStorage(undefined);
  assert.equal(loadSession(), null);
  assert.deepEqual(loadHistory(), {});
  assert.deepEqual(getPrefs(), {});
});

test("a session round-trips and is returned as a fresh copy", () => {
  const storage = memoryStorage();
  useStorage(storage);
  const session = { v: 1, scope: { kind: "topic", id: "mat-sabiranje-do-20" }, log: [{ questionId: "mat-sabiranje-do-20-q3", correct: false }], extensions: 0 };
  assert.equal(saveSession(session), true);
  assert.deepEqual(JSON.parse(storage.getItem(KEYS.session)), session);
  const loaded = loadSession();
  assert.deepEqual(loaded, session);
  loaded.log.push({ questionId: "x", correct: true });
  assert.equal(loadSession().log.length, 1, "the caller cannot change what is stored");
  saveSession(null);
  assert.equal(loadSession(), null);
  assert.equal(storage.getItem(KEYS.session), null);
});

test("a stored session that is not a session is ignored", () => {
  const storage = memoryStorage();
  useStorage(storage);
  for (const bad of ["{not json", "null", "42", '"text"', "[]", "{}", '{"log":[]}', '{"scope":{"kind":"topic","id":"a"},"log":"x"}']) {
    storage.setItem(KEYS.session, bad);
    assert.equal(loadSession(), null, bad);
  }
  storage.setItem(KEYS.session, JSON.stringify({ scope: { kind: "topic", id: "a" }, log: [] }));
  assert.deepEqual(loadSession(), { scope: { kind: "topic", id: "a" }, log: [] });
});

test("setPrefs merges into what is stored", () => {
  const storage = memoryStorage();
  useStorage(storage);
  assert.deepEqual(getPrefs(), {});
  setPrefs({ script: "cyr" });
  assert.deepEqual(getPrefs(), { script: "cyr" });
  setPrefs({ other: 1 });
  assert.deepEqual(getPrefs(), { script: "cyr", other: 1 });
  setPrefs({ script: "lat" });
  assert.deepEqual(getPrefs(), { script: "lat", other: 1 });
  storage.setItem(KEYS.prefs, "{broken");
  assert.deepEqual(getPrefs(), {});
});

test("pushHistory counts every question it is given", () => {
  useStorage(memoryStorage());
  pushHistory(["mat-a-q1", "mat-a-q2", "mat-a-q1"]);
  assert.deepEqual(loadHistory(), { "mat-a-q1": 2, "mat-a-q2": 1 });
  pushHistory(["mat-a-q2"]);
  assert.deepEqual(loadHistory(), { "mat-a-q1": 2, "mat-a-q2": 2 });
  pushHistory([]);
  pushHistory("mat-a-q1");
  assert.deepEqual(loadHistory(), { "mat-a-q1": 2, "mat-a-q2": 2 }, "only arrays of strings count");
});

test("clearAll removes our three keys and nothing else", () => {
  const storage = memoryStorage();
  useStorage(storage);
  saveSession({ scope: { kind: "grade", grade: 1 }, log: [] });
  setPrefs({ script: "cyr" });
  pushHistory(["mat-a-q1"]);
  storage.setItem("someone-else", "kept");
  assert.deepEqual(Object.keys(storage.dump()).sort(), ["someone-else", KEYS.history, KEYS.prefs, KEYS.session]);
  clearAll();
  assert.deepEqual(storage.dump(), { "someone-else": "kept" });
  assert.equal(loadSession(), null);
  assert.deepEqual(loadHistory(), {});
  assert.deepEqual(getPrefs(), {});
});

test("clearSession ends the session but keeps the rotation history and the script choice", () => {
  const storage = memoryStorage();
  useStorage(storage);
  saveSession({ scope: { kind: "grade", grade: 1 }, log: [] });
  setPrefs({ script: "cyr" });
  pushHistory(["mat-a-q1"]);
  clearSession();
  assert.equal(loadSession(), null);
  assert.deepEqual(loadHistory(), { "mat-a-q1": 1 });
  assert.deepEqual(getPrefs(), { script: "cyr" });
});
