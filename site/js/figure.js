// site/js/figure.js — declarative figures for questions (spec §12.3).
//
// renderFigure(spec) turns a figure record into a standalone SVG string.
// The parameter names are shared with the Python validator (zg/checks/figure.py)
// and must not change. A spec that cannot be drawn throws Error("ZG_FIGURE"),
// so the page can show the alt text instead. The page theme drives the colours:
// strokes are currentColor and the only other paints are var(--zg-accent) and
// var(--zg-ink). Labels are written exactly as given, in either script.

export const FIGURE_KINDS = Object.freeze([
  "numberline", "fractionbar", "pie", "dots", "bars", "pictogram",
  "grid", "polygon", "angle", "axes", "clock", "table",
]);

const PAD = 16; // canvas margin, px
const FONT = 14; // label font size, px
const CHAR_W = 8; // estimated width of one label character at FONT
const STROKE = 'stroke="currentColor" fill="none"';
const ACCENT = 'fill="var(--zg-accent, currentColor)"';

class FigureError extends Error {
  constructor() {
    super("ZG_FIGURE");
  }
}

export function renderFigure(spec) {
  try {
    ensure(isRecord(spec) && FIGURE_KINDS.includes(spec.kind) && typeof spec.alt === "string" && spec.alt.trim() !== "");
    const { alt } = spec;
    const { width, height, body } = PAINTERS[spec.kind](spec);
    return {
      alt,
      width,
      height,
      svg:
        `<svg xmlns="http://www.w3.org/2000/svg" class="zg-figure zg-figure--${spec.kind}"` +
        ` viewBox="0 0 ${width} ${height}" width="${width}" height="${height}"` +
        ` role="img" aria-label="${escapeXml(alt)}" font-size="${FONT}">` +
        `<title>${escapeXml(alt)}</title>${body}</svg>`,
    };
  } catch (err) {
    // A validation this module misses must still surface as the one error the page knows.
    throw err instanceof FigureError ? err : new FigureError();
  }
}

const PAINTERS = {
  numberline,
  fractionbar,
  pie,
  dots,
  bars,
  pictogram,
  grid,
  polygon,
  angle,
  axes,
  clock,
  table,
};

function numberline({ min, max, step = 1, marks = [], unit }) {
  ensure(Number.isInteger(min) && Number.isInteger(max) && min < max);
  ensure(Number.isInteger(step) && step > 0);
  ensure(Array.isArray(marks) && marks.every((mark) => isNumber(mark) && min <= mark && mark <= max));
  ensure(unit === undefined || typeof unit === "string");

  const ticks = [];
  for (let value = min; value <= max; value += step) ticks.push(value);
  ensure(ticks.length <= 60);

  // Ticks sit far enough apart for the widest label, and the margin holds half of it.
  const widest = Math.max(...ticks.map((value) => chars(formatNumber(value)).length));
  const pad = Math.max(PAD, (widest * CHAR_W) / 2 + 2);
  const span = Math.max(288 - 2 * PAD, (ticks.length - 1) * Math.max(34, widest * CHAR_W + 6));
  const width = span + 2 * pad;
  const axisY = 42;
  const x = (value) => pad + ((value - min) / (max - min)) * span;

  let body = `<path class="zg-axis" d="M${pad - 10} ${axisY}h${span + 20}" ${STROKE}/>`;
  body += `<path class="zg-arrow" d="M${pad - 3} ${axisY - 4}l-9 4 9 4z" fill="currentColor"/>`;
  body += `<path class="zg-arrow" d="M${width - pad + 3} ${axisY - 4}l9 4-9 4z" fill="currentColor"/>`;
  for (const value of ticks) {
    body += `<line class="zg-tick" x1="${px(x(value))}" y1="${axisY - 6}" x2="${px(x(value))}" y2="${axisY + 6}" ${STROKE}/>`;
    body += text(x(value), axisY + 23, formatNumber(value));
  }
  for (const value of marks) {
    // A mark stands above its number, clear of the line.
    body += `<circle class="zg-mark" cx="${px(x(value))}" cy="${axisY - 12}" r="5.5" ${ACCENT}/>`;
  }
  if (unit) body += text(width - pad, 20, unit, { anchor: "end" });
  return { width, height: 80, body };
}

