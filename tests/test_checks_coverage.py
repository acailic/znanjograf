"""``zg.checks.coverage``: V7, and what it alone checks in the curriculum edition files."""

import sys
import types
import unittest
from unittest import mock

from zg.corpus import Corpus
from zg.issues import Issues
from zg.checks import coverage
from tests import helpers

EDITION_FILES = {"g1-2026": "data/curriculum/math/g1-2026.json", "g2-2026": "data/curriculum/math/g2-2026.json"}
UNMAPPED_FILE = "data/curriculum/unmapped.json"
TOPIC_FILE = {"g1": "data/math/g1/topics.json", "g2": "data/math/g2/topics.json"}


def run(raw) -> Issues:
    issues = Issues()
    coverage.run(Corpus.from_raw("math", raw), issues)
    return issues


def of_code(issues: Issues, code: str) -> list:
    return [issue for issue in issues if issue.code == code]


def located(issues) -> list[tuple[str, str]]:
    return [(issue.path, issue.where) for issue in issues]


def field_check_spy(calls: list):
    """A stand-in for ``zg.checks.schema`` that notes every ``check_record`` call this gate makes."""
    module = types.ModuleType("zg.checks.schema")

    def check_record(record, kind, where, path, issues):
        calls.append((kind, where))

    module.check_record = check_record
    return module


