"""Tests for skills/brainrc-gatework/scripts/active_run.py: write and read the active-run pointer that
external tools use to locate the current spec-agent run."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "skills/brainrc-gatework/scripts/active_run.py"


class ActiveRunTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp()).resolve()
        self.home = self.root / "home"
        self.home.mkdir()
        self.aicfg = self.root / "cfg" / "ai-config"  # parent does not exist yet
        self.repo_a = self.root / "repo-a"
        self.cwd_b = self.root / "elsewhere"
        self.cwd_b.mkdir()

    def tearDown(self):
        shutil.rmtree(self.root)

    def run_dir(self, slug: str, base: Path | None = None, mtime: float | None = None) -> Path:
        run = (base or self.repo_a) / "specs" / slug
        run.mkdir(parents=True, exist_ok=True)
        state = run / "state.json"
        state.write_text("{}")
        if mtime is not None:
            os.utime(state, (mtime, mtime))
        return run

    def env(self, aicfg_home: Path | str | None = "default", **extra: str) -> dict:
        drop = {"BRAINRC_HOME", "AICFG_HOME", "XDG_CONFIG_HOME"}
        env = {k: v for k, v in os.environ.items() if k not in drop and not k.startswith("GIT_")}
        env["HOME"] = str(self.home)
        if aicfg_home == "default":
            aicfg_home = self.aicfg
        if aicfg_home is not None:
            env["BRAINRC_HOME"] = str(aicfg_home)
        env.update(extra)
        return env

    def cli(self, *args, cwd=None, aicfg_home="default", **extra):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True, text=True, cwd=cwd or self.cwd_b, env=self.env(aicfg_home, **extra),
        )

    @property
    def pointer(self) -> Path:
        return self.aicfg / "active-run"

    # AC1, AC8
    def test_write_from_other_directory_records_absolute_run_path(self):
        run = self.run_dir("071-x")
        result = self.cli("write", str(run), cwd=self.cwd_b)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.pointer.read_text(), f"{run}\n")

    def test_write_resolves_relative_run_dir_to_absolute(self):
        run = self.run_dir("071-x")
        result = self.cli("write", "specs/071-x", cwd=self.repo_a)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.pointer.read_text(), f"{run}\n")

    # AC2
    def test_write_defaults_to_dot_config_brainrc_when_env_unset(self):
        run = self.run_dir("071-x")
        result = self.cli("write", str(run), aicfg_home=None)
        self.assertEqual(result.returncode, 0, result.stderr)
        default = self.home / ".config/brainrc/active-run"
        self.assertEqual(default.read_text(), f"{run}\n")

    # AC15: resolution mirrors brainrc.config.settings_home, silently
    def written(self, path: Path, run: Path, result) -> None:
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual((path / "active-run").read_text(), f"{run}\n")

    def test_brainrc_home_wins_over_aicfg_home_and_xdg(self):
        run = self.run_dir("071-x")
        other = self.root / "other"
        r = self.cli("write", str(run), AICFG_HOME=str(other), XDG_CONFIG_HOME=str(other))
        self.written(self.aicfg, run, r)
        self.assertFalse(other.exists())

    def test_aicfg_home_is_not_read(self):
        run = self.run_dir("071-x")
        old = self.root / "old"
        r = self.cli("write", str(run), aicfg_home=None, AICFG_HOME=str(old))
        self.written(self.home / ".config/brainrc", run, r)
        self.assertFalse(old.exists())

    def test_absolute_xdg_config_home_uses_brainrc_subdir(self):
        run = self.run_dir("071-x")
        xdg = self.root / "xdg"
        r = self.cli("write", str(run), aicfg_home=None, XDG_CONFIG_HOME=str(xdg))
        self.written(xdg / "brainrc", run, r)

    def test_relative_xdg_config_home_is_ignored(self):
        run = self.run_dir("071-x")
        r = self.cli("write", str(run), aicfg_home=None, XDG_CONFIG_HOME="rel/xdg")
        self.written(self.home / ".config/brainrc", run, r)

    def test_legacy_home_is_not_read(self):
        run = self.run_dir("071-x")
        legacy = self.home / ".config/ai-config"
        legacy.mkdir(parents=True)
        r = self.cli("write", str(run), aicfg_home=None)
        self.written(self.home / ".config/brainrc", run, r)
        self.assertFalse((legacy / "active-run").exists())
        r = self.cli("read", aicfg_home=None)
        self.assertEqual(r.stdout.strip(), str(run))

    def test_legacy_home_is_not_read_with_xdg_set(self):
        run = self.run_dir("071-x")
        (self.home / ".config/ai-config").mkdir(parents=True)
        xdg = self.root / "xdg"
        r = self.cli("write", str(run), aicfg_home=None, XDG_CONFIG_HOME=str(xdg))
        self.written(xdg / "brainrc", run, r)

    def test_new_home_preferred_when_both_exist(self):
        run = self.run_dir("071-x")
        (self.home / ".config/ai-config").mkdir(parents=True)
        new = self.home / ".config/brainrc"
        new.mkdir(parents=True)
        r = self.cli("write", str(run), aicfg_home=None)
        self.written(new, run, r)

    # AC3
    def test_pointer_is_single_line_path_plus_newline_only(self):
        run = self.run_dir("071-x")
        self.cli("write", str(run))
        self.assertEqual(self.pointer.read_bytes(), f"{run}\n".encode())

    # AC5
    def test_write_replaces_another_runs_pointer(self):
        first = self.run_dir("070-a-much-longer-run-slug-than-the-next-one")
        second = self.run_dir("071-new")
        self.cli("write", str(first))
        self.cli("write", str(second))
        self.assertEqual(self.pointer.read_text(), f"{second}\n")

    def test_write_same_run_twice_is_idempotent(self):
        run = self.run_dir("071-x")
        self.cli("write", str(run))
        self.cli("write", str(run))
        self.assertEqual(self.pointer.read_text(), f"{run}\n")

    # AC8
    def test_write_creates_missing_aicfg_home_directory(self):
        run = self.run_dir("071-x")
        self.assertFalse(self.aicfg.exists())
        result = self.cli("write", str(run))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.aicfg.is_dir())
        self.assertTrue(self.pointer.is_file())

    # AC9
    def test_read_prints_pointer_run_when_directory_exists(self):
        run = self.run_dir("071-x")
        self.cli("write", str(run))
        result = self.cli("read", cwd=self.cwd_b)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), str(run))

    def test_read_prefers_pointer_over_newer_run_in_cwd(self):
        pointed = self.run_dir("070-pointed", mtime=1_000_000)
        self.run_dir("071-newer", base=self.cwd_b, mtime=2_000_000)
        self.cli("write", str(pointed))
        result = self.cli("read", cwd=self.cwd_b)
        self.assertEqual(result.stdout.strip(), str(pointed))

    # AC10
    def test_read_without_pointer_returns_newest_run_in_cwd_specs(self):
        self.run_dir("070-old", base=self.cwd_b, mtime=1_000_000)
        newest = self.run_dir("071-new", base=self.cwd_b, mtime=2_000_000)
        self.run_dir("069-older", base=self.cwd_b, mtime=500_000)
        result = self.cli("read", cwd=self.cwd_b)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Path(result.stdout.strip()).resolve(), newest)

    def test_read_with_pointer_to_missing_directory_falls_back_to_cwd_specs(self):
        newest = self.run_dir("071-new", base=self.cwd_b, mtime=2_000_000)
        self.run_dir("070-old", base=self.cwd_b, mtime=1_000_000)
        self.aicfg.mkdir(parents=True)
        self.pointer.write_text(f"{self.root}/gone/specs/nope\n")
        result = self.cli("read", cwd=self.cwd_b)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Path(result.stdout.strip()).resolve(), newest)

    def test_read_fallback_orders_by_state_json_mtime_not_name(self):
        newest = self.run_dir("aaa-first-by-name", base=self.cwd_b, mtime=2_000_000)
        self.run_dir("zzz-last-by-name", base=self.cwd_b, mtime=1_000_000)
        result = self.cli("read", cwd=self.cwd_b)
        self.assertEqual(Path(result.stdout.strip()).resolve(), newest)

    def test_read_with_nothing_found_prints_nothing_on_stdout(self):
        result = self.cli("read", cwd=self.cwd_b)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.returncode, 1)
        self.assertNotEqual(result.stderr.strip(), "")

    def test_read_with_blank_pointer_falls_back_to_cwd_specs(self):
        newest = self.run_dir("071-new", base=self.cwd_b, mtime=2_000_000)
        self.run_dir("070-old", base=self.cwd_b, mtime=1_000_000)
        self.aicfg.mkdir(parents=True)
        for content in ("\n", "  \n"):
            self.pointer.write_text(content)
            result = self.cli("read", cwd=self.cwd_b)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(Path(result.stdout.strip()).resolve(), newest)

    def test_read_with_pointer_naming_a_file_falls_back_to_cwd_specs(self):
        newest = self.run_dir("071-new", base=self.cwd_b, mtime=2_000_000)
        a_file = self.root / "plain.txt"
        a_file.write_text("x")
        self.aicfg.mkdir(parents=True)
        self.pointer.write_text(f"{a_file}\n")
        result = self.cli("read", cwd=self.cwd_b)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Path(result.stdout.strip()).resolve(), newest)

    def git(self, *args, cwd: Path) -> None:
        subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "maintenance.auto=false", *args],
            cwd=cwd, env=self.env(None), check=True, capture_output=True,
        )

    def make_worktree(self, name: str = "wt") -> Path:
        """Temp repo at repo_a with one commit and a linked worktree; returns the worktree."""
        self.repo_a.mkdir()
        self.git("init", "-q", cwd=self.repo_a)
        self.git("commit", "-q", "--allow-empty", "-m", "init", cwd=self.repo_a)
        wt = self.root / name
        self.git("worktree", "add", "-q", "-b", name, str(wt), cwd=self.repo_a)
        return wt

    # AC5
    def test_write_worktree_run_dir_records_it(self):
        wt = self.make_worktree()
        run = self.run_dir("255-x", base=wt)
        result = self.cli("write", str(run), cwd=self.repo_a)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.pointer.read_text(), f"{run}\n")
        self.assertEqual(self.cli("read", cwd=self.cwd_b).stdout.strip(), str(run))

    # AC6
    def test_read_fallback_finds_newest_run_across_worktrees(self):
        wt = self.make_worktree()
        self.run_dir("070-main", base=self.repo_a, mtime=1_000_000)
        newest = self.run_dir("071-wt", base=wt, mtime=2_000_000)
        for cwd in (self.repo_a, wt):
            result = self.cli("read", cwd=cwd)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(Path(result.stdout.strip()).resolve(), newest)

    def test_read_fallback_skips_detached_worktrees(self):
        wt = self.make_worktree()
        detached = self.root / "task-wt"
        self.git("worktree", "add", "-q", "--detach", str(detached), cwd=self.repo_a)
        self.run_dir("070-main", base=self.repo_a, mtime=1_000_000)
        branch_run = self.run_dir("071-wt", base=wt, mtime=2_000_000)
        self.run_dir("070-main", base=detached, mtime=3_000_000)  # committed copy, fresh checkout
        for cwd in (self.repo_a, wt):
            result = self.cli("read", cwd=cwd)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(Path(result.stdout.strip()).resolve(), branch_run)

    def test_read_fallback_keeps_cwd_even_when_detached(self):
        self.make_worktree()
        detached = self.root / "task-wt"
        self.git("worktree", "add", "-q", "--detach", str(detached), cwd=self.repo_a)
        mine = self.run_dir("070-main", base=detached, mtime=1_000_000)
        result = self.cli("read", cwd=detached)
        self.assertEqual(Path(result.stdout.strip()).resolve(), mine)

    def test_read_fallback_prefers_newer_cwd_run_over_worktree_run(self):
        wt = self.make_worktree()
        newest = self.run_dir("071-main", base=self.repo_a, mtime=2_000_000)
        self.run_dir("070-wt", base=wt, mtime=1_000_000)
        result = self.cli("read", cwd=self.repo_a)
        self.assertEqual(Path(result.stdout.strip()).resolve(), newest)

    def test_read_fallback_without_git_scans_cwd_only(self):
        wt = self.make_worktree()
        mine = self.run_dir("070-main", base=self.repo_a, mtime=1_000_000)
        self.run_dir("071-wt", base=wt, mtime=2_000_000)
        nogit = self.root / "nogit"
        nogit.mkdir()
        result = self.cli("read", cwd=self.repo_a, PATH=str(nogit))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Path(result.stdout.strip()).resolve(), mine)

    def test_read_pointer_wins_over_newer_worktree_run(self):
        wt = self.make_worktree()
        pointed = self.run_dir("070-pointed", base=self.repo_a, mtime=1_000_000)
        self.run_dir("071-wt", base=wt, mtime=2_000_000)
        self.cli("write", str(pointed), cwd=self.repo_a)
        result = self.cli("read", cwd=self.repo_a)
        self.assertEqual(result.stdout.strip(), str(pointed))

    # AC11
    def test_write_warns_and_exits_zero_when_aicfg_home_is_a_file(self):
        run = self.run_dir("071-x")
        bad = self.root / "not-a-dir"
        bad.write_text("x")
        result = self.cli("write", str(run), aicfg_home=bad / "sub")
        self.assertEqual(result.returncode, 0)
        self.assertIn("WARN", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_write_warns_and_exits_zero_when_default_home_is_unwritable(self):
        run = self.run_dir("071-x")
        # HOME is a file, so ~/.config/ai-config can never be created (works even as root).
        self.home.rmdir()
        self.home.write_text("x")
        result = self.cli("write", str(run), aicfg_home=None)
        self.assertEqual(result.returncode, 0)
        self.assertIn("WARN", result.stderr)

    def test_roots_parses_porcelain_skipping_detached(self):
        import importlib.util
        from unittest import mock
        spec = importlib.util.spec_from_file_location("active_run_under_test", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        cwd = Path.cwd().resolve()
        main, bare, branch, detached, prunable = (
            self.root / n for n in ("main", "bare", "branch", "detached", "prunable"))
        porcelain = (
            f"worktree {main}\nHEAD abc\nbranch refs/heads/main\n\n"
            f"worktree {bare}\nbare\n\n"
            f"worktree {detached}\nHEAD def\ndetached\n\n"
            f"worktree {prunable}\nHEAD 123\ndetached\nprunable gitdir file points to non-existent location\n\n"
            f"worktree {branch}\nHEAD 456\nbranch refs/heads/feat\n\n"
        )

        def fake(out):
            return mock.Mock(stdout=out)

        with mock.patch.object(mod.subprocess, "run", return_value=fake(porcelain)):
            roots = mod._roots()
        self.assertEqual(roots[0], cwd)
        self.assertEqual(set(roots[1:]), {main, bare, branch})
        self.assertNotIn(detached, roots)
        self.assertNotIn(prunable, roots)
        with mock.patch.object(mod.subprocess, "run", return_value=fake("")):
            self.assertEqual(mod._roots(), [cwd])


if __name__ == "__main__":
    unittest.main()
