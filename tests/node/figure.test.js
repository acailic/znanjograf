// Tests for site/js/figure.js: renderFigure draws the twelve closed-set figure
// kinds as standalone SVG and rejects everything else with Error("ZG_FIGURE").
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const { FIGURE_KINDS, renderFigure } = await import("../../site/js/figure.js");

// One valid figure per kind, written here; tests/fixtures/figures.json is
// checked too whenever its owner has created it.
const SPECS = {
  numberline: { kind: "numberline", alt: "Brojevna prava od 0 do 10 sa oznakama na 3 i 7.", min: 0, max: 10, marks: [3, 7] },
  fractionbar: { kind: "fractionbar", alt: "Traka podeljena na četiri jednaka dela, tri su obojena.", numerator: 3, denominator: 4 },
  pie: { kind: "pie", alt: "Krug podeljen na pet jednakih delova, dva su obojena.", parts: 5, shaded: 2 },
  dots: { kind: "dots", alt: "Osam tačaka poređanih u dva reda po četiri.", rows: 2, cols: 4 },
  bars: { kind: "bars", alt: "Stubičasti dijagram sa tri stubca visine 3, 5 i 4.", categories: ["ponedeljak", "utorak", "sreda"], values: [3, 5, 4], title: "Prodato kolača" },
  pictogram: { kind: "pictogram", alt: "Piktogram: jabuke 6, kruške 4; jedan znak je jedno voće.", symbol: "●", items: [{ label: "jabuke", count: 6 }, { label: "kruške", count: 4 }] },
  grid: { kind: "grid", alt: "Mreža od tri vrste i četiri kolone; dve ćelije su obojene.", cols: 4, rows: 3, cells: [[0, 1], [2, 3]] },
  polygon: { kind: "polygon", alt: "Pravougaonik sa stranicama od 5 cm i 3 cm.", vertices: [[0, 0], [5, 0], [5, 3], [0, 3]], sides: [{ index: 0, label: "5 cm" }, { index: 1, label: "3 cm" }], labels: [{ text: "A", x: 0, y: 0 }] },
  angle: { kind: "angle", alt: "Ugao od 35 stepeni sa temenom u tački T.", degrees: 35, label: "?" },
  axes: { kind: "axes", alt: "Koordinatni sistem od 0 do 6 sa tačkama A (1, 2) i B (4, 5).", xmin: 0, xmax: 6, ymin: 0, ymax: 6, points: [{ x: 1, y: 2, label: "A" }, { x: 4, y: 5, label: "B" }] },
  clock: { kind: "clock", alt: "Sat čiji je satna kazaljka na 3, a minutna na 12.", hour: 3, minute: 0 },
  table: { kind: "table", alt: "Tabela prodaje po danima: ponedeljak 3, utorak 5.", columns: ["dan", "kolača"], rows: [["ponedeljak", "3"], ["utorak", "5"]] },
};

test("FIGURE_KINDS is the closed set of twelve kinds", () => {
  assert.deepEqual(FIGURE_KINDS, Object.keys(SPECS));
});

for (const [kind, spec] of Object.entries(SPECS)) {
  test(`${kind} renders a standalone SVG described by its alt`, () => {
    const { svg, alt, width, height } = renderFigure(spec);
    assert.equal(alt, spec.alt);
    assert.ok(Number.isInteger(width) && width > 0);
    assert.ok(Number.isInteger(height) && height > 0);
    assert.match(svg, /^<svg xmlns="http:\/\/www\.w3\.org\/2000\/svg"/);
    assert.ok(svg.trimEnd().endsWith("</svg>"));
    assert.match(svg, new RegExp(` role="img" aria-label="${escapeRegExp(escapeXml(spec.alt))}"`));
    assert.match(svg, new RegExp(` viewBox="0 0 ${width} ${height}" width="${width}" height="${height}"`));
    assert.equal(titleOf(svg), spec.alt);
    assertWellFormed(svg);
    assertThemed(svg);
  });
}

