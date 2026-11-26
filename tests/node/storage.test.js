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

// ----- what the page does with a stored session --------------------------------------------

// The decision is pure (it reads neither the DOM nor storage), so it is tested here, next to
// the storage it is about. Importing the page module in Node draws nothing: without a
// document its boot() returns at once.
const { plan } = await import("../../site/js/pages/diagnose.js");

test("a stored session is shown again, resumed or left alone", () => {
  const topic = { kind: "topic", id: "mat-zadaci-sa-sabiranjem" };
  const other = { kind: "topic", id: "mat-brojevi-do-10" };
  const unit = { kind: "unit", grade: 2, unit: "Brojevi" };
  const finished = (scope) => ({ scope, log: [], finished: true });
  const open = (scope) => ({ scope, log: [], finished: false });

  // the fragment names the scope of the stored session
  assert.equal(plan({ saved: finished(topic), wanted: topic }), "show", "a finished session shows its result again");
  assert.equal(plan({ saved: open(topic), wanted: topic }), "resume", "an unfinished session goes on where it stopped");

  // the fragment names another scope
  assert.equal(plan({ saved: finished(topic), wanted: other }), "start");
  assert.equal(plan({ saved: open(topic), wanted: other }), "start");
  assert.equal(plan({ saved: finished(unit), wanted: { kind: "grade", grade: 2 } }), "start");

  // the fragment names no scope: the stored session is what the page is about
  assert.equal(plan({ saved: finished(topic), wanted: null }), "show");
  assert.equal(plan({ saved: open(topic) }), "resume");

  // the same unit written in the other script is the same scope (Brojevi)
  assert.equal(plan({ saved: finished(unit), wanted: { kind: "unit", grade: 2, unit: "\u0411\u0440\u043e\u0458\u0435\u0432\u0438" } }), "show");

  // nothing stored, or nothing that is a session
  assert.equal(plan({}), "start");
  assert.equal(plan({ saved: null, wanted: topic }), "start");
  assert.equal(plan({ saved: { scope: null, finished: true }, wanted: null }), "start");

  // only an exact true counts as finished
  assert.equal(plan({ saved: { scope: topic, log: [], finished: "yes" }, wanted: topic }), "resume");
});

// ----- bringing a stored log back ------------------------------------------------------------

// The engine replays a log strictly: an event whose question it would not have picked ends
// the replay there. Which question it picks depends on the history of rotation, which is
// not the same on another device, so the page replays under a history of its own making.

test("a stored log comes back whole, even when rotation asked a later question first", async () => {
  const { readFileSync } = await import("node:fs");
  const fixture = JSON.parse(readFileSync(new URL("../fixtures/engine-fixture.json", import.meta.url), "utf8"));
  const { buildIndex } = await import("../../site/js/engine/graph.js");
  const { apply, createSession, extend, next, summarise } = await import("../../site/js/engine/session.js");
  const page = await import("../../site/js/pages/diagnose.js");
  const { replay, replayHistory } = page;
  const graph = buildIndex(fixture.topics, fixture.edges, fixture.aliases);
  const engine = { bank: fixture.questions, curriculum: {} };
  const Q3 = "mat-sabiranje-do-10-q3";
  const Q4 = "mat-sabiranje-do-10-q4";

  // The first logged question gets the lowest counter, the last the highest; other counts stay.
  assert.deepEqual(replayHistory([{ questionId: Q4, correct: true }, { questionId: Q3, correct: true }], { [Q3]: 1 }), { [Q3]: -1, [Q4]: -2 });
  assert.deepEqual(replayHistory([], { [Q3]: 2 }), { [Q3]: 2 });
  assert.deepEqual(replayHistory("not a log"), {});

  // q3 was shown before, so rotation asks q4 first; both answers are right but not strong, so both are asked.
  const snapshot = { [Q3]: 1 };
  const scope = { kind: "topic", id: "mat-sabiranje-do-10" };
  let live = createSession({ scope, index: graph, bank: fixture.questions, budget: 25, history: snapshot });
  for (let step = next(live); step.kind === "question"; step = next(live)) {
    live = apply(live, { questionId: step.question.id, correct: true });
  }
  assert.deepEqual(live.log.map((event) => event.questionId), [Q4, Q3], "the later question was asked first");

  const restored = replay(live.log, scope, engine, snapshot, graph);
  assert.deepEqual(restored.log, live.log, "the log came back in full");
  assert.deepEqual(summarise(restored), summarise(live));
  assert.deepEqual(next(restored), next(live));
});

