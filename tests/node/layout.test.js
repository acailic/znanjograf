// Tests for site/js/layout.js and site/js/graph-view.js: the topic map is laid
// out in longest-path columns and grade bands, and drawn as hand-made SVG.
import test from "node:test";
import assert from "node:assert/strict";

const { layout } = await import("../../site/js/layout.js");
const { toSvg, mount } = await import("../../site/js/graph-view.js");

const node = (id, grade, name) => ({ id, grade, name });
const edge = (topic, requires, strength = "hard") => [topic, requires, strength];

test("x is the longest-path layer: one column per edge of the longest chain", () => {
  // d requires b and c; b and c require a; so d is two edges from a, c one past b.
  const { nodes } = layout({
    nodes: [node("a", 1, "A"), node("b", 1, "B"), node("c", 2, "C"), node("d", 2, "D")],
    edges: [edge("b", "a"), edge("c", "a"), edge("d", "b"), edge("d", "c")],
  });
  const x = Object.fromEntries(nodes.map((n) => [n.id, n.x]));
  assert.ok(x.a < x.b && x.b < x.d && x.a < x.c && x.c < x.d);
  assert.equal(x.b, x.c);
});

test("nodes of one grade in one layer stack in rows without overlapping", () => {
  const { nodes, width, height } = layout({ nodes: [node("a", 1, "A"), node("b", 1, "B"), node("c", 1, "C")], edges: [] });
  assert.equal(new Set(nodes.map((n) => n.x)).size, 1);
  assert.equal(new Set(nodes.map((n) => n.y)).size, 3);
  assertNoOverlap(nodes);
  assertInside(nodes, width, height);
});

test("y is a grade band: lower grades sit above higher ones and never interleave", () => {
  const { nodes } = layout({
    nodes: [node("a1", 1, "A"), node("a2", 1, "B"), node("b1", 2, "C"), node("b2", 2, "D"), node("c1", 3, "E"), node("b3", 2, "F"), node("a3", 1, "G")],
    edges: [edge("b1", "a2"), edge("b2", "a2"), edge("c1", "b1"), edge("b3", "b1")],
  });
  assert.deepEqual(nodes.map((n) => n.id), ["a1", "a2", "b1", "b2", "c1", "b3", "a3"]); // learning order is kept
  for (const n of nodes) assert.equal(n.band, n.id[0] === "a" ? 1 : n.id[0] === "b" ? 2 : 3);
  assertBandsOrdered(nodes);
  assertNoOverlap(nodes);
});

test("a band has as many rows as its widest cell needs", () => {
  const { nodes } = layout({
    nodes: [node("r1", 1, "R1"), node("r2", 1, "R2"), node("r3", 1, "R3"), node("r4", 1, "R4"), node("x", 2, "X"), node("y", 2, "Y")],
    edges: [edge("x", "r1"), edge("y", "r2")],
  });
  const first = nodes.find((n) => n.id === "x").y;
  const last = nodes.find((n) => n.id === "r4");
  assert.ok(first >= last.y + last.h, "the next band starts below the fourth row");
});

test("more than eight nodes in a cell collapse the overflow into one +N node", () => {
  const nodes = Array.from({ length: 10 }, (_, i) => node(`mat-a${i}`, 1, `Tema ${i}`));
  const { nodes: placed } = layout({ nodes, edges: [] });
  assert.equal(placed.filter((n) => n.id.startsWith("mat-")).length, 7);
  assert.deepEqual(placed.filter((n) => n.id.startsWith("+")).map((n) => [n.id, n.label, n.band]), [["+3@1", "+3", 1]]);
  assert.equal(new Set(placed.map((n) => n.y)).size, 8); // eight rows, never more
  assertNoOverlap(placed);
});

test("every overflowing cell of a band shares one +N node", () => {
  const nodes = [...Array.from({ length: 9 }, (_, i) => node(`mat-root${i}`, 1, `Koren ${i}`)), ...Array.from({ length: 9 }, (_, i) => node(`mat-leaf${i}`, 1, `List ${i}`))];
  const edges = nodes.filter((n) => n.id.includes("leaf")).map((n) => edge(n.id, "mat-root0"));
  const { nodes: placed } = layout({ nodes, edges });
  const extra = placed.filter((n) => n.id.startsWith("+"));
  assert.deepEqual(extra.map((n) => [n.id, n.label]), [["+4@1", "+4"]]); // 2 hidden roots + 2 hidden leaves
  assert.equal(placed.filter((n) => n.id.startsWith("mat-")).length, 14);
  assertNoOverlap(placed);
});

