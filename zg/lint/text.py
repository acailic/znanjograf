"""Lint of running text: words without diacritics (L2), digraph words (L3), spelling and units (L4), length (L5), mixed script (L7).

Every Serbian text field of the corpus is read word by word outside the protected
spans (math, markup, URLs, unit symbols). ``run`` mutates nothing and appends to ``issues``.
"""

from __future__ import annotations

import re
from typing import Iterator, NamedTuple

from zg.corpus import Corpus
from zg.issues import Issues
from zg.translit import rules
from zg.translit.protect import split_protected

LEXICON_FILE = "data/lint/digraphs.json"
# Longest text of a task by grade band (spec §6.4); explanations have one limit everywhere.
PROMPT_LIMITS = {1: 200, 2: 200, 3: 300, 4: 300}
EXPLANATION_LIMIT = 400
_GRADE_BANDS = {200: "1–2. razredu", 300: "3–4. razredu", 400: "5–8. razredu"}

_DIACRITICS = frozenset("čćđšž")
_CYRILLIC = re.compile(r"[\u0400-\u04ff\u0500-\u052f]")


def _decimal_message(match: re.Match) -> str:
    whole = match.group()
    comma, formula = whole.replace(".", ","), whole.replace(".", "{,}")
    return f"„{whole}“: decimalni broj piše se sa zarezom („{comma}“), a u formuli „{formula}“"


def _percent_message(match: re.Match) -> str:
    return f"„{match.group(1)}%“: ispred znaka % ide razmak, „{match.group(1)} %“"


# Spelling outside math. ``...`` at the end of a list is an ellipsis, not a full stop
# with a space before it.
_ORTHOGRAPHY = (
    (re.compile(r"\d\.\d"), _decimal_message),
    (re.compile(r"(\d+)%"), _percent_message),
    (re.compile(r"  "), lambda match: "dva razmaka zaredom"),
    (re.compile(r" (?=([,;:!?]|\.(?!\.)))"), lambda match: f"razmak ispred znaka „{match.group(1)}“"),
)


class TextField(NamedTuple):
    path: str  # repository-relative file
    where: str  # record id and field, e.g. "mat-sabiranje-do-20-q3.prompt"
    text: str


# ----- gates -------------------------------------------------------------------------

def run(corpus: Corpus, issues: Issues) -> None:
    """L2–L5 on the source text and L7 on the Cyrillic text the site is built from."""
    fields = list(iter_text_fields(corpus))
    folded: dict[str, str] = {}  # fold of a word with diacritics -> that word
    for field in fields:
        for word, _ in rules.iter_words(field.text):
            if _has_diacritic(word):
                folded.setdefault(rules.fold(word), word)
    for field in fields:
        _check_field(corpus, field, folded, issues)
    _check_lengths(corpus, issues)


def check_mixed_script(text: str, where: str, path: str, issues: Issues) -> None:
    """L7: in Cyrillic text no word mixes the scripts and no Serbian word is left in Latin."""
    seen: set = set()
    for word, _ in rules.iter_words(text):
        cyrillic = [char for char in word if _is_cyrillic(char)]
        latin = [char for char in word if char.isalpha() and not _is_cyrillic(char)]
        if cyrillic and latin:
            _report(seen, issues, path, where, "L7-mixed-script", word, f"reč „{word}“ meša ćirilicu i latinicu")
        elif not cyrillic and rules.is_transliterated(word):
            message = f"reč „{word}“ je srpska reč koja je ostala na latinici u ćiriličnom tekstu"
            _report(seen, issues, path, where, "L7-mixed-script", word, message)


def iter_text_fields(corpus: Corpus) -> Iterator[TextField]:
    """Every Serbian text field of topics, edges, questions and outcomes, in file order."""
    for index, topic in enumerate(corpus.topic_list):
        if not isinstance(topic, dict):
            continue
        topic_id = _record_id(topic, "topics", index)
        path = corpus.topic_file.get(topic_id, "")
        yield from _fields(path, topic_id, topic, ("name", "summary", "unit", "root_reason"))
        yield from _items(path, f"{topic_id}.mastery", topic.get("mastery"))
    for edge in corpus.edge_list:
        if isinstance(edge, dict) and isinstance(edge.get("reason"), str):
            where = f"{edge.get('topic')} -> {edge.get('requires')}.reason"
            yield TextField(_edge_path(corpus, edge), where, edge["reason"])
    yield from _question_fields(corpus)
    for edition_id, edition in corpus.editions.items():
        path = corpus.edition_file.get(edition_id, edition.file)
        for outcome_id, outcome in edition.outcomes.items():
            yield from _fields(path, outcome_id, outcome, ("text", "unit"))


def missing_from_lexicon(corpus: Corpus) -> list[str]:
    """Digraph words of the corpus that its lexicon does not classify: lowercase, distinct, in alphabet order."""
    found: set[str] = set()
    for field in iter_text_fields(corpus):
        found.update(
            word.lower() for word, _ in rules.iter_words(field.text)
            if rules.needs_lexicon(word) and word.lower() not in corpus.lexicon
        )
    return sorted(found, key=rules.collation_key)