function fractionbar({ numerator, denominator, shaded = numerator }) {
  ensure(Number.isInteger(numerator) && numerator > 0);
  ensure(Number.isInteger(denominator) && denominator > 0 && denominator <= 24);
  ensure(Number.isInteger(shaded) && 0 <= shaded && shaded <= numerator);

  // 5/4 is one full bar and one bar with a single part: a bar per whole number.
  const bars = Math.ceil(numerator / denominator);
  const inner = 288;
  const part = inner / denominator;
  const barH = 40;
  const gap = 12;

  let body = "";
  for (let bar = 0; bar < bars; bar += 1) {
    for (let i = 0; i < denominator; i += 1) {
      const filled = bar * denominator + i < shaded;
      body += `<rect class="zg-part${filled ? " zg-part--shaded" : ""}" x="${px(PAD + i * part)}" y="${PAD + bar * (barH + gap)}"`;
      body += ` width="${px(part)}" height="${barH}" ${filled ? ACCENT : 'fill="none"'} stroke="currentColor"/>`;
    }
  }
  return { width: inner + 2 * PAD, height: 2 * PAD + bars * barH + (bars - 1) * gap, body };
}

function pie({ parts, shaded = 0 }) {
  ensure(Number.isInteger(parts) && 2 <= parts && parts <= 12);
  ensure(Number.isInteger(shaded) && 0 <= shaded && shaded <= parts);

  const size = 240;
  const c = size / 2;
  const r = 92;
  // Slices start at 12 o'clock and go clockwise, one turn each `parts`th.
  const at = (turn) => [c + r * Math.sin(turn * 2 * Math.PI), c - r * Math.cos(turn * 2 * Math.PI)];

  let body = "";
  for (let i = 0; i < parts; i += 1) {
    const [x0, y0] = at(i / parts);
    const [x1, y1] = at((i + 1) / parts);
    const filled = i < shaded;
    body += `<path class="zg-slice${filled ? " zg-slice--shaded" : ""}" d="M${c} ${c}L${px(x0)} ${px(y0)}A${r} ${r} 0 0 1 ${px(x1)} ${px(y1)}Z"`;
    body += ` ${filled ? ACCENT : 'fill="none"'} stroke="currentColor"/>`;
  }
  return { width: size, height: size, body };
}

function dots({ rows, cols, count = rows * cols }) {
  ensure(Number.isInteger(rows) && 1 <= rows && rows <= 12);
  ensure(Number.isInteger(cols) && 1 <= cols && cols <= 12);
  ensure(Number.isInteger(count) && 0 <= count && count <= rows * cols);

  const cell = 36;
  let body = "";
  for (let i = 0; i < count; i += 1) {
    body += `<circle class="zg-dot" cx="${PAD + (i % cols) * cell + cell / 2}" cy="${PAD + Math.floor(i / cols) * cell + cell / 2}" r="10" ${ACCENT}/>`;
  }
  return { width: cols * cell + 2 * PAD, height: rows * cell + 2 * PAD, body };
}

