"""V9: a figure is of a known kind, says in ``alt`` enough to be solved without, and agrees with its own geometry.

Parameter names are the contract with the JavaScript renderer (``site/js/figure.js``): it draws what
``PARAMS`` below allows, and a name is changed here and there together, nowhere else. Defaults
(``step`` 1, ``count`` rows × cols, ``perSymbol`` 1) are the renderer's; an optional parameter left out is valid.
"""

from __future__ import annotations

import json
import math
import re

from ..corpus import Corpus
from ..issues import Issues

KINDS = (
    "numberline", "fractionbar", "pie", "dots", "bars", "pictogram",
    "grid", "polygon", "angle", "axes", "clock", "table",
)
MIN_ALT = 20  # characters, after stripping
SIDE_TOLERANCE = 0.01  # a side label may differ from the length of its side by this share
MAX_TICKS = 60  # a longer number line is more than site/js/figure.js draws

KIND_CODE, ALT_CODE, PARAM_CODE, GEOMETRY_CODE = (
    "V9-figure-kind", "V9-figure-alt", "V9-figure-param", "V9-figure-geometry",
)

# ----- parameter schema -------------------------------------------------------------------
# A scalar spec is (type, low, high) with inclusive bounds, open where None; a "+" type is strictly positive.
# A composite spec is ("list", item), ("pair", item) for [x, y], or ("records", {field: spec}) for objects
# that have exactly those fields. A parameter is (spec, required).


def _int(low=None, high=None) -> tuple:
    return ("int", low, high)


def _number(low=None, high=None) -> tuple:
    return ("number", low, high)


ANY_INT, ANY_NUMBER, TEXT = _int(), _number(), ("str", None, None)
POSITIVE_INT, POSITIVE_NUMBER = ("int+", None, None), ("number+", None, None)

PARAMS = {
    "numberline": {
        "min": (ANY_INT, True), "max": (ANY_INT, True),
        "step": (POSITIVE_INT, False),
        "marks": (("list", ANY_NUMBER), False),
        "unit": (TEXT, False),
    },
    "fractionbar": {
        "numerator": (POSITIVE_INT, True), "denominator": (_int(1, 24), True),
        "shaded": (_int(0), False),
    },
    "pie": {"parts": (_int(2, 12), True), "shaded": (_int(0), False)},
    "dots": {"rows": (_int(1, 12), True), "cols": (_int(1, 12), True), "count": (_int(0), False)},
    "bars": {
        "title": (TEXT, False),
        "categories": (("list", TEXT), True),
        "values": (("list", POSITIVE_NUMBER), True),
    },
    "pictogram": {
        "symbol": (TEXT, True),
        "items": (("records", {"label": TEXT, "count": _number(0)}), True),
        "perSymbol": (POSITIVE_NUMBER, False),
    },
    "grid": {
        "cols": (_int(1, 15), True), "rows": (_int(1, 15), True),
        "cells": (("list", ("pair", _int(0))), False),
    },
    "polygon": {
        "vertices": (("list", ("pair", ANY_NUMBER)), True),
        "sides": (("records", {"index": _int(0), "label": TEXT}), False),
        "labels": (("records", {"text": TEXT, "x": ANY_NUMBER, "y": ANY_NUMBER}), False),
    },
    "angle": {
        "degrees": (_number(0, 360), True), "label": (TEXT, False),
        "vertex": (("pair", ANY_NUMBER), False),
    },
    "axes": {
        "xmin": (ANY_NUMBER, True), "xmax": (ANY_NUMBER, True), "ymin": (ANY_NUMBER, True), "ymax": (ANY_NUMBER, True),
        "points": (("records", {"x": ANY_NUMBER, "y": ANY_NUMBER, "label": TEXT}), False),
    },
    "clock": {"hour": (_int(1, 12), True), "minute": (_int(0, 59), True)},
    "table": {"columns": (("list", TEXT), True), "rows": (("list", ("list", TEXT)), True)},
}
COMMON_FIELDS = ("kind", "alt")

# ----- one value against its spec ---------------------------------------------------------

_NAMES = {"int": "ceo broj", "int+": "pozitivan ceo broj", "number": "broj", "number+": "pozitivan broj", "str": "tekst"}


