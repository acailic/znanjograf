"""``zg.checks.bank``: V8. The shape of a question record is ``zg.checks.schema``'s, not this gate's."""

import decimal
import importlib
import re
import sys
import types
import unittest
from fractions import Fraction
from unittest import mock

from zg.corpus import Corpus
from zg.issues import Issues
from zg.checks import bank
from tests import helpers

QUESTION_FILES = {"g1": "data/math/g1/questions.json", "g2": "data/math/g2/questions.json"}
TOPIC_FILES = {"g1": "data/math/g1/topics.json", "g2": "data/math/g2/topics.json"}
ACCEPTED = ("15", "3,5", "3/4", "2 3/4", "-7", "1,41")
NUMBER = re.compile(r"[+-]?[0-9]+(,[0-9]+)?|[0-9]+/[0-9]+|[0-9]+ [0-9]+/[0-9]+")
MATHCHECK = "zg.mathcheck"


def run(raw, modules: dict | None = None) -> Issues:
    issues = Issues()
    with mock.patch.dict(sys.modules, modules or {}):
        bank.run(Corpus.from_raw("math", raw), issues)
    return issues


def of_code(issues: Issues, code: str) -> list:
    return [issue for issue in issues if issue.code == code]


def located(issues) -> list[tuple[str, str]]:
    return [(issue.path, issue.where) for issue in issues]


def mathcheck_stub(raises: str = ""):
    """A stand-in for ``zg.mathcheck``: it reads anything number-shaped and computes one irrational check."""
    dsl = types.ModuleType("zg.dsl")

    def parse(text):
        if text == "(sqrt 2)":
            return ("sqrt", "2")
        raise ValueError(f"ne mogu da raščlanim: {text}")

    dsl.parse = parse
    module = types.ModuleType(MATHCHECK)
    module.dsl = dsl

    def parse_answer(text):
        if text == raises:
            raise ValueError(text)
        return Fraction(1) if isinstance(text, str) and NUMBER.fullmatch(text) else None

    def evaluate(node):
        return decimal.Decimal("1.41") if node == ("sqrt", "2") else Fraction(0)

    module.parse_answer = parse_answer
    module.evaluate = evaluate
    return module


def field_check_spy(calls: list):
    """A stand-in for ``zg.checks.schema`` that notes every ``check_record`` call this gate makes."""
    module = types.ModuleType("zg.checks.schema")

    def check_record(record, kind, where, path, issues):
        calls.append((kind, where))

    module.check_record = check_record
    return module


def importable(name: str):
    try:
        return importlib.import_module(name)
    except ImportError:
        return None