function bars({ categories, values, title }) {
  ensure(Array.isArray(categories) && 2 <= categories.length && categories.length <= 8);
  ensure(categories.every(isText));
  ensure(Array.isArray(values) && values.length === categories.length);
  ensure(values.every((value) => isNumber(value) && value > 0));
  ensure(title === undefined || typeof title === "string");

  const slot = Math.max(72, Math.max(...categories.map((category) => chars(category).length)) * CHAR_W + 12);
  const inner = Math.max(288, categories.length * slot);
  const width = inner + 2 * PAD;
  const plot = 140;
  const base = PAD + (title ? 24 : 0) + 18 + plot;
  const max = Math.max(...values);
  const barW = Math.min(56, slot * 0.6);

  let body = title ? text(width / 2, PAD + 10, title, { cls: "zg-title" }) : "";
  for (let i = 0; i < values.length; i += 1) {
    const h = (values[i] / max) * plot;
    const cx = PAD + i * slot + slot / 2;
    body += `<rect class="zg-bar" x="${px(cx - barW / 2)}" y="${px(base - h)}" width="${px(barW)}" height="${px(h)}" ${ACCENT} stroke="currentColor"/>`;
    body += text(cx, base - h - 5, formatNumber(values[i]));
    body += text(cx, base + 20, categories[i]);
  }
  body += `<path class="zg-axis" d="M${PAD} ${base}h${inner}" ${STROKE}/>`;
  return { width, height: base + 42, body };
}

function pictogram({ symbol, items, perSymbol = 1 }) {
  ensure(typeof symbol === "string" && symbol.length > 0);
  ensure(Array.isArray(items) && items.length > 0);
  ensure(items.every((item) => isRecord(item) && typeof item.label === "string" && Number.isInteger(item.count) && item.count >= 0));
  ensure(Number.isInteger(perSymbol) && perSymbol > 0);

  const rowH = 32;
  const cell = 26;
  const labelW = Math.max(...items.map((item) => chars(item.label).length)) * CHAR_W + 12;
  const firstX = PAD + labelW;
  const columns = Math.max(...items.map((item) => Math.ceil(item.count / perSymbol)));
  const width = firstX + columns * cell + PAD;
  const id = refId({ symbol, items, perSymbol });
  let defs = "";
  let body = "";

  const symbolAt = (x, y, extra = "") =>
    `<text class="zg-symbol" x="${px(x)}" y="${px(y + 7)}" text-anchor="middle" font-size="20" fill="currentColor"${extra}>${escapeXml(symbol)}</text>`;

  items.forEach((item, row) => {
    const y = PAD + row * rowH + rowH / 2;
    body += text(firstX - 8, y + 5, item.label, { anchor: "end" });
    const full = Math.floor(item.count / perSymbol);
    const rest = item.count % perSymbol;
    for (let k = 0; k < full; k += 1) body += symbolAt(firstX + (k + 0.5) * cell, y);
    if (rest > 0) {
      // A part of a symbol stands for the remainder: it is clipped to its share.
      const x = firstX + (full + 0.5) * cell;
      defs += `<clipPath id="${id}-${row}"><rect x="${x - 13}" y="${y - rowH / 2}" width="${px((rest / perSymbol) * 26)}" height="${rowH}"/></clipPath>`;
      body += symbolAt(x, y, ` clip-path="url(#${id}-${row})"`);
    }
  });
  if (perSymbol > 1) {
    const y = PAD + items.length * rowH + rowH / 2;
    body += symbolAt(firstX - 6, y) + text(firstX + 8, y + 5, `= ${perSymbol}`, { anchor: "start" });
  }
  return { width, height: 2 * PAD + (items.length + (perSymbol > 1 ? 1 : 0)) * rowH, body: (defs ? `<defs>${defs}</defs>` : "") + body };
}

function grid({ cols, rows, cells = [] }) {
  ensure(Number.isInteger(cols) && 1 <= cols && cols <= 15);
  ensure(Number.isInteger(rows) && 1 <= rows && rows <= 15);
  ensure(Array.isArray(cells) && cells.every((cell) => isPoint(cell) && cell[0] < rows && cell[1] < cols));

  const size = 26;
  const shaded = new Set(cells.map(([row, col]) => `${row},${col}`));
  let body = "";
  for (let row = 0; row < rows; row += 1) {
    for (let col = 0; col < cols; col += 1) {
      const dark = shaded.has(`${row},${col}`);
      body += `<rect class="zg-cell${dark ? " zg-cell--shaded" : ""}" x="${PAD + col * size}" y="${PAD + row * size}" width="${size}" height="${size}"`;
      body += ` ${dark ? ACCENT : 'fill="none"'} stroke="currentColor"/>`;
    }
  }
  return { width: cols * size + 2 * PAD, height: rows * size + 2 * PAD, body };
}

