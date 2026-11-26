"""Rules V5 and V6 on the prerequisite graph, built here from ``corpus.edge_list``.

The derived views of ``Corpus`` raise on exactly the graphs this gate has to
describe, so nothing below asks them.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from typing import NamedTuple

from ..corpus import Corpus
from ..issues import Issues
from .schema import iter_edges

Successors = Callable[[str], list[str]]

# topic, requires, strength, where, path
Edge = tuple[str, str, object, str, str]


class _Graph(NamedTuple):
    """What reading every edge once leaves behind."""
    prerequisites: dict[str, list[str]]  # what each topic requires, any strength; self-loops are left out
    hard: dict[str, list[str]]  # the same, hard edges only
    as_topic: set[str]  # topics that an edge names as ``topic``
    as_requires: set[str]  # topics that an edge names as ``requires``
    kept: list[Edge]  # the edges that were read to the end


def run(corpus: Corpus, issues: Issues) -> None:
    """V5 and V6 over the edges and topics of the corpus. Mutates nothing; appends to ``issues``."""
    graph = _read_edges(corpus, issues)
    _check_redundant(graph, issues)
    _check_topics(corpus, graph, issues)


def _read_edges(corpus: Corpus, issues: Issues) -> _Graph:
    """Rule V5 for everything one edge says by itself, and the adjacency for the rules that need more."""
    topics = corpus.topics
    graph = _Graph({topic_id: [] for topic_id in topics}, {topic_id: [] for topic_id in topics}, set(), set(), [])
    pairs: set[tuple[str, str]] = set()  # (topic, requires) already read
    linked: set[frozenset[str]] = set()  # two topics joined in either order
    grades = {
        topic_id: record["grade"] for topic_id, record in topics.items()
        if isinstance(record.get("grade"), int) and not isinstance(record["grade"], bool)
    }
    for index, (edge, where, path) in enumerate(iter_edges(corpus)):
        if not isinstance(edge, dict):
            continue
        topic, requires = edge.get("topic"), edge.get("requires")
        if not (isinstance(topic, str) and isinstance(requires, str)):
            continue  # a field is missing: schema says which
        graph.as_topic.add(topic)
        graph.as_requires.add(requires)
        if topic not in topics or requires not in topics:
            unknown = " i ".join(f"„{end}“" for end in (topic, requires) if end not in topics)
            issues.add(path, where, "V5-edge-endpoint", f"grana pokazuje na nepostojeću temu: {unknown}")
            continue
        if (topic, requires) in pairs:
            issues.add(path, where, "V5-duplicate", "ista grana je navedena više puta")
            continue
        pairs.add((topic, requires))
        if frozenset((topic, requires)) in linked:
            issues.add(path, where, "V5-reverse-pair", f"postoji i suprotna grana {requires} → {topic}; dve teme ne mogu jedna drugu da zahtevaju")
        linked.add(frozenset((topic, requires)))
        if topic == requires:
            issues.add(path, where, "V5-self-loop", "tema ne može da zahteva samu sebe")
            continue
        graph.prerequisites[topic].append(requires)
        if edge.get("strength") == "hard":
            graph.hard[topic].append(requires)
        topic_grade, requires_grade = grades.get(topic), grades.get(requires)
        if topic_grade is not None and requires_grade is not None and requires_grade > topic_grade:
            issues.add(path, where, "V5-grade-order", f"tema je u {topic_grade}. razredu, a zahteva temu iz {requires_grade}. razreda")
        file_grade = corpus.edge_grade[index] if index < len(corpus.edge_grade) else None
        if topic_grade is not None and file_grade is not None and file_grade != topic_grade:
            issues.add(path, where, "V5-wrong-file", f"grana stoji u fajlu za {file_grade}. razred, a tema „{topic}“ je u {topic_grade}. razredu")
        graph.kept.append((topic, requires, edge.get("strength"), where, path))
    return graph


def _check_redundant(graph: _Graph, issues: Issues) -> None:
    """Rule V5 for a superfluous edge: it can be judged only once the whole graph is read."""
    for topic, requires, strength, where, path in graph.kept:
        if strength == "hard":
            successors, other = graph.hard, "drugi put samo preko čvrstih grana"
        elif strength == "soft":
            successors, other = graph.prerequisites, "drugi put"
        else:
            continue
        if _other_path(topic, requires, lambda node: successors[node]):
            issues.add(path, where, "V5-redundant", f"suvišna grana: do teme „{requires}“ već vodi {other}")


def _check_topics(corpus: Corpus, graph: _Graph, issues: Issues) -> None:
    """Rule V6: cycles, then roots and isolated topics."""
    for topic_id, record in corpus.topics.items():
        path = corpus.topic_file.get(topic_id, f"data/{corpus.subject}/topics.json")
        if graph.prerequisites[topic_id]:
            cycle = _cycle_through(topic_id, lambda node: graph.prerequisites[node])
            if cycle is not None:
                issues.add(path, topic_id, "V6-cycle", "ciklus zavisnosti: " + " → ".join(cycle))
        has_reason = "root_reason" in record
        if topic_id in graph.as_topic:
            if has_reason:
                issues.add(path, topic_id, "V6-root-reason-unneeded", "tema ima grane, pa joj „root_reason“ ne treba; to polje je samo za korene")
        elif topic_id in graph.as_requires:
            if not has_reason:
                issues.add(path, topic_id, "V6-root-reason-missing", "tema nema nijednu prethodnu temu, a nema ni „root_reason“ koji objašnjava zašto je koren")
        elif not has_reason:
            issues.add(path, topic_id, "V6-isolated", "tema nema nijednu granu u oba smera i nema „root_reason“; poveži je s grafom ili objasni zašto stoji sama")


def _other_path(start: str, target: str, successors: Successors) -> bool:
    """Is ``target`` reachable from ``start`` without the direct edge ``start → target``?"""
    seen = {start}
    stack = [node for node in successors(start) if node != target]
    while stack:
        node = stack.pop()
        if node == target:
            return True
        if node in seen:
            continue
        seen.add(node)
        stack.extend(successors(node))
    return False


def _cycle_through(start: str, successors: Successors) -> list[str] | None:
    """The shortest cycle through ``start``, as ``[start, …, start]``; ``None`` when there is none."""
    parent: dict[str, str] = {}
    queue: deque[str] = deque()
    for node in successors(start):
        if node not in parent:
            parent[node] = start
            queue.append(node)
    while queue:
        node = queue.popleft()
        for other in successors(node):
            if other == start:
                chain = [node]
                while parent[chain[-1]] != start:
                    chain.append(parent[chain[-1]])
                return [start, *reversed(chain), start]
            if other not in parent:
                parent[other] = node
                queue.append(other)
    return None
