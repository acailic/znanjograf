"""Serbian Latin to Cyrillic and back, and the keys that ignore script and diacritics.

Latin is the source of truth; every Cyrillic string of the repository is produced here.
The mapping is letter by letter and reversible: ``to_latin(to_cyrillic(text))`` is the
text again. Three sequences are one letter each, ``lj``, ``nj`` and ``dž``, unless the
digraph lexicon (``data/lint/digraphs.json``) marks the word as ``split:<left>|<right>``.

A word is rewritten only when it consists of Serbian letters alone. It stays Latin when
it has any other letter (``x``, ``q``, ``y``), and when it has a capital anywhere except
as its first letter: acronyms (``HTML``) and spellings such as ``JavaScript``.
"""

from __future__ import annotations

import re
from typing import Callable, Iterator

from .protect import split_protected

# The 27 single letters and their Cyrillic letters; ``lj``, ``nj`` and ``dž`` complete the alphabet of 30.
_LATIN = "abcčćdđefghijklmnoprsštuvzž"
_TO_CYRILLIC = dict(zip(_LATIN, "абцчћдђефгхијклмнопрсштувзж"))
_DIGRAPH_OF = {"lj": "љ", "nj": "њ", "dž": "џ"}
_TO_LATIN = {cyrillic: latin for latin, cyrillic in {**_TO_CYRILLIC, **_DIGRAPH_OF}.items()}
_TO_LATIN.update({letter.upper(): pair.capitalize() for letter, pair in _TO_LATIN.items()})

# The Serbian alphabet, in order: the key of ``collation_key``.
ALPHABET = "абвгдђежзијклљмнњопрстћуфхцчџш"
_POSITION = {letter: index for index, letter in enumerate(ALPHABET)}

# A word: a run of letters. Digits, marks and the underscore cut it.
WORD_PATTERN: re.Pattern = re.compile(r"[^\W\d_]+")
DIGRAPH_PATTERN: re.Pattern = re.compile(r"lj|nj|dž", re.IGNORECASE)
_DIACRITIC_FREE = {"č": "c", "ć": "c", "š": "s", "ž": "z", "đ": "dj"}
_NOT_ASCII_ALNUM = re.compile(r"[^a-z0-9]+")


# ----- letters -----------------------------------------------------------------------

def to_cyrillic(text: str, lexicon: dict[str, str] | None = None) -> str:
    """Rewrite every Serbian word of ``text`` in Cyrillic; protected spans are copied as they are.

    ``lexicon`` maps a lowercase word to ``"digraph"`` or ``"split:<left>|<right>"``;
    without it every ``lj``, ``nj`` and ``dž`` is one letter.
    """
    pieces = []
    for segment, protected in split_protected(text):
        if protected:
            pieces.append(segment)
        else:
            pieces.append(WORD_PATTERN.sub(lambda match: _cyrillic_word(match.group(), lexicon), segment))
    return "".join(pieces)


def to_latin(text: str) -> str:
    """Rewrite every Cyrillic letter of ``text`` in Latin; the exact inverse of ``to_cyrillic``."""
    return "".join(_TO_LATIN.get(char, char) for char in text)


def translit_obj(obj, fn: Callable[..., str] = to_cyrillic, lexicon: dict[str, str] | None = None):
    """Apply ``fn`` to every string inside dicts and lists of ``obj``; keys and other values pass through.

    With a ``lexicon`` the function is called as ``fn(text, lexicon)``, otherwise as ``fn(text)``.
    Nothing is mutated; the converted structure is returned.
    """
    convert = (lambda value: fn(value, lexicon)) if lexicon is not None else fn
    return _convert(obj, convert)


def _convert(value, convert: Callable[[str], str]):
    if isinstance(value, str):
        return convert(value)
    if isinstance(value, dict):
        return {key: _convert(item, convert) for key, item in value.items()}
    if isinstance(value, list):
        return [_convert(item, convert) for item in value]
    return value


def is_transliterated(word: str) -> bool:
    """True when ``to_cyrillic`` rewrites ``word``: Serbian letters only, no capital after the first letter."""
    return bool(word) and all(char in _TO_CYRILLIC for char in word.lower()) and not any(char.isupper() for char in word[1:])


def _cyrillic_word(word: str, lexicon: dict[str, str] | None) -> str:
    if not is_transliterated(word):
        return word
    lower = word.lower()
    split_at = _split_position(lower, lexicon)
    letters = []
    index = 0
    while index < len(lower):
        pair = lower[index : index + 2]
        if index != split_at and pair in _DIGRAPH_OF:
            letters.append(_DIGRAPH_OF[pair])
            index += 2
        else:
            letters.append(_TO_CYRILLIC[lower[index]])
            index += 1
    result = "".join(letters)
    return result[:1].upper() + result[1:] if word[:1].isupper() else result


def _split_position(lower: str, lexicon: dict[str, str] | None) -> int | None:
    """Where the lexicon forbids a digraph in ``lower``; ``None`` where it does not."""
    entry = (lexicon or {}).get(lower, "")
    if not entry.startswith("split:"):
        return None
    left, _, right = entry[len("split:") :].partition("|")
    if len(left) != 1 or len(right) != 1:
        return None
    return lower.find(left + right)


def iter_words(text: str) -> Iterator[tuple[str, int]]:
    """Yield ``(word, offset)`` for every word of the unprotected segments of ``text``."""
    offset = 0
    for segment, protected in split_protected(text):
        if not protected:
            for match in WORD_PATTERN.finditer(segment):
                yield match.group(), offset + match.start()
        offset += len(segment)


# ----- keys --------------------------------------------------------------------------

def needs_lexicon(word: str) -> bool:
    """True when ``word`` contains ``lj``, ``nj`` or ``dž``, whatever the case."""
    return DIGRAPH_PATTERN.search(word) is not None


def fold(text: str) -> str:
    """Lowercase ASCII of ``text``: no script, no diacritics, nothing but ``a-z`` and ``0-9``.

    ``lj`` and ``nj`` stay as they are, ``dž`` becomes ``dz`` and ``đ`` becomes ``dj``.
    """
    base = to_latin(text).lower().replace("dž", "dz")
    return _NOT_ASCII_ALNUM.sub("", "".join(_DIACRITIC_FREE.get(char, char) for char in base))


def collation_key(text: str) -> tuple[int, ...]:
    """Sort key in Serbian alphabet order; ``lj``, ``nj`` and ``dž`` count as one letter.

    Case and script are ignored. Every other character sorts after all letters and
    compares equal to every other such character.
    """
    key = []
    base = to_latin(text).lower()
    index = 0
    while index < len(base):
        letter = _DIGRAPH_OF.get(base[index : index + 2])
        if letter is not None:
            key.append(_POSITION[letter])
            index += 2
            continue
        char = base[index]
        key.append(_POSITION[_TO_CYRILLIC[char]] if char in _TO_CYRILLIC else len(ALPHABET))
        index += 1
    return tuple(key)