function polygon({ vertices, sides = [], labels = [] }) {
  ensure(Array.isArray(vertices) && 3 <= vertices.length && vertices.length <= 8 && vertices.every(isPoint));
  ensure(Array.isArray(sides) && sides.every((side) => isRecord(side) && Number.isInteger(side.index) && 0 <= side.index && side.index < vertices.length && typeof side.label === "string"));
  ensure(Array.isArray(labels) && labels.every((label) => isRecord(label) && typeof label.text === "string" && isPoint([label.x, label.y])));

  // Figure units are fitted into the canvas, keeping the ratio and y upwards.
  const width = 320;
  const height = 240;
  const margin = 36;
  const points = [...vertices, ...labels.map((label) => [label.x, label.y])];
  const xs = points.map((point) => point[0]);
  const ys = points.map((point) => point[1]);
  const [x0, x1] = [Math.min(...xs), Math.max(...xs)];
  const [y0, y1] = [Math.min(...ys), Math.max(...ys)];
  const scale = Math.min((width - 2 * margin) / (x1 - x0 || 1), (height - 2 * margin) / (y1 - y0 || 1));
  const shiftX = (width - (x1 - x0) * scale) / 2;
  const shiftY = (height - (y1 - y0) * scale) / 2;
  const map = ([x, y]) => [shiftX + (x - x0) * scale, height - shiftY - (y - y0) * scale];

  const corners = vertices.map(map);
  let body = `<path class="zg-outline" d="M${corners.map(([x, y]) => `${px(x)} ${px(y)}`).join("L")}Z" ${STROKE}/>`;
  const [cx, cy] = corners.reduce(([sx, sy], [x, y]) => [sx + x, sy + y], [0, 0]).map((sum) => sum / corners.length);
  for (const { index, label } of sides) {
    // The label sits beside the middle of its side, on the outside of the shape.
    const a = corners[index];
    const b = corners[(index + 1) % corners.length];
    const [mx, my] = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
    let [nx, ny] = [a[1] - b[1], b[0] - a[0]];
    const length = Math.hypot(nx, ny) || 1;
    [nx, ny] = [nx / length, ny / length];
    if (nx * (mx - cx) + ny * (my - cy) < 0) [nx, ny] = [-nx, -ny];
    body += text(mx + nx * 15, my + ny * 15 + 5, label);
  }
  for (const { text: str, x, y } of labels) {
    const [lx, ly] = map([x, y]);
    // A letter that names a vertex stands just outside the corner, not on it.
    const namesCorner = vertices.some(([vx, vy]) => vx === x && vy === y);
    const toCentre = Math.hypot(lx - cx, ly - cy) || 1;
    const push = namesCorner ? 15 / toCentre : 0;
    body += text(lx + (lx - cx) * push, ly + (ly - cy) * push + 5, str);
  }
  return { width, height, body };
}

