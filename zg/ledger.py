"""Which records have passed which gate, and which of them changed since.

The ledger is ``data/ledger.json``: ``{"<gate>": {"<record id>": "<content hash>"}}``.
A gate that passed marks the hash of every record it looked at. Later, ``stale``
lists the records whose hash no longer matches: edited since, or never marked
while the gate had already marked something. A gate without a section has never
run, so ``stale`` says nothing about it; ``report.status`` reports that case.

The ``edges`` gate looks at edges, keyed ``topic>requires`` (the dependent topic,
``>``, the prerequisite). Every other gate looks at questions, keyed by id.
"""

from __future__ import annotations

from pathlib import Path

from . import jsonio, paths
from .corpus import Corpus

LEDGER = paths.LEDGER_FILE
GATES = ("verify", "blind-solve", "classify", "cueing", "edges")
EDGES = "edges"


def content_hash(record: dict) -> str:
    """The same for equal records whatever the key order."""
    return jsonio.sha256_obj(record)


def edge_id(edge: dict) -> str:
    return f"{edge.get('topic')}>{edge.get('requires')}"


def gate_records(corpus: Corpus, gate: str) -> dict[str, dict]:
    """The records a gate looks at, keyed as the ledger keys them, in file order."""
    if gate == EDGES:
        return {edge_id(edge): edge for edge in corpus.edge_list}
    return dict(corpus.questions)


def load_ledger(path: Path | str | None = None) -> dict:
    """The ledger at ``path`` (``LEDGER`` by default); ``{}`` when there is no file.

    A file that cannot be read as ``{gate: {id: hash}}`` is an error, never an
    empty ledger: forgetting every pass would silently unverify the whole corpus.
    """
    path = LEDGER if path is None else Path(path)
    if not path.exists():
        return {}
    ledger = jsonio.load(path)
    if not isinstance(ledger, dict) or not all(isinstance(section, dict) for section in ledger.values()):
        raise jsonio.JsonError(f"{path}: glavna vrednost mora biti objekat sekcija po kapiji")
    return ledger


def mark(gate: str, ids: list[str], records: dict[str, dict], path: Path | str | None = None) -> None:
    """Record that every id in ``ids`` passes ``gate`` as it is now, and write the ledger.

    ``records`` maps id to record (``corpus.questions``, or edges keyed by ``edge_id``).
    Other gates and older entries stay; the file is written in a fixed order, so its
    bytes do not depend on the order in which gates were run.
    """
    _check_gate(gate)
    path = LEDGER if path is None else Path(path)
    ledger = load_ledger(path)
    section = ledger.setdefault(gate, {})
    for record_id in ids:
        section[record_id] = content_hash(records[record_id])
    jsonio.dump(_in_fixed_order(ledger), path)


def stale(gate: str, corpus: Corpus, path: Path | str | None = None) -> list[str]:
    """Ids of the gate's records whose stored hash differs, in file order.

    The ledger is ``LEDGER`` unless ``path`` says otherwise. A record missing from
    the gate's section counts as differing. A record that left the corpus is not
    reported: nothing claims it any more. When the gate has no section at all the
    result is ``[]`` — it never ran, so nothing can be stale.
    """
    _check_gate(gate)
    section = load_ledger(path).get(gate)
    if not isinstance(section, dict):
        return []
    return [
        record_id
        for record_id, record in gate_records(corpus, gate).items()
        if section.get(record_id) != content_hash(record)
    ]


def _check_gate(gate: str) -> None:
    """A misspelt gate must not pass as an empty list, nor land in the file as a section of its own."""
    if gate not in GATES:
        raise ValueError(f"nepoznata kapija: {gate!r}")


def _in_fixed_order(ledger: dict) -> dict:
    return {gate: {record_id: section[record_id] for record_id in sorted(section)} for gate, section in sorted(ledger.items())}