def _show(value: object) -> str:
    """A JSON value for a message: a scalar in Serbian quotes (``„13“``), a list or an object as JSON (``[1, 2]``)."""
    if isinstance(value, str):
        return f"„{value}“"
    text = json.dumps(value, ensure_ascii=False)
    return text if isinstance(value, (list, dict)) else f"„{text}“"


def _must(path: str, expected: str, value: object) -> str:
    return f"parametar „{path}“ mora biti {expected}, a jeste {_show(value)}"


def _count(count: int, one: str, few: str, many: str) -> str:
    """A number with its noun in the right form: ``1 znak``, ``2 znaka``, ``5 znakova``."""
    word = one if count == 1 else few if 2 <= count <= 4 else many
    return f"{count} {word}"


def _fits(value: object, spec: tuple) -> bool:
    """Does the scalar ``value`` satisfy ``spec``?  A JSON boolean is never a number here."""
    tag, low, high = spec
    if tag == "str":
        return isinstance(value, str)
    if isinstance(value, bool) or not isinstance(value, int if tag.startswith("int") else (int, float)):
        return False
    if not math.isfinite(value):
        return False
    if tag.endswith("+") and value <= 0:
        return False
    return (low is None or value >= low) and (high is None or value <= high)


def _describe(spec: tuple) -> str:
    """A scalar spec in words: ``tekst``, ``ceo broj od 1 do 24``, ``broj najmanje 0``."""
    tag, low, high = spec
    if low is not None and high is not None:
        return f"{_NAMES[tag]} od {low} do {high}"
    if low is not None:
        return f"{_NAMES[tag]} najmanje {low}"
    if high is not None:
        return f"{_NAMES[tag]} najviše {high}"
    return _NAMES[tag]


def _check(value: object, spec: tuple, path: str, out: list[str]) -> None:
    """Append a message for every way ``value`` departs from ``spec``; ``path`` names the parameter (``items[1].count``)."""
    tag = spec[0]
    if tag in ("list", "pair"):
        if not (isinstance(value, list) and (tag == "list" or len(value) == 2)):
            out.append(_must(path, "niz" if tag == "list" else "par [x, y]", value))
            return
        for index, item in enumerate(value):
            _check(item, spec[1], f"{path}[{index}]", out)
    elif tag == "records":
        _records(value, spec[1], path, out)
    elif not _fits(value, spec):
        out.append(_must(path, _describe(spec), value))


def _records(value: object, fields: dict, path: str, out: list[str]) -> None:
    if not isinstance(value, list):
        out.append(_must(path, "niz", value))
        return
    for index, record in enumerate(value):
        at = f"{path}[{index}]"
        if not isinstance(record, dict):
            out.append(_must(at, "objekat", record))
            continue
        for name in sorted(set(record) - set(fields)):
            out.append(f"parametar „{at}“ ima nepoznato polje „{name}“")
        for name, field_spec in fields.items():
            if name not in record:
                out.append(f"parametar „{at}“ nema polje „{name}“")
            else:
                _check(record[name], field_spec, f"{at}.{name}", out)


# ----- what a kind means beyond types -----------------------------------------------------
# These see only parameters that passed ``_check``, so they may read the values as they are.


def _at_most(spec: dict, name: str, limit_name: str, limit: int, out: list[str]) -> None:
    """``spec[name]`` lies between 0 and ``limit``, the valid value of ``spec[limit_name]`` (or a count of it)."""
    value = spec.get(name)
    if value is not None and not 0 <= value <= limit:
        out.append(f"„{name}“ mora biti od 0 do „{limit_name}“ ({limit})")


def _numberline(spec: dict, out: list[str]) -> None:
    low, high, step = spec["min"], spec["max"], spec.get("step", 1)
    if low >= high:
        out.append(f"„max“ mora biti veći od „min“ (min je {low}, a max {high})")
    ticks = (high - low) // step + 1
    if ticks > MAX_TICKS:
        out.append(
            f"„step“ = {step} daje {_count(ticks, 'oznaku', 'oznake', 'oznaka')} na pravoj, "
            f"a slika crta najviše {MAX_TICKS}; povećaj „step“"
        )
    if any(not low <= mark <= high for mark in spec.get("marks", [])):
        out.append(f"svaka oznaka u „marks“ mora biti od „min“ do „max“ ({low} do {high})")


