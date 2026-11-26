// result.js — what a session has found: where the knowledge most likely broke
// (the roots), the path to repair it, and the tallies for the result page.
//
// Everything here is derived from the session state, so a result can be shown
// at any moment: finished, paused or interrupted.

import { replay } from "./session.js";
import { STATUS } from "./verdict.js";

/** The status of every topic the session has given one: Map id → status. */
export function statusesOf(state) {
  return new Map(replay(state).world.status);
}

/**
 * summarise(state) →
 *   roots:     [{id, confirmed, missed}]  weak topics with no weak hard ancestor
 *   path:      [{id, status}]             the repair path, in learning order
 *   shaky:     [id]                       every shaky topic, in learning order
 *   counts:    {mastered, shaky, weak, inferred, untested}
 *   untested:  [id]                       scope topics not reached yet
 *   outcomes:  [{edition, id}]            curriculum outcomes of the roots and the path
 */
export function summarise(state) {
  const { world, scopeIds } = replay(state);
  const index = state.index;
  const status = world.status;

  const weak = topicsWith(status, STATUS.WEAK);
  const roots = index.learningOrder(weak.filter((id) => !hasWeakHardAncestor(index, status, id)));
  const untested = index.learningOrder(scopeIds.filter((id) => !status.has(id)));
  const path = pathTopics(index, scopeIds, status, roots);

  const counts = { mastered: 0, shaky: 0, weak: 0, inferred: 0, untested: untested.length };
  for (const value of status.values()) counts[value] += 1;

  return {
    roots: roots.map((id) => ({
      id,
      confirmed: isConfirmed(index, status, id),
      missed: [...(world.missed.get(id) ?? [])],
    })),
    path: index.learningOrder(path).map((id) => ({ id, status: status.get(id) })),
    shaky: index.learningOrder(topicsWith(status, STATUS.SHAKY)),
    counts,
    untested,
    outcomes: outcomesOf(state, index.learningOrder([...roots, ...path])),
  };
}

function topicsWith(status, wanted) {
  const ids = [];
  for (const [id, value] of status) {
    if (value === wanted) ids.push(id);
  }
  return ids;
}

/**
 * A root is confirmed once every hard ancestor of it was judged or inferred.
 * (A topic without a status is untested.)
 */
function isConfirmed(index, status, root) {
  for (const ancestor of index.hardAncestorsOf(root)) {
    if (!status.has(ancestor)) return false;
  }
  return true;
}

function hasWeakHardAncestor(index, status, id) {
  for (const ancestor of index.hardAncestorsOf(id)) {
    if (status.get(ancestor) === STATUS.WEAK) return true;
  }
  return false;
}

/**
 * The weak topics on a path from a root to a scope topic, plus the shaky ones
 * on such paths. The paths follow hard edges. A root that reaches the scope
 * only through soft edges would otherwise have no path at all, so for such a
 * root alone the paths may use edges of either strength.
 */
function pathTopics(index, scopeIds, status, roots) {
  const inPath = new Set();
  const scope = new Set(scopeIds);

  for (const root of roots) {
    const belowRootByHard = reach(index, root, "hard");
    const hardOnly = [...belowRootByHard].some((id) => scope.has(id));
    const belowRoot = hardOnly ? belowRootByHard : reach(index, root, "any");
    const ancestorsOf = hardOnly ? index.hardAncestorsOf : index.ancestorsOf;

    const toScope = new Set(scope);
    for (const id of scopeIds) {
      for (const ancestor of ancestorsOf(id)) toScope.add(ancestor);
    }

    for (const id of belowRoot) {
      const value = status.get(id);
      if ((value === STATUS.WEAK || value === STATUS.SHAKY) && toScope.has(id)) inPath.add(id);
    }
  }
  return [...inPath];
}

/** `start` and every topic that needs it, directly or further up. */
function reach(index, start, strength) {
  const found = new Set([start]);
  const queue = [start];
  while (queue.length > 0) {
    for (const edge of index.dependentsOf(queue.pop())) {
      if ((strength === "any" || edge.strength === strength) && !found.has(edge.id)) {
        found.add(edge.id);
        queue.push(edge.id);
      }
    }
  }
  return found;
}

/** The curriculum outcomes of the topics, each listed once. */
function outcomesOf(state, topicIds) {
  const outcomes = [];
  const seen = new Set();
  for (const topicId of topicIds) {
    for (const entry of state.curriculum?.[topicId] ?? []) {
      const key = `${entry.edition}/${entry.outcome}`;
      if (!seen.has(key)) {
        seen.add(key);
        outcomes.push({ edition: entry.edition, id: entry.outcome });
      }
    }
  }
  return outcomes;
}
