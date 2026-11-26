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
