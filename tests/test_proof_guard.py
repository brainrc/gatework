"""proof_guard.py: planning-mode proof commands are a narrow read-only allowlist inside the worktree, and plan files hold no secrets."""
import importlib.util
import os
import subprocess
import tempfile
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import helpers  # noqa: E402,F401  (sets BRAINRC_CORE: the guard reads core's secret patterns there)

REPO = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("proof_guard", REPO / "skills/brainrc-gatework/scripts/proof_guard.py")
pg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pg)
ENV = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


class GuardCase(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp()).resolve()
        (self.root / "src").mkdir()
        (self.root / "src/a.py").write_text("import os\nx = 1\n")
        (self.root / ".env").write_text("KEY=dummy\n")
        (self.root / ".env.example").write_text("KEY=\n")
        (self.root / "link").symlink_to("/etc/hostname")
        git = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "maintenance.auto=false", "-C", str(self.root)]
        for args in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "init"]):
            subprocess.run(git + args, check=True, capture_output=True, env=ENV)

    def denied(self, cmd):
        self.assertIsNotNone(pg.check(cmd, self.root), cmd)

    def allowed(self, cmd):
        self.assertIsNone(pg.check(cmd, self.root), cmd)


class CheckTest(GuardCase):
    def test_network_and_shell_denied_but_grepping_for_them_allowed(self):
        self.denied("curl https://example.com")
        self.denied("cat src/a.py | sh")
        self.denied("echo $(id)")
        self.allowed('grep -n "curl|wget" src/a.py')

    def test_program_executing_flags_denied(self):
        self.denied("rg --pre ./evil.sh x src/a.py")
        self.denied("rg --hostname-bin ./x x src/a.py")
        self.denied("git grep -O ./x x")
        self.denied("git show --ext-diff HEAD")
        self.denied("git show --textconv HEAD")
        self.denied("git -c core.pager=sh log")
        self.allowed("rg -n os src/a.py")
        self.allowed("git log --oneline -3")

    def test_git_show_and_log_paths_denied(self):
        self.denied("git show HEAD")
        self.denied("git show --stat HEAD")
        self.denied("git show HEAD:src/a.py")
        self.denied("git log .env")
        self.denied("git log --stat")

    def test_test_runners_are_not_re_run(self):
        self.denied("python3 -m pytest tests/test_x.py")
        self.denied("python3 -m unittest tests.test_x")

    def test_recursion_and_directory_args_denied(self):
        self.denied("grep -r KEY .")
        self.denied("rg -uu KEY .")
        self.denied("grep KEY src")
        self.denied("ls -R")
        self.allowed("grep -n os src/a.py")
        self.allowed("ls src")

    def test_secret_files_denied_in_every_form(self):
        self.denied("cat .env")
        self.denied("git show HEAD:.env")
        self.denied("grep --file=.env x src/a.py")
        self.denied("grep -f .env src/a.py")
        self.allowed("cat .env.example")

    def test_keys_and_git_internals_denied(self):
        for name in ("id_rsa", "c.pem", "server.key", "cert.p12", "terraform.tfstate", ".git-credentials"):
            (self.root / name).write_text("dummy\n")
            self.denied(f"cat {name}")
        (self.root / ".ssh").mkdir()
        (self.root / ".ssh/config").write_text("dummy\n")
        self.denied("cat .ssh/config")
        self.denied("cat .git/config")
        self.denied("ls .git")

    def test_more_secret_names_case_and_hard_links_denied(self):
        for name in ("credentials.json", "secrets.yml", "AuthKey.p8", ".htpasswd", "kubeconfig", "my.ppk",
                     "notes.gpg", "app.keystore", "service-account-prod.json", ".dockercfg", "ID_RSA",
                     "terraform.tfstate.backup"):
            (self.root / name).write_text("dummy\n")
            self.denied(f"cat {name}")
        self.denied("cat .ENV")
        (self.root / "hard.txt").hardlink_to(self.root / ".env")
        self.denied("cat hard.txt")

    def test_symlinks_and_outside_paths_denied(self):
        self.denied("cat link")
        self.denied("cat /etc/passwd")
        self.denied("cat ../x")
        self.denied("cat ~/.ssh/id_rsa")
        self.allowed("cat src/a.py")

    def test_unknown_flags_and_unparseable_denied(self):
        self.denied("cat -v src/a.py")
        self.denied("head -c 99999999 src/a.py")
        self.denied('grep "unterminated')
        self.denied("head -n ² src/a.py")
        self.allowed("head -n 5 src/a.py")
        self.allowed("wc -l src/a.py")


class RunTest(GuardCase):
    def test_run_reads_with_argv_and_reports_exit(self):
        got = pg.run("cat src/a.py", self.root, timeout=10)
        self.assertEqual(got[0], 0)
        self.assertIn("x = 1", got[1])

    def test_run_git_log(self):
        got = pg.run("git log --oneline -1", self.root, timeout=10)
        self.assertEqual(got[0], 0)
        self.assertIn("init", got[1])

    def test_run_refuses_a_denied_command(self):
        with self.assertRaises(ValueError):
            pg.run("cat .env", self.root)

    def test_matches_compares_exit_and_normalized_output(self):
        self.assertTrue(pg.matches((1, "FAIL  x\n\n"), (1, "FAIL x")))
        self.assertFalse(pg.matches((0, "FAIL x"), (1, "FAIL x")))
        self.assertFalse(pg.matches(None, (1, "x")))  # timeout


class ScanTest(unittest.TestCase):
    def test_secret_value_in_a_proof_file_is_found(self):
        d = Path(tempfile.mkdtemp())
        (d / "proof").mkdir()
        (d / "proof" / "1.txt").write_text("token ghp_" + "a" * 36 + "\n")
        self.assertTrue(any("GitHub token" in h for h in pg.scan(d)))

    def test_clean_plan_has_no_hits(self):
        d = Path(tempfile.mkdtemp())
        (d / "plan-report.md").write_text("# Plan report\nno secrets here\n")
        self.assertEqual(pg.scan(d), [])

    def test_missing_or_empty_dir_fails_closed(self):
        self.assertTrue(pg.scan(Path("/nonexistent/plan-x")))
        self.assertTrue(pg.scan(Path(tempfile.mkdtemp())))


if __name__ == "__main__":
    unittest.main()
