"""What transliteration must never touch: math, markup, URLs and unit symbols.

``split_protected`` cuts a string into ``(segment, is_protected)`` pieces. Joining the
segments gives the string back exactly, ``rules.to_cyrillic`` copies the protected
pieces verbatim, and the lint looks for spelling problems only in the others.

Protected pieces:

- ``$…$`` and ``$$…$$`` math. A lone ``$`` is ordinary text (rule V10 reports it).
- HTML markup: tags (a quoted attribute may contain ``<`` and ``>``), comments, the
  doctype and character references such as ``&nbsp;``.
- URLs that start with ``http://``, ``https://`` or ``www.``. A URL ends at whitespace
  or markup; a closing ``.,;:!?`` or a bracket it did not open belongs to the sentence.
- a unit symbol that follows a number with at most one space (``5 cm``, ``3 kg``,
  ``60 km/h``): the symbol only, never the number. The number may also be written in
  math (``$3{,}5$ cm``). ``°C`` is always a unit. A bare ``a``, ``m`` or ``s`` that does
  not follow a number is an ordinary Serbian word.
"""

from __future__ import annotations

import re

# Unit symbols of the primary-school curriculum, longest first, so that ``km/h`` is
# preferred to ``km`` and ``m²`` to ``m``.
UNIT_SYMBOLS: tuple[str, ...] = (
    "km/h", "m/s", "°C", "m²", "m³", "mm", "cm", "dm", "km", "kg", "mg", "ml", "dl", "min", "ha", "din",
    "m", "g", "t", "l", "h", "s", "a",
)

# A letter as far as ``re`` can tell: ``\w`` minus digits and the underscore. The
# superscripts count as ``\w`` too, so they are named where a unit may carry them.
_LETTER = r"[^\W\d_]"
_SPACES = " \u00a0\u2009\u202f"  # space, no-break space, thin space, narrow no-break space
_URL_TRAILING = ".,;:!?"

UNIT_PATTERN: re.Pattern = re.compile(
    rf"(?<!{_LETTER})(?:{'|'.join(re.escape(symbol) for symbol in UNIT_SYMBOLS)})(?![^\W\d_²³])"
)

_MARKUP: re.Pattern = re.compile(
    r"(?P<comment><!--[\s\S]*?-->)"
    r"|(?P<doctype>(?i:<!doctype)[^>]*>)"
    r"|(?P<tag></?[A-Za-z][A-Za-z0-9]*(?:\s+(?:\"[^\"]*\"|'[^']*'|[^<>\"'])*?)?/?>)"
    r"|(?P<entity>&#[0-9]+;|&#x[0-9A-Fa-f]+;|&[A-Za-z][A-Za-z0-9]*;)"
    r"|(?P<math>\$\$[\s\S]+?\$\$|\$[^$]+\$)"
    r"|(?P<url>(?i:https?://|www\.)[^\s<>\"'`]+)"
    r"|(?P<degree>°C)"
)


def split_protected(text: str) -> list[tuple[str, bool]]:
    """Cut ``text`` into ``(segment, is_protected)`` pieces; no piece is empty.

    ``"".join(segment for segment, _ in split_protected(text)) == text`` always.
    """
    markup: list[tuple[int, int, str]] = []
    for match in _MARKUP.finditer(text):
        start, end = match.span()
        if match.lastgroup == "url":
            end = _url_end(text, start, end)
            if end == start:
                continue
        markup.append((start, end, match.lastgroup or ""))
    cuts = sorted([(start, end) for start, end, _ in markup] + _unit_spans(text, markup))
    segments: list[tuple[str, bool]] = []
    plain_start = 0
    for start, end in cuts:
        if plain_start < start:
            segments.append((text[plain_start:start], False))
        segments.append((text[start:end], True))
        plain_start = end
    if plain_start < len(text):
        segments.append((text[plain_start:], False))
    return segments


def _unit_spans(text: str, markup: list[tuple[int, int, str]]) -> list[tuple[int, int]]:
    """Spans of the unit symbols that follow a number outside every markup span."""
    spans: list[tuple[int, int]] = []
    gap_start, before, index = 0, "", 0
    for match in UNIT_PATTERN.finditer(text):
        while index < len(markup) and markup[index][0] <= match.start():
            gap_start, before = markup[index][1], markup[index][2]
            index += 1
        if match.start() >= gap_start and _follows_number(text, match.start(), gap_start, before):
            spans.append(match.span())
    return spans


def _follows_number(text: str, unit_start: int, gap_start: int, before: str) -> bool:
    """True when the unit at ``unit_start`` follows a number, with at most one space between."""
    index = unit_start - 1
    if text[index : index + 1] in _SPACES:
        index -= 1
    if index >= gap_start:
        return index >= 0 and text[index].isdecimal()
    # The number may close the math span that ends the gap: ``$5$ cm``, ``$$5$$ cm``.
    if before != "math" or index != gap_start - 1:
        return False
    while index >= 0 and text[index] == "$":
        index -= 1
    return index >= 0 and text[index].isdecimal()


def _url_end(text: str, start: int, end: int) -> int:
    """Move ``end`` back over sentence punctuation and over a bracket the URL did not open."""
    while end > start:
        last = text[end - 1]
        if last in _URL_TRAILING or (last == ")" and text[start:end].count(")") > text[start:end].count("(")):
            end -= 1
        else:
            break
    return end
