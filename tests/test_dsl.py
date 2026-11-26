"""The check DSL: atoms, structure, arity and the limits every ``check`` must respect."""

import unittest
from fractions import Fraction

from zg import dsl


def nested(depth: int) -> str:
    """``depth`` nested one-argument calls around a single atom."""
    return "(abs " * depth + "1" + ")" * depth


def flat(count: int) -> str:
    """A sum of ``count`` atoms."""
    return "(+ " + " ".join(["1"] * count) + ")"


def tree(depth: int):
    node = Fraction(1)
    for _ in range(depth):
        node = ("abs", node)
    return node


class ParseTest(unittest.TestCase):
    def test_integer_atom(self):
        self.assertEqual(dsl.parse("7"), Fraction(7))
        self.assertEqual(dsl.parse("+3"), Fraction(3))

    def test_negative_integer_atom(self):
        self.assertEqual(dsl.parse("-3"), Fraction(-3))

    def test_decimal_atom_is_an_exact_fraction(self):
        self.assertEqual(dsl.parse("2.5"), Fraction(5, 2))

    def test_pi_is_a_symbol(self):
        self.assertEqual(dsl.parse("pi"), "pi")

    def test_expression_is_a_tuple_with_the_operator_first(self):
        self.assertEqual(dsl.parse("(+ 8 7)"), ("+", Fraction(8), Fraction(7)))

    def test_nested_expression_is_a_nested_tuple(self):
        self.assertEqual(
            dsl.parse("(+ 1 (- 2 3))"),
            ("+", Fraction(1), ("-", Fraction(2), Fraction(3))),
        )

    def test_whitespace_between_tokens_is_free(self):
        self.assertEqual(dsl.parse("  (percent\t15\n200) "), ("percent", Fraction(15), Fraction(200)))

    def test_negation_takes_one_argument(self):
        self.assertEqual(dsl.parse("(- 5)"), ("-", Fraction(5)))

    def test_round_takes_one_or_two_arguments(self):
        self.assertEqual(dsl.parse("(round 3.14 2)"), ("round", Fraction(157, 50), Fraction(2)))

    def test_twelve_levels_of_nesting_are_allowed(self):
        self.assertEqual(dsl.parse(nested(12)), tree(12))

    def test_two_hundred_nodes_are_allowed(self):
        self.assertEqual(len(dsl.parse(flat(199))), 200)


class ParseErrorTest(unittest.TestCase):
    def error(self, text) -> dsl.DslError:
        with self.assertRaises(dsl.DslError) as caught:
            dsl.parse(text)
        return caught.exception

    def test_unknown_operator(self):
        error = self.error("(foo 1)")
        self.assertEqual(error.rule, "S-check-parse")
        self.assertIn("foo", str(error))

    def test_atom_that_is_not_a_number(self):
        for text in ("trougao", "(+ 1 abc)", "3+4", "2,5", "1 000"):
            with self.subTest(text):
                self.assertEqual(self.error(text).rule, "S-check-parse")

    def test_malformed_text(self):
        for text in ("", "   ", "(", ")", "(+ 8 7", "(+ 8 7))", "(+ 8 7) 5", "()", "(+ 8 (7))"):
            with self.subTest(text):
                self.assertEqual(self.error(text).rule, "S-check-parse")

    def test_check_must_be_text(self):
        for text in (None, 7, ("+", 1, 2)):
            with self.subTest(text):
                self.assertEqual(self.error(text).rule, "S-check-parse")

    def test_number_too_long_to_be_an_atom(self):
        self.assertEqual(self.error("9" * 5000).rule, "S-check-parse")

    def test_wrong_number_of_arguments(self):
        for text in ("(sqrt 1 2)", "(pow 2)", "(mod 7)", "(round 3.14 1 0)", "(+)", "(*)", "(mean 4)"):
            with self.subTest(text):
                self.assertEqual(self.error(text).rule, "S-check-parse")

    def test_literal_zero_divisor(self):
        for text in ("(/ 1 0)", "(/ 1 2 0)", "(/ 1 0.0)"):
            with self.subTest(text):
                self.assertEqual(self.error(text).rule, "S-check-zero")

    def test_zero_dividend_is_fine(self):
        self.assertEqual(dsl.parse("(/ 0 5)"), ("/", Fraction(0), Fraction(5)))

    def test_thirteenth_level_of_nesting(self):
        error = self.error(nested(13))
        self.assertEqual(error.rule, "S-check-depth")

    def test_two_hundred_and_first_node(self):
        self.assertEqual(self.error(flat(200)).rule, "S-check-depth")
