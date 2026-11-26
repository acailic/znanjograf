"""Exact answers: computing a ``check``, reading an ``answer``, and verifying a whole corpus."""

import contextlib
import decimal
import io
import json
import tempfile
import unittest
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

from zg import __main__ as cli
from zg import dsl, mathcheck
from zg.corpus import Corpus
from zg.dsl import DslError
from zg.issues import Issues
from tests import helpers

VECTORS = Path(__file__).resolve().parent / "fixtures" / "answer-vectors.json"
SQRT_2 = "1.41421356237309504880168872420969807856967187537694807317668"
PI_50 = "3.14159265358979323846264338327950288419716939937510"


def value(check: str):
    return mathcheck.evaluate(dsl.parse(check))


def nested(depth: int) -> str:
    return "(abs " * depth + "1" + ")" * depth


class EvaluateTest(unittest.TestCase):
    def test_addition(self):
        self.assertEqual(value("(+ 8 7)"), 15)

    def test_division_is_exact_and_n_ary(self):
        result = value("(/ 3 4 5)")
        self.assertIs(type(result), Fraction)
        self.assertEqual(result, Fraction(3, 20))

    def test_subtraction_negates_with_one_argument(self):
        self.assertEqual(value("(- 5)"), -5)
        self.assertEqual(value("(- 10 3 2)"), 5)

    def test_percent(self):
        self.assertEqual(value("(percent 15 200)"), 30)

    def test_power(self):
        self.assertEqual(value("(pow 2 10)"), 1024)
        self.assertEqual(value("(pow 2 -2)"), Fraction(1, 4))

    def test_square_root_of_a_square_is_exact(self):
        result = value("(sqrt (/ 9 16))")
        self.assertIs(type(result), Fraction)
        self.assertEqual(result, Fraction(3, 4))

    def test_square_root_of_a_non_square_is_decimal(self):
        result = value("(sqrt 2)")
        self.assertIs(type(result), Decimal)
        self.assertEqual(str(result), SQRT_2)

    def test_pi_is_decimal_with_sixty_digits(self):
        result = value("pi")
        self.assertIs(type(result), Decimal)
        self.assertTrue(str(result).startswith(PI_50), str(result))
        self.assertEqual(len(result.as_tuple().digits), 60)

    def test_arithmetic_with_pi_stays_decimal(self):
        for check in ("(* 2 pi)", "(+ pi 1)", "(/ pi 4)"):
            with self.subTest(check):
                self.assertIs(type(value(check)), Decimal)
        self.assertTrue(str(value("(* 2 pi)")).startswith("6.283185307179586476925286766559"))

    def test_rational_arithmetic_stays_exact(self):
        self.assertEqual(value("(+ (/ 1 2) (/ 1 3))"), Fraction(5, 6))
        self.assertEqual(value("(* 0.1 3)"), Fraction(3, 10))

    def test_abs_min_max(self):
        self.assertEqual(value("(abs -7)"), 7)
        self.assertEqual(value("(min 3 1 2)"), 1)
        self.assertEqual(value("(max 3 1 2)"), 3)

    def test_floor_and_ceil_give_whole_numbers(self):
        self.assertEqual(value("(floor 3.7)"), 3)
        self.assertEqual(value("(ceil 3.2)"), 4)
        self.assertEqual(value("(floor -3.5)"), -4)
        self.assertIs(type(value("(floor pi)")), Fraction)
        self.assertEqual(value("(floor pi)"), 3)

    def test_round_rounds_half_up(self):
        self.assertEqual(value("(round 2.5)"), 3)
        self.assertEqual(value("(round 3.5)"), 4)
        self.assertEqual(value("(round -2.5)"), -3)
        self.assertEqual(value("(round 2.675 2)"), Fraction(268, 100))
        self.assertEqual(value("(round 1234 -2)"), 1200)

    def test_rounded_decimal_is_exact(self):
        result = value("(round (sqrt 2) 2)")
        self.assertIs(type(result), Fraction)
        self.assertEqual(result, Fraction(141, 100))

    def test_mean_median_mode(self):
        self.assertEqual(value("(mean 2 4 6)"), 4)
        self.assertEqual(value("(mean 1 2)"), Fraction(3, 2))
        self.assertEqual(value("(median 1 5 2)"), 2)
        self.assertEqual(value("(median 1 2 3 4)"), Fraction(5, 2))
        self.assertEqual(value("(mode 1 2 2 3)"), 2)

    def test_gcd_lcm_mod(self):
        self.assertEqual(value("(gcd 12 18)"), 6)
        self.assertEqual(value("(lcm 4 6)"), 12)
        self.assertEqual(value("(mod 17 5)"), 2)
        self.assertEqual(value("(mod -7 3)"), 2)

    def test_plain_numbers_are_accepted_as_nodes(self):
        self.assertEqual(mathcheck.evaluate(Fraction(3, 4)), Fraction(3, 4))
        self.assertEqual(mathcheck.evaluate(7), 7)

    def test_default_decimal_context_is_untouched(self):
        before = decimal.getcontext().prec
        value("(+ pi 1)")
        self.assertEqual(decimal.getcontext().prec, before)