def _fractionbar(spec: dict, out: list[str]) -> None:
    _at_most(spec, "shaded", "numerator", spec["numerator"], out)


def _pie(spec: dict, out: list[str]) -> None:
    _at_most(spec, "shaded", "parts", spec["parts"], out)


def _dots(spec: dict, out: list[str]) -> None:
    _at_most(spec, "count", "rows × cols", spec["rows"] * spec["cols"], out)


def _bars(spec: dict, out: list[str]) -> None:
    categories, values = spec["categories"], spec["values"]
    if not 2 <= len(categories) <= 8:
        out.append(f"„categories“ mora imati od 2 do 8 natpisa (ima {len(categories)})")
    if len(values) != len(categories):
        out.append(f"„values“ mora imati {len(categories)} vrednosti, koliko ima „categories“ (ima {len(values)})")


def _pictogram(spec: dict, out: list[str]) -> None:
    if not spec["symbol"].strip():
        out.append("parametar „symbol“ mora biti neprazan tekst")
    if not spec["items"]:
        out.append("„items“ mora imati bar jednu stavku")


def _grid(spec: dict, out: list[str]) -> None:
    rows, cols = spec["rows"], spec["cols"]
    for index, (row, col) in enumerate(spec.get("cells", [])):
        if not (row < rows and col < cols):
            out.append(f"polje „cells[{index}]“ mora biti u mreži: red od 0 do {rows - 1}, a kolona od 0 do {cols - 1}")


def _polygon(spec: dict, out: list[str]) -> None:
    count = len(spec["vertices"])
    if not 3 <= count <= 8:
        out.append(f"„vertices“ mora imati od 3 do 8 parova [x, y], po jedan za svako teme (ima {count})")
    for position, side in enumerate(spec.get("sides", [])):
        if side["index"] >= count:
            out.append(f"parametar „sides[{position}].index“ mora biti redni broj temena, najviše {count - 1}")


def _axes(spec: dict, out: list[str]) -> None:
    for low, high in (("xmin", "xmax"), ("ymin", "ymax")):
        if spec[low] >= spec[high]:
            out.append(f"„{high}“ mora biti veći od „{low}“ ({low} je {spec[low]}, a {high} {spec[high]})")
    for index, point in enumerate(spec.get("points", [])):
        if not (spec["xmin"] <= point["x"] <= spec["xmax"] and spec["ymin"] <= point["y"] <= spec["ymax"]):
            out.append(f"tačka „points[{index}]“ mora biti unutar osa: x od {spec['xmin']} do {spec['xmax']}, y od {spec['ymin']} do {spec['ymax']}")


def _table(spec: dict, out: list[str]) -> None:
    columns = spec["columns"]
    if not columns:
        out.append("„columns“ mora imati bar jednu kolonu")
    for index, row in enumerate(spec["rows"]):
        if len(row) != len(columns):
            out.append(f"red „rows[{index}]“ mora imati {len(columns)} ćelije, koliko ima „columns“ (ima {len(row)})")


def _nothing(spec: dict, out: list[str]) -> None:
    """For kinds whose parameters say all there is: the values have only to be of the right type."""


AGREEMENT = {
    "numberline": _numberline, "fractionbar": _fractionbar, "pie": _pie, "dots": _dots, "bars": _bars,
    "pictogram": _pictogram, "grid": _grid, "polygon": _polygon, "angle": _nothing,
    "axes": _axes, "clock": _nothing, "table": _table,
}

# ----- geometry ---------------------------------------------------------------------------

_LABEL_NUMBER = re.compile(r"\d+(?: \d{3})*(?:[.,]\d+)?")


def _stated_length(label: str) -> float | None:
    """The length a side label states — 5 for ``5 cm``, 5.5 for ``5,5 cm``, 2500 for ``2 500 m`` — or None."""
    found = _LABEL_NUMBER.search(label)
    return float(found.group().replace(" ", "").replace(",", ".")) if found else None