test("the shared fixture figures render when the file exists", (t) => {
  const specs = fixtureFigures();
  if (!specs) return t.skip("tests/fixtures/figures.json not created yet");
  assert.equal(specs.length, 12);
  for (const spec of specs) {
    const { svg, alt } = renderFigure(spec);
    assert.equal(titleOf(svg), spec.alt);
    assert.equal(alt, spec.alt);
    assertWellFormed(svg);
  }
});

test("numberline from 0 to 10 has exactly 11 equally spaced ticks", () => {
  const { svg } = renderFigure({ kind: "numberline", alt: "Brojevna prava od 0 do 10.", min: 0, max: 10 });
  const ticks = tags(svg, "line");
  assert.equal(ticks.length, 11); // the axis and its arrows are paths, so every line is a tick
  const xs = ticks.map((tag) => Number(attrs(tag).x1));
  assert.equal(new Set(xs).size, 11);
  const [first, ...rest] = spacings(xs);
  assert.ok(first > 0);
  nearEqual(rest, first);
  const labels = texts(svg);
  for (let n = 0; n <= 10; n += 1) assert.ok(labels.includes(String(n)), `label ${n}`);
});

test("numberline honours step, marks and unit", () => {
  const stepped = renderFigure({ kind: "numberline", alt: "Brojevna prava od 0 do 20 u koracima od 5.", min: 0, max: 20, step: 5 });
  assert.equal(tags(stepped.svg, "line").length, 5);
  const marked = renderFigure({ kind: "numberline", alt: "Brojevna prava u centimetrima sa oznakom na 3.", min: 0, max: 8, marks: [3], unit: "cm" });
  assert.equal(withClass(tags(marked.svg, "circle"), "zg-mark").length, 1);
  assert.ok(texts(marked.svg).includes("cm"));
});

test("a numberline mark stands above its number, over the tick", () => {
  const { svg } = renderFigure({ kind: "numberline", alt: "Iznad broja 7 na brojevnoj pravi stoji oznaka.", min: 0, max: 10, marks: [7] });
  const mark = attrs(withClass(tags(svg, "circle"), "zg-mark")[0]);
  const tick = tags(svg, "line").map(attrs).find((a) => a.x1 === mark.cx); // the tick it belongs to, by x
  assert.ok(tick, "the mark sits over a tick");
  assert.ok(Number(mark.cy) + Number(mark.r) <= Number(tick.y1), "the mark lies above the tick, clear of the line");
});

test("wide numberline labels fit the canvas and keep apart", () => {
  const { svg, width } = renderFigure({ kind: "numberline", alt: "Brojevna prava od 1 000 do 2 000 u koracima od 250.", min: 1000, max: 2000, step: 250 });
  const labels = texts(svg);
  assert.deepEqual(labels, ["1 000", "1 250", "1 500", "1 750", "2 000"]); // space as thousands separator
  const boxes = tags(svg, "text").map((tag, i) => {
    const half = (Array.from(labels[i]).length * 8) / 2; // the module's estimate of a label's width
    const x = Number(attrs(tag).x);
    return [x - half, x + half];
  });
  for (const [left, right] of boxes) assert.ok(left >= 0 && right <= width, `a label spans ${left}…${right} in a canvas of ${width}`);
  for (let i = 1; i < boxes.length; i += 1) assert.ok(boxes[i][0] >= boxes[i - 1][1] + 4, `labels ${labels[i - 1]} and ${labels[i]} touch`);
});

test("negative numbers on a numberline carry a minus sign, not a hyphen", () => {
  const { svg } = renderFigure({ kind: "numberline", alt: "Brojevna prava od minus pet do pet.", min: -5, max: 5 });
  const labels = texts(svg);
  assert.ok(labels.includes("\u22125") && labels.includes("\u22121"), "minus five and minus one");
  assert.ok(!labels.includes("-5"));
});

