// site/js/layout.js — positions for the topic map (spec §12.3).
//
// layout({ nodes, edges, focus }) is pure. It returns the canvas size and, in
// pixels, one rectangle per node (x, y = top-left corner) and the polyline of
// every drawable edge. Columns follow the longest path (one column per edge);
// rows are grade bands of at most eight rows, and whatever does not fit is
// collapsed into a single "+N" node per band.
//
// Input:
//   nodes  [{ id, grade, name | label }] in learning order
//   edges  [[topic, requires, strength]] as in the data bundle, or the same as
//          objects { topic, requires, strength } or { from, to, strength }
//          (from = the prerequisite, drawn on the left)
//   focus  id of the node the map is opened at; it is never collapsed

const MARGIN = 12;
const COL_GAP = 56; // room for the edges between two columns
const ROW_GAP = 6;
const BAND_PAD = 10;
const BAND_GAP = 8;
const NODE_H = 44; // a touch target
const PAD_X = 12;
const CHAR_W = 8; // estimated width of one character of a node label (14 px font)
const MAX_CHARS = 18; // longer labels are ellipsised
const MAX_ROWS = 8;
const STRENGTHS = ["hard", "soft"];

export function layout({ nodes = [], edges = [], focus } = {}) {
  const byId = new Map(nodes.map((node, order) => [node.id, describe(node, order)]));
  const links = edges.map((edge) => toLink(edge, byId)).filter(Boolean);
  const layer = longestLayers([...byId.keys()], links);
  const shown = choose(byId, layer, focus).sort((a, b) => a.order - b.order);

  // Every column is as wide as its widest node, every band as high as its fullest column.
  const columns = strips(shown, "column", (entries) => Math.max(...entries.map((entry) => entry.w)), COL_GAP);
  const bands = strips(shown, "grade", (entries) => bandHeight(Math.max(...entries.map((entry) => entry.row + 1))), BAND_GAP);

  const placed = new Map();
  for (const entry of shown) {
    placed.set(entry.id, {
      id: entry.id,
      x: columns.spans.get(entry.column)[0],
      y: bands.spans.get(entry.grade)[0] + BAND_PAD + entry.row * (NODE_H + ROW_GAP),
      w: entry.w,
      h: NODE_H,
      band: entry.grade,
      label: entry.label,
      text: entry.text,
    });
  }

  const routed = [];
  for (const { from, to, strength } of links) {
    const source = placed.get(from);
    const target = placed.get(to);
    // Edges of hidden nodes, and the ones a cycle would send backwards, are not drawn.
    if (source && target && layer.get(from) < layer.get(to)) {
      routed.push({ from, to, strength, points: route(source, target, columns.spans.get(layer.get(from))[1], columns.spans.get(layer.get(to))[0]) });
    }
  }

  return {
    width: columns.extent,
    height: bands.extent,
    nodes: [...placed.values()],
    edges: routed,
    focus: typeof focus === "string" ? focus : undefined,
  };
}

/** The node as drawn: its band, its (ellipsised) label and the size that label needs. */
function describe(node, order) {
  if (typeof node?.id !== "string" || !Number.isInteger(node.grade)) throw new TypeError("layout: every node needs a string id and an integer grade");
  const label = String(node.label ?? node.name ?? node.id);
  const letters = Array.from(label);
  const text = letters.length > MAX_CHARS ? `${letters.slice(0, MAX_CHARS - 1).join("")}…` : label;
  return { grade: node.grade, label, text, w: Math.max(40, 2 * PAD_X + letters.length * CHAR_W), order };
}

/** One edge of the input as { from, to, strength } with the left node first; null if it cannot exist. */
function toLink(edge, byId) {
  let from;
  let to;
  let strength;
  if (Array.isArray(edge)) [to, from, strength] = edge; // a topic requires its prerequisite
  else if (edge && "topic" in edge) ({ requires: from, topic: to, strength } = edge);
  else ({ from, to, strength } = edge ?? {});
  if (from === to || !byId.has(from) || !byId.has(to)) return null;
  return { from, to, strength: STRENGTHS.includes(strength) ? strength : "hard" };
}