test("every session of a seeded sweep comes back in full", async () => {
  const { readFileSync } = await import("node:fs");
  const fixture = JSON.parse(readFileSync(new URL("../fixtures/engine-fixture.json", import.meta.url), "utf8"));
  const { buildIndex } = await import("../../site/js/engine/graph.js");
  const { apply, createSession, extend, next, summarise } = await import("../../site/js/engine/session.js");
  const { replay } = await import("../../site/js/pages/diagnose.js");
  const graph = buildIndex(fixture.topics, fixture.edges, fixture.aliases);
  const engine = { bank: fixture.questions, curriculum: {} };
  const everyQuestion = Object.values(fixture.questions).flat();
  const scopes = [
    { kind: "topic", id: "mat-zadaci-sa-sabiranjem" },
    { kind: "unit", grade: 2, unit: "Brojevi" },
    { kind: "grade", grade: 1 },
    { kind: "grade-full", grade: 2 },
  ];

  let seed = 20261126;
  const random = () => (seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0) / 2 ** 32;
  let answers = 0;
  let stopped = 0;
  for (let round = 0; round < 400; round += 1) {
    const history = {};
    for (const question of everyQuestion) {
      if (random() < 0.5) history[question.id] = 1 + Math.floor(random() * 3);
    }
    const scope = scopes[round % scopes.length];
    let live = createSession({ scope, index: graph, bank: fixture.questions, budget: 5, history });
    for (let step = next(live); step.kind !== "done"; step = next(live)) {
      if (step.kind === "paused") {
        if (random() < 0.3) {
          stopped += 1;
          break; // the pupil put it away at the pause
        }
        live = extend(live);
        continue;
      }
      live = apply(live, { questionId: step.question.id, correct: random() < 0.6 });
    }
    const restored = replay(live.log, scope, engine, history, graph);
    assert.equal(restored.log.length, live.log.length, `round ${round}: the log came back in full`);
    assert.deepEqual(summarise(restored), summarise(live), `round ${round}`);
    answers += live.log.length;
  }
  assert.ok(answers > 1000, "the sweep asked enough to mean something");
  assert.ok(stopped > 0, "some sessions were stopped at a pause");
});

// ----- a unit named in the other script, and the count in one block ---------------------------

test("a unit scope is understood whichever script names it", async () => {
  const { scopeHere } = await import("../../site/js/pages/diagnose.js");
  const latin = [{ id: "mat-a", grade: 2, unit: "Brojevi" }, { id: "mat-b", grade: 2, unit: "Geometrija" }];
  const cyrillic = [{ id: "mat-a", grade: 2, unit: "\u0411\u0440\u043e\u0458\u0435\u0432\u0438" }, { id: "mat-b", grade: 2, unit: "\u0413\u0435\u043e\u043c\u0435\u0442\u0440\u0438\u0458\u0430" }]; // Brojevi, Geometrija
  // a session started in Latin, read in Cyrillic, and the other way round
  assert.deepEqual(scopeHere({ kind: "unit", grade: 2, unit: "Brojevi" }, cyrillic), { kind: "unit", grade: 2, unit: "\u0411\u0440\u043e\u0458\u0435\u0432\u0438" });
  assert.deepEqual(scopeHere({ kind: "unit", grade: 2, unit: "\u0411\u0440\u043e\u0458\u0435\u0432\u0438" }, latin), { kind: "unit", grade: 2, unit: "Brojevi" });
  // without diacritics too (Geometrija has none; a folded name still matches)
  assert.deepEqual(scopeHere({ kind: "unit", grade: 2, unit: "geometrija" }, cyrillic).unit, "\u0413\u0435\u043e\u043c\u0435\u0442\u0440\u0438\u0458\u0430");
  // another scope, or a unit nothing matches: as it was
  const topic = { kind: "topic", id: "mat-a" };
  assert.equal(scopeHere(topic, latin), topic);
  const full = { kind: "grade-full", grade: 2 };
  assert.equal(scopeHere(full, latin), full);
  assert.deepEqual(scopeHere({ kind: "unit", grade: 2, unit: "Nema me" }, latin), { kind: "unit", grade: 2, unit: "Nema me" });
  assert.deepEqual(scopeHere({ kind: "unit", grade: 3, unit: "Brojevi" }, latin), { kind: "unit", grade: 3, unit: "Brojevi" }, "the grade must match too");
  assert.equal(scopeHere(null, latin), null);
});

test("the pause counts the block that just ended, not the whole session", async () => {
  const { blockCount } = await import("../../site/js/pages/diagnose.js");
  assert.equal(blockCount(25, 0), 25);
  assert.equal(blockCount(50, 1), 25);
  assert.equal(blockCount(75, 2), 25);
  assert.equal(blockCount(26, 1), 1, "a restored session that went one question past its block");
  assert.equal(blockCount(3, 0), 3);
  assert.equal(blockCount(25), 25, "no extensions given");
  assert.equal(blockCount(10, 2), 0, "never below zero");
});

test("two tabs with one session do not keep waking each other", async () => {
  const { changedSince, sessionFingerprint } = await import("../../site/js/pages/diagnose.js");
  const scope = { kind: "topic", id: "mat-brojevi-do-10" };
  // Tab A answers and stores the session, with the time of the write.
  const stored = { v: 1, scope, log: [{ questionId: "mat-brojevi-do-10-q1", correct: true }], history: {}, extensions: 0, finished: false, updated: 1 };
  // Tab B wakes, draws the session again and would store it once more, a moment later.
  const drawn = { v: 1, scope, log: [{ questionId: "mat-brojevi-do-10-q1", correct: true }], history: {}, extensions: 0, finished: false, updated: 2 };
  assert.equal(sessionFingerprint(stored), sessionFingerprint(drawn), "the same session, whenever it was written");
  assert.equal(changedSince(drawn, stored), false, "so tab B writes nothing, and tab A is not woken again");
  assert.equal(changedSince({ ...drawn, log: [...drawn.log, { questionId: "mat-brojevi-do-10-q2", correct: false }] }, stored), true, "an answer is a change");
  assert.equal(changedSince({ ...drawn, finished: true }, stored), true, "so is the end of the session");
  assert.equal(changedSince({ ...drawn, extensions: 1 }, stored), true);
  assert.equal(changedSince({ ...drawn, scope: { ...scope, id: "other" } }, stored), true);
  assert.equal(changedSince(drawn, null), true, "nothing stored yet");
  assert.equal(changedSince({ ...drawn, v: undefined, history: undefined, extensions: undefined }, stored), true, "a session stored by an older page is brought up to date once");
});
