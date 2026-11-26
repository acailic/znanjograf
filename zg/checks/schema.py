"""Structural rules over the whole corpus.

V1: files that failed to load. V2: the fields of a record. V3: ids. V4: enumerations and grades.
V10: formulas. V11: aliases.

Records are the plain dicts ``Corpus`` holds, so ``check_record`` also serves the
other gates wherever they meet a record of a known kind.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterator

from .. import paths
from ..corpus import Corpus
from ..issues import Issues

MAX_ID_LENGTH = 48
MAX_GRADE = 8

# ``\d`` would also take non-ASCII digits and ``$`` would also match in front of
# a trailing newline; an id is plain ASCII, so both ends are pinned.
_SLUG = r"mat-[a-z0-9]+(-[a-z0-9]+)*"
TOPIC_ID = re.compile(rf"^{_SLUG}\Z")
QUESTION_ID = re.compile(rf"^(?P<topic>{_SLUG})-q(?P<number>[0-9]+)\Z")
OUTCOME_ID = re.compile(r"^g[1-8]-[0-9]{4}-[0-9]{3}\Z")
EDITION_ID = re.compile(r"^g[1-8]-[0-9]{4}\Z")

ENUMS: dict[str, frozenset[str]] = {
    "area": frozenset({"numbers", "geometry", "data"}),
    "kind": frozenset({"concept", "procedure", "problem", "reasoning"}),
    "level": frozenset({"basic", "standard"}),
    "type": frozenset({"numeric", "choice"}),
    "strength": frozenset({"hard", "soft"}),
    "match": frozenset({"exact", "partial"}),
    "outcome_level": frozenset({"basic", "medium", "advanced"}),
}

# Every field a record of each kind may have, and which of them may be left out.
FIELDS: dict[str, set[str]] = {
    "topic": {"id", "grade", "area", "unit", "kind", "name", "summary", "mastery", "curriculum", "root_reason"},
    "edge": {"topic", "requires", "strength", "reason"},
    "question": {"id", "topic", "level", "type", "prompt", "figure", "choices", "answer", "check", "round_to", "explanation",
                 "points_to"},
    "choice": {"id", "text"},
    "outcome": {"id", "text", "page", "code", "level", "area", "unit"},
    "theme": {"name", "area", "hours", "content", "page"},
    "curriculum_ref": {"edition", "outcome", "match"},
}
OPTIONAL: dict[str, set[str]] = {
    "topic": {"root_reason"},
    "edge": set(),
    "question": {"figure", "choices", "points_to", "round_to"},
    "choice": set(),
    "outcome": {"code", "level", "area", "unit"},
    "theme": {"area", "hours", "content", "page"},
    "curriculum_ref": set(),
}
REQUIRED: dict[str, set[str]] = {kind: fields - OPTIONAL[kind] for kind, fields in FIELDS.items()}
# Top level of an edition file (spec §5.3): the header plus the two lists.
EDITION_FIELDS = {"edition", "grade", "applies_from", "themes", "outcomes", "notes"}

Predicate = Callable[[object], bool]


def _text(value) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _hours(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0


def _mastery(value) -> bool:
    return isinstance(value, list) and 2 <= len(value) <= 3 and all(_text(item) for item in value)


def _texts(value) -> bool:
    return isinstance(value, list) and all(_text(item) for item in value)


def _points_to(value) -> bool:
    return isinstance(value, dict) and all(_text(target) for target in value.values())


def _is_list(value) -> bool:
    return isinstance(value, list)


def _is_dict(value) -> bool:
    return isinstance(value, dict)


def _list(value) -> list:
    """The value when it is a list, else nothing to walk; the wrong type itself is reported by the field's rule."""
    return value if isinstance(value, list) else []


