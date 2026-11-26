"""Tests for skills/brainrc-gatework/scripts/unavailable_gates.py and the `unavailable_gates` key
(brainrc/brainrc#145): a planned check that doesn't run yet is never reported as passing."""
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

from helpers import PACK_TOML, PackCase, brainrc, quiet
from test_validator import VALIDATOR

SCRIPT = Path(__file__).resolve().parent.parent / "skills/brainrc-gatework/scripts/unavailable_gates.py"

VERIFY = """# Verify: x

## Checks
| Check | Command | Result |
|---|---|---|
| Tests | `pytest -q` | pass: 3 passed, 0 failed |
| iac-scan | — | not run, unavailable |
"""


class ScriptTest(unittest.TestCase):
    def setUp(self):
        self.run_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.run_dir)
        (self.run_dir / "verify.md").write_text(VERIFY)

    def check(self, *gates: str) -> tuple[int, str]:
        p = subprocess.run([sys.executable, str(SCRIPT), "check", str(self.run_dir), *gates],
                           capture_output=True, text=True)
        return p.returncode, p.stdout

    def test_not_run_is_clean(self):
        (self.run_dir / "pr-body.md").write_text("## Checks\n- Tests pass\n- iac-scan: not run, unavailable\n")
        self.assertEqual(self.check("iac-scan"), (0, ""))

    def test_a_pass_claim_trips(self):
        for claim in ("- iac-scan passed", "| iac-scan | `tfsec .` | pass |", "- IAC-SCAN ✅", "iac-scan: OK",
                      "- [x] AC3: no misconfig, verified by `iac-scan`", "- iac-scan: clean",
                      "- iac-scan: no findings", "- ☑ iac-scan"):
            with self.subTest(claim=claim):
                (self.run_dir / "pr-body.md").write_text(f"## Checks\n{claim}\n")
                code, out = self.check("iac-scan")
                self.assertEqual(code, 1, out)
                self.assertIn("pr-body.md:2: `iac-scan` is unavailable, but this line claims a pass", out)

    def test_a_gate_verify_md_leaves_out_trips(self):
        code, out = self.check("iac-scan", "dast")
        self.assertEqual(code, 1, out)
        self.assertIn("verify.md: `## Checks` has no row for `dast` with Result `not run, unavailable`", out)
        self.assertNotIn("`iac-scan`", out)

    def test_verify_md_needs_the_row_under_checks(self):
        row = "| iac-scan | — | not run, unavailable |\n"
        variants = {
            "result is only not run": VERIFY.replace(row, "| iac-scan | — | not run |\n"),
            "row under another heading": VERIFY.replace(row, "") + "\n## Notes\n" + row,
            "named in prose only": VERIFY.replace(row, "") + "\niac-scan: not run, unavailable\n",
        }
        for why, verify in variants.items():
            with self.subTest(why):
                (self.run_dir / "verify.md").write_text(verify)
                code, out = self.check("iac-scan")
                self.assertEqual(code, 1, out)
                self.assertIn("has no row for `iac-scan`", out)

    def test_a_backticked_gate_cell_counts(self):
        (self.run_dir / "verify.md").write_text(VERIFY.replace("| iac-scan |", "| `IaC-Scan` |"))
        self.assertEqual(self.check("iac-scan"), (0, ""))

    def test_a_gate_named_like_a_pass_word_is_not_its_own_claim(self):
        (self.run_dir / "verify.md").write_text(VERIFY.replace("iac-scan", "scan-done"))
        self.assertEqual(self.check("scan-done"), (0, ""))

    def test_near_misses_do_not_trip(self):
        (self.run_dir / "pr-body.md").write_text("- iac-scanner bypass noted, not run\n- pre-iac-scan done\n")
        self.assertEqual(self.check("iac-scan"), (0, ""))


class KeyTest(PackCase):
    def test_renders_with_the_command_to_run(self):
        self.acme(PACK_TOML.replace("[extensions.gatework]\n",
                                    '[extensions.gatework]\nunavailable_gates = ["iac-scan", "dast"]\n'))
        code, out = self.validate()
        self.assertEqual(code, 0, out)
        code, out = quiet(brainrc.cmd_sync, True)
        self.assertEqual(code, 0, out)
        ext = (self.settings_home / "extensions.md").read_text()
        self.assertIn("## Unavailable gates", ext)
        self.assertIn("Never report one as passed or done", ext)
        self.assertIn("specs/<slug> iac-scan dast`", ext)
        self.assertIn("- (acme) iac-scan", ext)

    def test_a_name_that_is_a_pass_word_fails(self):
        for bad in ("done", "OK", "verified"):
            with self.subTest(bad=bad):
                errors = VALIDATOR.check_extensions({"unavailable_gates": [bad]}, "w", set(), set())
                self.assertEqual(errors, [f"w: unavailable_gates can't name `{bad}`: unavailable_gates.py "
                                          "reads that word as a pass"])

    def test_a_name_that_is_not_one_word_fails(self):
        for bad in ('"iac scan"', '"$(x)"', "3", '""'):
            with self.subTest(bad=bad):
                errors = VALIDATOR.check_extensions(
                    tomllib.loads(f"unavailable_gates = [{bad}]"), "w", set(), set())
                self.assertEqual(len(errors), 1, errors)
                self.assertIn("unavailable_gates must be a list of check names", errors[0])


if __name__ == "__main__":
    unittest.main()