test("the focused node is never collapsed and the focus is echoed", () => {
  const nodes = Array.from({ length: 10 }, (_, i) => node(`mat-a${i}`, 1, `Tema ${i}`));
  const result = layout({ nodes, edges: [], focus: "mat-a9" });
  assert.equal(result.focus, "mat-a9");
  assert.ok(result.nodes.some((n) => n.id === "mat-a9"));
  assert.deepEqual(result.nodes.filter((n) => n.id.startsWith("+")).map((n) => n.id), ["+3@1"]);
});

test("labels longer than 18 characters are ellipsised and kept in full", () => {
  const name = "Sabiranje i oduzimanje brojeva do sto";
  const { nodes } = layout({ nodes: [node("long", 1, name), node("s", 1, "S")], edges: [edge("s", "long")] });
  const long = nodes.find((n) => n.id === "long");
  assert.equal(long.label, name);
  assert.equal(Array.from(long.text).length, 18);
  assert.ok(long.text.endsWith("…"));
  assert.ok(long.w > nodes.find((n) => n.id === "s").w);
  assertNoOverlap(nodes);
});

test("a 40-node layered graph has no overlapping nodes and every edge goes left to right", () => {
  const { nodes, edges, width, height } = layout(layeredGraph(40));
  assert.equal(nodes.length, 40);
  assert.ok(edges.length > 40);
  assertNoOverlap(nodes);
  assertInside(nodes, width, height);
  assertBandsOrdered(nodes);
  for (const e of edges) {
    const xs = e.points.map((p) => p[0]);
    assert.ok(xs.every((x, i) => i === 0 || xs[i - 1] <= x), `${e.from}→${e.to}: x never decreases`);
    assert.ok(xs.at(-1) - xs[0] > 0, `${e.from}→${e.to}: ends to the right of where it starts`);
  }
});

test("an edge leaves the right border of its source and enters the left border of its target", () => {
  const { nodes, edges } = layout({
    nodes: [node("a", 1, "A"), node("b", 2, "B")],
    edges: [edge("b", "a")],
  });
  const [a, b] = nodes;
  assert.deepEqual(edges[0].points[0], [a.x + a.w, a.y + a.h / 2]);
  assert.deepEqual(edges[0].points.at(-1), [b.x, b.y + b.h / 2]);
  assert.ok(a.x + a.w < b.x);
});

test("an edge turns only in the gap after its column, even under a wider node", () => {
  // The wide node makes column 0 wide; the short source "a" sits beneath it.
  const { nodes, edges } = layout({
    nodes: [node("wide", 1, "Sabiranje i oduzimanje do sto"), node("a", 1, "A"), node("b", 1, "B")],
    edges: [edge("b", "a")],
  });
  const [wide, a, b] = nodes;
  assert.ok(a.y > wide.y && b.y === wide.y, "a is in the row under the wide node, b beside the wide node");
  assert.equal(edges[0].points.length, 4);
  const turn = edges[0].points[1][0];
  assert.ok(wide.x + wide.w < turn && turn < b.x, "the vertical part lies in the gap between the columns");
  assertEdgesClear(edges, nodes);
});

test("an edge that skips columns runs between two rows and crosses no node", () => {
  // d requires a, three columns back, and c, so it sits in the column of e, in the row under it.
  const { nodes, edges } = layout({
    nodes: [node("a", 1, "A"), node("b", 1, "B"), node("c", 1, "C"), node("e", 1, "E"), node("d", 1, "D")],
    edges: [edge("b", "a"), edge("c", "b"), edge("e", "c"), edge("d", "a"), edge("d", "c")],
  });
  const byId = Object.fromEntries(nodes.map((n) => [n.id, n]));
  assert.ok(byId.a.x < byId.b.x && byId.b.x < byId.c.x && byId.c.x < byId.d.x, "a, b, c, d are in four columns");
  assert.equal(byId.e.x, byId.d.x);
  assert.ok(byId.d.y > byId.e.y, "d is in the row under e");
  const skipping = edges.find((e) => e.from === "a" && e.to === "d");
  assert.equal(skipping.points.length, 6);
  assertEdgesClear(edges, nodes);
});

