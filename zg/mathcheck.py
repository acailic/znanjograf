"""Exact answers: computes a question's ``check`` and holds it against its ``answer``.

Every value is a :class:`~fractions.Fraction` unless ``pi`` or a non-square root is
involved; then it is a :class:`~decimal.Decimal` with ``PRECISION`` significant digits
and the question has to say, in ``round_to``, how many decimals the answer has.
``verify`` runs the rule over a whole corpus: it reports, it never raises.
"""

from __future__ import annotations

import math
import re
from decimal import ROUND_HALF_UP, Decimal, DivisionByZero, localcontext
from fractions import Fraction
from operator import add, gt, lt, mul, sub, truediv

from . import dsl
from .dsl import DslError

PRECISION = 60        # significant digits of an inexact value
MAX_ROUND_TO = 30     # the most decimals ``round_to`` may ask for
MAX_BITS = 40_000     # the largest power, in bits, so that no result can grow without bound
MAX_LENGTH = 100      # the longest text that can still be one answer

_IRRATIONAL = f"vrednost nije racionalan broj, pa je obavezno polje round_to (ceo broj od 0 do {MAX_ROUND_TO})"

_DIGITS = re.compile(r"[0-9]+")
# A natural number: plain digits, or groups of three digits behind a first group of one to three
# separated by single spaces: 7, 1234567, 1 000, 12 345 678.
_INTEGER = re.compile(r"[0-9]{1,3}(?: [0-9]{3})*|[0-9]+")

# One guard digit more than the precision, so that rounding to it is exact.
_PI = Decimal("3.141592653589793238462643383279502884197169399375105820974944")


# ----- evaluating a check ------------------------------------------------------------

def evaluate(node) -> Fraction | Decimal:
    """Value of a parsed check: a Fraction when exact, otherwise a Decimal with ``PRECISION`` digits."""
    with localcontext() as context:
        context.prec = PRECISION
        return _compute(node, 1)


def _compute(node, depth: int) -> Fraction | Decimal:
    if isinstance(node, Fraction):
        return node
    if isinstance(node, int) and not isinstance(node, bool):
        return Fraction(node)
    if isinstance(node, str):
        if node == "pi":
            return +_PI  # the unary plus rounds to the working precision
        raise DslError(f"„{node}“ nije broj")
    if not isinstance(node, tuple) or not node or not isinstance(node[0], str):
        raise DslError("deo izraza provere nije ni broj ni poziv operatora")
    if depth > dsl.MAX_DEPTH:
        raise DslError(f"izraz provere je ugnežđen dublje od {dsl.MAX_DEPTH} nivoa", "S-check-depth")
    name, *arguments = dsl.checked(node[0], node[1:])
    return _OPERATORS[name]([_compute(argument, depth + 1) for argument in arguments])


def _decimal(value) -> Decimal:
    """A fraction as a decimal; a decimal passes through."""
    if not isinstance(value, Fraction):
        return value
    return Decimal(value.numerator) / Decimal(value.denominator)


def _alike(values: list) -> list:
    """The values on one type, so that they can be compared or sorted."""
    if any(isinstance(value, Decimal) for value in values):
        return [_decimal(value) for value in values]
    return list(values)


def _pair(left, right, op) -> Fraction | Decimal:
    """``op(left, right)``: exact for fractions, decimal arithmetic once ``pi`` is involved."""
    try:
        if isinstance(left, Decimal) or isinstance(right, Decimal):
            return op(_decimal(left), _decimal(right))
        return op(left, right)
    except (ZeroDivisionError, DivisionByZero):
        raise DslError("deljenje nulom", "S-check-zero") from None
    except ArithmeticError as exc:  # the decimal module refused the operation
        raise DslError(f"računanje nije uspelo: {type(exc).__name__}") from None


def _fold(values: list, op) -> Fraction | Decimal:
    result = values[0]
    for value in values[1:]:
        result = _pair(result, value, op)
    return result


def _subtract(values: list) -> Fraction | Decimal:
    return -values[0] if len(values) == 1 else _fold(values, sub)


def _divide(values: list) -> Fraction | Decimal:
    """``a / (b * c * …)``: one divisor, the product of everything after the dividend."""
    divisor = _fold(values[1:], mul)
    if divisor == 0:
        raise DslError("deljenje nulom", "S-check-zero")
    return _pair(values[0], divisor, truediv)


