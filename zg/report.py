"""Counts for the README, and the per-grade view of what the gates have verified."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from . import ledger
from .corpus import Corpus

START = "<!-- zg:stats -->"
END = "<!-- /zg:stats -->"
HEADER = "| Razred | Teme | Grane | Zadaci |"


def questions_of_grade(corpus: Corpus, grade: int) -> list[dict]:
    """The questions of one grade in file order; a question belongs to the grade of its topic."""
    return [question for question in corpus.questions.values() if _grade(corpus, question.get("topic")) == grade]


def stats(corpus: Corpus) -> dict:
    """Totals and, per grade, topics, edges, questions and outcomes of the curriculum editions."""
    by_grade = {}
    for grade in sorted(corpus.grades):
        by_grade[str(grade)] = {
            "topics": len(_topics(corpus, grade)),
            "edges": len(_edges(corpus, grade)),
            "questions": len(questions_of_grade(corpus, grade)),
            "outcomes": sum(len(edition.outcomes) for edition in corpus.editions.values() if edition.grade == grade),
        }
    strength = Counter(edge.get("strength") if isinstance(edge, dict) else None for edge in corpus.edge_list)
    return {
        "topics": len(corpus.topics),
        "edges": len(corpus.edge_list),
        "hard": strength["hard"],
        "soft": strength["soft"],
        "questions": len(corpus.questions),
        "outcomes": sum(row["outcomes"] for row in by_grade.values()),
        "by_grade": by_grade,
    }


def status(corpus: Corpus, path: Path | str | None = None) -> dict:
    """Per grade: the counts, and for every gate how many records are verified and which are stale.

    ``stale`` holds the ids that changed since they were marked or were never
    marked (question ids; ``topic>requires`` for the ``edges`` gate). A gate with
    no section in the ledger never ran: it verifies nothing and says so with
    ``never_run``. Without ``path`` the ledger is the one in the corpus root, so
    ``zg status --root X`` never reads this repository's own ledger.
    """
    path = _ledger_path(corpus, path)
    marks = ledger.load_ledger(path)
    stale = {gate: set(ledger.stale(gate, corpus, path)) for gate in ledger.GATES}
    grades = {}
    for grade in sorted(corpus.grades):
        questions = [question.get("id") for question in questions_of_grade(corpus, grade)]
        edges = [ledger.edge_id(edge) for edge in _edges(corpus, grade)]
        gates = {}
        for gate in ledger.GATES:
            if not isinstance(marks.get(gate), dict):
                gates[gate] = {"verified": 0, "stale": [], "never_run": True}
                continue
            ids = edges if gate == ledger.EDGES else questions
            outdated = [record_id for record_id in ids if record_id in stale[gate]]
            gates[gate] = {"verified": len(ids) - len(outdated), "stale": outdated}
        outcomes = [outcome_id for edition in corpus.editions.values() if edition.grade == grade for outcome_id in edition.outcomes]
        grades[str(grade)] = {
            "topics": len(_topics(corpus, grade)),
            "edges": len(edges),
            "questions": len(questions),
            "outcomes": len(outcomes),
            "outcomes_without_topic": sum(1 for outcome_id in outcomes if outcome_id in corpus.unmapped),
            "gates": gates,
        }
    return {"grades": grades}


def readme_block(corpus: Corpus) -> str:
    """The Markdown table that goes between the two markers of the README."""
    counts = stats(corpus)
    lines = [HEADER, "|---|---|---|---|"]
    for grade, row in counts["by_grade"].items():
        lines.append(f"| {grade}. razred | {row['topics']} | {row['edges']} | {row['questions']} |")
    lines.append(f"| Ukupno | {counts['topics']} | {counts['edges']} | {counts['questions']} |")
    return "\n".join(lines)


def check_readme(text: str, block: str) -> bool:
    """True when the README ``text`` carries ``block`` verbatim between the two marker lines."""
    lines = [line.strip() for line in text.splitlines()]
    try:
        start, end = lines.index(START), lines.index(END)
    except ValueError:
        return False
    return start < end and _inner_lines(block) in "\n".join(lines[start + 1 : end])


def dumps_stats(corpus: Corpus) -> str:
    return json.dumps(stats(corpus), ensure_ascii=False, indent=2)


def dumps_status(corpus: Corpus, path: Path | str | None = None) -> str:
    return json.dumps(status(corpus, path), ensure_ascii=False, indent=2)


def _ledger_path(corpus: Corpus, path) -> Path:
    """The ledger that belongs to a corpus is ``data/ledger.json`` in its root (``ledger.LEDGER`` here)."""
    return corpus.root / "data" / "ledger.json" if path is None else Path(path)


def _inner_lines(block: str) -> str:
    return "\n".join(line.strip() for line in block.splitlines())


def _grade(corpus: Corpus, topic_id) -> object:
    topic = corpus.topics.get(topic_id)
    return topic.get("grade") if isinstance(topic, dict) else None


def _topics(corpus: Corpus, grade: int) -> list[dict]:
    return [topic for topic in corpus.topics.values() if topic.get("grade") == grade]


def _edges(corpus: Corpus, grade: int) -> list[dict]:
    """An edge belongs to the grade of its dependent topic: that is the file it lives in."""
    return [edge for edge in corpus.edge_list if isinstance(edge, dict) and _grade(corpus, edge.get("topic")) == grade]
