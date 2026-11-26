// Tests for the pure parts of site/js/common.js and site/js/data.js: the URL fragment,
// the script switch, search folding and the paths of the data bundles. No DOM is needed;
// the few functions that read the page set up a stand-in document for one test.

import test from "node:test";
import assert from "node:assert/strict";
import {
  esc, fold, formatHash, pageHref, parseHash, resolveScript, searchKey, t, twinPath,
} from "../../site/js/common.js";
import {
  DataError, bankOf, currentScript, dataBase, dataUrl, loadGrade, loadIndex, loadOutcomes,
  mergeGrades, resetDataCache, resolveAlias,
} from "../../site/js/data.js";

// ----- the fragment -------------------------------------------------------------------

test("parseHash reads the documented example", () => {
  assert.deepEqual(parseHash("#mat-sabiranje-do-20&pismo=cir"), { topic: "mat-sabiranje-do-20", script: "cyr" });
});

test("formatHash is the inverse of parseHash", () => {
  const hashes = [
    "#mat-sabiranje-do-20&pismo=cir",
    "#mat-brojevi-do-10",
    "#razred=5",
    "#razred=5&sve=1",
    "#razred=2&jedinica=Brojevi%20i%20merenje&pismo=lat",
    "#razred=3&oblast=geometry",
    "#mat-poredjenje-do-100&rezultat=v1.abc_-123&pismo=cir",
    "#pismo=cir",
  ];
  for (const hash of hashes) {
    const params = parseHash(hash);
    assert.equal(formatHash(params), hash, hash);
    assert.deepEqual(parseHash(formatHash(params)), params, hash);
  }
});

test("parseHash maps the Serbian parameter names", () => {
  assert.deepEqual(parseHash("#razred=5"), { grade: 5 });
  assert.deepEqual(parseHash("#razred=5&sve=1"), { grade: 5, all: true });
  assert.deepEqual(parseHash("#razred=2&jedinica=Brojevi%20i%20algebra"), { grade: 2, unit: "Brojevi i algebra" });
  assert.deepEqual(parseHash("#oblast=geometry"), { area: "geometry" });
  assert.deepEqual(parseHash("#rezultat=v1.abc"), { result: "v1.abc" });
  assert.deepEqual(parseHash("#pismo=lat"), { script: "lat" });
  assert.deepEqual(parseHash("#pismo=cyr"), { script: "cyr" });
  assert.deepEqual(parseHash("#razred=2&razred=3"), { grade: 3 }, "the last value wins");
});

test("a value that happens to be a property name is no script", () => {
  for (const value of ["constructor", "__proto__", "toString", "hasOwnProperty", "valueOf"]) {
    assert.deepEqual(parseHash(`#pismo=${value}`), {}, value);
    assert.deepEqual(resolveScript("lat", `#pismo=${value}`, {}), { script: "lat", redirect: false, adopt: false }, value);
  }
  assert.deepEqual(parseHash("#pismo=constructor&pismo=cir"), { script: "cyr" }, "the last usable value wins");
  assert.equal(formatHash({ script: "constructor" }), "");
});

test("parseHash ignores what it cannot use", () => {
  for (const junk of ["", "#", undefined, null, "#%zz&razred=pet&pismo=abc&jedinica=&rezultat=", "#razred=0", "#razred=-1", "#razred=2.5"]) {
    assert.deepEqual(parseHash(junk), {}, String(junk));
  }
  assert.deepEqual(parseHash("#Tema"), {}, "ids are lowercase");
});

test("formatHash orders the parts and escapes values", () => {
  assert.equal(formatHash({}), "");
  assert.equal(formatHash({ topic: "mat-brojevi-do-10" }), "#mat-brojevi-do-10");
  assert.equal(
    formatHash({
      script: "cyr", result: "v1.a", area: "numbers", unit: "Brojevi i merenje", all: true, grade: 4, topic: "mat-x",
    }),
    "#mat-x&razred=4&sve=1&jedinica=Brojevi%20i%20merenje&oblast=numbers&rezultat=v1.a&pismo=cir",
  );
  assert.equal(formatHash({ topic: "not an id!" }), "", "junk is dropped");
  assert.equal(formatHash({ grade: "5" }), "", "a grade is an integer");
  assert.equal(formatHash({ script: "klingon" }), "");
});

// ----- the script switch ----------------------------------------------------------------

test("resolveScript follows the fragment, then the stored choice, then the page", () => {
  assert.deepEqual(resolveScript("lat", "", {}), { script: "lat", redirect: false, adopt: false });
  assert.deepEqual(resolveScript("cyr", "", {}), { script: "cyr", redirect: false, adopt: false });
  // no pismo in the fragment: a different stored choice moves to the other tree
  assert.deepEqual(resolveScript("lat", "#mat-brojevi-do-10", { script: "cyr" }), { script: "cyr", redirect: true, adopt: false });
  assert.deepEqual(resolveScript("cyr", "", { script: "lat" }), { script: "lat", redirect: true, adopt: false });
  assert.deepEqual(resolveScript("lat", "#mat-brojevi-do-10", { script: "lat" }), { script: "lat", redirect: false, adopt: false });
  // pismo in the fragment wins over the stored choice and becomes the new choice
  assert.deepEqual(resolveScript("cyr", "#pismo=cir", {}), { script: "cyr", redirect: false, adopt: true });
  assert.deepEqual(resolveScript("cyr", "#pismo=cir", { script: "cyr" }), { script: "cyr", redirect: false, adopt: false });
  assert.deepEqual(resolveScript("cyr", "#pismo=lat", { script: "cyr" }), { script: "lat", redirect: true, adopt: true });
  assert.deepEqual(resolveScript("lat", "#pismo=cir", {}), { script: "cyr", redirect: true, adopt: true });
});