def _power(values: list) -> Fraction | Decimal:
    base, exponent = values
    exponent = _whole_number(exponent, "stepen")
    if isinstance(base, Fraction) and abs(base.numerator).bit_length() * abs(exponent) > MAX_BITS:
        raise DslError("stepen daje prevelik broj")
    if base == 0 and exponent < 0:
        raise DslError("deljenje nulom", "S-check-zero")
    return base ** exponent


def _sqrt(values: list) -> Fraction | Decimal:
    (value,) = values
    if value < 0:
        raise DslError("koren negativnog broja ne postoji")
    if isinstance(value, Fraction):
        numerator, denominator = math.isqrt(value.numerator), math.isqrt(value.denominator)
        if numerator ** 2 == value.numerator and denominator ** 2 == value.denominator:
            return Fraction(numerator, denominator)
    return _decimal(value).sqrt()


def _pick(values: list, better) -> Fraction | Decimal:
    """The smallest (``better = lt``) or the largest argument, given back as it was written."""
    best = values[0]
    for value in values[1:]:
        left, right = _alike([best, value])
        if better(right, left):
            best = value
    return best


def _round(values: list) -> Fraction:
    """Half up, the school rule: 2.5 becomes 3, −2.5 becomes −3. The result is exact."""
    digits = _whole_number(values[1], "broj decimala") if len(values) == 2 else 0
    if abs(digits) > MAX_ROUND_TO:
        raise DslError(f"broj decimala mora biti od −{MAX_ROUND_TO} do {MAX_ROUND_TO}")
    value = values[0]
    if isinstance(value, Decimal):
        return Fraction(_half_up(value, digits))
    scaled = abs(value * Fraction(10) ** digits)
    numerator, remainder = divmod(scaled.numerator, scaled.denominator)
    if remainder * 2 >= scaled.denominator:  # a tie goes away from zero
        numerator += 1
    rounded = Fraction(numerator) / Fraction(10) ** digits
    return rounded if value >= 0 else -rounded


def _half_up(value: Decimal, digits: int) -> Decimal:
    """A decimal rounded half up to ``digits`` places; a number of any size can be rounded."""
    with localcontext() as context:
        context.prec = PRECISION
        return value.scaleb(digits).to_integral_value(rounding=ROUND_HALF_UP).scaleb(-digits)


def _mean(values: list) -> Fraction | Decimal:
    return _divide([_fold(values, add), Fraction(len(values))])


def _median(values: list) -> Fraction | Decimal:
    ordered = sorted(_alike(values))
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return _mean(ordered[middle - 1: middle + 1])


def _mode(values: list) -> Fraction | Decimal:
    counts: dict = {}
    for value in _alike(values):
        counts[value] = counts.get(value, 0) + 1
    most = max(counts.values())
    winners = [value for value, count in counts.items() if count == most]
    if len(winners) > 1:
        raise DslError("moda nije jedinstvena, pa provera nema samo jednu vrednost")
    return winners[0]


def _gcd(values: list) -> Fraction:
    return Fraction(math.gcd(*_whole_numbers(values, "gcd")))


def _lcm(values: list) -> Fraction:
    return Fraction(math.lcm(*_whole_numbers(values, "lcm")))


def _mod(values: list) -> Fraction | Decimal:
    """The remainder of a division, as in school: never negative."""
    dividend, divisor = values
    if divisor == 0:
        raise DslError("deljenje nulom", "S-check-zero")
    if divisor < 0:
        raise DslError("delilac kod mod mora biti pozitivan broj")
    quotient = _pair(dividend, divisor, truediv)
    return _pair(dividend, _pair(divisor, Fraction(math.floor(quotient)), mul), sub)


def _percent(values: list) -> Fraction | Decimal:
    """The first argument as a percentage of the second."""
    return _divide([_pair(values[0], values[1], mul), Fraction(100)])


def _whole_number(value, what: str) -> int:
    if isinstance(value, Fraction) and value.denominator == 1:
        return value.numerator
    raise DslError(f"{what} mora biti ceo broj")


def _whole_numbers(values: list, what: str) -> list[int]:
    return [_whole_number(value, what) for value in values]


_OPERATORS = {
    "+": lambda values: _fold(values, add),
    "-": _subtract,
    "*": lambda values: _fold(values, mul),
    "/": _divide,
    "pow": _power,
    "sqrt": _sqrt,
    "abs": lambda values: abs(values[0]),
    "min": lambda values: _pick(values, lt),
    "max": lambda values: _pick(values, gt),
    "floor": lambda values: Fraction(math.floor(values[0])),
    "ceil": lambda values: Fraction(math.ceil(values[0])),
    "round": _round,
    "mean": _mean,
    "median": _median,
    "mode": _mode,
    "gcd": _gcd,
    "lcm": _lcm,
    "mod": _mod,
    "percent": _percent,
}