function angle({ degrees, label, vertex = [0, 0] }) {
  ensure(isNumber(degrees) && 0 <= degrees && degrees <= 360);
  ensure(label === undefined || typeof label === "string");
  ensure(isPoint(vertex));

  // The first ray points right; the second is `degrees` counter-clockwise from it.
  const width = 320;
  const height = 200;
  const ray = 104;
  const arc = 36;
  const rad = (degrees * Math.PI) / 180;
  const [ux, uy] = [Math.cos(rad), -Math.sin(rad)];
  const half = rad / 2;
  const labelAt = label ? [(arc + 22) * Math.cos(half), -(arc + 22) * Math.sin(half)] : [0, 0];

  // Everything is placed relative to the vertex, which goes where all of it fits:
  // in the middle of that room, moved by `vertex` (an offset in px) as far as the room allows.
  const reach = [[0, 0], [ray, 0], [ux * ray, uy * ray], [arc, 0], [ux * arc, uy * arc], labelAt];
  if (degrees >= 90) reach.push([0, -arc]);
  if (degrees >= 180) reach.push([-arc, 0]);
  if (degrees >= 270) reach.push([0, arc]);
  const room = [0, 1].map((axis) => {
    const values = reach.map((point) => point[axis]);
    return [PAD - Math.min(...values), (axis ? height : width) - PAD - Math.max(...values)];
  });
  const [vx, vy] = vertex.map((offset, axis) => clamp((room[axis][0] + room[axis][1]) / 2 + offset, ...room[axis]));

  let body = "";
  for (const [dx, dy] of [[1, 0], [ux, uy]]) {
    body += `<line class="zg-ray" x1="${px(vx)}" y1="${px(vy)}" x2="${px(vx + dx * ray)}" y2="${px(vy + dy * ray)}" stroke="currentColor"/>`;
  }
  const start = [vx + arc, vy];
  const end = [vx + ux * arc, vy + uy * arc];
  if (degrees === 360) {
    body += `<path class="zg-arc" d="M${start.map(px)} A${arc} ${arc} 0 1 0 ${px(vx - arc)} ${px(vy)}A${arc} ${arc} 0 1 0 ${start.map(px)}" ${STROKE}/>`;
  } else if (degrees > 0) {
    // Sweep 0 is counter-clockwise on screen; the large arc is the reflex one.
    body += `<path class="zg-arc" d="M${start.map(px)} A${arc} ${arc} 0 ${degrees > 180 ? 1 : 0} 0 ${end.map(px)}" ${STROKE}/>`;
  }
  if (degrees > 180) {
    // An arrowhead says that the long way round is meant.
    const [dx, dy] = [-Math.sin(rad), -Math.cos(rad)];
    body += `<path class="zg-arrow" d="M${px(end[0] + dx * 7)} ${px(end[1] + dy * 7)}L${px(end[0] - dx * 2 - dy * 4)} ${px(end[1] - dy * 2 + dx * 4)}L${px(end[0] - dx * 2 + dy * 4)} ${px(end[1] - dy * 2 - dx * 4)}Z" fill="currentColor"/>`;
  }
  if (label) body += text(vx + labelAt[0], vy + labelAt[1] + 5, label);
  body += `<circle class="zg-vertex" cx="${px(vx)}" cy="${px(vy)}" r="2.5" fill="currentColor"/>`;
  return { width, height, body };
}