class EvaluateErrorTest(unittest.TestCase):
    def node_error(self, node) -> DslError:
        with self.assertRaises(DslError) as caught:
            mathcheck.evaluate(node)
        return caught.exception

    def check_error(self, check: str) -> DslError:
        with self.assertRaises(DslError) as caught:
            value(check)
        return caught.exception

    def test_division_by_a_computed_zero(self):
        for check in ("(/ 1 (- 3 3))", "(/ pi (- 2 2))"):
            with self.subTest(check):
                self.assertEqual(self.check_error(check).rule, "S-check-zero")

    def test_mod_by_zero(self):
        self.assertEqual(self.check_error("(mod 7 (- 2 2))").rule, "S-check-zero")

    def test_zero_to_a_negative_power(self):
        self.assertEqual(self.check_error("(pow 0 -1)").rule, "S-check-zero")

    def test_unknown_operator(self):
        self.assertEqual(self.node_error(("foo", 1)).rule, "S-check-parse")

    def test_atom_that_is_not_a_number(self):
        for node in ("trougao", "abc", None, 2.5, ("+", 1, "x"), ["+", 1, 2], ()):
            with self.subTest(node):
                self.assertEqual(self.node_error(node).rule, "S-check-parse")

    def test_square_root_of_a_negative_number(self):
        self.assertIn("koren", str(self.check_error("(sqrt -4)")))

    def test_whole_numbers_are_required_for_a_power_or_gcd(self):
        self.assertEqual(self.node_error(("pow", Fraction(2), Fraction(1, 2))).rule, "S-check-parse")
        self.assertEqual(self.node_error(("gcd", Fraction(5, 2), Fraction(1))).rule, "S-check-parse")

    def test_tied_mode_has_no_single_value(self):
        self.assertIn("moda", str(self.check_error("(mode 1 1 2 2)")))

    def test_numbers_that_would_grow_without_bound(self):
        for check in ("(pow 2 100000)", f"(pow {'9' * 200} 2)", "9" * 5000):
            with self.subTest(check=check[:20]):
                self.assertEqual(self.check_error(check).rule, "S-check-parse")

    def test_hand_built_tree_respects_the_depth_limit(self):
        node = Fraction(1)
        for _ in range(13):
            node = ("abs", node)
        self.assertEqual(self.node_error(node).rule, "S-check-depth")


