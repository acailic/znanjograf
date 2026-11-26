"""JSON in and out, strictly: no duplicate keys, stable hashing, UTF-8 everywhere."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


class JsonError(ValueError):
    """A file could not be read or is not valid JSON."""


class DuplicateKeyError(JsonError):
    """An object has the same key twice, so one value would silently win."""


def _object(pairs: list[tuple[str, object]], origin: str) -> dict:
    out: dict = {}
    for key, value in pairs:
        if key in out:
            raise DuplicateKeyError(f"{origin}: dupliran ključ „{key}“")
        out[key] = value
    return out


def loads(text: str, origin: str = "<string>") -> object:
    try:
        return json.loads(text, object_pairs_hook=lambda pairs: _object(pairs, origin))
    except json.JSONDecodeError as exc:
        raise JsonError(f"{origin}: nevaljan JSON: {exc}") from None


def load(path: Path | str) -> object:
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise JsonError(f"{path}: fajl nije UTF-8 ({exc.reason} na bajtu {exc.start}); sačuvaj ga kao UTF-8") from None
    except OSError as exc:
        raise JsonError(f"{path}: ne mogu da pročitam: {exc}") from None
    return loads(text, str(path))


def load_or_none(path: Path | str, errors: list[tuple[str, str]], rel=str) -> object | None:
    """Load an optional file: missing is fine, broken is recorded in ``errors``."""
    path = Path(path)
    if not path.exists():
        return None
    try:
        return load(path)
    except JsonError as exc:
        errors.append((rel(path), str(exc)))
        return None


def dumps(obj: object) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"


def dump(obj: object, path: Path | str) -> None:
    """Write pretty JSON, creating parent directories when they do not exist yet."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps(obj), encoding="utf-8")


def canonical(obj: object) -> str:
    """One byte string per equal value, whatever the key order."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_obj(obj: object) -> str:
    return sha256_text(canonical(obj))