function axes({ xmin, xmax, ymin, ymax, points = [] }) {
  ensure(isNumber(xmin) && isNumber(xmax) && isNumber(ymin) && isNumber(ymax) && xmin < xmax && ymin < ymax);
  ensure(Array.isArray(points) && points.every((point) => isRecord(point) && isNumber(point.x) && isNumber(point.y) && xmin <= point.x && point.x <= xmax && ymin <= point.y && point.y <= ymax && (point.label === undefined || typeof point.label === "string")));

  const width = 320;
  const height = 280;
  const left = 36;
  const right = width - PAD;
  const top = PAD;
  const bottom = height - 28;
  const x = (value) => left + ((value - xmin) / (xmax - xmin)) * (right - left);
  const y = (value) => bottom - ((value - ymin) / (ymax - ymin)) * (bottom - top);
  // Each axis sits at 0 when 0 is in range, otherwise on the edge of the plot.
  const axisX = clamp(0, xmin, xmax);
  const axisY = clamp(0, ymin, ymax);
  const xBelow = y(axisY) >= bottom - 1; // labels go away from the plot
  const yLeft = x(axisX) <= left + 1;

  let grid = "";
  let body = `<path class="zg-axis" d="M${px(x(axisX))} ${bottom}v${top - bottom}M${left} ${px(y(axisY))}h${right - left}" ${STROKE}/>`;
  for (const value of ticksBetween(xmin, xmax)) {
    grid += `M${px(x(value))} ${top}v${bottom - top}`;
    body += text(x(value), y(axisY) + (xBelow ? 18 : -6), formatNumber(value));
  }
  for (const value of ticksBetween(ymin, ymax)) {
    grid += `M${left} ${px(y(value))}h${right - left}`;
    if (value !== axisY) body += text(x(axisX) + (yLeft ? -6 : 6), y(value) + 5, formatNumber(value), { anchor: yLeft ? "end" : "start" });
  }
  body = `<path class="zg-grid" d="${grid}" stroke="var(--zg-ink, currentColor)" stroke-opacity="0.15" fill="none"/>` + body;
  for (const { x: px0, y: py0, label } of points) {
    body += `<circle class="zg-point" cx="${px(x(px0))}" cy="${px(y(py0))}" r="4.5" ${ACCENT} stroke="currentColor"/>`;
    if (label) body += text(x(px0) + 7, y(py0) - 6, label, { anchor: "start" });
  }
  return { width, height, body };
}

function clock({ hour, minute }) {
  ensure(Number.isInteger(hour) && 1 <= hour && hour <= 12);
  ensure(Number.isInteger(minute) && 0 <= minute && minute <= 59);

  const size = 200;
  const c = size / 2;
  const r = 88;
  // `turn` is the share of a full turn, clockwise from 12 o'clock.
  const at = (turn, length) => [c + length * Math.sin(turn * 2 * Math.PI), c - length * Math.cos(turn * 2 * Math.PI)];
  let body = `<circle class="zg-face" cx="${c}" cy="${c}" r="${r}" ${STROKE}/>`;
  for (let i = 1; i <= 60; i += 1) {
    const [x1, y1] = at(i / 60, r);
    const [x2, y2] = at(i / 60, r - (i % 5 === 0 ? 7 : 3));
    body += `<line class="zg-tick-mark" x1="${px(x1)}" y1="${px(y1)}" x2="${px(x2)}" y2="${px(y2)}" stroke="currentColor"/>`;
  }
  for (let i = 1; i <= 12; i += 1) body += text(...at(i / 12, r - 22).map((v, k) => v + (k ? 5 : 0)), String(i));
  // The hour hand moves with the minutes too; it is the short, thick one.
  const hand = (name, turn, length, width) => {
    const [x2, y2] = at(turn, length);
    return `<line class="zg-hand zg-hand--${name}" x1="${c}" y1="${c}" x2="${px(x2)}" y2="${px(y2)}" stroke="currentColor" stroke-width="${width}" stroke-linecap="round"/>`;
  };
  body += hand("hour", ((hour % 12) + minute / 60) / 12, r - 48, 5);
  body += hand("minute", minute / 60, r - 24, 3);
  body += `<circle class="zg-pin" cx="${c}" cy="${c}" r="4" fill="currentColor"/>`;
  return { width: size, height: size, body };
}