class ParseAnswerTest(unittest.TestCase):
    def test_numbers_in_every_notation(self):
        self.assertEqual(mathcheck.parse_answer("15"), Fraction(15))
        self.assertEqual(mathcheck.parse_answer("3,5"), Fraction(7, 2))
        self.assertEqual(mathcheck.parse_answer("3.14"), Fraction(157, 50))
        self.assertEqual(mathcheck.parse_answer("3/4"), Fraction(3, 4))
        self.assertEqual(mathcheck.parse_answer("2 3/4"), Fraction(11, 4))
        self.assertEqual(mathcheck.parse_answer("-7"), Fraction(-7))
        self.assertEqual(mathcheck.parse_answer("1 000"), Fraction(1000))

    def test_result_is_always_a_fraction(self):
        for text in ("15", "3,5", "2 3/4", "-0"):
            with self.subTest(text):
                self.assertIs(type(mathcheck.parse_answer(text)), Fraction)

    def test_not_text(self):
        for text in (None, 15, Fraction(3), ["3"]):
            with self.subTest(text):
                self.assertIsNone(mathcheck.parse_answer(text))

    def test_far_too_long_text_is_not_one_number(self):
        self.assertIsNone(mathcheck.parse_answer("9" * 5000))
        self.assertEqual(mathcheck.parse_answer(" " * 300 + "15" + " " * 300), Fraction(15))


class AnswerVectorsTest(unittest.TestCase):
    """``answer-vectors.json`` is shared with the JS engine, so its shape is part of the contract."""

    def setUp(self):
        self.vectors = json.loads(VECTORS.read_text(encoding="utf-8"))

    def test_file_shape(self):
        self.assertEqual(set(self.vectors), {"valid", "invalid"})
        self.assertGreaterEqual(len(self.vectors["valid"]), 24)
        for vector in self.vectors["valid"]:
            self.assertEqual(set(vector), {"text", "num", "den"}, vector)
        self.assertTrue(all(isinstance(text, str) for text in self.vectors["invalid"]), "invalid")
        valid = [vector["text"] for vector in self.vectors["valid"]]
        invalid = self.vectors["invalid"]
        self.assertEqual(len(set(valid)), len(valid))
        self.assertFalse(set(valid) & set(invalid))

    def test_vectors_cover_the_required_cases(self):
        valid = [vector["text"] for vector in self.vectors["valid"]]
        for text in ("-7", "+7", "1 000", "1.000", "1.5", "007", "-0", "2 3/4", "-5/6"):
            self.assertIn(text, valid)
        for text in ("", "3,,5", "1/0", "abc", "3 4"):
            self.assertIn(text, self.vectors["invalid"])

    def test_every_valid_vector_parses(self):
        for vector in self.vectors["valid"]:
            with self.subTest(vector["text"]):
                self.assertEqual(mathcheck.parse_answer(vector["text"]), Fraction(int(vector["num"]), int(vector["den"])))

    def test_every_invalid_vector_is_rejected(self):
        for text in self.vectors["invalid"]:
            with self.subTest(text):
                self.assertIsNone(mathcheck.parse_answer(text))


class RationalTest(unittest.TestCase):
    def test_fraction(self):
        self.assertEqual(mathcheck.rational(Fraction(3, 4)), ("3", "4"))
        self.assertEqual(mathcheck.rational(Fraction(-5)), ("-5", "1"))
        self.assertEqual(mathcheck.rational(Fraction(7, 2), 2), ("7", "2"))  # round_to changes nothing here

    def test_decimal_rounds_to_round_to(self):
        self.assertEqual(mathcheck.rational(value("(sqrt 2)"), 2), ("141", "100"))
        self.assertEqual(mathcheck.rational(value("(sqrt 2)"), 0), ("1", "1"))
        self.assertEqual(mathcheck.rational(value("pi"), 3), ("1571", "500"))

    def test_decimal_without_round_to_rounds_to_an_integer(self):
        self.assertEqual(mathcheck.rational(value("(sqrt 2)")), ("1", "1"))


