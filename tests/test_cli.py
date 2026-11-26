import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from zg import __main__ as cli
from zg import jsonio
from tests import helpers


class CliTest(unittest.TestCase):
    """Global options (``--root``, ``--subject``) come before the command."""

    def run_cli(self, *argv):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = cli.main(list(argv))
        return code, output.getvalue()

    def fixture_root(self) -> Path:
        root = Path(self.tmp.name)
        return helpers.write_corpus(root, helpers.fixture_raw())

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_validate_passes_on_the_fixture(self):
        code, out = self.run_cli("--root", str(self.fixture_root()), "validate")
        self.assertEqual(code, 0, out)
        self.assertTrue(out.endswith("OK\n"), out)

    def test_validate_reports_a_broken_record_with_its_path(self):
        root = self.fixture_root()
        file = root / "data" / "math" / "g1" / "topics.json"
        topics = jsonio.load(file)
        topics[0]["nepostojeca"] = 1
        jsonio.dump(topics, file)
        code, out = self.run_cli("--root", str(root), "validate")
        self.assertEqual(code, 1)
        self.assertIn("data/math/g1/topics.json: mat-brojevi-do-10: V2-unknown-field:", out)
        self.assertIn("1 greška", out)

    def test_every_gate_is_wired(self):
        for gate, modules in cli.GATES.items():
            for module in modules:
                self.assertIsNotNone(cli._load(module), f"{module} nije uvezen")

    def test_report_write_fills_the_block_and_the_cyrillic_twin(self):
        root = self.fixture_root()
        (root / "README.md").write_text("# Proba\n\nTekst na latinici.\n", encoding="utf-8")
        code, out = self.run_cli("--root", str(root), "report", "--check")
        self.assertEqual(code, 1)
        code, out = self.run_cli("--root", str(root), "report", "--write")
        self.assertEqual(code, 0, out)
        readme = (root / "README.md").read_text(encoding="utf-8")
        self.assertIn(cli.README_BEGIN, readme)
        self.assertIn("Ukupno", readme)
        twin = (root / "README.cir.md").read_text(encoding="utf-8")
        self.assertIn("Текст на латиници.", twin)
        self.assertEqual(self.run_cli("--root", str(root), "report", "--check")[0], 0)
        (root / "README.cir.md").write_text(twin + "izmena", encoding="utf-8")
        self.assertEqual(self.run_cli("--root", str(root), "report", "--check")[0], 1)

    def test_verify_and_build_read_a_stored_decimal_as_a_decimal(self):
        import json
        from zg import build

        root = self.fixture_root()
        file = root / "data" / "math" / "g2" / "questions.json"
        questions = jsonio.load(file)
        for question in questions:
            if question["id"] == "mat-oduzimanje-do-100-q2":
                question["answer"], question["check"] = "0.125", "(/ 1 8)"
        jsonio.dump(questions, file)
        code, out = self.run_cli("--root", str(root), "verify")
        self.assertEqual(code, 0, out)
        build.build_site(root, root / "_site")
        stored = jsonio.load(root / "_site" / "podaci" / "g2.lat.json")["questions"]["mat-oduzimanje-do-100-q2"]
        self.assertEqual(stored["answerRational"], ["1", "8"])

    def test_report_check_without_a_readme_says_so(self):
        root = self.fixture_root()  # a fresh fixture tree has no README at all
        code, out = self.run_cli("--root", str(root), "report", "--check")
        self.assertEqual(code, 1)
        self.assertIn("ne postoji", out)

    def test_blind_sheet_then_diff_round_trip(self):
        root = self.fixture_root()
        sheet = root / "sheet.json"
        code, out = self.run_cli("--root", str(root), "blind", "sheet", "--grade", "2", "--out", str(sheet))
        self.assertEqual(code, 0, out)
        items = jsonio.load(sheet)["items"]
        self.assertEqual(len(items), 16)
        for item in items:
            self.assertNotIn("answer", item)
            self.assertNotIn("explanation", item)
        answers = {}
        for item in items:
            question = helpers.fixture_corpus().questions[item["id"]]
            answers[item["id"]] = {
                "answer": question["answer"], "check": question["check"], "unique": True, "assumptions": [],
                "distractors": {choice["id"]: 0 for choice in question.get("choices", []) if choice["id"] != question["answer"]},
            }
        file = root / "answers.json"
        jsonio.dump(answers, file)
        code, out = self.run_cli("--root", str(root), "blind", "diff", "--grade", "2", "--answers", str(file))
        self.assertEqual(code, 0, out)
        answers["mat-oduzimanje-do-100-q1"]["unique"] = False
        del answers["mat-poredjenje-do-100-q3"]["distractors"]["c"]
        jsonio.dump(answers, file)
        code, out = self.run_cli("--root", str(root), "blind", "diff", "--grade", "2", "--answers", str(file))
        self.assertEqual(code, 1)
        self.assertIn("mat-oduzimanje-do-100-q1: unique", out)
        self.assertIn("mat-poredjenje-do-100-q3: distractor", out)

    def test_ledger_marks_a_grade_only_when_the_gate_is_clean(self):
        root = self.fixture_root()
        code, out = self.run_cli("--root", str(root), "ledger", "mark", "--gate", "verify", "--grade", "1")
        self.assertEqual(code, 0, out)
        self.assertIn("zabeleženo: 16 zapisa", out)
        self.assertEqual(self.run_cli("--root", str(root), "ledger", "mark", "--gate", "classify", "--grade", "1")[0], 0)
        file = root / "data" / "math" / "g1" / "questions.json"
        questions = jsonio.load(file)
        next(q for q in questions if q["id"] == "mat-brojevi-do-10-q1")["answer"] = "8"
        jsonio.dump(questions, file)
        code, out = self.run_cli("--root", str(root), "ledger", "mark", "--gate", "verify", "--grade", "1")
        self.assertEqual(code, 1)
        self.assertIn("ništa nije zabeleženo", out)
        status = json.loads(self.run_cli("--root", str(root), "status")[1])
        self.assertEqual(status["grades"]["1"]["gates"]["verify"]["verified"], 15)
        self.assertEqual(status["grades"]["1"]["gates"]["verify"]["stale"], ["mat-brojevi-do-10-q1"])
