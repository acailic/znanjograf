"""The whole dataset in memory: what the gates look at and what the site is built from.

Records stay plain dicts straight from JSON, so a gate can also be pointed at a
mutated copy in memory (that is how the tests exercise every rule).
"""

from __future__ import annotations

import copy
import heapq
from pathlib import Path

from . import jsonio, paths


class CorpusError(Exception):
    """The graph is not well-formed enough to answer this question."""


class Edition:
    """One curriculum edition file: the outcomes of one grade in one school year's program."""

    __slots__ = ("id", "grade", "raw", "outcomes", "file")

    def __init__(self, edition_id: str, raw: dict, file: str = "") -> None:
        self.id = edition_id
        grade = raw.get("grade")
        self.grade = grade if isinstance(grade, int) else int(edition_id[1:edition_id.index("-")])
        self.raw = raw
        self.outcomes: dict[str, dict] = {}
        for record in raw.get("outcomes") or []:
            if isinstance(record, dict) and isinstance(record.get("id"), str):
                self.outcomes.setdefault(record["id"], record)
        self.file = file


class RawCorpus:
    """A corpus as plain data, grade by grade — what the fixture helpers build."""

    def __init__(
        self,
        grades: list[int],
        topics: dict[int, list[dict]],
        edges: dict[int, list[dict]],
        questions: dict[int, list[dict]],
        editions: dict[str, dict],
        registry: list[str],
        aliases: dict[str, list[str]],
        unmapped: dict[str, str],
        sources: dict,
        lexicon: dict[str, str] | None = None,
        notation: list[dict] | None = None,
    ) -> None:
        self.grades = grades
        self.topics = topics
        self.edges = edges
        self.questions = questions
        self.editions = editions
        self.registry = registry
        self.aliases = aliases
        self.unmapped = unmapped
        self.sources = sources
        # None means: read the real rule files under data/lint/.
        self.lexicon = lexicon
        self.notation = notation

    def copy(self) -> RawCorpus:
        return copy.deepcopy(self)