class FormatValueTest(unittest.TestCase):
    def test_integers_are_plain(self):
        self.assertEqual(mathcheck.format_value(Fraction(15)), "15")
        self.assertEqual(mathcheck.format_value(Fraction(-7)), "-7")
        self.assertEqual(mathcheck.format_value(42), "42")

    def test_fractions_keep_the_slash(self):
        self.assertEqual(mathcheck.format_value(Fraction(3, 4)), "3/4")
        self.assertEqual(mathcheck.format_value(Fraction(-5, 6)), "-5/6")
        self.assertEqual(mathcheck.format_value(Fraction(7, 2)), "7/2")

    def test_decimals_use_a_dot(self):
        self.assertEqual(mathcheck.format_value(value("(sqrt 2)"), 2), "1.41")
        self.assertEqual(mathcheck.format_value(value("pi"), 3), "3.142")
        self.assertEqual(mathcheck.format_value(value("(sqrt 2)")), "1")
        self.assertEqual(mathcheck.format_value(Decimal("2.004"), 2), "2")

    def test_decimals_have_no_trailing_zeros_or_negative_zero(self):
        self.assertEqual(mathcheck.format_value(Decimal("1.4100"), 4), "1.41")
        self.assertEqual(mathcheck.format_value(Decimal("0.500"), 3), "0.5")
        self.assertEqual(mathcheck.format_value(Decimal("-0.004"), 2), "0")
        self.assertEqual(mathcheck.format_value(Decimal("1E+3"), 2), "1000")


class AnswersEqualTest(unittest.TestCase):
    def test_fractions_compare_exactly(self):
        self.assertTrue(mathcheck.answers_equal(Fraction(15), Fraction(15)))
        self.assertTrue(mathcheck.answers_equal(Fraction(3, 4), Fraction(3, 4), 2))
        self.assertFalse(mathcheck.answers_equal(Fraction(5, 2), Fraction(3, 2)))
        self.assertFalse(mathcheck.answers_equal(Fraction(10, 3), Fraction(333, 100), 2))  # round_to does not relax an exact check
        self.assertFalse(mathcheck.answers_equal(Fraction(15), None))

    def test_decimal_needs_round_to(self):
        self.assertFalse(mathcheck.answers_equal(value("(sqrt 2)"), Fraction(141, 100)))
        self.assertTrue(mathcheck.answers_equal(value("(sqrt 2)"), Fraction(141, 100), 2))
        self.assertFalse(mathcheck.answers_equal(value("(sqrt 2)"), Fraction(142, 100), 2))


