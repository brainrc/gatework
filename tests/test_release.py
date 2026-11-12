"""scripts/gatework.py: the plugin manifests, the changelog check and the release fold."""
import contextlib
import importlib.util
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("gatework_script", ROOT / "scripts/gatework.py")
gw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gw)


def quiet(fn, *args, **kwargs):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = fn(*args, **kwargs)
    return code, buf.getvalue()


class RepoTest(unittest.TestCase):
    def test_the_committed_repo_passes_check(self):
        self.assertEqual(gw.check(ROOT), [])

    def test_the_plugin_is_named_gatework_and_lists_every_agent(self):
        plugin = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())
        self.assertEqual((plugin["name"], plugin["skills"]), ("gatework", "./skills/"))
        self.assertEqual(len(plugin["agents"]), len(list((ROOT / "agents").glob("*.md"))))


class ReleaseTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        for name in ("VERSION", "CHANGELOG.md", "agents"):
            src = ROOT / name
            (shutil.copytree if src.is_dir() else shutil.copy2)(src, self.root / name)
        (self.root / "changelog.d").mkdir()
        quiet(gw.cmd_plugin, self.root)

    def fragment(self, name: str, text: str) -> None:
        (self.root / "changelog.d" / name).write_text(text)

    def test_release_folds_fragments_by_the_largest_bump(self):
        major, minor, _ = gw.version(self.root)
        self.fragment("a.md", "---\nbump: patch\n---\n- A fix.\n")
        self.fragment("b.md", "---\nbump: minor\n---\n- A new skill.\n")
        code, out = quiet(gw.cmd_release, self.root)
        self.assertEqual(code, 0, out)
        new = f"{major}.{minor + 1}.0"
        self.assertEqual((self.root / "VERSION").read_text().strip(), new)
        self.assertEqual(gw.release_notes((self.root / "CHANGELOG.md").read_text(), new), "- A fix.\n- A new skill.")
        self.assertEqual(list((self.root / "changelog.d").glob("*.md")), [])
        self.assertEqual(gw.check(self.root), [])

    def test_no_fragments_releases_nothing(self):
        before = (self.root / "VERSION").read_text()
        code, out = quiet(gw.cmd_release, self.root)
        self.assertEqual(code, 0, out)
        self.assertIn("nothing to release", out)
        self.assertEqual((self.root / "VERSION").read_text(), before)

    def test_a_bad_fragment_fails_check_and_release(self):
        self.fragment("bad.md", "---\nbump: huge\n---\n- X.\n")
        self.assertTrue(any("`bump` must be one of" in e for e in gw.check(self.root)))
        code, out = quiet(gw.cmd_release, self.root)
        self.assertEqual(code, 1, out)

    def test_notes_need_a_whole_version(self):
        code, out = quiet(gw.cmd_notes, "0.7", self.root)
        self.assertEqual(code, 1, out)
        self.assertIn("not MAJOR.MINOR.PATCH", out)

    def test_a_stale_manifest_fails_check(self):
        (self.root / "VERSION").write_text("9.9.9\n")
        errors = gw.check(self.root)
        self.assertTrue(any("stale" in e for e in errors), errors)
        self.assertTrue(any("doesn't match VERSION" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main()
