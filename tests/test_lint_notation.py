"""L1 on deliberately broken notation: each rule code on one broken example, and the real rule file against the fixture."""

import copy
import tempfile
import unittest
from pathlib import Path

from zg import jsonio, paths
from zg.corpus import Corpus
from zg.issues import Issues
from zg.lint import notation
from tests import helpers

GRADE_ONE = "mat-brojevi-do-10-q1"
GRADE_TWO = "mat-sabiranje-do-100-q1"
# A LaTeX command is written with two backslashes in a pattern: as a regex, ``\times`` is a tab.
TIMES = {"pattern": r"\\times|\\cdot", "min_grade": 2, "outcome": "g2-2026-004", "note": "množenje"}
MINUS = {"pattern": r"\d\s*-\s*\d", "min_grade": 2, "outcome": "g2-2026-003", "note": "oduzimanje"}

# (pattern, min_grade, outcome) of every rule data/lint/notation.json must hold.
EXPECTED_RULES = [
    (r"\\times|\\cdot", 2, "g2-2026-004"),
    (r"\d\s*-\s*\d", 2, "g2-2026-003"),
    (r"(?<!\\):", 3, "g2-2026-004"),
    (r"\\frac", 3, "g2-2026-004"),
    (r"\d+\{,\}\d+", 5, "g2-2026-006"),
    (r"\^", 7, "g2-2026-004"),
    (r"\\sqrt", 8, "g2-2026-004"),
    (r"\\pi", 8, "g2-2026-004"),
    (r"\\le|\\ge", 5, "g2-2026-005"),
    (r"\\neq", 5, "g2-2026-005"),
    (r"(?<![A-Za-z\\])[a-z](?![A-Za-z])", 5, "g2-2026-004"),
    (r"[<>]", 2, "g2-2026-005"),
]

VARIABLE = {"pattern": r"(?<![A-Za-z\\])[a-z](?![A-Za-z])", "min_grade": 5, "outcome": "g2-2026-004", "note": "slovo kao promenljiva"}
LESS = {"pattern": "[<>]", "min_grade": 2, "outcome": "g2-2026-005", "note": "znaci „manje“ i „veće“"}


class NotationCase(unittest.TestCase):
    def lint(self, rules: list, question_id: str | None = None, **fields) -> Issues:
        """The fixture with ``rules``; ``fields`` replace fields of the question ``question_id``."""
        raw = helpers.fixture_raw()
        helpers.notation_rules(raw, rules)
        if question_id is not None:
            helpers.question(raw, question_id).update(fields)
        issues = Issues()
        notation.run(Corpus.from_raw("math", raw), issues)
        return issues


