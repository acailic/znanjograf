"""The question bank: two basic and two standard questions per topic, well-formed choices, and
``points_to`` targets that are hard ancestors of the question's topic.

``zg.mathcheck`` is used when it can be imported; while it is missing, only the two rules that
call it are skipped. It reads numeric answers, and it computes ``check``, which is how an
irrational answer without ``round_to`` is recognised. The shape of a question record is
``zg.checks.schema``'s.
"""

from __future__ import annotations

import decimal
import importlib
from collections import Counter

from ..corpus import Corpus, CorpusError
from ..issues import Issues

MIN_PER_LEVEL = 2
CHOICE_SIZES = (3, 4)


def run(corpus: Corpus, issues: Issues) -> None:
    mathcheck = _load("zg.mathcheck")
    parser = _parser(mathcheck)
    ancestors = _HardAncestors(corpus)
    _check_sizes(corpus, issues)
    for question in corpus.question_list:
        if not isinstance(question, dict):
            continue  # not a record; schema reports it
        question_id = question.get("id")
        if not isinstance(question_id, str) or not question_id:
            continue  # a record without an id is schema's to report
        where, path = question_id, corpus.question_file[question_id]
        if question.get("type") == "choice":
            _check_choices(question, where, path, issues)
        if mathcheck is not None:
            if question.get("type") == "numeric":
                _check_numeric_answer(question, where, path, issues, mathcheck)
            _check_round_to(question, where, path, issues, mathcheck, parser)
        _check_points_to(question, where, path, issues, ancestors)


def _check_sizes(corpus: Corpus, issues: Issues) -> None:
    counts: Counter = Counter()
    for question in corpus.question_list:
        if not isinstance(question, dict):
            continue
        topic_id, level = question.get("topic"), question.get("level")
        if isinstance(topic_id, str) and isinstance(level, str):
            counts[(topic_id, level)] += 1
    for topic_id in corpus.topics:
        basic = counts[(topic_id, "basic")]
        standard = counts[(topic_id, "standard")]
        if basic < MIN_PER_LEVEL or standard < MIN_PER_LEVEL:
            issues.add(
                corpus.topic_file[topic_id], topic_id, "V8-bank-count",
                f"tema ima osnovnih zadataka: {basic}, standardnih: {standard}; treba najmanje {MIN_PER_LEVEL} i {MIN_PER_LEVEL}",
            )


def _check_choices(question: dict, where: str, path: str, issues: Issues) -> None:
    choices = question.get("choices")
    if not isinstance(choices, list):
        return  # a missing or malformed list is a field problem (V2)
    options = [option for option in choices if isinstance(option, dict)]
    if len(choices) not in CHOICE_SIZES:
        issues.add(path, where, "V8-choice-count", f"broj ponuda u zadatku je {len(choices)}, a treba {CHOICE_SIZES[0]} ili {CHOICE_SIZES[-1]}")
    ids = [option.get("id") for option in options]
    broken = _unique(value for value in ids if not (isinstance(value, str) and value))
    repeated = _unique(value for value in ids if value not in broken and ids.count(value) > 1)
    if broken or repeated:
        parts = []
        if broken:
            parts.append(f"id ponude mora biti neprazna niska, a nije: {_listing(broken)}")
        if repeated:
            parts.append(f"id ponuda se ponavljaju: {_listing(repeated)}")
        issues.add(path, where, "V8-choice-ids", "; ".join(parts))
    if question.get("answer") not in ids:
        issues.add(path, where, "V8-choice-ids", f"odgovor {_show(question.get('answer'))} nije id nijedne ponude")
    # Surrounding spaces do not show on the site, so they do not make two texts different.
    texts = [option["text"].strip() for option in options if isinstance(option.get("text"), str)]
    repeated_texts = _unique(text for text in texts if texts.count(text) > 1)
    if repeated_texts:
        issues.add(path, where, "V8-choice-text", f"više ponuda ima isti tekst: {_listing(repeated_texts)}")


