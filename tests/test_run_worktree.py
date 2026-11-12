"""Tests for skills/brainrc-gatework/scripts/run_worktree.py: open the per-run git worktree outside the
main checkout (create, reuse, recreate, refuse)."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "skills/brainrc-gatework/scripts/run_worktree.py"
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "maintenance.auto=false"]



def clean_env(**extra: str) -> dict:
    """The environment without GIT_* variables, so no subprocess can be redirected to another repo."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    return {**env, **extra}


class RunWorktreeTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp()).resolve()
        self.main = self.root / "proj"
        self.main.mkdir()
        self.git(self.main, "init", "-q", "-b", "trunk")
        (self.main / "tests").mkdir()
        (self.main / "tests/test_a.py").write_text(
            "import unittest\nclass T(unittest.TestCase):\n    def test_a(self):\n        pass\n")
        self.git(self.main, "add", "-A")
        self.git(self.main, "commit", "-q", "-m", "init")
        self.wt_root = self.root / ".brainrc-worktrees" / "proj"

    def tearDown(self):
        shutil.rmtree(self.root)

    def git(self, cwd: Path, *args: str, ok: bool = True) -> str:
        # A bad path (e.g. Path("") from empty script output) must never reach the real checkout.
        assert str(cwd) and Path(cwd).resolve().is_relative_to(self.root), \
            f"git outside the test root: {cwd!r}"
        out = subprocess.run([*GIT, "-C", str(cwd), *args], capture_output=True, text=True,
                             env=clean_env())
        if ok:
            assert out.returncode == 0, out.stderr
        return out.stdout.strip()

    def opened(self) -> Path:
        """Open the default worktree; its path must lie inside this test's temp root."""
        r = self.open()
        self.assertEqual(r.returncode, 0, r.stderr)
        wt = Path(r.stdout.strip())
        self.assertTrue(r.stdout.strip() and wt.resolve().is_relative_to(self.root), repr(r.stdout))
        return wt

    def open(self, slug="s1", branch="feat/s1", base="trunk", cwd=None, env=None, extra=()):
        cmd = [sys.executable, str(SCRIPT), "open", slug, "--branch", branch]
        if base:
            cmd += [f"--base={base}"]
        return subprocess.run([*cmd, *extra], cwd=cwd or self.main, capture_output=True, text=True,
                              env=env or clean_env())

    def test_creates_at_default_path_and_prints_only_path(self):
        r = self.open()
        self.assertEqual(r.returncode, 0, r.stderr)
        want = self.wt_root / "s1"
        self.assertEqual(r.stdout, f"{want}\n")
        self.assertEqual(self.git(want, "branch", "--show-current"), "feat/s1")

    def test_path_outside_main_and_not_under_tmpdir(self):
        other_tmp = self.root / "othertmp"
        other_tmp.mkdir()
        r = self.open(env=clean_env(TMPDIR=str(other_tmp)))
        self.assertEqual(r.returncode, 0, r.stderr)
        path = Path(r.stdout.strip())
        self.assertEqual(path, self.wt_root / "s1")
        self.assertNotIn(self.main, path.parents)
        self.assertNotIn(other_tmp, path.parents)

    def test_unittest_discover_in_main_ignores_worktree(self):
        wt = self.opened()
        self.assertTrue((wt / "tests/test_a.py").is_file())
        out = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                             cwd=self.main, capture_output=True, text=True, env=clean_env())
        self.assertIn("Ran 1 test", out.stderr)

    def test_works_from_inside_a_worktree(self):
        first = self.opened()
        r = self.open(slug="s2", branch="feat/s2", cwd=first)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), str(self.wt_root / "s2"))

    def test_existing_worktree_is_reused(self):
        first = self.open().stdout
        r = self.open(base=None)
        self.assertEqual((r.returncode, r.stdout), (0, first))

    def test_commit_in_worktree_leaves_main_untouched(self):
        wt = self.opened()
        head, status = self.git(self.main, "rev-parse", "HEAD"), self.git(self.main, "status", "--porcelain")
        (wt / "new.txt").write_text("x")
        self.git(wt, "add", "-A")
        self.git(wt, "commit", "-q", "-m", "work")
        self.assertEqual(self.git(self.main, "rev-parse", "HEAD"), head)
        self.assertEqual(self.git(self.main, "status", "--porcelain"), status)
        self.assertEqual(self.git(self.main, "log", "-1", "--format=%s", "feat/s1"), "work")

    def test_recreates_missing_worktree_from_branch(self):
        wt = self.opened()
        (wt / "new.txt").write_text("x")
        self.git(wt, "add", "-A")
        self.git(wt, "commit", "-q", "-m", "work")
        shutil.rmtree(wt)
        r = self.open(base=None)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), str(wt))
        self.assertTrue((wt / "new.txt").exists())

    def test_missing_branch_without_base_exits_1_and_creates_nothing(self):
        r = self.open(branch="feat/nope", base=None)
        self.assertEqual(r.returncode, 1)
        self.assertEqual(r.stdout, "")
        self.assertFalse((self.wt_root / "s1").exists())
        self.assertEqual(self.git(self.main, "branch", "--list", "feat/nope"), "")
        self.assertEqual(len(self.git(self.main, "worktree", "list").splitlines()), 1)

    def test_main_on_branch_is_refused_and_changes_nothing(self):
        self.git(self.main, "switch", "-q", "-c", "feat/s1")
        before = self.git(self.main, "worktree", "list", "--porcelain")
        status = self.git(self.main, "status", "--porcelain")
        r = self.open()
        self.assertEqual(r.returncode, 1)
        self.assertEqual(r.stdout, "")
        self.assertIn("feat/s1", r.stderr)
        self.assertIn(f"git -C {self.main} switch", r.stderr)
        self.assertEqual(self.git(self.main, "worktree", "list", "--porcelain"), before)
        self.assertEqual(self.git(self.main, "status", "--porcelain"), status)
        self.assertFalse(self.wt_root.exists())

    def test_rejects_unsafe_slug_and_branch(self):
        for slug in ("../x", "a/b", "..", ""):
            r = self.open(slug=slug)
            self.assertNotEqual(r.returncode, 0, slug)
            self.assertEqual(r.stdout, "")
        r = self.open(branch="-evil")
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse(self.wt_root.exists())

    def test_git_failure_exits_2(self):
        r = self.open(branch="feat/new", base="no-such-base")
        self.assertEqual(r.returncode, 2)
        self.assertEqual(r.stdout, "")

    def test_unsafe_base_exits_2_and_creates_nothing(self):
        r = self.open(branch="feat/new", base="--detach")
        self.assertEqual((r.returncode, r.stdout), (2, ""))
        self.assertFalse(self.wt_root.exists())
        self.assertEqual(self.git(self.main, "branch", "--list", "feat/new"), "")

    def test_plain_directory_at_path_exits_1_and_creates_no_branch(self):
        (self.wt_root / "s1").mkdir(parents=True)
        r = self.open()
        self.assertEqual((r.returncode, r.stdout), (1, ""))
        self.assertEqual(self.git(self.main, "branch", "--list", "feat/s1"), "")

    def test_worktree_on_other_branch_at_path_exits_1_and_creates_no_branch(self):
        self.git(self.main, "worktree", "add", "-q", "-b", "other", str(self.wt_root / "s1"), "trunk")
        r = self.open()
        self.assertEqual((r.returncode, r.stdout), (1, ""))
        self.assertEqual(self.git(self.main, "branch", "--list", "feat/s1"), "")

    def test_branch_checked_out_in_other_worktree_exits_2_and_adds_none(self):
        elsewhere = self.root / "elsewhere"
        self.git(self.main, "worktree", "add", "-q", "-b", "feat/s1", str(elsewhere), "trunk")
        r = self.open()
        self.assertEqual((r.returncode, r.stdout), (2, ""))
        self.assertFalse((self.wt_root / "s1").exists())
        self.assertEqual(len(self.git(self.main, "worktree", "list").splitlines()), 2)

    def test_symlinked_worktrees_dir_reuses_existing_worktree(self):
        real = self.root / "real"
        real.mkdir()
        (self.root / ".brainrc-worktrees").symlink_to(real)
        first = self.open()
        self.assertEqual(first.returncode, 0, first.stderr)
        r = self.open(base=None)
        self.assertEqual((r.returncode, r.stdout), (0, first.stdout), r.stderr)

    def test_not_a_repo_exits_2(self):
        r = self.open(cwd=self.root)
        self.assertEqual(r.returncode, 2)


if __name__ == "__main__":
    unittest.main()