test("fractionbar divides into exactly the requested number of equal parts", () => {
  const { svg } = renderFigure({ kind: "fractionbar", alt: "Traka podeljena na sedam jednakih delova.", numerator: 7, denominator: 7 });
  const parts = withClass(tags(svg, "rect"), "zg-part");
  assert.equal(parts.length, 7);
  const [width, ...others] = parts.map((tag) => Number(attrs(tag).width));
  assert.ok(width > 0);
  nearEqual(others, width);
  const shaded = renderFigure({ kind: "fractionbar", alt: "Traka podeljena na šest jednakih delova, četiri su obojena.", numerator: 6, denominator: 6, shaded: 4 });
  assert.equal(withClass(tags(shaded.svg, "rect"), "zg-part--shaded").length, 4);
});

test("pie divides into exactly the requested number of equal parts", () => {
  const parts = 5;
  const { svg } = renderFigure({ kind: "pie", alt: "Krug podeljen na pet jednakih delova.", parts, shaded: 1 });
  const slices = withClass(tags(svg, "path"), "zg-slice");
  assert.equal(slices.length, parts);
  assert.equal(withClass(slices, "zg-slice--shaded").length, 1);
  const angles = slices.map((tag) => arcAngles(attrs(tag).d));
  for (let i = 0; i < parts; i += 1) {
    nearEqual([(angles[i][1] - angles[i][0] + 360) % 360], 360 / parts); // every slice spans the same angle
    nearEqual([angles[i][1]], angles[(i + 1) % parts][0]); // and neighbours share an edge
  }
});

test("dots draws count dots in rows and columns", () => {
  const { svg } = renderFigure({ kind: "dots", alt: "Pet tačaka u tri reda po četiri.", rows: 3, cols: 4, count: 5 });
  assert.equal(withClass(tags(svg, "circle"), "zg-dot").length, 5);
  const full = renderFigure({ kind: "dots", alt: "Dvanaest tačaka u tri reda po četiri.", rows: 3, cols: 4 });
  assert.equal(withClass(tags(full.svg, "circle"), "zg-dot").length, 12);
});

test("bars scale to their values and label every category", () => {
  const { svg } = renderFigure(SPECS.bars);
  const heights = withClass(tags(svg, "rect"), "zg-bar").map((tag) => Number(attrs(tag).height));
  assert.equal(heights.length, 3);
  nearEqual(heights.map((h, i) => (h * SPECS.bars.values[0]) / (heights[0] * SPECS.bars.values[i])), 1); // height ∝ value
  const labels = texts(svg);
  for (const text of ["ponedeljak", "utorak", "sreda", "Prodato kolača", "3", "5", "4"]) assert.ok(labels.includes(text), text);
});

test("pictogram draws one symbol per perSymbol items", () => {
  const symbols = (spec) => withClass(tags(renderFigure(spec).svg, "text"), "zg-symbol").length;
  // two symbols for 4 cars and one for 2 buses, plus the symbol of the legend "■ = 2"
  assert.equal(symbols({ kind: "pictogram", alt: "Piktogram: auto 4, autobus 2; jedan znak su dva vozila.", symbol: "■", items: [{ label: "auto", count: 4 }, { label: "autobus", count: 2 }], perSymbol: 2 }), 4);
  // 5 balls are two whole symbols and one clipped to a half, plus the legend
  assert.equal(symbols({ kind: "pictogram", alt: "Piktogram: pet lopti, jedan znak su dve lopte.", symbol: "●", items: [{ label: "lopte", count: 5 }], perSymbol: 2 }), 4);
  assert.equal(symbols(SPECS.pictogram), 10); // perSymbol 1 needs no legend
});

test("grid draws every cell and shades only the listed ones", () => {
  const { svg } = renderFigure(SPECS.grid);
  const cells = withClass(tags(svg, "rect"), "zg-cell");
  assert.equal(cells.length, 12);
  assert.equal(withClass(cells, "zg-cell--shaded").length, 2);
});

test("labels are passed through unchanged in either script and XML-escaped", () => {
  const { svg } = renderFigure({ kind: "table", alt: "Tabela sa ćiriličkim naslovima.", columns: ["Дан", "a & b"], rows: [["понедељак", "<3"]] });
  const labels = texts(svg);
  for (const text of ["Дан", "a & b", "понедељак", "<3"]) assert.ok(labels.includes(text), text);
  assert.ok(!svg.includes("<3>") && !svg.includes("a & b"));
});