class VerifyTest(unittest.TestCase):
    def setUp(self):
        self.raw = helpers.fixture_raw()

    def issues(self) -> Issues:
        issues = Issues()
        mathcheck.verify(Corpus.from_raw("math", self.raw), issues)
        return issues

    def codes(self) -> set[str]:
        return self.issues().codes()

    def edit(self, question_id: str, **fields) -> dict:
        question = helpers.question(self.raw, question_id)
        question.update(fields)
        return question

    # ----- numeric questions ---------------------------------------------------------

    def test_fixture_is_clean(self):
        self.assertEqual(self.issues(), [])

    def test_issue_points_at_its_question(self):
        self.edit("mat-sabiranje-do-20-q3", answer="16")
        issue = self.issues()[0]
        self.assertEqual((issue.path, issue.where, issue.code), ("data/math/g1/questions.json", "mat-sabiranje-do-20-q3", "S-answer-mismatch"))

    def test_changed_answer_is_a_mismatch(self):
        self.edit("mat-sabiranje-do-20-q3", answer="16")
        self.assertEqual(self.codes(), {"S-answer-mismatch"})

    def test_answer_in_another_notation_is_still_equal(self):
        self.edit("mat-sabiranje-do-100-q1", answer="3,5", check="(/ 7 2)")
        self.assertEqual(self.issues(), [])

    def test_answer_that_is_not_a_number(self):
        for answer in ("petnaest", "", "15 kg", None, 15):
            with self.subTest(answer):
                self.edit("mat-sabiranje-do-20-q3", answer=answer)
                self.assertEqual(self.codes(), {"S-answer-mismatch"})

    def test_division_by_zero(self):
        self.edit("mat-sabiranje-do-20-q3", check="(/ 1 0)")
        self.assertEqual(self.codes(), {"S-check-zero"})

    def test_thirteenth_level_of_nesting(self):
        self.edit("mat-sabiranje-do-20-q3", check=nested(13))
        self.assertEqual(self.codes(), {"S-check-depth"})

    def test_twelfth_level_of_nesting_passes(self):
        self.edit("mat-sabiranje-do-20-q3", check=nested(12), answer="1")
        self.assertEqual(self.issues(), [])

    def test_unknown_operator(self):
        self.edit("mat-sabiranje-do-20-q3", check="(foo 1)")
        self.assertEqual(self.codes(), {"S-check-parse"})

    def test_check_that_is_not_an_expression(self):
        for check in (None, "", "trougao", "15 +", 7):
            with self.subTest(check):
                self.edit("mat-sabiranje-do-20-q3", check=check)
                self.assertEqual(self.codes(), {"S-check-parse"})

    def test_irrational_answer_needs_round_to(self):
        question = self.edit("mat-sabiranje-do-20-q3", check="(sqrt 2)", answer="1.41")
        self.assertEqual(self.codes(), {"S-round-to"})
        question["round_to"] = 2
        self.assertEqual(self.issues(), [])
        question["answer"] = "1.42"
        self.assertEqual(self.codes(), {"S-answer-mismatch"})

    def test_round_to_must_be_a_small_whole_number(self):
        question = self.edit("mat-sabiranje-do-20-q3", check="(sqrt 2)", answer="1.41")
        for round_to in ("2", -1, True, 10 ** 9):
            with self.subTest(round_to):
                question["round_to"] = round_to
                self.assertEqual(self.codes(), {"S-round-to"})

    def test_rounding_inside_the_check_needs_no_round_to(self):
        self.edit("mat-sabiranje-do-20-q3", check="(round (sqrt 2) 2)", answer="1.41")
        self.assertEqual(self.issues(), [])

    def test_round_to_does_not_relax_an_exact_check(self):
        self.edit("mat-sabiranje-do-20-q3", check="(/ 10 3)", answer="3.33", round_to=2)
        self.assertEqual(self.codes(), {"S-answer-mismatch"})
        self.edit("mat-sabiranje-do-20-q3", check="(/ 10 4)", answer="2.5", round_to=0)
        self.assertEqual(self.issues(), [])

    def test_records_that_are_not_questions_are_skipped(self):
        self.raw.questions[1].append("niz zapisa")
        self.raw.questions[1].append({"topic": "mat-brojevi-do-10", "level": "basic", "type": "numeric", "check": None})
        issues = self.issues()
        self.assertEqual([issue.where for issue in issues], ["questions[17]"])
        self.assertEqual(issues.codes(), {"S-check-parse"})

    # ----- choice questions ------------------------------------------------------------

    def test_wrong_choice_with_the_value_of_the_answer(self):
        self.edit("mat-geometrijski-oblici-q3")["choices"][0]["text"] = "$4$"
        self.assertEqual(self.codes(), {"S-choice-value"})

    def test_correct_choice_that_does_not_give_the_answer(self):
        self.edit("mat-geometrijski-oblici-q3")["choices"][2]["text"] = "$5$"
        self.assertEqual(self.codes(), {"S-choice-value"})

    def test_choice_text_that_is_not_a_number_among_numbers(self):
        self.edit("mat-geometrijski-oblici-q3")["choices"][0]["text"] = "$4O$"
        self.assertEqual(self.codes(), {"S-choice-value"})

    def test_decimal_comma_inside_a_math_span(self):
        question = self.edit("mat-geometrijski-oblici-q3", check="(/ 7 2)", answer="a")
        for choice, text in zip(question["choices"], ["$3{,}5$", "$3$", "$4$", "$5$"]):
            choice["text"] = text
        self.assertEqual(self.issues(), [])
        question["choices"][1]["text"] = "$3{,}50$"
        self.assertEqual(self.codes(), {"S-choice-value"})

    def test_choice_with_an_irrational_check_needs_round_to(self):
        question = self.edit("mat-geometrijski-oblici-q3", check="(sqrt 16)")
        self.assertEqual(self.issues(), [])
        question["check"] = "(sqrt 17)"
        self.assertEqual(self.codes(), {"S-round-to"})
        question["round_to"] = 1
        self.assertEqual(self.codes(), {"S-choice-value"})

    def test_numeric_choices_need_a_numeric_check(self):
        self.edit("mat-geometrijski-oblici-q3", check="cetiri")
        self.assertEqual(self.codes(), {"S-check-parse"})

    def test_text_choices_compare_the_check_with_the_option_text(self):
        question = self.edit("mat-geometrijski-oblici-q1", check="kvadrat")
        self.assertEqual(self.codes(), {"S-choice-value"})
        question["check"] = " trougao "
        self.assertEqual(self.issues(), [])

    def test_math_span_is_unwrapped_from_choice_text(self):
        self.edit("mat-poredjenje-do-100-q3", check=">")
        self.assertEqual(self.codes(), {"S-choice-value"})

    def test_text_check_may_contain_spaces_and_units(self):
        question = self.edit("mat-geometrijski-oblici-q1", check="5 cm", answer="a")
        for choice, text in zip(question["choices"], ["5 cm", "6 cm", "7 cm", "8 cm"]):
            choice["text"] = text
        self.assertEqual(self.issues(), [])
        question["check"] = "6 cm"
        self.assertEqual(self.codes(), {"S-choice-value"})

    def test_choice_that_is_a_fraction(self):
        question = self.edit("mat-geometrijski-oblici-q3", check="(/ 3 4)", answer="a")
        for choice, text in zip(question["choices"], ["$3/4$", "$2/4$", "$4/4$", "$1/4$"]):
            choice["text"] = text
        self.assertEqual(self.issues(), [])
        question["choices"][1]["text"] = "$6/8$"
        self.assertEqual(self.codes(), {"S-choice-value"})

    def test_answer_id_without_an_option(self):
        self.edit("mat-geometrijski-oblici-q1", answer="e")
        self.assertEqual(self.codes(), {"S-choice-value"})

    def test_broken_records_are_reported_not_raised(self):
        question = self.edit("mat-geometrijski-oblici-q1", choices="kvadrat")
        self.assertEqual(self.codes(), {"S-choice-value"})
        self.edit("mat-geometrijski-oblici-q3", check=None)
        self.assertEqual(self.codes(), {"S-choice-value", "S-check-parse"})

    def test_text_choice_without_a_check_is_reported_even_without_an_option_text(self):
        question = self.edit("mat-geometrijski-oblici-q1", check=None)
        for choice in question["choices"]:
            del choice["text"]
        self.assertEqual(self.codes(), {"S-check-parse"})


