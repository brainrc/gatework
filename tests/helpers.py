"""Shared test setup: brainrc core on sys.path, and a throwaway core whose packs.toml enables a
copy of this pack.

Core is the checkout $BRAINRC_CORE names, else a `brainrc` checkout beside this one (CI checks
both out side by side). The validator and the proof guard need it."""
import contextlib
import io
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORE = Path(os.environ.get("BRAINRC_CORE") or ROOT.parent / "brainrc").expanduser().resolve()
if not (CORE / "brainrc" / "__init__.py").is_file():
    raise RuntimeError(f"no brainrc checkout at {CORE}: clone brainrc/brainrc beside this repo, "
                       "or set BRAINRC_CORE to one")
os.environ["BRAINRC_CORE"] = str(CORE)  # proof_guard.py reads core's secret patterns from here
sys.path.insert(0, str(CORE))
import brainrc  # noqa: E402

CORE_FILES = ("rules", "overrides", "harnesses.toml", "VERSION", "CHANGELOG.md")
HARNESS_HOMES = (".claude", ".codex", ".config/opencode", ".gemini/config", ".cursor")
HARNESS_VARS = ("XDG_CONFIG_HOME", "CLAUDE_CONFIG_DIR", "CODEX_HOME")
PACK_IGNORE = shutil.ignore_patterns(".git", "tests", "__pycache__", "*.local.*")


def quiet(fn, *args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = fn(*args)
    return code, buf.getvalue()


def write_skill(pack: Path, name: str, body: str = "", description: str = "A test skill.") -> Path:
    d = pack / "skills" / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(f"---\nname: {name}\ndescription: {description}\n---\n{body}")
    return d


PACK_TOML = """\
name = "acme"
prefix = "acme-"
requires_core = ">=0"

[extensions.gatework]
deliver_checks = ["Deploy plan reviewed"]

[[extensions.gatework.domains]]
files = "`deploy/*.yaml`"
skills = ["acme-deploy"]
reviewer = "brainrc-infra-reviewer"

[[extensions.gatework.intake_context]]
skill = "acme-context"
when = "every ticket"

[extensions.gatework.ticket]
connector = "brainrc-ticket-github"
refs = ["gh:*"]
draft = true
"""


def make_pack(root: Path, pack_toml: str = PACK_TOML) -> Path:
    """A small pack `acme` that extends Gatework: two skills, one agent and the given pack.toml."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "pack.toml").write_text(pack_toml)
    write_skill(root, "acme-context", description="Load Acme's context for a ticket.")
    write_skill(root, "acme-deploy", description="Deploy Acme services.")
    (root / "agents").mkdir(exist_ok=True)
    (root / "agents/acme-reviewer.md").write_text(
        "---\nname: acme-reviewer\ndescription: Reviews Acme changes.\ntools: Read, Grep\n---\nReview.\n")
    return root


class PackCase(unittest.TestCase):
    """brainrc pointed at a temp copy of core (`self.core`) whose packs.toml enables a temp copy of
    this pack (`self.pack`), with a fake HOME and BRAINRC_HOME, so a test never touches anything real."""

    def setUp(self):
        tmp = Path(tempfile.mkdtemp()).resolve()  # macOS: /var is a link to /private/var
        self.addCleanup(shutil.rmtree, tmp)
        self.core, self.pack, self.home = tmp / "core", tmp / "gatework", tmp / "home"
        self.core.mkdir()
        for name in CORE_FILES:
            src = CORE / name
            if src.is_dir():
                shutil.copytree(src, self.core / name, symlinks=True,
                                ignore=shutil.ignore_patterns("*.local.md", "__pycache__"))
            else:
                shutil.copy2(src, self.core / name)
        shutil.copytree(ROOT, self.pack, symlinks=True, ignore=PACK_IGNORE)
        # run_validator: core before 0.7.1 trusts only a pack it bundles; a path pack has to opt in
        self.packs_toml('[gatework]\npath = "{pack}"\nrun_validator = true\n')
        for d in HARNESS_HOMES:
            (self.home / d).mkdir(parents=True)
        self.settings_home = tmp / "brainrc-home"
        old_repo, old_env = brainrc.config.REPO, dict(os.environ)
        brainrc.config.REPO = self.core
        os.environ.update(HOME=str(self.home), BRAINRC_HOME=str(self.settings_home))
        for v in HARNESS_VARS:
            os.environ.pop(v, None)
        self.addCleanup(lambda: (setattr(brainrc.config, "REPO", old_repo), os.environ.clear(),
                                 os.environ.update(old_env)))

    def packs_toml(self, text: str) -> None:
        """Core's packs.toml; `{pack}` is this pack's copy."""
        (self.core / "packs.toml").write_text(text.replace("{pack}", str(self.pack)))

    def local_packs(self, text: str) -> None:
        (self.core / "packs.local.toml").write_text(text)

    def acme(self, pack_toml: str = PACK_TOML) -> Path:
        """Enable a pack `acme` that extends Gatework, beside this one. Tests validate it as an
        enabled pack rather than with `validate --pack`, which needs Gatework to be a default pack."""
        pack = make_pack(self.pack.parent / "acme", pack_toml)
        self.local_packs(f'[acme]\npath = "{pack}"\n')
        return pack

    def validate(self) -> tuple[int, str]:
        return quiet(brainrc.cmd_validate)
