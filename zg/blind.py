"""The blind pass: a sheet of questions without their answers, and the check of what the solver returned.

The sheet gives an independent solver only what a pupil sees. The solver answers
from the text alone and sends back, per question, its own answer and check, whether
exactly one answer is defensible, everything it had to assume, and a 0–3 rating of
how defensible each wrong option is. ``diff`` compares that with the bank; there is
no adjudication, any difference means the question is reworked.
"""

from __future__ import annotations

import importlib
import random

from .corpus import Corpus
from .report import questions_of_grade

LATIN, CYRILLIC = "lat", "cyr"
TRANSLIT_PACKAGE = "zg.translit"
TRANSLIT = TRANSLIT_PACKAGE + ".rules"


def make_sheet(corpus: Corpus, grade: int, script: str = CYRILLIC, seed=None) -> dict:
    """Every question of one grade as a pupil sees it, in a random order set by ``seed``.

    An item is ``{"id", "prompt", "figure", "choices": [{"id", "text"}]}`` and nothing
    else: no answer, check, explanation, level or topic. In Cyrillic every text goes
    through ``translit.rules.to_cyrillic``; ids stay as they are written.
    """
    if script not in (LATIN, CYRILLIC):
        raise ValueError(f"nepoznato pismo: {script!r}")
    text = _cyrillic() if script == CYRILLIC else _unchanged
    items = [_item(question, text) for question in questions_of_grade(corpus, grade)]
    random.Random(seed).shuffle(items)
    return {"grade": grade, "script": script, "items": items}


def diff(corpus: Corpus, grade: int, answers: dict) -> list[dict]:
    """The questions of one grade on which the blind solver's answer differs from the bank.

    ``answers`` maps question id to ``{"answer": str, "check": str, "unique": bool,
    "assumptions": [str], "distractors": {option id: 0–3}}``. The result is
    ``[{"id", "reasons"}]`` in file order. A reason is ``missing`` (no entry),
    ``answer`` (another text), ``check`` (another expression, whitespace aside),
    ``unique`` (anything but exactly ``True``), ``assumptions`` (not empty) or
    ``distractor`` (a wrong option rated 2 or 3, or a rating of something that is
    not a wrong option).
    """
    failures = []
    for question in questions_of_grade(corpus, grade):
        question_id = question.get("id")
        entry = answers.get(question_id)
        if not isinstance(entry, dict):
            failures.append({"id": question_id, "reasons": ["missing"]})
            continue
        reasons = [reason for reason, fails in _CHECKS if fails(question, entry)]
        if reasons:
            failures.append({"id": question_id, "reasons": reasons})
    return failures


def _other_answer(question: dict, entry: dict) -> bool:
    return str(entry.get("answer")).strip() != str(question.get("answer")).strip()


def _other_check(question: dict, entry: dict) -> bool:
    return _squeeze(entry.get("check")) != _squeeze(question.get("check"))


def _not_unique(question: dict, entry: dict) -> bool:
    return entry.get("unique") is not True


def _assumed_something(question: dict, entry: dict) -> bool:
    return bool(entry.get("assumptions"))


def _cued_option(question: dict, entry: dict) -> bool:
    wrong = {
        choice.get("id") for choice in question.get("choices") or [] if choice.get("id") != question.get("answer")
    }
    ratings = entry.get("distractors") or {}
    if not isinstance(ratings, dict):
        return True  # not ratings by option id at all
    return any(option_id not in wrong or _defensible(rating) for option_id, rating in ratings.items())


# What makes a question fail, in the order the reasons are reported.
_CHECKS = (
    ("answer", _other_answer),
    ("check", _other_check),
    ("unique", _not_unique),
    ("assumptions", _assumed_something),
    ("distractor", _cued_option),
)


def _defensible(rating) -> bool:
    """A rating of 2 or 3 on the 0–3 scale, written as a number or as digits."""
    if isinstance(rating, str):
        try:
            rating = float(rating)
        except ValueError:
            return False
    return isinstance(rating, (int, float)) and rating >= 2


def _squeeze(value) -> str:
    """Text with every run of whitespace reduced to one space and nothing around it."""
    return " ".join(str(value).split())


def _text(value) -> str:
    return value if isinstance(value, str) else ""


def _item(question: dict, text) -> dict:
    figure = question.get("figure")
    return {
        "id": question.get("id"),
        "prompt": text(_text(question.get("prompt"))),
        "figure": None if figure is None else _figure(figure, text),
        "choices": [{"id": choice.get("id"), "text": text(_text(choice.get("text")))} for choice in question.get("choices") or []],
    }


def _figure(figure, text):
    """A copy of the figure declaration with its strings passed through ``text``.

    ``kind`` is left alone: it names the sort of figure and is read by code, not by people.
    """
    if isinstance(figure, dict):
        return {key: item if key == "kind" else _figure(item, text) for key, item in figure.items()}
    if isinstance(figure, list):
        return [_figure(item, text) for item in figure]
    return text(figure) if isinstance(figure, str) else figure


def _unchanged(value: str) -> str:
    return value


def _cyrillic():
    """``to_cyrillic``, imported only when a Cyrillic sheet is asked for: the module may not exist yet."""
    try:
        rules = importlib.import_module(TRANSLIT)
    except ModuleNotFoundError as exc:
        missing = exc.name or ""
        if missing == TRANSLIT_PACKAGE or missing.startswith(TRANSLIT_PACKAGE + "."):
            raise RuntimeError("translit nije dostupan") from None
        raise
    return rules.to_cyrillic
