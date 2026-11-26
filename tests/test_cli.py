import contextlib
import io
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