class Corpus:
    def __init__(self, subject: str, root: Path) -> None:
        self.subject = subject
        self.root = Path(root)
        self.grades: list[int] = []
        self.topic_list: list[dict] = []
        self.edge_list: list[dict] = []
        self.question_list: list[dict] = []
        self.topics: dict[str, dict] = {}
        self.questions: dict[str, dict] = {}
        self.editions: dict[str, Edition] = {}
        self.registry: set[str] = set()
        self.aliases: dict[str, list[str]] = {}
        self.unmapped: dict[str, str] = {}
        self.sources: dict = {}
        self.review: dict = {}
        self.meta: dict = {}
        self.lexicon: dict[str, str] = {}
        self.notation: list[dict] = []
        # Where each record came from, for messages.
        self.topic_file: dict[str, str] = {}
        self.question_file: dict[str, str] = {}
        self.edition_file: dict[str, str] = {}
        self.edge_file: dict[int, str] = {}
        self.edge_grade: list[int] = []
        self.load_errors: list[tuple[str, str]] = []
        self._graph: tuple[dict, dict] | None = None

    # ----- building -----------------------------------------------------------------

    @classmethod
    def from_raw(cls, subject: str, raw: RawCorpus) -> Corpus:
        corpus = cls(subject, Path("."))
        corpus.grades = list(raw.grades)
        corpus.meta = {"subject": subject, "name": "Matematika", "areas": ["numbers", "geometry", "data"]}
        for grade in sorted(raw.grades):
            base = f"data/{subject}/g{grade}"
            corpus.edge_file[grade] = f"{base}/edges.json"
            for record in raw.topics.get(grade, []):
                corpus.topic_list.append(record)
                record_id = record.get("id")
                if isinstance(record_id, str):
                    corpus.topic_file.setdefault(record_id, f"{base}/topics.json")
                    corpus.topics.setdefault(record_id, record)
            for record in raw.edges.get(grade, []):
                corpus.edge_list.append(record)
                corpus.edge_grade.append(grade)
            for record in raw.questions.get(grade, []):
                corpus.question_list.append(record)
                record_id = record.get("id")
                if isinstance(record_id, str):
                    corpus.question_file.setdefault(record_id, f"{base}/questions.json")
                    corpus.questions.setdefault(record_id, record)
        for edition_id, data in raw.editions.items():
            edition = Edition(edition_id, data if isinstance(data, dict) else {}, f"data/curriculum/{subject}/{edition_id}.json")
            corpus.editions[edition_id] = edition
        corpus.registry = set(raw.registry)
        corpus.aliases = copy.deepcopy(raw.aliases)
        corpus.unmapped = copy.deepcopy(raw.unmapped)
        corpus.sources = copy.deepcopy(raw.sources)
        corpus.lexicon = {} if raw.lexicon is None else dict(raw.lexicon)
        corpus.notation = [] if raw.notation is None else copy.deepcopy(raw.notation)
        if raw.lexicon is None or raw.notation is None:
            corpus.load_lint_rules()
        return corpus

    @classmethod
    def load(cls, subject: str = "math", root: Path | str | None = None) -> Corpus:
        root = Path(root) if root is not None else paths.ROOT
        corpus = cls(subject, root)
        data_dir = root / "data" / subject
        meta = jsonio.load_or_none(data_dir / "meta.json", corpus.load_errors, corpus._rel)
        grades: list[int] = []
        if isinstance(meta, dict):
            corpus.meta = meta
            grades = [g for g in meta.get("grades", []) if isinstance(g, int)]
        if not grades:
            grades = sorted(int(p.name[1:]) for p in data_dir.glob("g[0-9]") if p.is_dir())
        corpus.grades = grades
        for grade in grades:
            grade_path = data_dir / f"g{grade}"
            for name, target in (("topics", corpus.topic_list), ("edges", corpus.edge_list), ("questions", corpus.question_list)):
                file = grade_path / f"{name}.json"
                data = jsonio.load_or_none(file, corpus.load_errors, corpus._rel)
                if data is None:
                    continue
                if not isinstance(data, list):
                    corpus.load_errors.append((corpus._rel(file), "sadržaj mora biti niz zapisa"))
                    continue
                target.extend(data)
                if name == "topics":
                    for record in data:
                        if isinstance(record, dict) and isinstance(record.get("id"), str):
                            corpus.topic_file.setdefault(record["id"], corpus._rel(file))
                            corpus.topics.setdefault(record["id"], record)
                elif name == "questions":
                    for record in data:
                        if isinstance(record, dict) and isinstance(record.get("id"), str):
                            corpus.question_file.setdefault(record["id"], corpus._rel(file))
                            corpus.questions.setdefault(record["id"], record)
                else:
                    corpus.edge_file[grade] = corpus._rel(file)
                    corpus.edge_grade.extend([grade] * len(data))
        curriculum = root / "data" / "curriculum"
        for file in sorted((curriculum / subject).glob("*.json")):
            data = jsonio.load_or_none(file, corpus.load_errors, corpus._rel)
            if isinstance(data, dict):
                corpus.editions[file.stem] = Edition(file.stem, data, corpus._rel(file))
        corpus.sources = _optional(curriculum / "sources.json", corpus, dict)
        corpus.unmapped = _optional(curriculum / "unmapped.json", corpus, dict)
        registry = _optional(root / "data" / "registry.json", corpus, dict)
        corpus.registry = set(registry.get("topics", [])) if registry else set()
        corpus.aliases = _optional(root / "data" / "aliases.json", corpus, dict)
        corpus.review = _optional(root / "data" / "review" / "teachers.json", corpus, dict)
        corpus.load_lint_rules()
        return corpus

    def load_lint_rules(self) -> None:
        base = self.root / "data" / "lint"
        lexicon = jsonio.load_or_none(base / "digraphs.json", self.load_errors, self._rel)
        notation = jsonio.load_or_none(base / "notation.json", self.load_errors, self._rel)
        if isinstance(lexicon, dict):
            self.lexicon = {k: v for k, v in lexicon.items() if isinstance(v, str)}
        if isinstance(notation, list):
            self.notation = [rule for rule in notation if isinstance(rule, dict)]

    def _rel(self, path: Path | str) -> str:
        path = Path(path)
        try:
            return path.resolve().relative_to(self.root.resolve()).as_posix()
        except ValueError:
            return str(path)

    # ----- derived views (need a well-formed graph) ----------------------------------

    def _adjacency(self) -> tuple[dict[str, list[tuple[str, object]]], dict[str, list[str]]]:
        if self._graph is None:
            prerequisites: dict[str, list[tuple[str, object]]] = {tid: [] for tid in self.topics}
            dependents: dict[str, list[str]] = {tid: [] for tid in self.topics}
            for index, edge in enumerate(self.edge_list):
                topic, requires = edge.get("topic"), edge.get("requires")
                if topic not in prerequisites or requires not in prerequisites:
                    raise CorpusError(f"grana {index}: pokazuje na nepostojeću temu")
                prerequisites[topic].append((requires, edge.get("strength")))
                dependents[requires].append(topic)
            self._assert_acyclic(prerequisites)
            self._graph = (prerequisites, dependents)
        return self._graph

    @staticmethod
    def _assert_acyclic(prerequisites: dict[str, list[tuple[str, object]]]) -> None:
        open_, closed = 1, 2
        colour = dict.fromkeys(prerequisites, 0)
        for start in prerequisites:
            if colour[start]:
                continue
            colour[start] = open_
            stack = [(start, iter(prerequisites[start]))]
            while stack:
                node, edges = stack[-1]
                descended = False
                for other, _ in edges:
                    if colour[other] == open_:
                        raise CorpusError(f"ciklus kroz temu {other}")
                    if colour[other] == 0:
                        colour[other] = open_
                        stack.append((other, iter(prerequisites[other])))
                        descended = True
                        break
                if not descended:
                    colour[node] = closed
                    stack.pop()

    def prereqs(self, topic_id: str, strengths: tuple[str, ...] = ("hard", "soft")) -> list[dict]:
        return [e for e in self.edge_list if e.get("topic") == topic_id and e.get("strength") in strengths]

    def hard_ancestors(self, topic_id: str) -> set[str]:
        prerequisites, _ = self._adjacency()
        return self._reach(topic_id, lambda node: [b for b, strength in prerequisites[node] if strength == "hard"])

    def ancestors(self, topic_id: str) -> set[str]:
        prerequisites, _ = self._adjacency()
        return self._reach(topic_id, lambda node: [b for b, _ in prerequisites[node]])

    def descendants(self, topic_id: str) -> set[str]:
        _, dependents = self._adjacency()
        return self._reach(topic_id, lambda node: dependents[node])

    @staticmethod
    def _reach(start: str, step) -> set[str]:
        seen: set[str] = set()
        queue = [start]
        while queue:
            node = queue.pop()
            for other in step(node):
                if other not in seen:
                    seen.add(other)
                    queue.append(other)
        seen.discard(start)
        return seen

    def learning_order(self) -> list[str]:
        """Topological order: grade ascending, then file order inside the grade."""
        prerequisites, dependents = self._adjacency()
        position: dict[str | None, int] = {}
        for index, record in enumerate(self.topic_list):
            position.setdefault(record.get("id"), index)
        grade_of = {tid: (t.get("grade") if isinstance(t.get("grade"), int) else 99) for tid, t in self.topics.items()}

        def key(tid: str) -> tuple[int, int, str]:
            return (grade_of[tid], position.get(tid, 0), tid)

        remaining = {tid: len(edges) for tid, edges in prerequisites.items()}
        heap = [key(tid) for tid, count in remaining.items() if count == 0]
        heapq.heapify(heap)
        order: list[str] = []
        while heap:
            tid = heapq.heappop(heap)[2]
            order.append(tid)
            for dependent in dependents[tid]:
                remaining[dependent] -= 1
                if remaining[dependent] == 0:
                    heapq.heappush(heap, key(dependent))
        if len(order) != len(prerequisites):
            raise CorpusError("graf ima ciklus")
        return order

    def grade_exits(self, grade: int) -> list[str]:
        _, dependents = self._adjacency()
        return [
            tid
            for tid in self.learning_order()
            if self.topics[tid].get("grade") == grade
            and not any(self.topics[d].get("grade") == grade for d in dependents[tid])
        ]

    def bank(self, topic_id: str) -> list[dict]:
        return [q for q in self.question_list if q.get("topic") == topic_id]


def _optional(file: Path, corpus: Corpus, kind: type) -> dict | list:
    data = jsonio.load_or_none(file, corpus.load_errors, corpus._rel)
    return data if isinstance(data, kind) else kind()