test("random layered graphs keep every invariant", () => {
  let seed = 7; // fixed, so a failure can be replayed
  const random = () => (seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff;
  for (let run = 0; run < 150; run += 1) {
    const input = { nodes: [], edges: [] };
    const count = 1 + Math.floor(random() * 40);
    for (let i = 0; i < count; i += 1) {
      input.nodes.push(node(`mat-n${i}`, 1 + Math.floor(random() * (random() < 0.3 ? 1 : 3)), `Tema ${i}`.padEnd(5 + Math.floor(random() * 26), "x")));
      for (let k = Math.floor(random() * 3); k > 0; k -= 1) {
        const j = Math.floor(random() * i);
        if (j < i) input.edges.push(edge(`mat-n${i}`, `mat-n${j}`, random() < 0.3 ? "soft" : "hard"));
      }
    }
    const { nodes, edges, width, height } = layout(input);
    const where = `run ${run}`;

    const extras = nodes.filter((n) => n.id.startsWith("+"));
    const hidden = extras.reduce((sum, n) => sum + Number(n.id.slice(1).split("@")[0]), 0);
    assert.equal(nodes.length - extras.length, count - hidden, `${where}: exactly the collapsed nodes are missing`);
    const visible = nodes.filter((n) => !n.id.startsWith("+"));
    const shown = input.nodes.filter((n) => visible.some((v) => v.id === n.id));
    assert.deepEqual(visible.map((n) => n.id), shown.map((n) => n.id), `${where}: input order`);
    assert.deepEqual(visible.map((n) => n.band), shown.map((n) => n.grade), `${where}: band = grade`);
    assertNoOverlap(nodes);
    assertBandsOrdered(nodes);
    assertInside(nodes, width, height);
    for (const band of new Set(nodes.map((n) => n.band))) {
      assert.ok(new Set(nodes.filter((n) => n.band === band).map((n) => n.y)).size <= 8, `${where}: at most eight rows in band ${band}`);
      assert.ok(extras.filter((n) => n.band === band).length <= 1, `${where}: one +N node per band`);
    }
    for (const e of edges) {
      const xs = e.points.map((p) => p[0]);
      assert.ok(xs.every((x, i) => i === 0 || xs[i - 1] <= x) && xs.at(-1) > xs[0], `${where}: ${e.from}→${e.to} goes left to right`);
    }
    assertEdgesClear(edges, nodes);
  }
});

test("edges accept the bundle triple or an object in either field naming", () => {
  const nodes = [node("a", 1, "A"), node("b", 2, "B"), node("c", 2, "C")];
  const expected = layout({ nodes, edges: [edge("b", "a", "soft"), edge("c", "a")] }).edges;
  const object = layout({ nodes, edges: [{ from: "a", to: "b", strength: "soft" }, { topic: "c", requires: "a", strength: "hard" }] }).edges;
  assert.deepEqual(object, expected);
  assert.deepEqual(expected.map((e) => [e.from, e.to, e.strength]), [["a", "b", "soft"], ["a", "c", "hard"]]);
});

test("edges that cannot be drawn are left out", () => {
  const { edges } = layout({
    nodes: [node("a", 1, "A"), node("b", 2, "B")],
    edges: [edge("b", "a"), edge("b", "ghost"), edge("ghost", "a"), edge("a", "a")],
  });
  assert.deepEqual(edges.map((e) => [e.from, e.to]), [["a", "b"]]);
});

test("a cyclic graph still lays out without an edge pointing left", () => {
  const { nodes, edges } = layout({ nodes: [node("a", 1, "A"), node("b", 1, "B"), node("c", 1, "C")], edges: [edge("b", "a"), edge("c", "b"), edge("a", "c")] });
  assert.equal(nodes.length, 3);
  assertNoOverlap(nodes);
  for (const e of edges) assert.ok(e.points.at(-1)[0] > e.points[0][0]);
});

test("no nodes give an empty layout", () => {
  assert.deepEqual(layout({ nodes: [], edges: [] }), { width: 0, height: 0, nodes: [], edges: [], focus: undefined });
});

/* graph-view */

test("toSvg draws hard edges solid and soft edges with stroke-dasharray", () => {
  const svg = toSvg(layout({ nodes: [node("a", 1, "A"), node("b", 2, "B"), node("c", 2, "C")], edges: [edge("b", "a"), edge("c", "a", "soft")] }), {});
  const polylines = svg.match(/<polyline\b[^>]*>/g);
  assert.equal(polylines.length, 2);
  const byStrength = Object.fromEntries(polylines.map((tag) => [/zg-edge--(hard|soft)/.exec(tag)[1], tag]));
  assert.doesNotMatch(byStrength.hard, /stroke-dasharray/);
  assert.match(byStrength.soft, /stroke-dasharray="[^"]+"/);
  assert.match(svg, /^<svg xmlns="http:\/\/www\.w3\.org\/2000\/svg" [\s\S]*viewBox="0 0 \d+ \d+"/);
});

test("toSvg gives every node its verdict class and a title with its full label", () => {
  const name = "Sabiranje i oduzimanje brojeva do sto";
  const result = layout({ nodes: [node("a", 1, name), node("b", 2, "B"), node("c", 2, "C")], edges: [] });
  const svg = toSvg(result, { a: "mastered", b: "weak", c: "nonsense" });
  const groups = svg.match(/<g class="zg-node[^"]*" data-id="[^"]+">[\s\S]*?<\/g>/g);
  assert.equal(groups.length, 3);
  const group = (id) => groups.find((g) => g.includes(`data-id="${id}"`));
  assert.match(group("a"), /^<g class="zg-node zg-node--mastered" data-id="a"><title>Sabiranje i oduzimanje brojeva do sto<\/title>/);
  assert.match(group("b"), /^<g class="zg-node zg-node--weak" data-id="b">/);
  assert.match(group("c"), /^<g class="zg-node zg-node--untested" data-id="c">/); // an unknown verdict is "not tested"
  assert.ok(group("a").includes(`<text`)); // the ellipsised label is what is shown
  assert.ok(!group("a").includes(`>${name}</text>`));
});

test("the focused node carries zg-node--focus, and only that one", () => {
  const result = layout({ nodes: [node("a", 1, "A"), node("b", 2, "B")], edges: [edge("b", "a")], focus: "b" });
  const svg = toSvg(result, { a: "shaky", b: "inferred" });
  const focused = svg.match(/<g class="[^"]*zg-node--focus[^"]*"[^>]*>/g);
  assert.deepEqual(focused, ['<g class="zg-node zg-node--inferred zg-node--focus" data-id="b">']);
});

test("mount puts the SVG into the container and reports a click on a node", () => {
  const result = layout({ nodes: [node("a", 1, "A"), node("b", 2, "B")], edges: [edge("b", "a", "soft")] });
  const page = fakeContainer();
  const selected = [];
  mount(page.container, result, { a: "weak" }, (id) => selected.push(id));
  assert.equal(page.container.innerHTML, toSvg(result, { a: "weak" }));

  page.click({ closest: (selector) => selector === ".zg-node" && { in: page.svg, dataset: { id: "b" } } });
  page.click({ closest: () => ({ in: page.svg, dataset: { id: "a" } }) });
  page.click({ closest: () => null }); // the background is not a node
  page.click({ closest: () => ({ in: {}, dataset: { id: "elsewhere" } }) }); // nor a node of another graph
  assert.deepEqual(selected, ["b", "a"]);
  assert.deepEqual(Object.keys(page.listeners), ["click"]); // and nothing else is wired up
});

/* fixtures and helpers */

/** `count` topics in grades of ten; each requires its 1st, 4th and 9th predecessor. */
function layeredGraph(count) {
  const nodes = [];
  const edges = [];
  for (let i = 0; i < count; i += 1) {
    nodes.push(node(`mat-t${i}`, 1 + Math.floor(i / 10), `Tema ${i}`));
    for (const back of [1, 4, 9]) {
      if (i - back >= 0) edges.push(edge(`mat-t${i}`, `mat-t${i - back}`, back === 9 ? "soft" : "hard"));
    }
  }
  return { nodes, edges };
}

/** The smallest support mount needs: a container with one <svg> that records its listeners. */
function fakeContainer() {
  const listeners = {};
  const svg = {
    addEventListener: (type, handler) => (listeners[type] = handler),
    contains: (target) => target?.in === svg,
  };
  const container = { innerHTML: "", querySelector: (selector) => (selector === "svg" ? svg : null) };
  return { container, svg, listeners, click: (target) => listeners.click({ target }) };
}

function assertNoOverlap(nodes) {
  for (const a of nodes) {
    for (const b of nodes) {
      if (a !== b) assert.ok(a.x + a.w < b.x || b.x + b.w < a.x || a.y + a.h < b.y || b.y + b.h < a.y, `${a.id} overlaps ${b.id}`);
    }
  }
}

/** A lower band lies entirely above every higher band. */
function assertBandsOrdered(nodes) {
  for (const a of nodes) {
    for (const b of nodes) {
      if (a.band !== b.band) assert.ok(a.band < b.band ? a.y + a.h <= b.y : b.y + b.h <= a.y, `bands ${a.band} and ${b.band} interleave`);
    }
  }
}

function assertInside(nodes, width, height) {
  assert.ok(width > 0 && height > 0);
  for (const n of nodes) {
    assert.ok(n.x >= 0 && n.y >= 0 && n.x + n.w <= width && n.y + n.h <= height, `${n.id} leaves the canvas`);
  }
}

/** No segment of any edge passes through the inside of a node rectangle. */
function assertEdgesClear(edges, nodes) {
  for (const { from, to, points } of edges) {
    for (let i = 1; i < points.length; i += 1) {
      const [[xa, ya], [xb, yb]] = [points[i - 1], points[i]];
      assert.ok(xa === xb || ya === yb, `${from}→${to}: a segment is diagonal`);
      const through = nodes.find((n) =>
        ya === yb
          ? n.y < ya && ya < n.y + n.h && Math.min(xa, xb) < n.x + n.w && n.x < Math.max(xa, xb)
          : n.x < xa && xa < n.x + n.w && Math.min(ya, yb) < n.y + n.h && n.y < Math.max(ya, yb),
      );
      assert.ok(!through, `${from}→${to}: the edge runs through ${through?.id}`);
    }
  }
}