class VerifyCommandTest(unittest.TestCase):
    def test_verify_command_passes_on_the_fixture_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = helpers.write_corpus(Path(tmp), helpers.fixture_raw())
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = cli.main(["--root", str(root), "verify"])
        self.assertEqual(code, 0, output.getvalue())
        self.assertIn("OK", output.getvalue())


class CanonicalAnswerTest(unittest.TestCase):
    def test_in_a_data_file_a_dot_is_always_the_decimal_point(self):
        self.assertEqual(mathcheck.parse_answer("0.125", canonical=True), Fraction(1, 8))
        self.assertEqual(mathcheck.parse_answer("2.500", canonical=True), Fraction(5, 2))
        self.assertEqual(mathcheck.parse_answer("3/4", canonical=True), Fraction(3, 4))
        self.assertEqual(mathcheck.parse_answer("2 3/4", canonical=True), Fraction(11, 4))
        self.assertEqual(mathcheck.parse_answer("-0.5", canonical=True), Fraction(-1, 2))

    def test_as_a_pupil_types_it_three_digits_after_a_dot_are_thousands(self):
        self.assertEqual(mathcheck.parse_answer("0.125"), Fraction(125))
        self.assertEqual(mathcheck.parse_answer("2.500"), Fraction(2500))
        self.assertEqual(mathcheck.parse_answer("2.5"), Fraction(5, 2))