# What a value must be, field by field: rule V2. Which text an enumerated field
# may hold, and how large a number may be, is rule V4 and is checked in run().
_TEXT_FIELDS = {
    "topic": {"id", "unit", "name", "summary", "root_reason"},
    "edge": {"topic", "requires", "reason"},
    "question": {"id", "topic", "prompt", "answer", "check", "explanation"},
    "choice": {"id", "text"},
    "outcome": {"id", "text", "code", "unit"},
    "theme": {"name"},
    "curriculum_ref": {"edition", "outcome"},
}
_INT_FIELDS = {"topic": {"grade"}, "question": {"round_to"}, "outcome": {"page"}, "theme": {"page"}}
_ENUM_FIELDS = {
    "topic": {"area": "area", "kind": "kind"},
    "edge": {"strength": "strength"},
    "question": {"level": "level", "type": "type"},
    "curriculum_ref": {"match": "match"},
    "outcome": {"level": "outcome_level", "area": "area"},
    "theme": {"area": "area"},
}
_STRUCTURE_FIELDS: dict[tuple[str, str], tuple[Predicate, str]] = {
    ("topic", "mastery"): (_mastery, "mora biti niz od 2 do 3 neprazna teksta"),
    ("topic", "curriculum"): (_is_list, "mora biti niz stavaka {edition, outcome, match}"),
    ("question", "figure"): (_is_dict, "mora biti objekat, opis slike"),
    ("question", "choices"): (_is_list, "mora biti niz stavaka {id, text}"),
    ("question", "points_to"): (_points_to, "mora biti rečnik „id ponude“ → id teme, s nepraznim vrednostima"),
    ("theme", "hours"): (_hours, "mora biti broj koji nije negativan"),
    ("theme", "content"): (_texts, "mora biti niz nepraznih tekstova"),
}

# A field that holds records of another kind; each one is checked as that kind.
_NESTED = {"topic": ("curriculum", "curriculum_ref"), "question": ("choices", "choice")}


def _rules() -> dict[tuple[str, str], tuple[Predicate, str]]:
    rules = dict(_STRUCTURE_FIELDS)
    for table, test, must in (
        (_TEXT_FIELDS, _text, "mora biti neprazan tekst"),
        (_INT_FIELDS, _int, "mora biti ceo broj"),
        (_ENUM_FIELDS, _text, "mora biti tekst"),
    ):
        for kind, fields in table.items():
            for field in fields:
                rules[kind, field] = (test, must)
    return rules


_RULES = _rules()

REGISTRY_PATH = paths.REGISTRY_FILE.relative_to(paths.ROOT).as_posix()
ALIASES_PATH = paths.ALIASES_FILE.relative_to(paths.ROOT).as_posix()


def _excerpt(text: str, limit: int = 40) -> str:
    return text if len(text) <= limit else text[:limit] + "…"


