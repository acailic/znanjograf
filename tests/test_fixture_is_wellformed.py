"""The fixture is the yardstick: every gate must pass on it, so its own shape is pinned here."""

import re
import unittest

from tests import helpers

TOPIC_ID = re.compile(r"^mat-[a-z0-9]+(-[a-z0-9]+)*$")
OUTCOME_ID = re.compile(r"^g[1-8]-\d{4}-\d{3}$")


class FixtureShapeTest(unittest.TestCase):
    def setUp(self):
        self.raw = helpers.fixture_raw()
        self.corpus = helpers.fixture_corpus()

    def test_counts(self):
        self.assertEqual(len(self.corpus.topic_list), 8)
        self.assertEqual(len(self.corpus.edge_list), 8)
        self.assertEqual(len(self.corpus.question_list), 32)
        self.assertEqual(sum(len(e.outcomes) for e in self.corpus.editions.values()), 11)

    def test_every_topic_has_two_basic_and_two_standard_questions(self):
        for topic_id in self.corpus.topics:
            levels = sorted(q["level"] for q in self.corpus.bank(topic_id))
            self.assertEqual(levels, ["basic", "basic", "standard", "standard"], topic_id)

    def test_ids(self):
        for record in self.corpus.topic_list:
            self.assertRegex(record["id"], TOPIC_ID)
            self.assertLessEqual(len(record["id"]), 48)
        for question in self.corpus.question_list:
            self.assertRegex(question["id"], rf"^{re.escape(question['topic'])}-q\d$")

    def test_registry_and_outcome_ids(self):
        self.assertEqual(self.corpus.registry, set(self.corpus.topics))
        for edition in self.corpus.editions.values():
            for outcome_id in edition.outcomes:
                self.assertRegex(outcome_id, OUTCOME_ID)
                self.assertTrue(outcome_id.startswith(edition.id))

    def test_fixture_copy_is_independent(self):
        first, second = helpers.fixture_raw(), helpers.fixture_raw()
        helpers.topic(first, "mat-brojevi-do-10")["mastery"].append("dodatni kriterijum")
        self.assertEqual(len(helpers.topic(second, "mat-brojevi-do-10")["mastery"]), 2)

    def test_grade_two_has_one_choice_only_topic(self):
        geometry = self.corpus.bank("mat-geometrijski-oblici")
        self.assertEqual({q["type"] for q in geometry}, {"choice"})
        self.assertTrue(all(len(q["choices"]) == 4 for q in geometry))