test("clock hands point where hour and minute say", () => {
  const { svg } = renderFigure({ kind: "clock", alt: "Sat koji pokazuje tri sata i trideset minuta.", hour: 3, minute: 30 });
  const hand = (name) => {
    const a = attrs(tags(svg, "line").find((tag) => tag.includes(`zg-hand--${name}`)));
    return { from: [Number(a.x1), Number(a.y1)], to: [Number(a.x2), Number(a.y2)] };
  };
  const hour = hand("hour");
  const minute = hand("minute");
  assert.deepEqual(hour.from, minute.from);
  nearEqual([angleOf(hour)], 105, 0.5); // 3:30 → hour hand a bit past 3, minute hand at 6
  nearEqual([angleOf(minute)], 180, 0.5);
  assert.ok(length(hour) < length(minute)); // the hour hand is the shorter one
});

test("a polygon letter naming a vertex is pushed off the corner, outside the shape", () => {
  const triangle = { kind: "polygon", alt: "Pravougli trougao ABC s katetama od 3 cm i 4 cm.", vertices: [[0, 0], [3, 0], [0, 4]], labels: [{ text: "A", x: 0, y: 0 }, { text: "B", x: 3, y: 0 }, { text: "C", x: 0, y: 4 }] };
  const { svg } = renderFigure(triangle);
  const outline = tags(svg, "path")[0].match(/ d="([^"]+)"/)[1];
  const corners = outline.slice(1, outline.indexOf("Z")).split("L").map((pair) => pair.split(" ").map(Number));
  const centre = corners.reduce(([sx, sy], [x, y]) => [sx + x / 3, sy + y / 3], [0, 0]);
  const distance = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]);
  assert.equal(tags(svg, "text").length, 3);
  for (const tag of tags(svg, "text")) {
    const { x, y } = attrs(tag);
    const letter = [Number(x), Number(y) - 5]; // labels are drawn with their centre 5 px above the baseline
    const corner = corners.reduce((best, c) => (distance(c, letter) < distance(best, letter) ? c : best));
    nearEqual([distance(letter, corner)], 15, 3); // beside its own corner, not on it
    assert.ok(distance(letter, centre) > distance(corner, centre), "on the far side of the corner from the shape");
  }
});

