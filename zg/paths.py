"""Every path the toolchain reads from or writes to, derived from the repository root."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SITE_SRC = ROOT / "site"
SITE_OUT = ROOT / "_site"

SOURCES_FILE = DATA / "curriculum" / "sources.json"
UNMAPPED_FILE = DATA / "curriculum" / "unmapped.json"
REGISTRY_FILE = DATA / "registry.json"
ALIASES_FILE = DATA / "aliases.json"
REVIEW_FILE = DATA / "review" / "teachers.json"
LEDGER_FILE = DATA / "ledger.json"
NOTATION_FILE = DATA / "lint" / "notation.json"
DIGRAPHS_FILE = DATA / "lint" / "digraphs.json"


def meta_file(subject: str) -> Path:
    return DATA / subject / "meta.json"


def grade_dir(subject: str, grade: int) -> Path:
    return DATA / subject / f"g{grade}"


def curriculum_file(subject: str, edition: str) -> Path:
    return DATA / "curriculum" / subject / f"{edition}.json"