function table({ columns, rows }) {
  ensure(Array.isArray(columns) && columns.length > 0 && columns.every(isText));
  ensure(Array.isArray(rows) && rows.every((row) => Array.isArray(row) && row.length === columns.length && row.every(isText)));

  const LIMIT = 24; // a cell wraps after this many characters
  const pad = 8;
  const lineH = 18;
  const head = columns.map((cell) => wrapText(cell, LIMIT));
  const grid = rows.map((row) => row.map((cell) => wrapText(cell, LIMIT)));
  const colW = columns.map((_, col) => Math.max(...[head, ...grid].map((row) => Math.max(...row[col].map((line) => chars(line).length)))) * CHAR_W + 2 * pad);
  const lefts = colW.map((_, col) => PAD + colW.slice(0, col).reduce((sum, w) => sum + w, 0));
  const inner = colW.reduce((sum, w) => sum + w, 0);
  let y = PAD;
  let body = "";
  const drawRow = (cells, cls) => {
    cells.forEach((lines, col) => {
      lines.forEach((line, i) => {
        body += `<text class="${cls}" x="${lefts[col] + pad}" y="${y + 14 + i * lineH}" fill="currentColor">${escapeXml(line)}</text>`;
      });
    });
    y += Math.max(...cells.map((lines) => lines.length)) * lineH + 10;
  };
  drawRow(head, "zg-th");
  body += `<path class="zg-rule" d="M${PAD} ${y}h${inner}" ${STROKE}/>`;
  for (const row of grid) drawRow(row, "zg-td");
  body += `<rect class="zg-frame" x="${PAD}" y="${PAD}" width="${inner}" height="${y - PAD}" ${STROKE}/>`;
  return { width: inner + 2 * PAD, height: y + PAD, body };
}

/* building blocks */

function ensure(condition) {
  if (!condition) throw new FigureError();
}

const isRecord = (value) => typeof value === "object" && value !== null && !Array.isArray(value);
const isText = (value) => typeof value === "string";
const isNumber = (value) => typeof value === "number" && Number.isFinite(value);
const isPoint = (value) => Array.isArray(value) && value.length === 2 && value.every(isNumber);
const chars = (str) => Array.from(str);

/** Coordinates are written with at most two decimals, so equal parts stay equal on paper. */
const px = (value) => String(Math.round(value * 100) / 100);

function clamp(value, low, high) {
  return Math.min(Math.max(value, low), high);
}

function text(x, y, str, { anchor = "middle", cls = "zg-label" } = {}) {
  return `<text class="${cls}" x="${px(x)}" y="${px(y)}" text-anchor="${anchor}" fill="currentColor">${escapeXml(str)}</text>`;
}

function escapeXml(text) {
  return text.replace(/[&<>"]/g, (ch) => `&${{ "&": "amp", "<": "lt", ">": "gt", '"': "quot" }[ch]};`);
}

/** Serbian notation (spec §6.2): a minus sign, decimal comma, space as thousands separator. */
function formatNumber(value) {
  const [whole, fraction] = String(Math.abs(value)).split(".");
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  return `${value < 0 ? "\u2212" : ""}${fraction === undefined ? grouped : `${grouped},${fraction}`}`;
}

/** Tick values from min to max in a 1-2-5 step that keeps them near eight per axis. */
function ticksBetween(min, max) {
  const rough = (max - min) / 8;
  const unit = 10 ** Math.floor(Math.log10(rough));
  const step = [1, 2, 5, 10].find((multiple) => multiple * unit >= rough) * unit;
  const values = [];
  for (let value = min; value <= max + step * 1e-9; value += step) values.push(Number(value.toPrecision(12)));
  return values;
}

/** Greedy word wrap at `limit` characters; a longer word is cut. */
function wrapText(str, limit) {
  const lines = [];
  for (const word of str.split(" ")) {
    const letters = chars(word);
    for (let i = 0; i < Math.max(letters.length, 1); i += limit) {
      const piece = letters.slice(i, i + limit).join("");
      const line = lines.at(-1);
      if (line !== undefined && chars(line).length + 1 + chars(piece).length <= limit) lines[lines.length - 1] = `${line} ${piece}`;
      else lines.push(piece);
    }
  }
  return lines;
}

/** Stable id for references inside the SVG (FNV-1a of the parameters, base 36). */
function refId(spec) {
  let hash = 0x811c9dc5;
  for (const ch of JSON.stringify(spec)) hash = Math.imul(hash ^ ch.codePointAt(0), 0x01000193) >>> 0;
  return `zg-fig-${hash.toString(36)}`;
}