class NotationTest(NotationCase):
    def test_times_in_grade_one_is_notation(self):
        issues = self.lint([TIMES], GRADE_ONE, prompt="Koliko je $3 \\times 4$?")
        self.assertEqual(issues.codes(), {"L1-notation"})
        self.assertEqual(len(issues), 1)

    def test_issue_points_at_the_question(self):
        issues = self.lint([TIMES], GRADE_ONE, prompt="Koliko je $3 \\times 4$")
        self.assertEqual(
            [(issue.path, issue.where, issue.code) for issue in issues],
            [("data/math/g1/questions.json", GRADE_ONE, "L1-notation")],
        )

    def test_message_quotes_the_note_and_the_matched_text(self):
        issues = self.lint([TIMES], GRADE_ONE, prompt="Koliko je $3 \\times 4$")
        self.assertIn("množenje", issues[0].message)
        self.assertIn("\\times", issues[0].message)
        self.assertIn("g2-2026-004", issues[0].message)
        issues = self.lint([TIMES], GRADE_ONE, prompt="Koliko je $3 \\cdot 4$")
        self.assertIn("\\cdot", issues[0].message)

    def test_the_same_in_grade_two_is_clean(self):
        self.assertEqual(self.lint([TIMES], GRADE_TWO, prompt="Koliko je $3 \\times 4$?"), [])

    def test_choice_text_is_searched(self):
        issues = self.lint(
            [TIMES], "mat-brojevi-do-10-q3",
            choices=[{"id": "a", "text": "$6$"}, {"id": "b", "text": "$2 \\times 3$"}],
        )
        self.assertEqual(issues.codes(), {"L1-notation"})

    def test_explanation_is_searched(self):
        issues = self.lint([TIMES], GRADE_ONE, explanation="Računamo $2 \\cdot 3$.")
        self.assertEqual(issues.codes(), {"L1-notation"})

    def test_one_issue_per_question_and_rule(self):
        issues = self.lint(
            [TIMES], GRADE_ONE,
            prompt="$3 \\times 4$ pa $2 \\cdot 5$", explanation="Jer je $1 \\times 1$.",
            choices=[{"id": "a", "text": "$9 \\times 9$"}],
        )
        self.assertEqual(len(issues), 1)

    def test_each_rule_reports_on_its_own(self):
        issues = self.lint([TIMES, MINUS], GRADE_ONE, prompt="Koliko je $3 \\times 4 - 1$")
        self.assertEqual(len(issues), 2)
        self.assertEqual(sorted("množenje" in issue.message for issue in issues), [False, True])

    def test_every_question_of_the_grade_is_looked_at(self):
        raw = helpers.fixture_raw()
        helpers.notation_rules(raw, [MINUS])
        for question_id in (GRADE_ONE, "mat-brojevi-do-10-q2"):
            helpers.question(raw, question_id)["prompt"] = "Koliko je $5 - 3$?"
        issues = Issues()
        notation.run(Corpus.from_raw("math", raw), issues)
        self.assertEqual(sorted(issue.where for issue in issues), ["mat-brojevi-do-10-q1", "mat-brojevi-do-10-q2"])

    def test_text_outside_a_formula_is_not_searched(self):
        self.assertEqual(self.lint([TIMES], GRADE_ONE, prompt="Koliko je 3 \\times 4?"), [])
        self.assertEqual(self.lint([TIMES], GRADE_ONE, prompt="Koliko je $3$ puta $4$?"), [])

    def test_negative_number_is_not_a_binary_minus(self):
        self.assertEqual(self.lint([MINUS], GRADE_ONE, prompt="Koliko je $-3 + 5$?"), [])

    def test_question_of_an_unknown_topic_is_left_to_the_other_gates(self):
        self.assertEqual(self.lint([TIMES], GRADE_ONE, prompt="Koliko je $3 \\times 4$?", topic="mat-nepostojeca"), [])
        self.assertEqual(self.lint([TIMES], GRADE_ONE, prompt="Koliko je $3 \\times 4$?", topic=["mat-brojevi-do-10"]), [])

    def test_a_record_without_a_usable_id_is_still_linted(self):
        issues = self.lint([TIMES], GRADE_ONE, prompt="Koliko je $3 \\times 4$?", id=["not", "a", "string"])
        self.assertEqual([(issue.path, issue.where) for issue in issues], [("-", "-")])

    def test_a_record_that_is_not_an_object_does_not_stop_the_lint(self):
        raw = helpers.fixture_raw()
        helpers.notation_rules(raw, [TIMES])
        helpers.question(raw, GRADE_ONE)["prompt"] = "Koliko je $3 \\times 4$?"
        raw.questions[1].append(5)  # Corpus.load keeps it; from_raw would not
        with tempfile.TemporaryDirectory() as tmp:
            corpus = Corpus.load("math", root=helpers.write_corpus(Path(tmp), raw))
        issues = Issues()
        notation.run(corpus, issues)
        self.assertEqual([issue.where for issue in issues], [GRADE_ONE])

    def test_run_changes_nothing(self):
        raw = helpers.fixture_raw()
        helpers.notation_rules(raw, [TIMES])
        helpers.question(raw, GRADE_ONE)["prompt"] = "Koliko je $3 \\times 4$?"
        corpus = Corpus.from_raw("math", raw)
        before = copy.deepcopy((corpus.notation, corpus.question_list))
        notation.run(corpus, Issues())
        self.assertEqual((corpus.notation, corpus.question_list), before)


