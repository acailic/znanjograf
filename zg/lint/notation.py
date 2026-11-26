"""L1: notation that the topic's grade has not met yet, pinned to the outcome that introduces it.

A rule in ``data/lint/notation.json`` is ``{"pattern": "<regex searched inside a math span>",
"min_grade": 2, "outcome": "g2-2026-004", "note": "množenje"}``. A question whose topic is below
``min_grade`` and whose formulas contain the pattern is reported once per rule. A rule that cannot
be trusted (malformed, or citing an outcome no edition has) is reported once and left out.
"""

from __future__ import annotations

import re

from .. import paths
from ..corpus import Corpus
from ..issues import Issues

RULE_FILE = paths.NOTATION_FILE.relative_to(paths.ROOT).as_posix()
RULE_FIELDS = ("pattern", "min_grade", "outcome", "note")
GRADES = range(1, 9)
MATH_SPAN = re.compile(r"\$([^$]*)\$")
# A pattern is a regex, so a LaTeX command starts with two backslashes. Written with one,
# ``\times`` and ``\frac`` compile without a word to a tab and a form feed and then match nothing.
CONTROL_ESCAPE = re.compile(r"\\[tnrvfa]")


def math_spans(text: str) -> list[str]:
    """The inside of every ``$…$`` formula in ``text``, in order of appearance."""
    return MATH_SPAN.findall(text)


def _control_escape(pattern: str) -> str | None:
    """A control-character escape in ``pattern``, or None; an escaped backslash is not one."""
    found = CONTROL_ESCAPE.search(pattern.replace("\\\\", ""))
    return found.group(0) if found else None


def _problem(rule: object) -> str | None:
    """What keeps ``rule`` from being a rule, or None when it can be applied."""
    if not isinstance(rule, dict):
        return "pravilo mora biti objekat"
    missing = [name for name in RULE_FIELDS if name not in rule]
    if missing:
        return "nedostaje polje: " + ", ".join(f"„{name}“" for name in missing)
    unknown = sorted(set(rule) - set(RULE_FIELDS))
    if unknown:
        return "nepoznato polje: " + ", ".join(f"„{name}“" for name in unknown)
    pattern, min_grade, outcome, note = (rule[name] for name in RULE_FIELDS)
    if not isinstance(pattern, str) or not pattern.strip():
        return "„pattern“ mora biti neprazan tekst"
    control = _control_escape(pattern)
    if control is not None:
        return f"„pattern“ sadrži „{control}“, što je kontrolni znak, a ne LaTeX komanda; piše se „\\\\times“"
    if isinstance(min_grade, bool) or not isinstance(min_grade, int) or min_grade not in GRADES:
        return "„min_grade“ mora biti ceo broj od 1 do 8"
    if not isinstance(outcome, str):
        return "„outcome“ mora biti tekst"
    if not isinstance(note, str):
        return "„note“ mora biti tekst"
    try:
        re.compile(pattern)
    except re.error as exc:
        return f"„pattern“ nije valjan regularni izraz: {exc}"
    return None


def _rules(corpus: Corpus, issues: Issues) -> list[tuple[re.Pattern, int, str, str]]:
    """The rules that can be applied, compiled; every other rule is reported (once) and dropped."""
    usable = []
    for index, rule in enumerate(corpus.notation):
        where = f"notation[{index}]"
        problem = _problem(rule)
        if problem is not None:
            issues.add(RULE_FILE, where, "L1-rule-invalid", f"{problem}; pravilo je preskočeno")
            continue
        edition_id = rule["outcome"].rsplit("-", 1)[0]
        if edition_id not in corpus.editions:
            continue  # the program that introduces this notation is not in the corpus yet
        if rule["outcome"] not in corpus.editions[edition_id].outcomes:
            issues.add(RULE_FILE, where, "L1-rule-outcome", _uncited(rule))
            continue
        usable.append((re.compile(rule["pattern"]), rule["min_grade"], rule["outcome"], rule["note"]))
    return usable


def _uncited(rule: dict) -> str:
    return (
        f"pravilo „{rule['note']}“ navodi ishod „{rule['outcome']}“, koji ne postoji ni u jednom izdanju; "
        "pravilo je preskočeno"
    )


def _formulas(question: dict) -> list[str]:
    """Every formula of ``question``: of the prompt, then of each choice, then of the explanation."""
    texts = [question.get("prompt")]
    choices = question.get("choices")
    if isinstance(choices, list):
        texts.extend(choice.get("text") for choice in choices if isinstance(choice, dict))
    texts.append(question.get("explanation"))
    return [_without_units(span) for text in texts if isinstance(text, str) for span in math_spans(text)]


_TEXT = re.compile(r"\\text\{[^{}]*\}")


def _without_units(span: str) -> str:
    """The formula without its ``\\text{…}`` unit symbols, so that ``m`` in ``$5\\ \\text{m}$`` is not a variable."""
    return _TEXT.sub(" ", span)


def run(corpus: Corpus, issues: Issues) -> None:
    """Report notation used below its grade, once per question and rule, with the outcome that introduces it."""
    rules = _rules(corpus, issues)
    for question in corpus.question_list:
        if not isinstance(question, dict):
            continue  # a record that is not an object is for the schema gate to report
        topic_id = question.get("topic")
        grade = corpus.topics.get(topic_id, {}).get("grade") if isinstance(topic_id, str) else None
        if isinstance(grade, bool) or not isinstance(grade, int):
            continue  # a question of an unknown topic is for the schema gate to report too
        formulas = _formulas(question)
        for regex, min_grade, outcome, note in rules:
            if grade >= min_grade:
                continue
            hit = next((match for span in formulas if (match := regex.search(span))), None)
            if hit is not None:
                question_id = question.get("id")
                where = question_id if isinstance(question_id, str) else "-"
                issues.add(
                    corpus.question_file.get(where, "-"), where, "L1-notation",
                    f"notacija „{note}“ (nađeno: „{hit.group(0)}“) uvodi se ishodom {outcome}, "
                    f"a najranije u {min_grade}. razredu; ovo je tema {grade}. razreda",
                )