def _side_length(vertices: list, index: int) -> float:
    """Side ``index`` joins ``vertices[index]`` and the next vertex; the last side closes the polygon."""
    (ax, ay), (bx, by) = vertices[index], vertices[(index + 1) % len(vertices)]
    return math.hypot(bx - ax, by - ay)


def _quantity(value: float) -> str:
    """A computed number for a message: at most two decimals and a Serbian comma (``4``, ``5,66``)."""
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return ("0" if text in ("", "-0") else text).replace(".", ",")


def _geometry(spec: dict) -> list[str]:
    """Sides of a polygon whose label states a length its vertices contradict, by more than ``SIDE_TOLERANCE``.

    Called only on a polygon without a parameter problem, so vertices and sides are whole and indices in range.
    """
    vertices = spec["vertices"]
    found = []
    for side in spec.get("sides", []):
        index, label = side["index"], side["label"]
        stated = _stated_length(label)
        if stated is None:
            continue  # a letter such as „a“ names a side without stating its length
        length = _side_length(vertices, index)
        if abs(stated - length) > length * (SIDE_TOLERANCE + 1e-9):  # the 1e-9 keeps „exactly 1 %“ inside
            found.append(
                f"natpis strane {index} („{label}“) ne odgovara dužini te strane ({_quantity(length)}); "
                f"dozvoljeno je odstupanje do {round(SIDE_TOLERANCE * 100)} %"
            )
    return found


# ----- the gate ---------------------------------------------------------------------------


def _parameters(kind: str, spec: dict) -> list[str]:
    """What is wrong with the parameters of a figure of a known ``kind``; every message starts with the kind."""
    params = PARAMS[kind]
    body = [f"nepoznat parametar „{name}“" for name in sorted(set(spec) - set(params) - set(COMMON_FIELDS))]
    for name, (type_spec, required) in params.items():
        if name not in spec:
            if required:
                body.append(f"obavezan parametar „{name}“ nedostaje")
            continue
        _check(spec[name], type_spec, name, body)
    if not body:
        AGREEMENT[kind](spec, body)  # lengths and bounds only make sense on values of the right type
    return [f"{kind}: {message}" for message in body]


def _problems(spec: object) -> list[tuple[str, str]]:
    """(code, message) for everything wrong with ``spec``, most general first."""
    if not isinstance(spec, dict):
        return [(KIND_CODE, "slika mora biti objekat s poljima „kind“ i „alt“")]
    allowed = "dozvoljene vrste su: " + ", ".join(KINDS)
    found = []
    if "kind" not in spec:
        found.append((KIND_CODE, f"slika nema polje „kind“; {allowed}"))
    elif spec["kind"] not in KINDS:
        found.append((KIND_CODE, f"nepoznata vrsta slike {_show(spec['kind'])}; {allowed}"))
    alt = spec.get("alt")
    if "alt" not in spec:
        found.append((ALT_CODE, "slika nema polje „alt“"))
    elif not isinstance(alt, str):
        found.append((ALT_CODE, f"polje „alt“ mora biti tekst, a jeste {_show(alt)}"))
    elif len(alt.strip()) < MIN_ALT:
        found.append((ALT_CODE, f"„alt“ ima {_count(len(alt.strip()), 'znak', 'znaka', 'znakova')}, a treba najmanje {MIN_ALT}"))
    if spec.get("kind") in KINDS:
        kind = spec["kind"]
        parameters = _parameters(kind, spec)
        found.extend((PARAM_CODE, message) for message in parameters)
        if not parameters and kind == "polygon":  # geometry is worth judging only on sound parameters
            found.extend((GEOMETRY_CODE, f"polygon: {message}") for message in _geometry(spec))
    return found


def validate(spec: object) -> list[str]:
    """Serbian messages for everything wrong with a figure; empty when the renderer may draw it."""
    return [message for _, message in _problems(spec)]


def run(corpus: Corpus, issues: Issues) -> None:
    """V9 on every question that carries a figure; a question without one is not this gate's business."""
    for question in corpus.question_list:
        if not isinstance(question, dict) or "figure" not in question:
            continue
        question_id = question.get("id")
        where = question_id if isinstance(question_id, str) else "-"
        for code, message in _problems(question["figure"]):
            issues.add(corpus.question_file.get(where, "-"), where, code, message)