class BrokenRuleTest(NotationCase):
    MALFORMED = [
        ("bad regex", {"pattern": "(", "min_grade": 2, "outcome": "g2-2026-004", "note": "x"}),
        ("missing pattern", {"min_grade": 2, "outcome": "g2-2026-004", "note": "x"}),
        ("missing note", {"pattern": "\\\\times", "min_grade": 2, "outcome": "g2-2026-004"}),
        ("unknown key", dict(TIMES, minGrade=2)),
        ("pattern is not text", dict(TIMES, pattern=3)),
        ("empty pattern", dict(TIMES, pattern="  ")),
        ("undoubled LaTeX command is a tab", dict(TIMES, pattern="\\times")),
        ("undoubled LaTeX command is a form feed", dict(TIMES, pattern="\\frac")),
        ("min_grade is text", dict(TIMES, min_grade="2")),
        ("min_grade is a boolean", dict(TIMES, min_grade=True)),
        ("min_grade is below 1", dict(TIMES, min_grade=0)),
        ("min_grade is above 8", dict(TIMES, min_grade=9)),
        ("outcome is not text", dict(TIMES, outcome=None)),
        ("note is not text", dict(TIMES, note=["množenje"])),
        ("rule is not an object", "\\times"),
    ]

    def test_outcome_no_edition_has_is_reported_once_and_the_rule_is_skipped(self):
        rule = dict(TIMES, outcome="g2-2026-999")
        issues = self.lint([rule], GRADE_ONE, prompt="Koliko je $3 \\times 4$?", explanation="$2 \\cdot 2$")
        self.assertEqual(issues.codes(), {"L1-rule-outcome"})
        self.assertEqual(len(issues), 1)

    def test_missing_outcome_issue_names_the_rule_and_the_outcome(self):
        issues = self.lint([dict(TIMES, outcome="g2-2026-999")])
        self.assertEqual(
            [(issue.path, issue.where, issue.code) for issue in issues],
            [("data/lint/notation.json", "notation[0]", "L1-rule-outcome")],
        )
        self.assertIn("g2-2026-999", issues[0].message)
        self.assertIn("množenje", issues[0].message)

    def test_two_rules_citing_the_same_missing_outcome_are_both_reported(self):
        missing = dict(TIMES, outcome="g2-2026-999")
        issues = self.lint([missing, dict(MINUS, outcome="g2-2026-999")], GRADE_ONE, prompt="$3 \\times 4 - 1$")
        self.assertEqual([issue.where for issue in issues], ["notation[0]", "notation[1]"])
        self.assertEqual(issues.codes(), {"L1-rule-outcome"})

    def test_rule_with_an_unparsable_pattern_is_invalid(self):
        issues = self.lint([dict(TIMES, pattern="(")], GRADE_ONE, prompt="Koliko je $3 \\times 4$")
        self.assertEqual(issues.codes(), {"L1-rule-invalid"})
        self.assertEqual(len(issues), 1)

    def test_invalid_rule_message_says_why(self):
        issues = self.lint([dict(TIMES, pattern="(")])
        self.assertEqual(issues[0].where, "notation[0]")
        self.assertEqual(issues[0].path, "data/lint/notation.json")
        self.assertIn("pattern", issues[0].message)

    def test_every_malformed_rule_is_reported_and_skipped(self):
        for name, rule in self.MALFORMED:
            with self.subTest(name):
                issues = self.lint([rule, TIMES], GRADE_ONE, prompt="Koliko je $3 \\times 4$")
                self.assertEqual(
                    [(issue.where, issue.code) for issue in issues],
                    [("notation[0]", "L1-rule-invalid"), (GRADE_ONE, "L1-notation")],
                )

    def test_no_rules_means_no_issues(self):
        self.assertEqual(self.lint([], GRADE_ONE, prompt="Koliko je $3 \\times 4$?"), [])


