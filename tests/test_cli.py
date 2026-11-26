import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from zg import __main__ as cli
from tests import helpers


class CliTest(unittest.TestCase):
    """Global options (``--root``, ``--subject``) come before the command."""

    def run_cli(self, *argv):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = cli.main(list(argv))
        return code, output.getvalue()

    def test_unimplemented_gate_says_so(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = helpers.write_corpus(Path(tmp), helpers.fixture_raw())
            code, out = self.run_cli("--root", str(root), "validate")
        self.assertEqual(code, cli.NOT_IMPLEMENTED)
        self.assertIn("nije implementirano", out)

    def test_unimplemented_tool_says_so(self):
        for command in ("build", "status"):
            code, out = self.run_cli(command)
            self.assertEqual(code, cli.NOT_IMPLEMENTED, command)
            self.assertIn("nije implementirano", out)

    def test_all_fails_while_anything_is_missing(self):
        code, out = self.run_cli("all", "--skip-site")
        self.assertNotEqual(code, 0)
        self.assertIn("PALO", out)