test("an angle stays inside its canvas whatever vertex and degrees are asked for", () => {
  for (const degrees of [0, 15, 35, 90, 135, 180, 225, 270, 300, 359, 360]) {
    for (const vertex of [undefined, [0, 0], [320, 200], [400, -50], [100, 100]]) {
      const spec = { kind: "angle", alt: `Ugao od ${degrees} stepeni, jedan krak ide udesno.`, degrees, label: `${degrees}°`, ...(vertex ? { vertex } : {}) };
      const { svg, width, height } = renderFigure(spec);
      const where = `${degrees}° at ${vertex}`;
      const rays = tags(svg, "line").map(attrs);
      assert.equal(rays.length, 2, where);
      const inside = (value, limit) => value === undefined || (Number(value) >= 0 && Number(value) <= limit);
      for (const a of [...rays, ...tags(svg, "text").map(attrs), ...tags(svg, "path").map((tag) => ({ d: tag.match(/ d="([^"]+)"/)[1] }))]) {
        assert.ok(inside(a.x, width) && inside(a.y, height) && inside(a.x1, width) && inside(a.x2, width) && inside(a.y1, height) && inside(a.y2, height), `${where}: leaves the canvas`);
      }
      // the arc is written `M x y A r r 0 f f x y`: only the four numbers around it are points
      const arcPoints = tags(svg, "path").flatMap((tag) => tag.match(/ d="([^"]+)"/)[1].replace(/A\d+ \d+ \d+ \d \d /g, "A").match(/-?[\d.]+/g)).map(Number);
      for (let i = 0; i < arcPoints.length; i += 2) assert.ok(arcPoints[i] >= 0 && arcPoints[i] <= width && arcPoints[i + 1] >= 0 && arcPoints[i + 1] <= height, `${where}: the arc leaves the canvas`);
    }
  }
  // the second ray of 35° is tilted upwards from the one that goes right
  const { svg } = renderFigure({ kind: "angle", alt: "Ugao od 35 stepeni; jedan krak ide udesno, a drugi je nagnut prema gore.", degrees: 35, vertex: [0, 0] });
  const [right, tilted] = tags(svg, "line").map(attrs);
  assert.equal(right.y1, right.y2);
  assert.ok(Number(tilted.y2) < Number(tilted.y1) && Number(tilted.x2) > Number(tilted.x1));
});

test("an unknown or malformed spec throws ZG_FIGURE", () => {
  const bad = [
    null,
    "pie",
    { kind: "cube", alt: "Kocka sa ivicom od 3 cm." },
    { alt: "Slika bez vrste." },
    { kind: "pie", parts: 4 },
    { kind: "pie", alt: "" },
    { kind: "pie", alt: 42, parts: 4 },
    { kind: "numberline", alt: "Brojevna prava.", min: 10, max: 0 },
    { kind: "numberline", alt: "Brojevna prava.", min: 0, max: 1.5 },
    { kind: "numberline", alt: "Brojevna prava.", min: 0, max: 10, step: 0 },
    { kind: "numberline", alt: "Brojevna prava.", min: 0, max: 10, marks: [11] },
    { kind: "fractionbar", alt: "Razlomak.", numerator: 3 },
    { kind: "fractionbar", alt: "Razlomak.", numerator: 3, denominator: 25 },
    { kind: "fractionbar", alt: "Razlomak.", numerator: 1, denominator: 4, shaded: 2 },
    { kind: "pie", alt: "Krug.", parts: 1 },
    { kind: "pie", alt: "Krug.", parts: 13 },
    { kind: "pie", alt: "Krug.", parts: 4, shaded: 5 },
    { kind: "dots", alt: "Tačke.", rows: 0, cols: 4 },
    { kind: "dots", alt: "Tačke.", rows: 2, cols: 2, count: 5 },
    { kind: "bars", alt: "Dijagram.", categories: ["a"], values: [1] },
    { kind: "bars", alt: "Dijagram.", categories: ["a", "b"], values: [1] },
    { kind: "bars", alt: "Dijagram.", categories: ["a", "b"], values: [1, 0] },
    { kind: "pictogram", alt: "Piktogram.", items: [{ label: "a", count: 1 }] },
    { kind: "pictogram", alt: "Piktogram.", symbol: "●", items: [] },
    { kind: "grid", alt: "Mreža.", cols: 4, cells: [[0, 0]] },
    { kind: "grid", alt: "Mreža.", cols: 4, rows: 3, cells: [[3, 0]] },
    { kind: "polygon", alt: "Trougao.", vertices: [[0, 0], [1, 1]] },
    { kind: "polygon", alt: "Trougao.", vertices: [[0, 0], [1, 0], [0, 1]], sides: [{ index: 3, label: "1" }] },
    { kind: "angle", alt: "Ugao.", degrees: 361 },
    { kind: "axes", alt: "Koordinate.", xmin: 5, xmax: 5, ymin: 0, ymax: 5 },
    { kind: "axes", alt: "Koordinate.", xmin: 0, xmax: 5, ymin: 0, ymax: 5, points: [{ x: 9, y: 1 }] },
    { kind: "clock", alt: "Sat.", hour: 13, minute: 0 },
    { kind: "clock", alt: "Sat.", hour: 3, minute: 60 },
    { kind: "clock", alt: "Sat.", minute: 30 },
    { kind: "table", alt: "Tabela.", columns: ["a", "b"], rows: [["samo jedan"]] },
  ];
  for (const spec of bad) assert.throws(() => renderFigure(spec), { name: "Error", message: "ZG_FIGURE" }), JSON.stringify(spec);
});

/* helpers */

function attrs(tag) {
  return Object.fromEntries([...tag.matchAll(/([\w:-]+)="([^"]*)"/g)].map((m) => [m[1], m[2]]));
}

/** Every opening or self-closing tag named `name`, in document order. */
function tags(svg, name) {
  return svg.match(new RegExp(`<${name}\\b[^>]*>`, "g")) ?? [];
}

/** Tags whose class attribute lists `name` as a whole class. */
function withClass(list, name) {
  return list.filter((tag) => (attrs(tag).class ?? "").split(" ").includes(name));
}

/** Text content of every <text> element, with XML entities decoded. */
function texts(svg) {
  return [...svg.matchAll(/<text\b[^>]*>([^]*?)<\/text>/g)].map((m) => unescapeXml(m[1].replace(/<[^>]+>/g, "")));
}

function titleOf(svg) {
  return unescapeXml(/<title>([^]*)<\/title>/.exec(svg)?.[1] ?? "");
}

function escapeXml(text) {
  return text.replace(/[&<>"]/g, (ch) => `&${{ "&": "amp", "<": "lt", ">": "gt", '"': "quot" }[ch]};`);
}

function unescapeXml(text) {
  return text.replace(/&(amp|lt|gt|quot);/g, (m) => ({ "&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"' }[m]));
}

function escapeRegExp(text) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** Node has no XML parser in its standard library: tags must balance and text must be escaped. */
function assertWellFormed(svg) {
  const stack = [];
  for (const m of svg.matchAll(/<(\/?)([a-zA-Z][\w:-]*)\b([^>]*)>/g)) {
    if (m[1]) assert.equal(stack.pop(), m[2], `unbalanced <${m[2]}>`);
    else if (!m[3].endsWith("/")) stack.push(m[2]);
  }
  assert.deepEqual(stack, []);
  const prose = svg.replace(/<[^>]*>/g, "");
  assert.ok(!prose.includes("<"), "raw < inside text");
  assert.doesNotMatch(prose, /&(?!(?:amp|lt|gt|quot);)/, "raw & inside text");
}

/** The only paints are the text colour, the theme variables and `none`: no hard-coded colour. */
function assertThemed(svg) {
  const paints = [...svg.matchAll(/(?:stroke|fill)="([^"]*)"/g)].map((m) => m[1]);
  assert.ok(paints.length > 0);
  for (const paint of paints) assert.match(paint, /^(?:currentColor|none|var\(--zg-(?:ink|accent)(?:, currentColor)?\))$/);
}

function fixtureFigures() {
  let json;
  try {
    json = JSON.parse(readFileSync(new URL("../fixtures/figures.json", import.meta.url), "utf8"));
  } catch (err) {
    if (err.code === "ENOENT") return null;
    throw err;
  }
  const entries = Array.isArray(json) ? json.map((spec) => [spec.kind, spec]) : Object.entries(json);
  return entries.map(([kind, spec]) => ({ ...spec, kind }));
}

/** Start and end angle of a slice path `M cx cy L x0 y0 A r r 0 0 1 x1 y1`, in degrees from 12 o'clock. */
function arcAngles(d) {
  const [cx, cy, x0, y0, , , , , , x1, y1] = d.match(/-?[\d.]+/g).map(Number);
  const deg = (x, y) => ((Math.atan2(y - cy, x - cx) * 180) / Math.PI + 450) % 360;
  return [deg(x0, y0), deg(x1, y1)];
}

function spacings(xs) {
  return xs.slice(1).map((x, i) => x - xs[i]);
}

/** Coordinates are written with two decimals, so equality is checked to a hundredth. */
function nearEqual(values, expected, tolerance = 0.01) {
  for (const value of values) assert.ok(Math.abs(value - expected) < tolerance, `${value} ≈ ${expected}`);
}

function angleOf(hand) {
  return ((Math.atan2(hand.to[1] - hand.from[1], hand.to[0] - hand.from[0]) * 180) / Math.PI + 450) % 360;
}

function length(hand) {
  return Math.hypot(hand.to[0] - hand.from[0], hand.to[1] - hand.from[1]);
}