class RuleFileTest(NotationCase):
    """``data/lint/notation.json`` itself: usable, cited against the fixture, and silent on the unmutated fixture."""

    def setUp(self):
        self.rules = jsonio.load(paths.NOTATION_FILE)
        self.fixture = Corpus.from_raw("math", helpers.fixture_raw())

    def test_every_cited_outcome_is_in_the_fixture(self):
        outcomes = {outcome for edition in self.fixture.editions.values() for outcome in edition.outcomes}
        self.assertIsInstance(self.rules, list)
        for rule in self.rules:
            self.assertIn(rule["outcome"], outcomes, rule["pattern"])

    def test_rules_carry_a_short_serbian_note(self):
        for rule in self.rules:
            with self.subTest(rule["pattern"]):
                self.assertEqual(sorted(rule), ["min_grade", "note", "outcome", "pattern"])
                self.assertTrue(rule["note"].strip())
                self.assertNotRegex(rule["note"], "[\u0400-\u04ff]")

    def test_file_holds_the_rules_the_plan_asks_for(self):
        present = {(rule["pattern"], rule["min_grade"], rule["outcome"]) for rule in self.rules}
        for rule in EXPECTED_RULES:
            self.assertIn(rule, present)
        self.assertEqual(len(self.rules), len(EXPECTED_RULES))

    def test_unmutated_fixture_produces_no_notation_issue(self):
        issues = Issues()
        notation.run(self._corpus(), issues)
        self.assertEqual(issues, [])

    def test_minus_in_grade_two_is_what_the_fixture_already_writes(self):
        issues = self.lint(self.rules, "mat-oduzimanje-do-100-q1", prompt="Koliko je $58 - 23$?")
        self.assertEqual(issues, [])

    def test_notation_that_comes_later_is_reported_with_its_note(self):
        for prompt, note in [
            ("$6 : 2$", "deljenje"),
            (r"$\frac{1}{2}$", "razlomci"),
            (r"$3{,}5$", "decimalni brojevi"),
            (r"$2^3$", "stepen"),
            (r"$\sqrt{9}$", "kvadratni koren"),
            (r"$\pi$", "broj pi"),
            (r"$2 \le 3$", "manje ili jednako"),
            (r"$3 \ge 2$", "veće ili jednako"),
            (r"$2 \neq 3$", "nije jednako"),
            (r"$x + 2$", "slovo kao promenljiva"),
        ]:
            with self.subTest(prompt):
                issues = self.lint(self.rules, GRADE_TWO, prompt=f"Koliko je {prompt}?")
                self.assertEqual(len(issues), 1, [issue.message for issue in issues])
                self.assertEqual(issues[0].code, "L1-notation")
                self.assertIn(note, issues[0].message)

    def test_multiplication_and_minus_are_notation_in_grade_one(self):
        for prompt, note in [("$3 \\times 4$", "množenje"), ("$5 - 3$", "oduzimanje")]:
            with self.subTest(prompt):
                issues = self.lint(self.rules, GRADE_ONE, prompt=f"Koliko je {prompt}?")
                self.assertEqual(len(issues), 1, [issue.message for issue in issues])
                self.assertIn(note, issues[0].message)

    def _corpus(self) -> Corpus:
        raw = helpers.fixture_raw()
        helpers.notation_rules(raw, copy.deepcopy(self.rules))
        return Corpus.from_raw("math", raw)


if __name__ == "__main__":
    unittest.main()


class RuleApplicabilityTest(NotationCase):
    def test_a_rule_for_an_edition_that_is_not_loaded_yet_is_skipped_silently(self):
        issues = self.lint([{"pattern": r"\\sqrt", "min_grade": 8, "outcome": "g8-2026-001", "note": "koren"}])
        self.assertEqual(issues.codes(), set())

    def test_a_rule_for_a_missing_outcome_of_a_loaded_edition_is_reported(self):
        issues = self.lint([{"pattern": r"\\sqrt", "min_grade": 8, "outcome": "g2-2026-999", "note": "koren"}])
        self.assertEqual(issues.codes(), {"L1-rule-outcome"})

    def test_a_rule_that_is_not_an_object_is_reported_not_dropped(self):
        raw = helpers.fixture_raw()
        raw.notation = ["nije objekat"]
        issues = Issues()
        notation.run(Corpus.from_raw("math", raw), issues)
        self.assertEqual(issues.codes(), {"L1-rule-invalid"})


class UnitsAreNotVariablesTest(NotationCase):
    def test_a_unit_letter_inside_text_is_not_a_variable(self):
        issues = self.lint([VARIABLE], GRADE_ONE, prompt="Koliko je $5\\ \\text{m}$?")
        self.assertEqual(issues.codes(), set())

    def test_a_bare_letter_still_is_a_variable(self):
        issues = self.lint([VARIABLE], GRADE_ONE, prompt="Koliko je $x + 2$?")
        self.assertIn("L1-notation", issues.codes())


class ComparisonSignsTest(NotationCase):
    def test_less_or_greater_below_grade_two_is_reported(self):
        issues = self.lint([LESS], GRADE_ONE, prompt="Koji je broj veći: $6 > 9$?")
        self.assertIn("L1-notation", issues.codes())

    def test_less_or_greater_from_grade_two_is_fine(self):
        issues = self.lint([LESS], GRADE_TWO, prompt="Upiši znak: $56 < 65$")
        self.assertEqual(issues.codes(), set())
