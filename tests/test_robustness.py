"""Malformed input must come back as a reported problem, never as a traceback (review of 2026-11-26)."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from zg import __main__ as cli, jsonio, report
from zg.checks import schema
from zg.corpus import Corpus, CorpusError
from zg.issues import Issues
from tests import helpers


def run_cli(*argv):
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        code = cli.main(list(argv))
    return code, output.getvalue()


class FixtureTree(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = helpers.write_corpus(Path(self.tmp.name), helpers.fixture_raw())

    def cli(self, command):
        return run_cli("--root", str(self.root), command)


class MalformedInputTest(FixtureTree):
    def codes(self):
        corpus = Corpus.load("math", root=self.root)
        issues = Issues()
        schema.run(corpus, issues)
        return issues

    def test_an_edge_that_is_not_an_object_is_reported_by_every_gate(self):
        file = self.root / "data" / "math" / "g1" / "edges.json"
        edges = jsonio.load(file)
        edges.append(None)
        edges.append("nije objekat")
        jsonio.dump(edges, file)
        code, out = self.cli("validate")
        self.assertEqual(code, 1, out)
        self.assertIn("V2-type", out)
        for gate in ("verify", "lint", "status", "report"):
            code, out = self.cli(gate)
            self.assertNotIn("Traceback", out, gate)

    def test_a_file_that_cannot_be_loaded_fails_verify_and_lint_too(self):
        (self.root / "data" / "math" / "g2" / "questions.json").write_text("{", encoding="utf-8")
        for gate in ("verify", "lint"):
            code, out = self.cli(gate)
            self.assertEqual(code, 1, f"{gate}: {out}")
            self.assertIn("V1-json:", out)

    def test_derived_views_raise_instead_of_crashing_on_a_broken_edge(self):
        raw = helpers.fixture_raw()
        raw.edges[1].append(None)
        with self.assertRaises(CorpusError):
            Corpus.from_raw("math", raw).learning_order()

    def test_a_file_in_another_encoding_is_a_load_error(self):
        file = self.root / "data" / "math" / "g2" / "questions.json"
        file.write_bytes('["č".encode("cp1250")]'.encode("cp1250"))
        code, out = self.cli("validate")
        self.assertEqual(code, 1)
        self.assertIn("V1-json:", out)
        self.assertIn("nije UTF-8", out)
        self.assertEqual(self.cli("status")[0], 0)  # status reads what it can

    def test_a_duplicate_key_keeps_its_own_code(self):
        file = self.root / "data" / "math" / "g1" / "topics.json"
        file.write_text('[{"id": "a", "id": "b"}]', encoding="utf-8")
        code, out = self.cli("validate")
        self.assertEqual(code, 1)
        self.assertIn("V1-duplicate-key:", out)

    def test_a_grade_folder_missing_from_meta_is_reported_and_still_loaded(self):
        (self.root / "data" / "math" / "g3").mkdir()
        corpus = Corpus.load("math", root=self.root)
        self.assertIn(3, corpus.grades)
        self.assertTrue(any("nije naveden u meta.json" in message for _, message in corpus.load_errors))

    def test_a_rule_file_that_is_not_a_list_is_a_load_error(self):
        (self.root / "data" / "lint" / "notation.json").write_text('{"pattern": "x"}', encoding="utf-8")
        code, out = self.cli("lint")
        self.assertEqual(code, 1)
        self.assertIn("pravila notacije moraju biti niz", out)

    def test_an_edition_without_outcomes_is_reported(self):
        raw = helpers.fixture_raw()
        del raw.editions["g1-2026"]["outcomes"]
        corpus = Corpus.from_raw("math", raw)
        issues = Issues()
        schema.run(corpus, issues)
        self.assertIn("V2-missing-field", issues.codes())

    def test_alias_targets_of_mixed_types_do_not_crash(self):
        raw = helpers.fixture_raw()
        raw.aliases["mat-stari"] = ["mat-brojevi-do-10", 5, None]
        issues = Issues()
        schema.run(Corpus.from_raw("math", raw), issues)
        self.assertIn("V11-alias-target", issues.codes())

    def test_statistics_survive_a_broken_edge(self):
        raw = helpers.fixture_raw()
        raw.edges[1].append(7)
        self.assertEqual(report.stats(Corpus.from_raw("math", raw))["topics"], 8)


class BrokenLedgerTest(FixtureTree):
    def test_a_ledger_with_conflict_markers_is_a_message(self):
        (self.root / "data" / "ledger.json").write_text("<<<<<<< ours\n{}", encoding="utf-8")
        for argv in (("status",), ("ledger", "mark", "--gate", "classify", "--grade", "1")):
            code, out = run_cli("--root", str(self.root), *argv)
            self.assertEqual(code, 1, out)
            self.assertNotIn("Traceback", out)

    def test_blind_diff_rejects_an_answer_file_that_is_not_an_object(self):
        answers = self.root / "answers.json"
        jsonio.dump([1, 2, 3], answers)
        code, out = run_cli("--root", str(self.root), "blind", "diff", "--grade", "1", "--answers", str(answers))
        self.assertEqual(code, 1)
        self.assertNotIn("Traceback", out)
        self.assertIn("mora biti objekat", out)


class TeacherReviewFileTest(unittest.TestCase):
    def codes(self, reviews):
        raw = helpers.fixture_raw()
        corpus = Corpus.from_raw("math", raw)
        corpus.review = reviews
        issues = Issues()
        schema.run(corpus, issues)
        return issues

    def test_a_well_formed_mark_is_clean(self):
        issues = self.codes({"mat-brojevi-do-10": {"name": "Milana Marković", "role": "nastavnica matematike", "date": "2026-11-26", "note": ""}})
        self.assertEqual(issues.codes(), set())

    def test_a_mark_for_an_unknown_topic_is_reported(self):
        issues = self.codes({"mat-nepostojeca": {"name": "Milana Marković", "role": "nastavnica", "date": "2026-11-26"}})
        self.assertIn("V3-id-unknown", issues.codes())

    def test_a_mark_of_the_wrong_shape_is_reported(self):
        issues = self.codes({"mat-brojevi-do-10": "pregledano", "mat-sabiranje-do-10": {"name": "M", "role": "nastavnica", "date": "26.11.2026.", "dodatno": 1}})
        self.assertIn("V2-type", issues.codes())
        self.assertIn("V2-unknown-field", issues.codes())

    def test_a_file_that_is_not_an_object_is_reported(self):
        self.assertIn("V2-type", self.codes([]).codes())