# ----- reading an answer --------------------------------------------------------------

def parse_answer(text: str, canonical: bool = False) -> Fraction | None:
    """Read a number; None when the text is not one.

    As a pupil types it (the default) a dot followed by exactly three digits is a thousands
    separator. In a data file (``canonical``) a dot is always the decimal point, so that
    ``0.125`` is one eighth and not a hundred and twenty-five.
    """
    if not isinstance(text, str):
        return None
    body = text.strip()
    negative = body.startswith("-")
    if body[:1] in ("+", "-"):
        body = body[1:]
    if canonical:
        body = body.replace(".", ",")  # the comma is always a decimal separator below
    value = _unsigned(body) if 0 < len(body) <= MAX_LENGTH else None
    if value is None:
        return None
    return -value if negative else value


def _unsigned(body: str) -> Fraction | None:
    """The number without its sign, or None when the text is not exactly one number."""
    if "/" in body:  # a fraction, possibly mixed: 3/4, 2 3/4
        head, _, denominator = body.partition("/")
        integer, space, numerator = head.rpartition(" ")
        if not space:
            integer, numerator = "", head
        if not (_DIGITS.fullmatch(numerator) and _DIGITS.fullmatch(denominator)):
            return None
        whole = Fraction(0) if not integer else _natural(integer)
        if whole is None or int(denominator) == 0:
            return None
        return whole + Fraction(int(numerator), int(denominator))
    if "," not in body:
        dot = body.rfind(".")
        if dot != -1 and len(body) - dot == 4:  # a dot and exactly three digits at the end: 1.000 is a thousand
            return None if body.count(".") > 1 else _natural(body.replace(".", " "))
        whole, _, decimals = body.partition(".")
        if "." in decimals:
            return None  # a second decimal point
    else:  # a comma is always a decimal separator
        whole, _, decimals = body.partition(",")
        if "," in decimals:
            return None  # a second decimal comma
    if not decimals:
        return _natural(body)
    if not _DIGITS.fullmatch(decimals):
        return None
    whole = _natural(whole)
    if whole is None:
        return None
    return whole + Fraction(int(decimals), 10 ** len(decimals))


def _natural(text: str) -> Fraction | None:
    """A natural number whose thousands are separated by single spaces; None when the text is not one."""
    if not _INTEGER.fullmatch(text):
        return None
    return Fraction(int(text.replace(" ", "")))


# ----- comparing and formatting -------------------------------------------------------

def _decimals(round_to) -> int | None:
    """``round_to`` as a usable number of decimals; None when it is missing or malformed."""
    if isinstance(round_to, int) and not isinstance(round_to, bool) and 0 <= round_to <= MAX_ROUND_TO:
        return round_to
    return None


def format_value(value, round_to: int | None = None) -> str:
    """The canonical text of an answer: integers plain, fractions as ``a/b``, decimals with a dot."""
    if isinstance(value, Decimal):
        decimals = _decimals(round_to)
        return _decimal_text(_half_up(value, 0 if decimals is None else decimals))
    value = Fraction(value)
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def _decimal_text(value: Decimal) -> str:
    """A finite decimal without trailing zeros: 1.410 is 1.41 and 2.00 is 2."""
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text == "-0" else text


def answers_equal(expected, given, round_to: int | None = None) -> bool:
    """True when ``given`` is the expected value; an inexact value counts only rounded to ``round_to``."""
    if isinstance(expected, Decimal):
        decimals = _decimals(round_to)
        if decimals is None:
            return False
        expected = _half_up(expected, decimals)
    return Fraction(expected) == given


def rational(value, round_to: int | None = None) -> tuple[str, str]:
    """Numerator and denominator as decimal strings: the exact answer the JS engine compares with."""
    if isinstance(value, Decimal):
        decimals = _decimals(round_to)
        value = _half_up(value, 0 if decimals is None else decimals)
    value = Fraction(value)
    return (str(value.numerator), str(value.denominator))


# ----- verifying a corpus --------------------------------------------------------------

