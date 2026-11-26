"""Helpers for tests: a fresh copy of the fixture, lookup by id, and writing it to disk."""

from __future__ import annotations

import copy
from pathlib import Path

from zg.corpus import Corpus, RawCorpus, jsonio
from tests.fixtures import raw


def fixture_raw() -> RawCorpus:
    """A deep copy, so a test may mutate anything without touching the module constants."""
    return RawCorpus(
        grades=list(raw.GRADES),
        topics=copy.deepcopy(raw.TOPICS),
        edges=copy.deepcopy(raw.EDGES),
        questions=copy.deepcopy(raw.QUESTIONS),
        editions=copy.deepcopy(raw.EDITIONS),
        registry=list(raw.REGISTRY),
        aliases=copy.deepcopy(raw.ALIASES),
        unmapped=dict(raw.UNMAPPED),
        sources=copy.deepcopy(raw.SOURCES),
        lexicon=dict(raw.DIGRAPHS),
        notation=copy.deepcopy(raw.NOTATION),
    )


def fixture_corpus() -> Corpus:
    return Corpus.from_raw("math", fixture_raw())


def grade_of(raw_corpus: RawCorpus, topic_id: str) -> int:
    for grade in raw_corpus.grades:
        if any(t["id"] == topic_id for t in raw_corpus.topics[grade]):
            return grade
    raise KeyError(topic_id)


def topic(raw_corpus: RawCorpus, topic_id: str) -> dict:
    return next(t for g in raw_corpus.grades for t in raw_corpus.topics[g] if t["id"] == topic_id)


def question(raw_corpus: RawCorpus, question_id: str) -> dict:
    return next(q for g in raw_corpus.grades for q in raw_corpus.questions[g] if q["id"] == question_id)


def add_edge(raw_corpus: RawCorpus, topic_id: str, requires: str, strength: str, reason: str = "test") -> None:
    raw_corpus.edges[grade_of(raw_corpus, topic_id)].append(
        {"topic": topic_id, "requires": requires, "strength": strength, "reason": reason}
    )


def notation_rules(raw_corpus: RawCorpus, rules: list[dict]) -> None:
    raw_corpus.notation = rules


def write_corpus(root: Path, raw_corpus: RawCorpus) -> Path:
    """Write the corpus as a real repository-shaped tree under ``root``."""
    root = Path(root)
    subject = root / "data" / "math"
    jsonio.dump({"subject": "math", "name": "Matematika", "grades": raw_corpus.grades, "areas": ["numbers", "geometry", "data"]}, subject / "meta.json")
    for grade in raw_corpus.grades:
        grade_dir = subject / f"g{grade}"
        jsonio.dump(raw_corpus.topics[grade], grade_dir / "topics.json")
        jsonio.dump(raw_corpus.edges[grade], grade_dir / "edges.json")
        jsonio.dump(raw_corpus.questions[grade], grade_dir / "questions.json")
    for edition_id, data in raw_corpus.editions.items():
        jsonio.dump(data, root / "data" / "curriculum" / "math" / f"{edition_id}.json")
    jsonio.dump(raw_corpus.sources, root / "data" / "curriculum" / "sources.json")
    jsonio.dump(raw_corpus.unmapped, root / "data" / "curriculum" / "unmapped.json")
    jsonio.dump({"topics": raw_corpus.registry}, root / "data" / "registry.json")
    jsonio.dump(raw_corpus.aliases, root / "data" / "aliases.json")
    jsonio.dump(raw_corpus.lexicon, root / "data" / "lint" / "digraphs.json")
    if raw_corpus.notation is not None:
        jsonio.dump(raw_corpus.notation, root / "data" / "lint" / "notation.json")
    return root