class BankTest(unittest.TestCase):
    def setUp(self):
        self.raw = helpers.fixture_raw()

    def assertNoCode(self, issues: Issues, prefix: str) -> None:
        self.assertEqual([issue.line() for issue in issues if issue.code.startswith(prefix)], [])

    # ----- bank size -------------------------------------------------------------------

    def test_fixture_has_no_bank_issues(self):
        self.assertNoCode(run(self.raw), "V8")

    def test_topic_with_three_questions(self):
        self.raw.questions[1] = [q for q in self.raw.questions[1] if q["id"] != "mat-brojevi-do-10-q4"]
        found = of_code(run(self.raw), "V8-bank-count")
        self.assertEqual(located(found), [(TOPIC_FILES["g1"], "mat-brojevi-do-10")])
        self.assertIn("osnovnih zadataka: 2, standardnih: 1", found[0].message)

    def test_topic_with_one_basic_question(self):
        self.raw.questions[1] = [q for q in self.raw.questions[1] if q["id"] != "mat-sabiranje-do-20-q2"]
        self.assertEqual(located(of_code(run(self.raw), "V8-bank-count")), [(TOPIC_FILES["g1"], "mat-sabiranje-do-20")])

    def test_topic_without_questions(self):
        self.raw.questions[1] = [q for q in self.raw.questions[1] if q["topic"] != "mat-geometrijski-oblici"]
        self.assertEqual(located(of_code(run(self.raw), "V8-bank-count")), [(TOPIC_FILES["g1"], "mat-geometrijski-oblici")])

    def test_question_of_another_level_does_not_count(self):
        helpers.question(self.raw, "mat-sabiranje-do-10-q2")["level"] = "advanced"
        self.assertEqual(located(of_code(run(self.raw), "V8-bank-count")), [(TOPIC_FILES["g1"], "mat-sabiranje-do-10")])

    # ----- choices ---------------------------------------------------------------------

    def test_choice_with_two_options(self):
        question = helpers.question(self.raw, "mat-brojevi-do-10-q3")
        question["choices"] = question["choices"][:2]
        self.assertEqual(located(of_code(run(self.raw), "V8-choice-count")), [(QUESTION_FILES["g1"], "mat-brojevi-do-10-q3")])

    def test_choice_with_five_options(self):
        helpers.question(self.raw, "mat-brojevi-do-10-q3")["choices"].append({"id": "e", "text": "$5$"})
        self.assertEqual(located(of_code(run(self.raw), "V8-choice-count")), [(QUESTION_FILES["g1"], "mat-brojevi-do-10-q3")])

    def test_answer_outside_the_choice_ids(self):
        helpers.question(self.raw, "mat-brojevi-do-10-q3")["answer"] = "e"
        found = of_code(run(self.raw), "V8-choice-ids")
        self.assertEqual(located(found), [(QUESTION_FILES["g1"], "mat-brojevi-do-10-q3")])
        self.assertIn("„e“", found[0].message)

    def test_duplicate_choice_ids(self):
        question = helpers.question(self.raw, "mat-brojevi-do-10-q3")
        question["choices"][1]["id"] = "a"
        question["answer"] = "a"
        found = of_code(run(self.raw), "V8-choice-ids")
        self.assertEqual(located(found), [(QUESTION_FILES["g1"], "mat-brojevi-do-10-q3")])
        self.assertIn("„a“", found[0].message)

    def test_empty_choice_id(self):
        helpers.question(self.raw, "mat-brojevi-do-10-q3")["choices"][0]["id"] = ""
        self.assertEqual(located(of_code(run(self.raw), "V8-choice-ids")), [(QUESTION_FILES["g1"], "mat-brojevi-do-10-q3")])

    def test_duplicate_choice_text(self):
        helpers.question(self.raw, "mat-brojevi-do-10-q3")["choices"][2]["text"] = "$6$"
        found = of_code(run(self.raw), "V8-choice-text")
        self.assertEqual(located(found), [(QUESTION_FILES["g1"], "mat-brojevi-do-10-q3")])
        self.assertIn("„$6$“", found[0].message)

    def test_choice_texts_differing_only_by_spaces_are_the_same(self):
        helpers.question(self.raw, "mat-brojevi-do-10-q3")["choices"][2]["text"] = " $6$ "
        self.assertEqual(located(of_code(run(self.raw), "V8-choice-text")), [(QUESTION_FILES["g1"], "mat-brojevi-do-10-q3")])

    # ----- points_to -------------------------------------------------------------------

    def test_points_to_a_topic_that_is_not_an_ancestor(self):
        helpers.question(self.raw, "mat-poredjenje-do-100-q3")["points_to"] = {"a": "mat-oduzimanje-do-100"}
        self.assertEqual(located(of_code(run(self.raw), "V8-points-to")), [(QUESTION_FILES["g2"], "mat-poredjenje-do-100-q3")])

    def test_points_to_a_soft_prerequisite(self):
        helpers.question(self.raw, "mat-poredjenje-do-100-q3")["points_to"] = {"a": "mat-sabiranje-do-10"}
        self.assertEqual(located(of_code(run(self.raw), "V8-points-to")), [(QUESTION_FILES["g2"], "mat-poredjenje-do-100-q3")])

    def test_points_to_the_correct_option(self):
        helpers.question(self.raw, "mat-poredjenje-do-100-q3")["points_to"] = {"b": "mat-brojevi-do-10"}
        self.assertEqual(located(of_code(run(self.raw), "V8-points-to")), [(QUESTION_FILES["g2"], "mat-poredjenje-do-100-q3")])

    def test_points_to_an_option_that_does_not_exist(self):
        helpers.question(self.raw, "mat-poredjenje-do-100-q3")["points_to"] = {"z": "mat-brojevi-do-10"}
        self.assertEqual(located(of_code(run(self.raw), "V8-points-to")), [(QUESTION_FILES["g2"], "mat-poredjenje-do-100-q3")])

    def test_points_to_may_name_any_hard_ancestor(self):
        helpers.question(self.raw, "mat-poredjenje-do-100-q3")["points_to"] = {"a": "mat-brojevi-do-10", "c": "mat-brojevi-do-10"}
        self.assertNoCode(run(self.raw), "V8")

    def test_targets_are_not_judged_while_the_graph_has_a_cycle(self):
        helpers.add_edge(self.raw, "mat-brojevi-do-10", "mat-sabiranje-do-10", "hard")
        helpers.question(self.raw, "mat-poredjenje-do-100-q3")["points_to"] = {"a": "mat-oduzimanje-do-100"}
        self.assertEqual(of_code(run(self.raw), "V8-points-to"), [])

    def test_targets_are_not_judged_while_an_edge_points_nowhere(self):
        helpers.add_edge(self.raw, "mat-sabiranje-do-10", "mat-nepostojeca", "hard")
        helpers.question(self.raw, "mat-poredjenje-do-100-q3")["points_to"] = {"a": "mat-oduzimanje-do-100"}
        self.assertEqual(of_code(run(self.raw), "V8-points-to"), [])

    def test_option_keys_are_still_judged_while_the_graph_is_broken(self):
        helpers.add_edge(self.raw, "mat-brojevi-do-10", "mat-sabiranje-do-10", "hard")
        helpers.question(self.raw, "mat-poredjenje-do-100-q3")["points_to"] = {"b": "mat-brojevi-do-10"}
        self.assertEqual(located(of_code(run(self.raw), "V8-points-to")), [(QUESTION_FILES["g2"], "mat-poredjenje-do-100-q3")])

    def test_question_of_an_unknown_topic_does_not_stop_the_gate(self):
        helpers.question(self.raw, "mat-poredjenje-do-100-q3")["topic"] = "mat-nepostojeca"
        self.assertEqual(of_code(run(self.raw), "V8-points-to"), [])

    # ----- numeric answers (``zg.mathcheck`` stands in) ----------------------------------

    def test_numeric_answer_must_be_a_number(self):
        for bad in ("sedam", "", "3,,5"):
            with self.subTest(bad=bad), mock.patch.dict(sys.modules, {MATHCHECK: mathcheck_stub()}):
                raw = helpers.fixture_raw()
                helpers.question(raw, "mat-brojevi-do-10-q1")["answer"] = bad
                self.assertEqual(located(of_code(run(raw), "V8-numeric-answer")), [(QUESTION_FILES["g1"], "mat-brojevi-do-10-q1")])

    def test_missing_numeric_answer_is_reported(self):
        del helpers.question(self.raw, "mat-brojevi-do-10-q1")["answer"]
        with mock.patch.dict(sys.modules, {MATHCHECK: mathcheck_stub()}):
            self.assertEqual(located(of_code(run(self.raw), "V8-numeric-answer")), [(QUESTION_FILES["g1"], "mat-brojevi-do-10-q1")])

    def test_numeric_answers_the_parser_reads_are_clean(self):
        for good in ACCEPTED:
            with self.subTest(good=good), mock.patch.dict(sys.modules, {MATHCHECK: mathcheck_stub()}):
                raw = helpers.fixture_raw()
                helpers.question(raw, "mat-brojevi-do-10-q1")["answer"] = good
                self.assertEqual(of_code(run(raw), "V8-numeric-answer"), [])

    def test_parser_that_raises_means_the_answer_is_not_a_number(self):
        helpers.question(self.raw, "mat-brojevi-do-10-q1")["answer"] = "baci"
        with mock.patch.dict(sys.modules, {MATHCHECK: mathcheck_stub(raises="baci")}):
            self.assertEqual(located(of_code(run(self.raw), "V8-numeric-answer")), [(QUESTION_FILES["g1"], "mat-brojevi-do-10-q1")])

    def test_irrational_answer_needs_round_to(self):
        question = helpers.question(self.raw, "mat-brojevi-do-10-q1")
        question["check"], question["answer"] = "(sqrt 2)", "1,41"
        with mock.patch.dict(sys.modules, {MATHCHECK: mathcheck_stub()}):
            self.assertEqual(located(of_code(run(self.raw), "V8-round-to")), [(QUESTION_FILES["g1"], "mat-brojevi-do-10-q1")])

    def test_irrational_answer_with_round_to_is_clean(self):
        question = helpers.question(self.raw, "mat-brojevi-do-10-q1")
        question["check"], question["answer"], question["round_to"] = "(sqrt 2)", "1,41", 2
        with mock.patch.dict(sys.modules, {MATHCHECK: mathcheck_stub()}):
            self.assertEqual(of_code(run(self.raw), "V8-round-to"), [])

    def test_choice_with_an_irrational_value_needs_round_to(self):
        helpers.question(self.raw, "mat-geometrijski-oblici-q3")["check"] = "(sqrt 2)"
        with mock.patch.dict(sys.modules, {MATHCHECK: mathcheck_stub()}):
            self.assertEqual(located(of_code(run(self.raw), "V8-round-to")), [(QUESTION_FILES["g1"], "mat-geometrijski-oblici-q3")])

    def test_check_that_does_not_compute_is_left_to_verify(self):
        helpers.question(self.raw, "mat-brojevi-do-10-q1")["check"] = "(nepoznato 2)"
        with mock.patch.dict(sys.modules, {MATHCHECK: mathcheck_stub()}):
            self.assertEqual(of_code(run(self.raw), "V8-round-to"), [])

    def test_parser_may_live_in_the_dsl_module(self):
        helpers.question(self.raw, "mat-brojevi-do-10-q1")["check"] = "(sqrt 2)"
        stub = mathcheck_stub()
        dsl = stub.dsl
        del stub.dsl
        with mock.patch.dict(sys.modules, {MATHCHECK: stub, "zg.dsl": dsl}):
            self.assertEqual(located(of_code(run(self.raw), "V8-round-to")), [(QUESTION_FILES["g1"], "mat-brojevi-do-10-q1")])

    def test_works_without_the_answer_parser(self):
        """``zg.mathcheck`` is optional: only the answer and ``round_to`` rules depend on it."""
        helpers.question(self.raw, "mat-brojevi-do-10-q1")["answer"] = "sedam"
        helpers.question(self.raw, "mat-brojevi-do-10-q2")["check"] = "(sqrt 2)"
        self.raw.questions[1] = [q for q in self.raw.questions[1] if q["id"] != "mat-sabiranje-do-20-q4"]
        with mock.patch.dict(sys.modules, {MATHCHECK: None}):
            issues = run(self.raw)
        self.assertEqual(located(issues), [(TOPIC_FILES["g1"], "mat-sabiranje-do-20")])
        self.assertEqual(issues.codes(), {"V8-bank-count"})

    # ----- records ---------------------------------------------------------------------

    def test_record_shape_is_the_field_check_s_alone(self):
        """``zg.checks.schema`` reports the shape of a question once; this gate neither repeats it nor calls into it."""
        calls: list = []
        question = helpers.question(self.raw, "mat-brojevi-do-10-q1")
        question["nepoznato"], question["prompt"] = 1, None
        with mock.patch.dict(sys.modules, {"zg.checks.schema": field_check_spy(calls)}):
            issues = run(self.raw)
        self.assertEqual([issue.line() for issue in issues], [])
        self.assertEqual(calls, [])

    def test_record_without_an_id_is_left_to_the_field_check(self):
        self.raw.questions[1].append({"topic": "mat-brojevi-do-10", "level": "basic", "type": "numeric"})
        self.raw.questions[1].append("niz zapisa")
        self.assertNoCode(run(self.raw), "V8")


