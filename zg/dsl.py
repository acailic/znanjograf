"""Parser for ``check``, the S-expression that computes the answer of a question.

``parse`` turns the text into plain data — a tuple per call, ``("+", 8, 7)``, or a
single atom — and enforces what every check must respect: known operators, their
number of arguments, at most ``MAX_DEPTH`` levels of nesting and ``MAX_NODES`` nodes.
Computing the value of that tree is the job of :mod:`zg.mathcheck`.
"""

from __future__ import annotations

import re
from fractions import Fraction

MAX_DEPTH = 12
MAX_NODES = 200
MAX_ATOM = 100  # the longest number an atom may spell out

# operator -> (fewest arguments, most arguments; None means any number)
ARITY: dict[str, tuple[int, int | None]] = {
    "+": (2, None), "-": (1, None), "*": (2, None), "/": (2, None),
    "pow": (2, 2), "sqrt": (1, 1), "abs": (1, 1), "min": (2, None), "max": (2, None),
    "floor": (1, 1), "ceil": (1, 1), "round": (1, 2), "mean": (2, None), "median": (2, None),
    "mode": (2, None), "gcd": (2, None), "lcm": (2, None), "mod": (2, 2), "percent": (2, 2),
}

_TOKEN = re.compile(r"\(|\)|[^\s()]+")  # a bracket, or a run of characters without whitespace
_NUMBER = re.compile(r"[+-]?[0-9]+(?:\.[0-9]+)?")  # the data file writes a decimal with a dot


class DslError(ValueError):
    """A check is not a valid computation. ``rule`` is the verify code that reports it."""

    def __init__(self, message: str, rule: str = "S-check-parse") -> None:
        super().__init__(message)
        self.rule = rule


def parse(text: str) -> tuple | Fraction | str:
    """Parse a check into a tuple tree; a lone atom comes back as a Fraction or the symbol ``pi``."""
    if not isinstance(text, str):
        raise DslError("izraz provere mora biti tekst")
    tokens = _TOKEN.findall(text)
    if not tokens:
        raise DslError("izraz provere je prazan")
    parser = _Parser(tokens)
    node = parser.expression(1)
    if parser.peek() is not None:
        raise DslError("posle izraza provere ima još teksta")
    return node


def checked(operator: str, arguments: list) -> tuple:
    """The call node ``(operator, *arguments)`` once its operator and argument count are right.

    The parser and the evaluator both go through here, so a tree built by hand gets
    the same scrutiny as parsed text.
    """
    if operator not in ARITY:
        raise DslError(f"nepoznat operator „{operator}“")
    fewest, most = ARITY[operator]
    if len(arguments) < fewest or (most is not None and len(arguments) > most):
        raise DslError(f"operator „{operator}“ traži {_expects(fewest, most)}, a ima {len(arguments)}")
    if operator == "/" and any(argument == 0 for argument in arguments[1:]):
        raise DslError("deljenje nulom", "S-check-zero")
    return (operator, *arguments)


class _Parser:
    """Recursive descent over the tokens; one call of ``expression`` reads one node."""

    def __init__(self, tokens: list[str]) -> None:
        self.tokens = tokens
        self.position = 0
        self.size = 0

    def peek(self) -> str | None:
        return self.tokens[self.position] if self.position < len(self.tokens) else None

    def take(self) -> str:
        token = self.peek()
        if token is None:
            raise DslError("izraz provere nije kompletan")
        self.position += 1
        return token

    def expression(self, depth: int) -> tuple | Fraction | str:
        self.size += 1
        if self.size > MAX_NODES:
            raise DslError(f"izraz provere ima više od {MAX_NODES} delova", "S-check-depth")
        token = self.take()
        if token != "(":
            return _atom(token)
        if depth > MAX_DEPTH:
            raise DslError(f"izraz provere je ugnežđen dublje od {MAX_DEPTH} nivoa", "S-check-depth")
        operator = self.take()
        if operator in ("(", ")"):
            raise DslError("posle otvorene zagrade ide operator, a zatim argumenti")
        arguments: list = []
        while self.peek() != ")":
            arguments.append(self.expression(depth + 1))
        self.take()
        return checked(operator, arguments)


def _atom(token: str) -> Fraction | str:
    if _NUMBER.fullmatch(token):
        if len(token) > MAX_ATOM:  # Python cannot even convert thousands of digits to text again
            raise DslError("broj u izrazu provere je prevelik")
        return Fraction(token)
    if token == "pi":
        return "pi"
    raise DslError(f"„{token}“ nije broj ni pi")


def _expects(fewest: int, most: int | None) -> str:
    if most is None:
        return "najmanje dva argumenta" if fewest == 2 else "najmanje jedan argument"
    if fewest == most:
        return "jedan argument" if most == 1 else "dva argumenta" if most == 2 else f"{most} argumenata"
    return "jedan ili dva argumenta"