test("twinPath finds the same page in the other tree", () => {
  assert.equal(twinPath("/zg/mapa/", "/zg/", "cyr"), "/zg/cir/mapa/");
  assert.equal(twinPath("/zg/", "/zg/", "cyr"), "/zg/cir/");
  assert.equal(twinPath("/zg/mapa/index.html", "/zg/", "cyr"), "/zg/cir/mapa/index.html");
  assert.equal(twinPath("/zg/cir/mapa/", "/zg/cir/", "lat"), "/zg/mapa/");
  assert.equal(twinPath("/zg/cir/", "/zg/cir/", "lat"), "/zg/");
  assert.equal(twinPath("/mapa/", "/", "cyr"), "/cir/mapa/");
  assert.equal(twinPath("/cir/mapa/", "/cir/", "lat"), "/mapa/");
  // asked for the tree the page is already in: the page itself
  assert.equal(twinPath("/zg/mapa/", "/zg/", "lat"), "/zg/mapa/");
  assert.equal(twinPath("/zg/cir/mapa/", "/zg/cir/", "cyr"), "/zg/cir/mapa/");
  // a page outside the declared tree root cannot be mirrored
  assert.equal(twinPath("/elsewhere/", "/cir/", "lat"), null);
});

// ----- search ---------------------------------------------------------------------------

test("fold lowercases, strips diacritics and unifies the scripts", () => {
  assert.equal(fold("Množenje"), "mnozenje");
  assert.equal(fold("Č, Ć, Š, Ž, Đ, č, ć, š, ž, đ"), "c, c, s, z, dj, c, c, s, z, dj");
  assert.equal(fold("\u041c\u043d\u043e\u0436\u0435\u045a\u0435"), "mnozenje", "Множење");
  assert.equal(fold("\u0409\u0443\u0431\u0438\u0446\u0430"), "ljubica", "Љубица");
  assert.equal(fold("\u040a\u0435\u043c\u0430"), "njema", "Њема");
  assert.equal(fold("\u045f\u0430\u0431\u0443\u043a\u0430"), "dzabuka", "џабука");
  assert.equal(fold("\u0402\u0430\u043a"), "djak", "Ђак");
  assert.equal(fold("Poređenje brojeva do 100"), "poredjenje brojeva do 100");
  assert.equal(fold("  a   b "), "a b");
  assert.equal(fold(undefined), "");
});

test("searchKey matches across the scripts and ignores punctuation", () => {
  assert.equal(searchKey("Deljenje"), searchKey("\u0414\u0459\u0435\u045a\u0435"), "Дљење");
  assert.equal(searchKey("mat-sabiranje-do-20"), searchKey("mat sabiranje do 20"));
  assert.equal(searchKey("Njuška"), searchKey("\u040a\u0443\u0448\u043a\u0430"), "Њушка");
  assert.notEqual(searchKey("sabiranje"), searchKey("oduzimanje"));
});

// ----- text ----------------------------------------------------------------------------

test("t fills placeholders and shows a missing key by its name", () => {
  assert.equal(t("site.name"), "Znanjograf");
  assert.equal(t("common.grade.n", { n: 3 }), "3. razred");
  assert.equal(t("common.grade.n", {}), "${n}. razred", "an unknown placeholder is left alone");
  assert.equal(t("common.grade.n"), "${n}. razred");
  assert.equal(t("diag.result.scope", { scope: "<b>x</b>" }), "Proveravano: <b>x</b>", "the value goes in as it is; the caller escapes it");
  assert.equal(t("missing.key"), "missing.key");
  assert.equal(esc(`<a href="x">&'`), "&lt;a href=&quot;x&quot;&gt;&amp;&#39;");
});

// ----- paths ----------------------------------------------------------------------------

test("pageHref is relative to the depth of the current page", () => {
  assert.equal(pageHref("mapa/"), "mapa/");
  globalThis.document = {
    baseURI: "https://example.org/mapa/",
    body: { dataset: { pismo: "cyr", podaci: "../podaci/" } },
  };
  try {
    assert.equal(currentScript(), "cyr");
    assert.equal(dataBase(), "../podaci/");
    assert.equal(pageHref("mapa/"), "../mapa/");
    assert.equal(dataUrl("index.cyr.json"), "https://example.org/podaci/index.cyr.json");
  } finally {
    delete globalThis.document;
  }
  assert.equal(currentScript(), "lat");
  assert.equal(dataBase(), "podaci/");
  assert.equal(dataUrl("ishodi/g1-2026.lat.json"), "podaci/ishodi/g1-2026.lat.json");
});

