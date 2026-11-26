// graph.js — the index of the knowledge graph that the diagnostic engine walks.
//
// buildIndex(topics, edges, aliases) takes the shapes of the built
// `podaci/index.*.json` and answers everything the engine asks about the graph:
// the learning order, the exit topics of a grade, prerequisites and ancestors.
// It mirrors zg.corpus.Corpus, so Python and the browser agree on the graph.
// Pure data in, pure data out: no DOM, no storage, no fetch.

/** Grade used for a topic whose grade is not an integer (same as Python). */
const FALLBACK_GRADE = 99;

/** An edge that names a topic the index does not know, or a cycle. */
function badGraph(detail) {
  return new Error(`ZG_BAD_GRAPH: ${detail}`);
}

/**
 * Kahn's algorithm with a priority: among the topics whose prerequisites are
 * all emitted, the one with the smallest key goes first. Mirrors
 * `Corpus.learning_order()` in zg/corpus.py.
 */
function learningOrderOf(ids, keyOf, prerequisites, dependents) {
  const waiting = new Map();
  const available = [];
  for (const id of ids) {
    waiting.set(id, prerequisites.get(id).length);
    if (prerequisites.get(id).length === 0) available.push(id);
  }

  const order = [];
  while (available.length > 0) {
    let best = 0;
    for (let i = 1; i < available.length; i += 1) {
      if (compareKeys(keyOf(available[i]), keyOf(available[best])) < 0) best = i;
    }
    const id = available.splice(best, 1)[0];
    order.push(id);
    for (const edge of dependents.get(id)) {
      const left = waiting.get(edge.id) - 1;
      waiting.set(edge.id, left);
      if (left === 0) available.push(edge.id);
    }
  }

  if (order.length !== ids.length) throw badGraph("the graph has a cycle");
  return order;
}

function compareKeys(a, b) {
  for (let i = 0; i < a.length; i += 1) {
    if (a[i] !== b[i]) return a[i] < b[i] ? -1 : 1;
  }
  return 0;
}

/**
 * Every topic reachable from `id` by following `step`, without `id` itself.
 * Mirrors `Corpus._reach`.
 */
function reach(id, step) {
  const seen = new Set();
  const queue = [id];
  while (queue.length > 0) {
    for (const next of step(queue.pop())) {
      if (!seen.has(next)) {
        seen.add(next);
        queue.push(next);
      }
    }
  }
  seen.delete(id);
  return seen;
}

/**
 * Build the index.
 *
 * topics  [{id, grade, area, unit, kind, name}] in file order
 * edges   [[topic, requires, "hard" | "soft"]]
 * aliases {oldId: [id, …]}
 *
 * Throws Error("ZG_BAD_GRAPH: …") when an edge names an unknown topic or the
 * graph has a cycle; the `validate` gate keeps such data out of the build.
 */
export function buildIndex(topics, edges, aliases = {}) {
  const position = new Map(); // id → place in the file (the first occurrence wins)
  const gradeOf = new Map();
  const unitOf = new Map();
  topics.forEach((topic, place) => {
    if (position.has(topic.id)) return;
    position.set(topic.id, place);
    gradeOf.set(topic.id, Number.isInteger(topic.grade) ? topic.grade : FALLBACK_GRADE);
    unitOf.set(topic.id, topic.unit);
  });

  const prerequisites = new Map(); // id → [{id, strength}]
  const dependents = new Map(); // id → [{id, strength}]
  for (const id of position.keys()) {
    prerequisites.set(id, []);
    dependents.set(id, []);
  }
  for (const [topic, requires, strength] of edges) {
    if (!prerequisites.has(topic) || !prerequisites.has(requires)) {
      throw badGraph(`edge ${topic} -> ${requires} names an unknown topic`);
    }
    prerequisites.get(topic).push({ id: requires, strength });
    dependents.get(requires).push({ id: topic, strength });
  }

  const keyOf = (id) => [gradeOf.get(id), position.get(id), id];
  const topicIds = learningOrderOf([...position.keys()], keyOf, prerequisites, dependents);

  const hardSteps = (adjacency) => (id) => adjacency.get(id).filter((edge) => edge.strength === "hard").map((edge) => edge.id);
  const anySteps = (adjacency) => (id) => adjacency.get(id).map((edge) => edge.id);
  const hardAncestors = new Map(topicIds.map((id) => [id, reach(id, hardSteps(prerequisites))]));
  const ancestors = new Map(topicIds.map((id) => [id, reach(id, anySteps(prerequisites))]));

  const copy = (edgesOf) => edgesOf.map((edge) => ({ ...edge }));

  return {
    /** Every topic id, in learning order. */
    topicIds,
    /** id → grade. */
    gradeOf,
    /** id → unit (the name a `unit` scope is matched against). */
    unitOf,

    /** What `id` needs before it, in file order: [{id, strength}]. */
    prereqsOf(id) {
      return prerequisites.has(id) ? copy(prerequisites.get(id)) : [];
    },

    /** What needs `id`, in file order: [{id, strength}]. */
    dependentsOf(id) {
      return dependents.has(id) ? copy(dependents.get(id)) : [];
    },

    /** Every ancestor of `id` through hard edges only (a Set, without `id`). */
    hardAncestorsOf(id) {
      return hardAncestors.get(id) ?? new Set();
    },

    /** Every ancestor of `id` through edges of either strength (a Set, without `id`). */
    ancestorsOf(id) {
      return ancestors.get(id) ?? new Set();
    },

    /** `ids` in learning order (unknown ids are ignored); all topics when omitted. */
    learningOrder(ids) {
      if (ids === undefined) return [...topicIds];
      const wanted = new Set(ids);
      return topicIds.filter((id) => wanted.has(id));
    },

    /** Topics of `grade` that no topic of the same grade needs (hard or soft), in learning order. */
    gradeExits(grade) {
      return topicIds.filter((id) => gradeOf.get(id) === grade && !dependents.get(id).some((edge) => gradeOf.get(edge.id) === grade));
    },

    /** The current ids of an old one; `[id]` for a topic that exists; `[]` otherwise. */
    resolveAlias(id) {
      if (Object.hasOwn(aliases, id)) return [...aliases[id]];
      return position.has(id) ? [id] : [];
    },
  };
}