class CoverageTest(unittest.TestCase):
    def setUp(self):
        self.raw = helpers.fixture_raw()

    def assertNoCode(self, issues: Issues, prefix: str) -> None:
        self.assertEqual([issue.line() for issue in issues if issue.code.startswith(prefix)], [])

    # ----- V7 -------------------------------------------------------------------------

    def test_fixture_has_no_coverage_issues(self):
        self.assertNoCode(run(self.raw), "V7")

    def test_outcome_missing_from_its_edition(self):
        helpers.topic(self.raw, "mat-sabiranje-do-10")["curriculum"][0]["outcome"] = "g1-2026-999"
        found = of_code(run(self.raw), "V7-outcome-missing")
        self.assertEqual(located(found), [(TOPIC_FILE["g1"], "mat-sabiranje-do-10")])
        self.assertIn("g1-2026-999", found[0].message)

    def test_edition_missing(self):
        helpers.topic(self.raw, "mat-sabiranje-do-10")["curriculum"][0]["edition"] = "g1-2025"
        self.assertEqual(located(of_code(run(self.raw), "V7-outcome-missing")), [(TOPIC_FILE["g1"], "mat-sabiranje-do-10")])

    def test_outcome_of_another_edition_does_not_count(self):
        helpers.topic(self.raw, "mat-sabiranje-do-100")["curriculum"].append({"edition": "g2-2026", "outcome": "g1-2026-002", "match": "exact"})
        self.assertEqual(located(of_code(run(self.raw), "V7-outcome-missing")), [(TOPIC_FILE["g2"], "mat-sabiranje-do-100")])

    def test_uncovered_outcome_must_be_listed(self):
        helpers.topic(self.raw, "mat-brojevi-do-10")["curriculum"].pop()  # g1-2026-005 loses its only topic
        found = of_code(run(self.raw), "V7-outcome-unmapped")
        self.assertEqual(located(found), [(EDITION_FILES["g1-2026"], "g1-2026-005")])

    def test_listed_uncovered_outcome_is_clean(self):
        helpers.topic(self.raw, "mat-brojevi-do-10")["curriculum"].pop()
        self.raw.unmapped["g1-2026-005"] = "Program ga uvodi od 2027/28."
        self.assertNoCode(run(self.raw), "V7")

    def test_listing_is_stale_once_the_outcome_is_covered_again(self):
        topic = helpers.topic(self.raw, "mat-brojevi-do-10")
        entry = topic["curriculum"].pop()
        self.raw.unmapped["g1-2026-005"] = "Program ga uvodi od 2027/28."
        self.assertNoCode(run(self.raw), "V7")
        topic["curriculum"].append(entry)
        found = of_code(run(self.raw), "V7-unmapped-stale")
        self.assertEqual(located(found), [(UNMAPPED_FILE, "g1-2026-005")])

    def test_listing_of_a_covered_outcome_is_stale(self):
        self.raw.unmapped["g1-2026-002"] = "Zaboravljen unos."
        self.assertEqual(located(of_code(run(self.raw), "V7-unmapped-stale")), [(UNMAPPED_FILE, "g1-2026-002")])

    def test_listing_of_an_outcome_that_does_not_exist_is_stale(self):
        self.raw.unmapped["g1-2026-999"] = "Ishod je ispao iz programa."
        self.assertEqual(located(of_code(run(self.raw), "V7-unmapped-stale")), [(UNMAPPED_FILE, "g1-2026-999")])

    def test_topic_without_outcome(self):
        helpers.topic(self.raw, "mat-sabiranje-do-10")["curriculum"] = []
        self.assertEqual(located(of_code(run(self.raw), "V7-topic-without-outcome")), [(TOPIC_FILE["g1"], "mat-sabiranje-do-10")])

    def test_unit_must_be_a_theme_of_an_edition_the_topic_names(self):
        helpers.topic(self.raw, "mat-geometrijski-oblici")["unit"] = "Merenje i mere"
        found = of_code(run(self.raw), "V7-topic-unit")
        self.assertEqual(located(found), [(TOPIC_FILE["g1"], "mat-geometrijski-oblici")])
        self.assertIn("„Merenje i mere“", found[0].message)
        self.assertIn("Geometrija", found[0].message)  # the message names the themes the edition does have

    def test_unit_may_be_a_theme_of_any_edition_the_topic_names(self):
        self.raw.editions["g2-2026"]["themes"].append({"name": "Merenje i mere", "area": "geometry", "hours": 10, "content": ["Dužina"], "page": 22})
        topic = helpers.topic(self.raw, "mat-geometrijski-oblici")
        topic["curriculum"].append({"edition": "g2-2026", "outcome": "g2-2026-001", "match": "partial"})
        topic["unit"] = "Merenje i mere"  # a theme of the second edition only
        self.assertEqual(of_code(run(self.raw), "V7-topic-unit"), [])
        topic["unit"] = "Celi brojevi"  # a theme of neither
        found = of_code(run(self.raw), "V7-topic-unit")
        self.assertIn("u izdanju „g2-2026“: Brojevi, Merenje i mere", found[0].message)  # the message says which edition has what

    def test_empty_unit_is_reported_once_by_the_field_check_only(self):
        for unit in ("", "   "):
            with self.subTest(unit=unit):
                raw = helpers.fixture_raw()
                helpers.topic(raw, "mat-sabiranje-do-10")["unit"] = unit
                self.assertEqual(of_code(run(raw), "V7-topic-unit"), [])

    def test_unit_is_not_checked_against_an_edition_the_topic_names_nothing_of(self):
        topic = helpers.topic(self.raw, "mat-geometrijski-oblici")
        topic["curriculum"] = [{"edition": "g2-2026", "outcome": "g1-2026-004", "match": "exact"}]  # no outcome of g2
        self.assertEqual(of_code(run(self.raw), "V7-topic-unit"), [])  # the missing outcome is reported instead

    def test_unit_of_a_topic_without_outcome_is_left_alone(self):
        topic = helpers.topic(self.raw, "mat-sabiranje-do-10")
        topic["curriculum"], topic["unit"] = [], "Nepostojeća celina"
        self.assertEqual([issue.code for issue in run(self.raw) if issue.where == "mat-sabiranje-do-10"], ["V7-topic-without-outcome"])

    def test_unit_that_is_not_text_is_the_field_check_s(self):
        helpers.topic(self.raw, "mat-sabiranje-do-10")["unit"] = 7
        self.assertEqual(of_code(run(self.raw), "V7-topic-unit"), [])

    def test_broken_citation_is_left_to_the_field_check(self):
        """A ``curriculum`` that is not a list, or entries without ids, are field problems (V2), not coverage ones."""
        helpers.topic(self.raw, "mat-sabiranje-do-10")["curriculum"] = None
        helpers.topic(self.raw, "mat-sabiranje-do-20")["curriculum"] = [{"edition": "g1-2026", "match": "exact"}, "g1-2026-003"]
        self.raw.unmapped.update({"g1-2026-002": "Bez teme.", "g1-2026-003": "Bez teme."})  # both are left uncovered
        self.assertNoCode(run(self.raw), "V7")

    # ----- edition files ---------------------------------------------------------------

    def test_grade_disagrees_with_the_edition_id(self):
        self.raw.editions["g2-2026"]["grade"] = 3
        self.assertEqual(located(of_code(run(self.raw), "V7-edition-grade")), [(EDITION_FILES["g2-2026"], "g2-2026")])

    def test_edition_field_disagrees_with_the_edition_id(self):
        self.raw.editions["g2-2026"]["edition"] = "g2-2025"
        self.assertEqual(located(of_code(run(self.raw), "V7-edition-grade")), [(EDITION_FILES["g2-2026"], "g2-2026")])

    def test_page_that_is_not_positive_is_reported(self):
        for page in (0, -3):
            with self.subTest(page=page):
                raw = helpers.fixture_raw()
                raw.editions["g1-2026"]["outcomes"][0]["page"] = page
                self.assertEqual(located(of_code(run(raw), "V2-type")), [(EDITION_FILES["g1-2026"], "g1-2026-001")])

    def test_page_that_is_not_an_integer_is_left_to_the_field_check(self):
        """The type of a field is ``zg.checks.schema``'s rule; this one is only about the value."""
        for page in ("12", 1.5, True, None):
            with self.subTest(page=page):
                raw = helpers.fixture_raw()
                raw.editions["g1-2026"]["outcomes"][0]["page"] = page
                self.assertEqual(of_code(run(raw), "V2-type"), [])

    def test_theme_page_must_be_positive_when_present(self):
        self.raw.editions["g1-2026"]["themes"][0]["page"] = 0
        self.assertEqual(located(of_code(run(self.raw), "V2-type")), [(EDITION_FILES["g1-2026"], "themes[0]")])
        del self.raw.editions["g1-2026"]["themes"][0]["page"]  # a theme may leave the page out
        self.assertEqual(of_code(run(self.raw), "V2-type"), [])

    def test_record_shape_and_id_format_are_the_field_check_s_alone(self):
        """``zg.checks.schema`` reports these once; this gate neither repeats them nor calls into it."""
        calls: list = []
        self.raw.editions["g1-2026"]["themes"][0]["hours"] = "mnogo"
        outcome = self.raw.editions["g1-2026"]["outcomes"][1]
        outcome["nepoznato"], outcome["text"] = 1, None
        for bad in ("g1-2026-2", "G1-2026-002", "g1-2026-0020", "mat-sabiranje-do-10"):
            with self.subTest(bad=bad):
                outcome["id"] = bad
                helpers.topic(self.raw, "mat-sabiranje-do-10")["curriculum"][0]["outcome"] = bad
                with mock.patch.dict(sys.modules, {"zg.checks.schema": field_check_spy(calls)}):
                    issues = run(self.raw)
                self.assertEqual([issue.line() for issue in issues], [])
        self.assertEqual(calls, [])

    def test_does_not_need_the_field_check(self):
        """Record shape is ``zg.checks.schema``'s, so this gate gives the same answer with or without that module."""
        self.raw.editions["g1-2026"]["outcomes"][1]["id"] = "g1-2026-2"
        helpers.topic(self.raw, "mat-sabiranje-do-10")["curriculum"][0]["outcome"] = "g1-2026-2"
        helpers.topic(self.raw, "mat-sabiranje-do-20")["curriculum"] = []
        self.raw.editions["g2-2026"]["grade"] = 3
        self.raw.editions["g2-2026"]["outcomes"][0]["page"] = 0
        expected = sorted([
            (TOPIC_FILE["g1"], "mat-sabiranje-do-20", "V7-topic-without-outcome"),
            (EDITION_FILES["g1-2026"], "g1-2026-003", "V7-outcome-unmapped"),  # the topic no longer names it
            (EDITION_FILES["g2-2026"], "g2-2026", "V7-edition-grade"),
            (EDITION_FILES["g2-2026"], "g2-2026-001", "V2-type"),
        ])
        self.assertEqual(sorted((issue.path, issue.where, issue.code) for issue in run(self.raw)), expected)
        with mock.patch.dict(sys.modules, {"zg.checks.schema": None}):
            self.assertEqual(sorted((issue.path, issue.where, issue.code) for issue in run(self.raw)), expected)


if __name__ == "__main__":
    unittest.main()
