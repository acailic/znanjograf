"""Coverage of the curriculum in both directions: every topic names outcomes that exist, and every
outcome is either named by a topic or listed in ``unmapped.json`` with a reason. The same pass
checks what it alone checks in the edition files: that the header agrees with the file's id, and
that a page is positive. The shape of a record and the format of an id are ``zg.checks.schema``'s.
"""

from __future__ import annotations

import re

from ..corpus import Corpus, Edition
from ..issues import Issues

# ``Corpus`` keeps no path for the unmapped list; this is the file it reads the list from.
UNMAPPED_FILE = "data/curriculum/unmapped.json"
_GRADE_IN_ID = re.compile(r"g(\d+)-")


def run(corpus: Corpus, issues: Issues) -> None:
    existing = {(edition.id, outcome_id) for edition in corpus.editions.values() for outcome_id in edition.outcomes}
    cited = _cited_outcomes(corpus, issues, existing)
    _check_unmapped(corpus, issues, existing, cited)
    _check_editions(corpus, issues)


def _cited_outcomes(corpus: Corpus, issues: Issues, existing: set[tuple[str, str]]) -> set[tuple[str, str]]:
    """Every (edition, outcome) pair that a topic names; a pair that does not exist is reported."""
    cited: set[tuple[str, str]] = set()
    for topic_id, topic in corpus.topics.items():
        curriculum = topic.get("curriculum")
        if not isinstance(curriculum, list):
            continue  # a missing or malformed list is a field problem (V2), not a coverage one
        if not curriculum:
            issues.add(corpus.topic_file[topic_id], topic_id, "V7-topic-without-outcome", "tema ne navodi nijedan ishod nastavnog programa")
        for entry in curriculum:
            if not isinstance(entry, dict):
                continue
            edition_id, outcome_id = entry.get("edition"), entry.get("outcome")
            if not (isinstance(edition_id, str) and isinstance(outcome_id, str)):
                continue  # the shape of the entry is schema's to report
            if (edition_id, outcome_id) in existing:
                cited.add((edition_id, outcome_id))
            elif edition_id in corpus.editions:
                issues.add(corpus.topic_file[topic_id], topic_id, "V7-outcome-missing", f"tema navodi ishod „{outcome_id}“, a izdanje „{edition_id}“ ga nema")
            else:
                issues.add(corpus.topic_file[topic_id], topic_id, "V7-outcome-missing", f"tema navodi ishod „{outcome_id}“ izdanja „{edition_id}“, a to izdanje ne postoji")
    return cited


def _check_unmapped(corpus: Corpus, issues: Issues, existing: set[tuple[str, str]], cited: set[tuple[str, str]]) -> None:
    """An outcome is either named by a topic or listed in ``unmapped``: it may not be neither, nor both."""
    for edition_id, outcome_id in sorted(existing):
        if (edition_id, outcome_id) not in cited and outcome_id not in corpus.unmapped:
            issues.add(
                _edition_path(corpus, corpus.editions[edition_id]), outcome_id, "V7-outcome-unmapped",
                "ishod nema nijednu temu; dodaj temu koja ga pokriva ili ga upiši u unmapped.json s razlogom",
            )
    editions_of: dict[str, list[str]] = {}
    for edition_id, outcome_id in existing:
        editions_of.setdefault(outcome_id, []).append(edition_id)
    for outcome_id in corpus.unmapped:
        if not editions_of.get(outcome_id):
            issues.add(UNMAPPED_FILE, outcome_id, "V7-unmapped-stale", "ishod je upisan u unmapped.json, a ne postoji ni u jednom izdanju; ukloni unos")
        elif any((edition_id, outcome_id) in cited for edition_id in editions_of[outcome_id]):
            issues.add(UNMAPPED_FILE, outcome_id, "V7-unmapped-stale", "ishod je upisan u unmapped.json, a teme ga pokrivaju; ukloni unos")


def _check_editions(corpus: Corpus, issues: Issues) -> None:
    """The header of every edition file, then the one rule about its themes and outcomes that is not about their shape."""
    for edition in corpus.editions.values():
        path = _edition_path(corpus, edition)
        _check_header(edition, path, issues)
        for index, theme in enumerate(_records(edition.raw.get("themes"))):
            _check_page(theme, f"themes[{index}]", path, issues)
        for index, outcome in enumerate(_records(edition.raw.get("outcomes"))):
            _check_page(outcome, _record_where(outcome, index), path, issues)


def _check_header(edition: Edition, path: str, issues: Issues) -> None:
    raw = edition.raw
    if raw.get("edition") != edition.id:
        issues.add(path, edition.id, "V7-edition-grade", f"polje „edition“ glasi {_show(raw.get('edition'))}, a fajl izdanja je „{edition.id}“")
    grade = _GRADE_IN_ID.match(edition.id)
    if grade and raw.get("grade") != int(grade.group(1)):
        issues.add(path, edition.id, "V7-edition-grade", f"id izdanja nosi razred {grade.group(1)}, a polje „grade“ glasi {_show(raw.get('grade'))}")


def _check_page(record: dict, where: str, path: str, issues: Issues) -> None:
    """``page`` is the printed page in the source, so it is positive. A page that is not an integer
    at all is a type error, which ``zg.checks.schema`` reports."""
    page = record.get("page")
    if _is_int(page) and page <= 0:
        issues.add(path, where, "V2-type", f"stranica „page“ mora biti pozitivan ceo broj, a upisana je {page}")


def _record_where(record: dict, index: int) -> str:
    """An outcome is named by its id; without one, by its position in the file."""
    record_id = record.get("id")
    return record_id if isinstance(record_id, str) and record_id else f"outcomes[{index}]"


def _edition_path(corpus: Corpus, edition: Edition) -> str:
    # ``Edition.file`` is the same path, and still there for a ``Corpus`` built without the dict.
    return corpus.edition_file.get(edition.id) or edition.file


def _records(value) -> list[dict]:
    return [record for record in value if isinstance(record, dict)] if isinstance(value, list) else []


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _show(value) -> str:
    """A value for a message: a string in quotes, anything else as Python writes it."""
    return f"„{value}“" if isinstance(value, str) else repr(value)