def _describe(value) -> str:
    """The value as a message quotes it: enough to recognise what was written."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return f"broj {value}"
    if isinstance(value, str):
        return f"tekst „{_excerpt(value)}“"
    if isinstance(value, list):
        return f"niz dužine {len(value)}"
    if isinstance(value, dict):
        return f"objekat {_excerpt(json.dumps(value, ensure_ascii=False))}"
    return type(value).__name__


def _listing(values) -> str:
    return ", ".join(f"„{value}“" for value in sorted(values))


def iter_strings(record: object) -> Iterator[str]:
    """Every string value of a record, also the ones inside lists and dicts; keys are left out."""
    if isinstance(record, str):
        yield record
    elif isinstance(record, dict):
        for value in record.values():
            yield from iter_strings(value)
    elif isinstance(record, list):
        for item in record:
            yield from iter_strings(item)


def check_record(record: object, kind: str, where: str, path: str, issues: Issues) -> None:
    """Rule V2 for one record of a known ``kind``: no unknown field, every required one, every value of its type."""
    if not isinstance(record, dict):
        issues.add(path, where, "V2-type", f"zapis mora biti objekat s poljima, a jest {_describe(record)}")
        return
    allowed = FIELDS[kind]
    for key in record:
        if key not in allowed:
            issues.add(path, where, "V2-unknown-field", f"nepoznato polje „{key}“ u zapisu vrste „{kind}“; dozvoljena su: {_listing(allowed)}")
    for key in sorted(allowed):
        if key not in record:
            if key in REQUIRED[kind]:
                issues.add(path, where, "V2-missing-field", f"obavezno polje „{key}“ nedostaje")
            continue
        rule = _RULES.get((kind, key))
        if rule is not None and not rule[0](record[key]):
            issues.add(path, where, "V2-type", f"polje „{key}“ {rule[1]}, a jest {_describe(record[key])}")
    nested = _NESTED.get(kind)
    if nested is not None:
        field, nested_kind = nested
        for index, item in enumerate(_list(record.get(field))):
            check_record(item, nested_kind, f"{where}.{field}[{index}]", path, issues)


def _check_enums(kind: str, record: dict, where: str, path: str, issues: Issues) -> None:
    """Rule V4: an enumerated field holds a value from its set."""
    for field, name in _ENUM_FIELDS.get(kind, {}).items():
        value = record.get(field)
        if _text(value) and value not in ENUMS[name]:
            issues.add(path, where, "V4-enum", f"polje „{field}“ ima vrednost „{value}“, a dozvoljene su: {_listing(ENUMS[name])}")


def _check_grade(record: dict, where: str, path: str, issues: Issues) -> None:
    grade = record.get("grade")
    if _int(grade) and not 1 <= grade <= MAX_GRADE:
        issues.add(path, where, "V4-grade", f"razred mora biti broj od 1 do {MAX_GRADE}, a jest {grade}")


def _check_dollars(record: object, where: str, path: str, issues: Issues) -> None:
    """Rule V10: in every string the ``$`` come in pairs and no ``$…$`` is empty."""
    for text in iter_strings(record):
        marks = [index for index, char in enumerate(text) if char == "$"]
        if len(marks) % 2:
            issues.add(path, where, "V10-dollar", f"neparan broj znakova `$` ({len(marks)}): „{_excerpt(text, 60)}“")
        elif any(not text[start + 1:end].strip() for start, end in zip(marks[::2], marks[1::2])):
            issues.add(path, where, "V10-dollar", f"prazna formula `$…$`: „{_excerpt(text, 60)}“")


def _id(record: object) -> str | None:
    return record["id"] if isinstance(record, dict) and isinstance(record.get("id"), str) else None


def _paths(known: list[str | None], fallback: str) -> list[str]:
    """The file of every record. Corpus keeps a file per id, so a record without an id takes the file of the one before it."""
    resolved: list[str | None] = []
    for file in known:
        if file:
            resolved.append(file)
        elif resolved:
            resolved.append(resolved[-1])
        else:
            resolved.append(None)
    first = next((file for file in resolved if file), fallback)
    return [file or first for file in resolved]


def _in_files(records: list, known: list[str | None], fallback: str, label: Callable[[object, int], str]) -> Iterator[tuple[object, str, str]]:
    """``(record, where, path)`` in file order; ``label`` names a record by its position in its file."""
    position: dict[str, int] = {}
    for record, path in zip(records, _paths(known, fallback)):
        index = position.get(path, 0)
        position[path] = index + 1
        yield record, label(record, index), path


def _named(records: list, files: dict[str, str], subject: str, name: str) -> Iterator[tuple[object, str, str]]:
    """``(record, where, path)`` for topics or questions: ``where`` is the id, or the position in the file when there is none."""
    def label(record, index):
        record_id = _id(record)
        return record_id if _text(record_id) else f"{name}[{index}]"

    return _in_files(records, [files.get(_id(record)) for record in records], f"data/{subject}/{name}.json", label)


def iter_edges(corpus: Corpus) -> Iterator[tuple[object, str, str]]:
    """``(edge, where, path)`` for every edge in file order; ``where`` is ``topic>requires``."""
    grades = corpus.edge_grade[: len(corpus.edge_list)]
    known = [corpus.edge_file.get(grade) for grade in grades] + [None] * (len(corpus.edge_list) - len(grades))

    def label(edge, index):
        ends = [edge.get(field) for field in ("topic", "requires")] if isinstance(edge, dict) else []
        return f"{ends[0]}>{ends[1]}" if len(ends) == 2 and all(isinstance(end, str) for end in ends) else f"edges[{index}]"

    return _in_files(corpus.edge_list, known, f"data/{corpus.subject}/edges.json", label)


def _is_topic_id(topic_id: str) -> bool:
    return len(topic_id) <= MAX_ID_LENGTH and TOPIC_ID.fullmatch(topic_id) is not None


def _check_topic_id(topic_id: str, where: str, path: str, issues: Issues) -> None:
    """Rule V3 for a topic id."""
    if len(topic_id) > MAX_ID_LENGTH:
        issues.add(path, where, "V3-id-format", f"id „{topic_id}“ ima više od {MAX_ID_LENGTH} znakova")
    elif not _is_topic_id(topic_id):
        issues.add(path, where, "V3-id-format", f"id „{topic_id}“ ne odgovara pravilu: „mat-“, pa mala slova, cifre i crtice")


def _topics(corpus: Corpus, issues: Issues) -> None:
    seen: dict[str, str] = {}  # id → file of its first occurrence
    for record, where, path in _named(corpus.topic_list, corpus.topic_file, corpus.subject, "topics"):
        check_record(record, "topic", where, path, issues)
        if not isinstance(record, dict):
            continue
        record_id = record.get("id")
        if isinstance(record_id, str):
            _check_topic_id(record_id, where, path, issues)
            if record_id in seen:
                issues.add(path, where, "V3-id-duplicate", f"id „{record_id}“ je već upotrebljen (prvi put u {seen[record_id]})")
            else:
                seen[record_id] = path
            if _is_topic_id(record_id) and record_id not in corpus.registry:
                issues.add(path, where, "V3-id-unregistered", f"tema „{record_id}“ nije upisana u {REGISTRY_PATH}")
        _check_enums("topic", record, where, path, issues)
        _check_grade(record, where, path, issues)
        for index, reference in enumerate(_list(record.get("curriculum"))):
            if not isinstance(reference, dict):
                continue
            reference_where = f"{where}.curriculum[{index}]"
            _check_enums("curriculum_ref", reference, reference_where, path, issues)
            for field, pattern, example in (("edition", EDITION_ID, "g1-2026"), ("outcome", OUTCOME_ID, "g1-2026-012")):
                value = reference.get(field)
                if isinstance(value, str) and not pattern.fullmatch(value):
                    issues.add(path, reference_where, "V3-id-format", f"„{value}“ u polju „{field}“ ne odgovara pravilu, npr. {example}")
        _check_dollars(record, where, path, issues)


def _questions(corpus: Corpus, issues: Issues) -> None:
    topics = corpus.topics
    seen: set[str] = set()
    for record, where, path in _named(corpus.question_list, corpus.question_file, corpus.subject, "questions"):
        check_record(record, "question", where, path, issues)
        if not isinstance(record, dict):
            continue
        question_id, topic_id = record.get("id"), record.get("topic")
        if isinstance(question_id, str):
            match = QUESTION_ID.fullmatch(question_id)
            if match is None or (isinstance(topic_id, str) and match["topic"] != topic_id):
                example = f"{topic_id}-q1" if _text(topic_id) else "<id teme>-q1"
                issues.add(path, where, "V3-qid-format", f"id pitanja „{question_id}“ treba da bude <id teme>-q<broj>, npr. {example}")
            if question_id in seen:
                issues.add(path, where, "V3-id-duplicate", f"id „{question_id}“ je već upotrebljen; id mora biti jedinstven")
            seen.add(question_id)
        if _text(topic_id) and topic_id not in topics:
            issues.add(path, where, "V3-id-unknown", f"pitanje pripada nepostojećoj temi „{topic_id}“")
        points_to = record.get("points_to")
        for choice_id, target in points_to.items() if isinstance(points_to, dict) else []:
            if _text(target) and target not in topics:
                issues.add(path, where, "V3-id-unknown", f"points_to za ponudu „{choice_id}“ pokazuje na nepostojeću temu „{target}“")
        _check_enums("question", record, where, path, issues)
        _check_dollars(record, where, path, issues)


def _edges(corpus: Corpus, issues: Issues) -> None:
    for edge, where, path in iter_edges(corpus):
        check_record(edge, "edge", where, path, issues)
        if isinstance(edge, dict):
            _check_enums("edge", edge, where, path, issues)
            _check_dollars(edge, where, path, issues)


def _file_lists(raw: dict, edition_id: str, path: str, issues: Issues) -> dict[str, list]:
    """``themes`` and ``outcomes`` of an edition file as lists, whatever the file says."""
    lists = {}
    for field in ("themes", "outcomes"):
        value = raw.get(field)
        if value is not None and not isinstance(value, list):
            issues.add(path, edition_id, "V2-type", f"polje „{field}“ mora biti niz, a jest {_describe(value)}")
        lists[field] = value if isinstance(value, list) else []
    return lists


def _editions(corpus: Corpus, issues: Issues) -> None:
    for edition_id, edition in sorted(corpus.editions.items()):
        path = edition.file or f"data/curriculum/{corpus.subject}/{edition_id}.json"
        if not EDITION_ID.fullmatch(edition_id):
            issues.add(path, edition_id, "V3-id-format", f"id izdanja „{edition_id}“ ne odgovara pravilu, npr. g1-2026")
        header = edition.raw if isinstance(edition.raw, dict) else {}
        for key in sorted(set(header) - EDITION_FIELDS):
            issues.add(path, key, "V2-unknown-field", f"nepoznato polje „{key}“ u zaglavlju izdanja „{edition_id}“")
        if "applies_from" in header and not isinstance(header["applies_from"], str):
            issues.add(path, "applies_from", "V2-type", "„applies_from“ mora biti niska, npr. „2026/27“")
        lists = _file_lists(header, edition_id, path, issues)
        for index, theme in enumerate(lists["themes"]):
            where = f"themes[{index}]"
            check_record(theme, "theme", where, path, issues)
            if isinstance(theme, dict):
                _check_enums("theme", theme, where, path, issues)
                _check_dollars(theme, where, path, issues)
        seen: set[str] = set()  # outcome ids of this edition
        for index, outcome in enumerate(lists["outcomes"]):
            outcome_id = _id(outcome)
            where = outcome_id if _text(outcome_id) else f"outcomes[{index}]"
            check_record(outcome, "outcome", where, path, issues)
            if not isinstance(outcome, dict):
                continue
            if outcome_id is not None:
                if not OUTCOME_ID.fullmatch(outcome_id):
                    issues.add(path, where, "V3-id-format", f"id ishoda „{outcome_id}“ ne odgovara pravilu, npr. g1-2026-012")
                if outcome_id in seen:
                    issues.add(path, where, "V3-id-duplicate", f"id ishoda „{outcome_id}“ je dvaput naveden u izdanju „{edition_id}“")
                seen.add(outcome_id)
            _check_enums("outcome", outcome, where, path, issues)
            _check_dollars(outcome, where, path, issues)


def _aliases(corpus: Corpus, issues: Issues) -> None:
    if not isinstance(corpus.aliases, dict):
        issues.add(ALIASES_PATH, "-", "V2-type", "sadržaj mora biti objekat „stari id“ → niz id-ova tema")
        return
    aliases = corpus.aliases
    targets: set[str] = set()
    for alias, value in aliases.items():
        if not (isinstance(alias, str) and _is_topic_id(alias)):
            issues.add(ALIASES_PATH, alias, "V3-id-format", f"stari id „{alias}“ ne odgovara pravilu za id teme")
        if not isinstance(value, list) or not value:
            issues.add(ALIASES_PATH, alias, "V11-alias-target", "vrednost aliasa mora biti neprazan niz id-ova postojećih tema")
            continue
        targets.update(target for target in value if isinstance(target, str))
        unknown = [target for target in value if not (_text(target) and target in corpus.topics)]
        if unknown:
            issues.add(ALIASES_PATH, alias, "V11-alias-target", f"alias „{alias}“ pokazuje na nepostojeću temu: {_listing(unknown)}")
    for alias in aliases:
        if alias in targets:
            issues.add(ALIASES_PATH, alias, "V11-alias-chain", f"alias „{alias}“ je cilj drugog aliasa; aliasi ne smeju da grade lance")


def _registry(corpus: Corpus, issues: Issues) -> None:
    for topic_id in sorted(corpus.registry, key=str):
        if not (isinstance(topic_id, str) and _is_topic_id(topic_id)):
            issues.add(REGISTRY_PATH, topic_id, "V3-id-format", f"upis u registru „{topic_id}“ ne odgovara pravilu za id teme")


def run(corpus: Corpus, issues: Issues) -> None:
    """V1–V4, V10 and V11 over the whole corpus. Mutates nothing; appends to ``issues``."""
    for path, message in corpus.load_errors:
        issues.add(path, "-", "V1-json", message)
    _topics(corpus, issues)
    _questions(corpus, issues)
    _edges(corpus, issues)
    _editions(corpus, issues)
    _aliases(corpus, issues)
    _registry(corpus, issues)