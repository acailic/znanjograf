import tempfile
import unittest
from pathlib import Path

from zg import jsonio
from zg.corpus import Corpus, CorpusError
from tests import helpers


class CorpusTest(unittest.TestCase):
    def setUp(self):
        self.raw = helpers.fixture_raw()
        self.corpus = Corpus.from_raw("math", self.raw)

    def test_learning_order_follows_file_order_inside_a_grade(self):
        self.assertEqual(
            self.corpus.learning_order()[:3],
            ["mat-brojevi-do-10", "mat-sabiranje-do-10", "mat-sabiranje-do-20"],
        )

    def test_hard_ancestors_follow_only_hard_edges(self):
        self.assertEqual(
            self.corpus.hard_ancestors("mat-sabiranje-do-100"),
            {"mat-sabiranje-do-20", "mat-sabiranje-do-10", "mat-brojevi-do-10"},
        )

    def test_soft_edge_is_ancestor_but_not_hard_ancestor(self):
        self.assertIn("mat-sabiranje-do-10", self.corpus.ancestors("mat-poredjenje-do-100"))
        self.assertNotIn("mat-sabiranje-do-10", self.corpus.hard_ancestors("mat-poredjenje-do-100"))

    def test_descendants(self):
        self.assertEqual(
            self.corpus.descendants("mat-brojevi-do-10"),
            {"mat-sabiranje-do-10", "mat-sabiranje-do-20", "mat-sabiranje-do-100", "mat-poredjenje-do-100",
             "mat-oduzimanje-do-100", "mat-zadaci-sa-sabiranjem"},
        )

    def test_exits_are_not_required_by_the_same_grade(self):
        self.assertEqual(
            set(self.corpus.grade_exits(2)),
            {"mat-oduzimanje-do-100", "mat-zadaci-sa-sabiranjem"},
        )
        self.assertEqual(
            self.corpus.grade_exits(1),
            ["mat-sabiranje-do-20", "mat-geometrijski-oblici"],
        )

    def test_learning_order_beats_file_order(self):
        self.raw.topics[2].reverse()  # puts the dependents before their prerequisite
        order = Corpus.from_raw("math", self.raw).learning_order()
        self.assertLess(order.index("mat-sabiranje-do-100"), order.index("mat-oduzimanje-do-100"))

    def test_cycle_raises(self):
        helpers.add_edge(self.raw, "mat-brojevi-do-10", "mat-sabiranje-do-10", "hard")
        with self.assertRaises(CorpusError):
            Corpus.from_raw("math", self.raw).learning_order()

    def test_unknown_endpoint_raises(self):
        helpers.add_edge(self.raw, "mat-sabiranje-do-10", "mat-nepostojeca", "hard")
        with self.assertRaises(CorpusError):
            Corpus.from_raw("math", self.raw).ancestors("mat-sabiranje-do-10")

    def test_prereqs_filter_by_strength(self):
        self.assertEqual(len(self.corpus.prereqs("mat-poredjenje-do-100")), 2)
        self.assertEqual(len(self.corpus.prereqs("mat-poredjenje-do-100", ("soft",))), 1)

    def test_edition_file_is_filled_in_memory(self):
        self.assertEqual(self.corpus.edition_file["g2-2026"], "data/curriculum/math/g2-2026.json")

    def test_a_record_that_is_not_an_object_is_kept_for_the_validators(self):
        self.raw.topics[1].append("nije objekat")
        self.raw.questions[1].append(7)
        corpus = Corpus.from_raw("math", self.raw)
        self.assertEqual(len(corpus.topic_list), 9)
        self.assertEqual(len(corpus.questions), 32)

    def test_bank_keeps_file_order(self):
        self.assertEqual(
            [q["id"] for q in self.corpus.bank("mat-oduzimanje-do-100")],
            [f"mat-oduzimanje-do-100-q{n}" for n in range(1, 5)],
        )


class CorpusLoadTest(unittest.TestCase):
    def test_load_from_disk_matches_in_memory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = helpers.write_corpus(Path(tmp), helpers.fixture_raw())
            loaded = Corpus.load("math", root=root)
        self.assertEqual(loaded.load_errors, [])
        self.assertEqual(loaded.learning_order(), Corpus.from_raw("math", helpers.fixture_raw()).learning_order())
        self.assertEqual(loaded.topic_file["mat-sabiranje-do-20"], "data/math/g1/topics.json")
        self.assertEqual(loaded.edge_file[2], "data/math/g2/edges.json")
        self.assertEqual(set(loaded.editions), {"g1-2026", "g2-2026"})
        self.assertEqual(loaded.edition_file["g1-2026"], "data/curriculum/math/g1-2026.json")

    def test_broken_file_is_reported_not_raised(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = helpers.write_corpus(Path(tmp), helpers.fixture_raw())
            (root / "data" / "math" / "g2" / "questions.json").write_text('[{"id": "a", "id": "b"}]', encoding="utf-8")
            loaded = Corpus.load("math", root=root)
        self.assertEqual(len(loaded.load_errors), 1)
        self.assertIn("dupliran ključ", loaded.load_errors[0][1])


class JsonioTest(unittest.TestCase):
    def test_duplicate_key_is_rejected(self):
        with self.assertRaises(jsonio.DuplicateKeyError):
            jsonio.loads('{"a": 1, "b": {"c": 1, "c": 2}}')

    def test_same_key_in_different_objects_is_fine(self):
        self.assertEqual(jsonio.loads('{"a": {"x": 1}, "b": {"x": 2}}'), {"a": {"x": 1}, "b": {"x": 2}})

    def test_hash_ignores_key_order(self):
        self.assertEqual(jsonio.sha256_obj({"a": 1, "b": [2, 3]}), jsonio.sha256_obj({"b": [2, 3], "a": 1}))

    def test_hash_sees_a_change(self):
        self.assertNotEqual(jsonio.sha256_obj({"a": 1}), jsonio.sha256_obj({"a": 2}))
