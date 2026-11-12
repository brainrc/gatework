"""Tests for skills/brainrc-gatework/scripts/living_specs.py: apply a spec's requirement delta to the
per-area truth files in specs/living/."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "skills/brainrc-gatework/scripts/living_specs.py"

RUN1 = """# Spec: shout

## Acceptance criteria
- **AC1**: ...

## Requirement changes
### Area: cli
Purpose: How `greet.py` is invoked and what it prints.
#### ADDED: Default greeting
`greet.py <name>` SHALL print `Hello, <name>!`. (AC1)
#### ADDED: Shout flag
With `--shout`, the greeting SHALL be printed in upper case. (AC2)

### Area: packaging
Purpose: How the tool is versioned.
#### ADDED: Version flag
`--version` SHALL print `greet 1.0`. (AC3)

## Open questions
None.
"""

RUN2 = """# Spec: quiet

## Requirement changes
### Area: cli
#### MODIFIED: Shout flag
With `--shout`, the greeting SHALL be printed in upper case followed by `!!`. (AC1)
#### REMOVED: Default greeting
Why: covered by the new greeting requirement.
#### ADDED: Custom greeting
`--greeting WORD` SHALL replace `Hello`. (AC2)
"""


class LivingSpecsTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.living = self.root / "specs/living"

    def tearDown(self):
        shutil.rmtree(self.root)

    def spec(self, slug: str, text: str) -> Path:
        path = self.root / "specs" / slug / "spec.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def run_script(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True,
                              timeout=30)

    def apply(self, slug: str, text: str, ok: bool = True) -> subprocess.CompletedProcess:
        result = self.run_script("apply", str(self.spec(slug, text)))
        self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
        return result

    def area(self, name: str) -> str:
        return (self.living / f"{name}.md").read_text()

    def test_first_run_creates_area_files_with_purpose_and_provenance(self):
        out = self.apply("001-shout", RUN1).stdout
        self.assertIn("specs/living/cli.md", out)
        cli = self.area("cli")
        self.assertTrue(cli.startswith("# cli\n\nHow `greet.py` is invoked and what it prints.\n"))
        self.assertIn("### Shout flag\nWith `--shout`, the greeting SHALL be printed in upper case. (AC2)\n"
                      "_Last changed by 001-shout._", cli)
        self.assertIn("### Version flag", self.area("packaging"))

    def test_second_run_modifies_removes_and_adds(self):
        self.apply("001-shout", RUN1)
        self.apply("003-quiet", RUN2)
        cli = self.area("cli")
        self.assertIn("followed by `!!`. (AC1)\n_Last changed by 003-quiet._", cli)
        self.assertNotIn("Default greeting", cli)
        self.assertIn("### Custom greeting", cli)
        self.assertLess(cli.index("### Shout flag"), cli.index("### Custom greeting"))  # order kept, new last
        self.assertIn("_Last changed by 001-shout._", self.area("packaging"))  # untouched area

    def test_none_changes_nothing(self):
        result = self.apply("002-docs", "# Spec\n\n## Requirement changes\nNone.\n")
        self.assertIn("no requirement changes", result.stdout)
        self.assertFalse(self.living.exists())

    def test_bad_deltas_fail_and_write_nothing(self):
        self.apply("001-shout", RUN1)
        before = {p.name: p.read_text() for p in self.living.iterdir()}
        cases = {
            "unknown MODIFIED": "### Area: cli\n#### MODIFIED: Nope\nText.\n",
            "unknown REMOVED": "### Area: cli\n#### REMOVED: Nope\nWhy: x.\n",
            "duplicate ADDED": "### Area: cli\n#### ADDED: Shout flag\nAgain.\n",
            "REMOVED without why": "### Area: cli\n#### REMOVED: Shout flag\n",
            "empty requirement": "### Area: cli\n#### ADDED: Empty\n",
            "unknown kind": "### Area: cli\n#### CHANGED: Shout flag\nText.\n",
            "MODIFIED in a new area": "### Area: newarea\n#### MODIFIED: X\nText.\n",
            "bad area name": "### Area: Has Space\n#### ADDED: X\nText.\n",
            "block outside an area": "#### ADDED: X\nText.\n",
            "a later good block": "### Area: cli\n#### ADDED: Fine\nText.\n#### MODIFIED: Nope\nText.\n",
        }
        for why, body in cases.items():
            with self.subTest(why):
                result = self.apply("009-bad", f"# Spec\n\n## Requirement changes\n{body}", ok=False)
                self.assertTrue(result.stderr.strip(), why)
                self.assertEqual({p.name: p.read_text() for p in self.living.iterdir()}, before)

    def test_a_note_before_the_first_area_is_ignored(self):
        note = "## Requirement changes\nNo `specs/living/` exists yet, so this creates the area.\n\n"
        self.apply("001-shout", RUN1.replace("## Requirement changes\n", note))
        self.assertIn("### Shout flag", self.area("cli"))
        self.assertNotIn("exists yet", self.area("cli"))

    def test_text_between_an_area_and_its_blocks_is_still_an_error(self):
        body = "### Area: cli\nPurpose: x.\nA stray line.\n#### ADDED: X\nText.\n"
        result = self.apply("009-bad", f"# Spec\n\n## Requirement changes\n{body}", ok=False)
        self.assertIn("stray line", result.stderr)

    def test_template_guidance_comments_are_ignored(self):
        template = (SCRIPT.parent.parent / "templates/spec.md").read_text()
        guidance = template[template.index("## Requirement changes"):].split("### Area")[0]
        self.assertIn("<!--", guidance)
        self.apply("004-docs", "# Spec\n\n" + guidance + "None.\n")
        self.apply("001-shout", RUN1.replace("## Requirement changes\n", guidance))
        self.assertIn("### Shout flag", self.area("cli"))

    def test_missing_section_is_an_error(self):
        result = self.apply("010-old", "# Spec\n\n## Acceptance criteria\n- **AC1**: x\n", ok=False)
        self.assertIn("## Requirement changes", result.stderr)

    def test_applying_the_same_spec_twice_is_an_error_not_a_duplicate(self):
        self.apply("001-shout", RUN1)
        before = self.area("cli")
        self.apply("001-shout", RUN1, ok=False)
        self.assertEqual(self.area("cli"), before)

    def test_check_validates_without_writing(self):
        spec = self.spec("001-shout", RUN1)
        result = self.run_script("check", str(spec))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.living.exists())
        self.apply("001-shout", RUN1)
        self.assertNotEqual(self.run_script("check", str(spec)).returncode, 0)  # now duplicates

    def test_living_dir_and_run_name_can_be_given(self):
        spec = self.spec("001-shout", RUN1)
        other = self.root / "truth"
        result = self.run_script("apply", str(spec), "--living", str(other), "--run", "gh-1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("_Last changed by gh-1._", (other / "cli.md").read_text())


if __name__ == "__main__":
    unittest.main()