def verify(corpus, issues) -> None:
    """Recompute every answer from its ``check`` and report each question that disagrees."""
    for index, question in enumerate(corpus.question_list):
        if not isinstance(question, dict):
            continue
        question_id = question.get("id")
        known = isinstance(question_id, str)
        where = question_id if known else f"questions[{index}]"
        path = corpus.question_file.get(question_id, "") if known else ""
        try:
            if question.get("type") == "choice":
                _verify_choice(question, path, where, issues)
            else:
                _verify_numeric(question, path, where, issues)
        except DslError as exc:
            issues.add(path, where, exc.rule, f"{_about(question.get('check'))}: {exc}")
        except (ValueError, ArithmeticError, TypeError) as exc:  # numbers too large to convert, an operation refused
            issues.add(path, where, "S-check-parse", f"{_about(question.get('check'))}: računanje nije uspelo ({type(exc).__name__})")


def _verify_numeric(question: dict, path: str, where: str, issues) -> None:
    check, answer, round_to = question.get("check"), question.get("answer"), question.get("round_to")
    value = _expected(check, round_to)
    given = parse_answer(answer, canonical=True)
    if given is None:
        issues.add(path, where, "S-answer-mismatch", _not_a_number(answer))
    elif not answers_equal(value, given, round_to):
        issues.add(path, where, "S-answer-mismatch", f"odgovor {_quoted(answer)} nije jednak vrednosti provere {format_value(value, round_to)}")


def _verify_choice(question: dict, path: str, where: str, issues) -> None:
    check, round_to = question.get("check"), question.get("round_to")
    if not isinstance(check, str) or not check.strip():
        raise DslError("nedostaje" if not isinstance(check, str) else "je prazan")
    choices = question.get("choices")
    options = [choice for choice in choices if isinstance(choice, dict)] if isinstance(choices, list) else []
    correct = next((choice for choice in options if choice.get("id") == question.get("answer")), None)
    if correct is None:
        issues.add(path, where, "S-choice-value", f"nijedna ponuda nema id odgovora {_quoted(question.get('answer'))}")
        return
    texts = [(choice, _option_value(choice.get("text"))) for choice in options]
    if all(option_value is None for _, option_value in texts):
        # Words, signs or units: no option is a number, so the check is compared as text.
        if _plain_text(correct.get("text")) != _plain_text(check):
            issues.add(path, where, "S-choice-value", f"tekst tačne ponude {_quoted(correct.get('text'))} nije jednak polju check {_quoted(check)}")
        return
    value = _expected(check, round_to)
    expected = format_value(value, round_to)
    for choice, option_value in texts:
        same = option_value is not None and answers_equal(value, option_value, round_to)
        if choice is correct and not same:
            issues.add(path, where, "S-choice-value", f"tekst tačne ponude {_quoted(choice.get('text'))} ne daje odgovor {expected}")
        elif choice is not correct and option_value is None:
            issues.add(path, where, "S-choice-value", f"tekst pogrešne ponude {_quoted(choice.get('id'))} nije broj, a ostale ponude su")
        elif choice is not correct and same:
            issues.add(path, where, "S-choice-value", f"pogrešna ponuda {_quoted(choice.get('id'))} ima vrednost odgovora")


def _expected(check, round_to) -> Fraction | Decimal:
    """The value a check promises — or a DslError that says which rule the check breaks."""
    value = evaluate(dsl.parse(check))
    if isinstance(value, Decimal) and _decimals(round_to) is None:
        raise DslError(_IRRATIONAL, "S-round-to")
    return value


def _option_value(text) -> Fraction | Decimal | None:
    """The value of an option's text: read as an answer first, then parsed as a check."""
    plain = _plain_text(text)
    if plain is None:
        return None
    value = parse_answer(plain, canonical=True)
    if value is None:
        try:
            value = evaluate(dsl.parse(plain))
        except DslError:
            return None
    return value


def _plain_text(text) -> str | None:
    """An option's text or a check without the ``$…$`` a formula wears and with ``{,}`` as a comma."""
    if not isinstance(text, str):
        return None
    text = text.strip()
    if len(text) > 1 and text.startswith("$") and text.endswith("$") and "$" not in text[1:-1]:
        text = text[1:-1]
    return text.replace("{,}", ",").strip()


def _quoted(text) -> str:
    """A value for a message: text in Serbian quotes, anything else described."""
    if isinstance(text, str):
        return f"„{text}“"
    return "nedostaje" if text is None else repr(text)


def _about(check) -> str:
    """How a message names the check: quoted text (shortened when long), or the field itself when it is not text."""
    if not isinstance(check, str):
        return "polje check"
    shown = check if len(check) <= 60 else check[:60] + "…"
    return f"izraz provere „{shown}“"


def _not_a_number(answer) -> str:
    if isinstance(answer, str):
        return f"odgovor „{answer}“ nije broj"
    return 'odgovor mora biti broj napisan kao tekst, na primer "15"'