# ----- one field ---------------------------------------------------------------------

def _check_field(corpus: Corpus, field: TextField, folded: dict[str, str], issues: Issues) -> None:
    seen: set = set()
    for word, _ in rules.iter_words(field.text):
        if not _has_diacritic(word):
            twin = folded.get(rules.fold(word))
            if twin is not None:
                message = f"reč „{word}“ nema dijakritike, a u korpusu postoji „{twin}“"
                _report(seen, issues, field.path, field.where, "L2-folded", rules.fold(word), message)
        if rules.needs_lexicon(word) and word.lower() not in corpus.lexicon:
            digraph = rules.DIGRAPH_PATTERN.search(word).group().lower()
            message = (
                f"reč „{word}“ sadrži „{digraph}“, a nije klasifikovana u {LEXICON_FILE}: "
                f"upiši „{word.lower()}: digraph“ ili „{word.lower()}: split:levo|desno“"
            )
            _report(seen, issues, field.path, field.where, "L3-digraph", word.lower(), message)
    for segment, protected in split_protected(field.text):
        if protected:
            continue
        for pattern, message_of in _ORTHOGRAPHY:
            for match in pattern.finditer(segment):
                message = message_of(match)
                _report(seen, issues, field.path, field.where, "L4-orthography", message, message)
    for match in _CYRILLIC.finditer(field.text):
        message = f"slovo „{match.group()}“ je ćirilično, a izvor mora biti na latinici"
        _report(seen, issues, field.path, field.where, "L4-orthography", "cyrillic", message)
    check_mixed_script(rules.to_cyrillic(field.text, corpus.lexicon), field.where, field.path, issues)


def _check_lengths(corpus: Corpus, issues: Issues) -> None:
    for index, question in enumerate(corpus.question_list):
        if not isinstance(question, dict):
            continue
        question_id = _record_id(question, "questions", index)
        path = corpus.question_file.get(question_id, "")
        topic = corpus.topics.get(question.get("topic"))
        grade = topic.get("grade") if isinstance(topic, dict) else None
        prompt = question.get("prompt")
        if isinstance(prompt, str) and isinstance(grade, int):
            limit = PROMPT_LIMITS.get(grade, EXPLANATION_LIMIT)
            if len(prompt) > limit:
                message = f"tekst zadatka ima {len(prompt)} znakova, a najviše {limit} u {_GRADE_BANDS[limit]}"
                issues.add(path, f"{question_id}.prompt", "L5-length", message)
        explanation = question.get("explanation")
        if isinstance(explanation, str) and len(explanation) > EXPLANATION_LIMIT:
            message = f"objašnjenje ima {len(explanation)} znakova, a najviše {EXPLANATION_LIMIT}"
            issues.add(path, f"{question_id}.explanation", "L5-length", message)


# ----- helpers -----------------------------------------------------------------------

def _question_fields(corpus: Corpus) -> Iterator[TextField]:
    for index, question in enumerate(corpus.question_list):
        if not isinstance(question, dict):
            continue
        question_id = _record_id(question, "questions", index)
        path = corpus.question_file.get(question_id, "")
        yield from _fields(path, question_id, question, ("prompt", "explanation"))
        choices = question.get("choices")
        if isinstance(choices, list):
            for choice_index, choice in enumerate(choices):
                if isinstance(choice, dict):
                    yield from _fields(path, f"{question_id}.choices[{choice_index}]", choice, ("text",))
        figure = question.get("figure")
        if isinstance(figure, dict):
            yield from _fields(path, f"{question_id}.figure", figure, ("alt",))


def _fields(path: str, where: str, record: dict, names: tuple[str, ...]) -> Iterator[TextField]:
    for name in names:
        value = record.get(name)
        if isinstance(value, str):
            yield TextField(path, f"{where}.{name}", value)


def _items(path: str, where: str, values) -> Iterator[TextField]:
    if isinstance(values, list):
        for index, value in enumerate(values):
            if isinstance(value, str):
                yield TextField(path, f"{where}[{index}]", value)


def _record_id(record: dict, kind: str, index: int) -> str:
    record_id = record.get("id")
    return record_id if isinstance(record_id, str) else f"{kind}[{index}]"


def _edge_path(corpus: Corpus, edge: dict) -> str:
    """The edges file of the grade of the dependent topic, or any edges file when the topic is unknown."""
    topic = corpus.topics.get(edge.get("topic"))
    grade = topic.get("grade") if isinstance(topic, dict) else None
    any_file = next(iter(corpus.edge_file.values()), "")
    return next((path for edge_grade, path in corpus.edge_file.items() if edge_grade == grade), any_file)


def _has_diacritic(word: str) -> bool:
    return any(char in _DIACRITICS for char in word.lower())


def _is_cyrillic(char: str) -> bool:
    return "\u0400" <= char <= "\u04ff" or "\u0500" <= char <= "\u052f"


def _report(seen: set, issues: Issues, path: str, where: str, code: str, key: object, message: str) -> None:
    """Add the issue once per field and key."""
    if (code, key) not in seen:
        seen.add((code, key))
        issues.add(path, where, code, message)
