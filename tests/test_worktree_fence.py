"""Tests for skills/brainrc-gatework/scripts/worktree_fence.py: before a wave task lands, every changed
path must be inside the task's worktree fence and the main tree must be unchanged."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "skills/brainrc-gatework/scripts/worktree_fence.py"


def git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", "-c", "maintenance.auto=false", *args], cwd=cwd, check=True, capture_output=True)


class WorktreeFenceTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp()).resolve()
        self.main = self.root / "repo"
        self.main.mkdir()
        git(self.main, "init", "-q", "-b", "main")
        git(self.main, "config", "user.email", "t@example.com")
        git(self.main, "config", "user.name", "t")
        (self.main / "src").mkdir()
        (self.main / "src/a.py").write_text("a = 1\n")
        (self.main / "README.md").write_text("readme\n")
        git(self.main, "add", "-A")
        git(self.main, "commit", "-qm", "init")
        self.wt = self.root / "wt"
        git(self.main, "worktree", "add", "-q", str(self.wt), "HEAD")

    def tearDown(self):
        shutil.rmtree(self.root)

    def fence(self, *extra: str) -> subprocess.CompletedProcess:
        args = [sys.executable, str(SCRIPT), "check", str(self.wt), "--main", str(self.main),
                "--files", "src/a.py", "tests/test_*.py", *extra]
        return subprocess.run(args, capture_output=True, text=True)

    def test_changes_inside_fence_pass(self):
        (self.wt / "src/a.py").write_text("a = 2\n")
        (self.wt / "tests").mkdir()
        (self.wt / "tests/test_a.py").write_text("x = 1\n")  # untracked, matches a glob
        result = self.fence()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout)

    def test_tracked_stray_path_fails(self):
        (self.wt / "src/a.py").write_text("a = 2\n")
        (self.wt / "README.md").write_text("changed\n")
        result = self.fence()
        self.assertEqual(result.returncode, 1)
        self.assertIn("STRAY README.md", result.stdout)
        self.assertNotIn("src/a.py", result.stdout)

    def test_untracked_stray_path_fails(self):
        (self.wt / "src/new.py").write_text("n = 1\n")
        result = self.fence()
        self.assertEqual(result.returncode, 1)
        self.assertIn("STRAY src/new.py", result.stdout)

    def test_rename_from_outside_the_fence_fails(self):
        git(self.wt, "mv", "README.md", "src/a_doc.py")  # the deletion of README.md is out of scope
        result = self.fence("--files", "src/*")
        self.assertEqual(result.returncode, 1)
        self.assertIn("STRAY README.md", result.stdout)
        self.assertNotIn("src/a_doc.py", result.stdout)

    def test_main_tree_write_fails(self):
        (self.wt / "src/a.py").write_text("a = 2\n")
        (self.main / "src/a.py").write_text("a = 3\n")  # the implementer wrote to the root
        result = self.fence()
        self.assertEqual(result.returncode, 1)
        self.assertIn("MAIN src/a.py", result.stdout)

    def test_allowed_main_prefix_passes(self):
        (self.main / "specs/001-x").mkdir(parents=True)
        (self.main / "specs/001-x/state.json").write_text("{}")  # the engine's own state
        result = self.fence("--allow", "specs/001-x/")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_not_a_repo_is_exit_2(self):
        shutil.rmtree(self.wt)
        result = self.fence()
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