// ----- the bundles ----------------------------------------------------------------------

const ok = (url) => ({ ok: true, status: 200, json: async () => ({ url }) });

async function withFetch(reply, run) {
  const saved = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (url) => {
    calls.push(String(url));
    return reply(url);
  };
  resetDataCache();
  try {
    await run(calls);
  } finally {
    if (saved === undefined) delete globalThis.fetch;
    else globalThis.fetch = saved;
    resetDataCache();
  }
}

test("loaders ask for the bundle of the requested script under podaci/", async () => {
  await withFetch(ok, async (calls) => {
    const index = await loadIndex("cyr");
    assert.equal(index.url, "podaci/index.cyr.json");
    await loadGrade(3, "lat");
    await loadOutcomes("g1-2026", "lat");
    assert.deepEqual(calls, ["podaci/index.cyr.json", "podaci/g3.lat.json", "podaci/ishodi/g1-2026.lat.json"]);
    await loadIndex("cyr");
    assert.equal(calls.length, 3, "a bundle is fetched once per page");
  });
});

test("a bundle that cannot be loaded rejects with DataError", async () => {
  await withFetch(() => ({ ok: false, status: 404, json: async () => ({}) }), async () => {
    await assert.rejects(loadGrade(9, "lat"), (error) => error instanceof DataError && error.url === "podaci/g9.lat.json" && error.status === 404);
  });
  await withFetch(() => {
    throw new TypeError("offline");
  }, async () => {
    await assert.rejects(loadIndex("lat"), DataError);
  });
  await withFetch(() => ({ ok: true, status: 200, json: async () => {
    throw new SyntaxError("not json");
  } }), async () => {
    await assert.rejects(loadIndex("lat"), DataError);
  });
});

test("loaders refuse names that are not bundle names", async () => {
  await withFetch(ok, async (calls) => {
    await assert.rejects(loadGrade("../x", "lat"), DataError);
    await assert.rejects(loadGrade(1, "cyr/../lat"), DataError);
    await assert.rejects(loadOutcomes("g1-2026/../../etc", "lat"), DataError);
    assert.deepEqual(calls, []);
  });
});

test("resolveAlias expands an alias and passes ids through", () => {
  const index = { aliases: { "mat-brojevi": ["mat-brojevi-do-10"], "mat-old": ["mat-a", "mat-b"], "mat-chain": ["mat-brojevi"] } };
  assert.deepEqual(resolveAlias(index, "mat-brojevi"), ["mat-brojevi-do-10"]);
  assert.deepEqual(resolveAlias(index, "mat-sabiranje-do-20"), ["mat-sabiranje-do-20"]);
  assert.deepEqual(resolveAlias(index, "mat-nikad-postojao"), ["mat-nikad-postojao"]);
  assert.deepEqual(resolveAlias(index, "mat-old"), ["mat-a", "mat-b"]);
  assert.deepEqual(resolveAlias(index, "mat-chain"), ["mat-brojevi-do-10"], "a chain (forbidden by V11) still ends somewhere");
  assert.deepEqual(resolveAlias({}, "mat-brojevi"), ["mat-brojevi"]);
  assert.deepEqual(resolveAlias(null, undefined), []);
});

test("mergeGrades and bankOf rebuild the question records the engine expects", () => {
  const g1 = {
    topics: { "mat-brojevi-do-10": { summary: "a" } },
    questions: {
      "mat-brojevi-do-10-q1": { type: "numeric", level: "basic", prompt: "x", answerRational: ["7", "1"] },
      "mat-sabiranje-do-10-q1": { type: "numeric", level: "basic" },
    },
  };
  const g2 = {
    topics: { "mat-zadaci-sa-sabiranjem": { summary: "b" } },
    questions: { "mat-zadaci-sa-sabiranjem-q3": { type: "choice", level: "standard", choices: [{ id: "a", text: "x" }] } },
  };
  const merged = mergeGrades([g1, g2]);
  assert.deepEqual(Object.keys(merged.topics), ["mat-brojevi-do-10", "mat-zadaci-sa-sabiranjem"]);
  const bank = bankOf(merged);
  assert.deepEqual(Object.keys(bank), ["mat-brojevi-do-10", "mat-sabiranje-do-10", "mat-zadaci-sa-sabiranjem"]);
  assert.equal(bank["mat-brojevi-do-10"][0].id, "mat-brojevi-do-10-q1");
  assert.equal(bank["mat-brojevi-do-10"][0].topic, "mat-brojevi-do-10");
  assert.deepEqual(bank["mat-zadaci-sa-sabiranjem"][0].choices, [{ id: "a", text: "x" }]);
  const later = mergeGrades([g1, { topics: { "mat-brojevi-do-10": { summary: "later" } }, questions: {} }]);
  assert.equal(later.topics["mat-brojevi-do-10"].summary, "a", "the first bundle wins");
});