@unittest.skipUnless(importable(MATHCHECK), "zg.mathcheck nije dostupan")
class BankWithRealParserTest(unittest.TestCase):
    """The seam to the real ``zg.mathcheck``, which the tests above replace with a stand-in."""

    def setUp(self):
        self.raw = helpers.fixture_raw()

    def test_word_is_not_a_numeric_answer(self):
        helpers.question(self.raw, "mat-brojevi-do-10-q1")["answer"] = "sedam"
        self.assertEqual(located(of_code(run(self.raw), "V8-numeric-answer")), [(QUESTION_FILES["g1"], "mat-brojevi-do-10-q1")])

    def test_sqrt_without_round_to(self):
        question = helpers.question(self.raw, "mat-brojevi-do-10-q1")
        question["check"], question["answer"] = "(sqrt 2)", "1,41"
        self.assertEqual(located(of_code(run(self.raw), "V8-round-to")), [(QUESTION_FILES["g1"], "mat-brojevi-do-10-q1")])

    def test_sqrt_with_round_to_is_clean(self):
        question = helpers.question(self.raw, "mat-brojevi-do-10-q1")
        question["check"], question["answer"], question["round_to"] = "(sqrt 2)", "1,41", 2
        self.assertEqual(of_code(run(self.raw), "V8-round-to"), [])


if __name__ == "__main__":
    unittest.main()
