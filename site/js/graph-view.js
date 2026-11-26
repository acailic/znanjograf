// site/js/graph-view.js — draws a layout as hand-made SVG (spec §12.3).
//
// toSvg(layoutResult, verdicts) is pure: it returns the markup of the topic
// map. Hard edges are solid lines and soft edges are dashed. Every node carries
// its verdict as a class (zg-node--mastered, --shaky, --weak, --inferred or
// --untested) and the focused node also zg-node--focus; a <title> holds the
// full label. The page theme supplies the colours: lines and text use
// currentColor, and zg.css styles the classes.
// mount() is the only function here that touches the DOM.

const VERDICTS = ["mastered", "shaky", "weak", "inferred", "untested"];
const DASHED = ' stroke-dasharray="6 4"';

export function toSvg(layoutResult, verdicts = {}) {
  const { width, height, nodes = [], edges = [], focus } = layoutResult ?? {};
  const lines = edges.map((edge) => {
    const strength = edge.strength === "soft" ? "soft" : "hard";
    const points = edge.points.map((point) => point.map(px).join(",")).join(" ");
    return `<polyline class="zg-edge zg-edge--${strength}" data-from="${escapeXml(edge.from)}" data-to="${escapeXml(edge.to)}" points="${points}" fill="none" stroke="currentColor"${strength === "soft" ? DASHED : ""}/>`;
  });
  const boxes = nodes.map((node) => {
    const verdict = VERDICTS.includes(verdicts[node.id]) ? verdicts[node.id] : "untested";
    const classes = `zg-node zg-node--${verdict}${node.id === focus ? " zg-node--focus" : ""}`;
    const label = node.label ?? node.text ?? node.id;
    const shown = node.text ?? label;
    return (
      `<g class="${classes}" data-id="${escapeXml(node.id)}"><title>${escapeXml(label)}</title>` +
      `<rect x="${px(node.x)}" y="${px(node.y)}" width="${px(node.w)}" height="${px(node.h)}" rx="8" fill="none" stroke="currentColor"/>` +
      `<text x="${px(node.x + node.w / 2)}" y="${px(node.y + node.h / 2 + 5)}" text-anchor="middle" fill="currentColor">${escapeXml(shown)}</text></g>`
    );
  });
  return `<svg xmlns="http://www.w3.org/2000/svg" class="zg-graph" viewBox="0 0 ${px(width)} ${px(height)}" width="${px(width)}" height="${px(height)}">${lines.join("")}${boxes.join("")}</svg>`;
}

/** Draws the map into `container`; a click on a node calls `onSelect(id)`. */
export function mount(container, layoutResult, verdicts, onSelect) {
  container.innerHTML = toSvg(layoutResult, verdicts);
  const svg = container.querySelector("svg");
  if (svg) {
    svg.addEventListener("click", (event) => {
      const node = event.target.closest?.(".zg-node");
      if (node && svg.contains(node)) onSelect?.(node.dataset.id);
    });
  }
}

const px = (value) => String(Number(value.toFixed(2)));

function escapeXml(text) {
  return String(text).replace(/[&<>"]/g, (ch) => `&${{ "&": "amp", "<": "lt", ">": "gt", '"': "quot" }[ch]};`);
}