def _check_numeric_answer(question: dict, where: str, path: str, issues: Issues, mathcheck) -> None:
    answer = question.get("answer")
    if _reads_as_number(mathcheck.parse_answer, answer):
        return
    issues.add(path, where, "V8-numeric-answer", f"odgovor {_show(answer)} nije broj u upisu koji alat prihvata, npr. „15“, „3,5“, „3/4“ ili „-7“")


def _reads_as_number(parse_answer, text) -> bool:
    """False for whatever the parser rejects, or chokes on. Its promise is ``None`` for a text that
    is not a number; the except is for the day it does not keep it."""
    if not isinstance(text, str):
        return False
    try:
        return parse_answer(text) is not None
    except (ValueError, TypeError, ArithmeticError):
        return False


def _check_round_to(question: dict, where: str, path: str, issues: Issues, mathcheck, parser) -> None:
    check = question.get("check")
    if parser is None or not isinstance(check, str) or question.get("round_to") is not None:
        return
    try:
        value = mathcheck.evaluate(parser.parse(check))
    except (ValueError, TypeError, ArithmeticError):
        return  # a check that does not compute (``DslError`` is a ``ValueError``) is verify's to report
    if isinstance(value, decimal.Decimal):
        issues.add(path, where, "V8-round-to", "tačan odgovor je iracionalan, a nedostaje polje „round_to“ (na koliko decimala se zaokružuje)")


def _check_points_to(question: dict, where: str, path: str, issues: Issues, ancestors: _HardAncestors) -> None:
    points_to = question.get("points_to")
    if not isinstance(points_to, dict):
        return  # absent, or a field problem (V2)
    choices = question.get("choices")
    option_ids = [option.get("id") for option in choices if isinstance(option, dict)] if isinstance(choices, list) else []
    for option_id, target in points_to.items():
        if option_id == question.get("answer") or option_id not in option_ids:
            issues.add(path, where, "V8-points-to", f"„points_to“ navodi ponudu {_show(option_id)}, a to nije id pogrešne ponude")
            continue
        hard = ancestors.of(question.get("topic"))
        if hard is not None and not (isinstance(target, str) and target in hard):
            issues.add(
                path, where, "V8-points-to",
                f"„points_to“ za ponudu {_show(option_id)} pokazuje na temu {_show(target)}, a ona nije čvrst predak teme {_show(question.get('topic'))}",
            )


class _HardAncestors:
    """Hard ancestors of a topic, computed once each. ``of`` answers None when it cannot know:
    the topic does not exist, or the graph is broken enough for ``Corpus`` to give up on it."""

    def __init__(self, corpus: Corpus) -> None:
        self._corpus = corpus
        self._known: dict[str, set[str]] = {}
        self._broken = False

    def of(self, topic_id) -> set[str] | None:
        if self._broken or not isinstance(topic_id, str) or topic_id not in self._corpus.topics:
            return None
        if topic_id not in self._known:
            try:
                self._known[topic_id] = self._corpus.hard_ancestors(topic_id)
            except CorpusError:
                self._broken = True
                return None
        return self._known[topic_id]


def _unique(values) -> list:
    """``values`` without repetitions, in the order they come; a value need not be hashable."""
    out = []
    for value in values:
        if value not in out:
            out.append(value)
    return out


def _listing(values) -> str:
    return ", ".join(_show(value) for value in values)


def _show(value) -> str:
    """A value for a message: a string in quotes, anything else as Python writes it."""
    return f"„{value}“" if isinstance(value, str) else repr(value)


def _parser(mathcheck):
    """The S-expression parser: ``mathcheck.dsl`` when it exposes one, else the ``zg.dsl`` module."""
    if mathcheck is None:
        return None
    return getattr(mathcheck, "dsl", None) or _load("zg.dsl")


def _load(module_name: str):
    """A module this gate uses but does not need: None while it is missing, which turns off only the rules that call it."""
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None