/** layer(node) = 1 + the largest layer of its prerequisites, 0 for a node without any. */
function longestLayers(ids, links) {
  const layer = new Map();
  const waiting = new Map(ids.map((id) => [id, 0])); // prerequisites not placed yet
  const longest = new Map(ids.map((id) => [id, 0])); // longest path seen so far
  const successors = new Map(ids.map((id) => [id, []]));
  for (const { from, to } of links) {
    waiting.set(to, waiting.get(to) + 1);
    successors.get(from).push(to);
  }
  let frontier = ids.filter((id) => waiting.get(id) === 0);
  while (layer.size < ids.length) {
    // Valid data is acyclic. In a cycle nobody is free, so the first node still waiting is released.
    if (frontier.length === 0) frontier = [ids.find((id) => !layer.has(id))];
    const next = [];
    for (const id of frontier) {
      layer.set(id, longest.get(id));
      for (const to of successors.get(id)) {
        longest.set(to, Math.max(longest.get(to), layer.get(id) + 1));
        waiting.set(to, waiting.get(to) - 1);
        if (waiting.get(to) === 0) next.push(to);
      }
    }
    frontier = next;
  }
  return layer;
}

/**
 * Decides what is shown: per grade band, its columns in order, and per column
 * its nodes in learning order. A band has at most MAX_ROWS rows: every node
 * past the seventh of a column is hidden and counted in one "+N" node (id
 * "+N@<grade>"), which takes the last row of the column that hid the most.
 */
function choose(byId, layer, focus) {
  const shown = [];
  const add = (id, entry, column, row) => shown.push({ id, ...entry, column, row });

  for (const grade of gradesOf(byId.values())) {
    const columns = new Map(); // layer → ids in learning order
    for (const [id, entry] of byId) {
      if (entry.grade === grade) columns.set(layer.get(id), [...(columns.get(layer.get(id)) ?? []), id]);
    }
    const ordered = [...columns].sort(([a], [b]) => a - b);
    const crowded = ordered.filter(([, ids]) => ids.length > MAX_ROWS);
    const hidden = crowded.reduce((sum, [, ids]) => sum + ids.length - (MAX_ROWS - 1), 0);

    for (const [column, ids] of ordered) {
      const kept = ids.length > MAX_ROWS ? keep(ids, MAX_ROWS - 1, focus) : ids;
      kept.forEach((id, row) => add(id, byId.get(id), column, row));
    }
    if (hidden > 0) {
      const [column] = crowded.reduce((widest, next) => (next[1].length > widest[1].length ? next : widest));
      add(`+${hidden}@${grade}`, { grade, label: `+${hidden}`, text: `+${hidden}`, w: 48, order: Infinity }, column, MAX_ROWS - 1);
    }
  }
  return shown;
}

/** The first `count` ids, plus the focused one wherever it comes. */
function keep(ids, count, focus) {
  const kept = new Set(ids.filter((id) => id !== focus).slice(0, ids.includes(focus) ? count - 1 : count));
  kept.add(focus);
  return ids.filter((id) => kept.has(id));
}

/**
 * The strips along one axis (the columns, or the grade bands), lowest key
 * first: value → [start, end], each as wide as `size` says, `gap` in between.
 * `extent` is where the last one ends, plus the margin.
 */
function strips(entries, key, size, gap) {
  const spans = new Map();
  let at = MARGIN;
  for (const value of [...new Set(entries.map((entry) => entry[key]))].sort((a, b) => a - b)) {
    const extent = size(entries.filter((entry) => entry[key] === value));
    spans.set(value, [at, at + extent]);
    at += extent + gap;
  }
  return { spans, extent: entries.length ? at - gap + MARGIN : 0 };
}

const bandHeight = (rows) => 2 * BAND_PAD + rows * NODE_H + (rows - 1) * ROW_GAP;

/**
 * Orthogonal route from the right border of `source` into the left border of
 * `target`. It turns only in the gaps between columns and, when it skips
 * columns, runs along the space just above the target's row, so it never
 * crosses a node.
 */
function route(source, target, columnEnd, columnStart) {
  const x0 = source.x + source.w;
  const y0 = source.y + source.h / 2;
  const x1 = target.x;
  const y1 = target.y + target.h / 2;
  const points = [[x0, y0]];
  if (columnStart - columnEnd === COL_GAP) {
    const turn = columnEnd + COL_GAP / 2; // neighbouring columns share one gap
    points.push([turn, y0], [turn, y1]);
  } else {
    const lane = target.y - ROW_GAP / 2;
    points.push([columnEnd + COL_GAP / 2, y0], [columnEnd + COL_GAP / 2, lane], [columnStart - COL_GAP / 2, lane], [columnStart - COL_GAP / 2, y1]);
  }
  points.push([x1, y1]);
  return points;
}

/** Grade bands from the lowest grade up. */
function gradesOf(entries) {
  return [...new Set([...entries].map((entry) => entry.grade))].sort((a, b) => a - b);
}
