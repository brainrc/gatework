#!/usr/bin/env python3
"""Planning mode (/plan): gate the proof commands the engine re-runs, and scan plan files for secrets.

Usage:
  proof_guard.py check <command> [--root <worktree>]   exit 0 allowed, 1 denied (reason on stderr)
  proof_guard.py run <command> [--root <worktree>]     re-run an allowed command; prints exit code then output
  proof_guard.py scan <specs/plan-<slug>>               exit 0 clean, 1 secret values found (names only)

A proof command is untrusted: a researcher wrote it after reading untrusted content. It may only
read, as an argv list (never a shell), inside the worktree, with no network and no URL. `run`
uses a scrubbed environment, a timeout, and an output cap. Stdlib only, Python 3.11+.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

READ_ONLY = {"cat", "head", "tail", "wc", "ls", "grep", "rg", "diff", "test"}  # not find: -exec, -delete
GIT_READ = {"log", "show", "diff", "status", "grep", "blame", "ls-files", "rev-parse"}
TEST_RUNNERS = {("-m", "unittest"), ("-m", "pytest")}
SHELL_CHARS = re.compile(r"[;&|`$<>\n]")
URL = re.compile(r"(?i)\b[a-z][a-z0-9+.-]*://")
TIMEOUT, OUTPUT_CAP = 60, 64_000


def _guard_secrets():
    path = Path(__file__).resolve().parents[3] / "overrides/claude/hooks/guard_secrets.py"
    spec = importlib.util.spec_from_file_location("guard_secrets", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check(command: str, root: Path) -> str | None:
    """Why `command` may not be run as proof, or None when it may."""
    try:
        argv = shlex.split(command, posix=True)
    except ValueError:
        return "does not parse as an argv list"
    if not argv:
        return "empty command"
    unquoted = re.sub(r"'[^']*'|\"[^\"]*\"", "", command)
    if SHELL_CHARS.search(unquoted):
        return "shell syntax (pipe, ;, &, $, redirect) is not allowed"
    if any(URL.search(a) for a in argv):
        return "URLs are not allowed"
    prog, args = Path(argv[0]).name, argv[1:]
    if prog in {"python", "python3"}:
        if tuple(args[:2]) not in TEST_RUNNERS:
            return "python only as the project's test runner (-m unittest / -m pytest)"
    elif prog == "git":
        if not args or args[0] not in GIT_READ:
            return f"git {args[0] if args else ''} is not read-only"
    elif prog not in READ_ONLY:
        return f"`{prog}` is not an allowed read-only command"
    secrets = _guard_secrets()
    for a in args:
        if a.startswith("--output"):
            return "--output writes a file"
        if a.startswith("-"):
            continue
        if a.startswith("~") or secrets.is_secret_file(a):
            return f"`{a}` is a secret or home path"
        p = Path(a)
        if p.is_absolute() or ".." in p.parts:
            if not (root / p).resolve().is_relative_to(root):
                return f"`{a}` is outside the worktree"
    return None


def run(command: str, root: Path, timeout: int = TIMEOUT) -> tuple[int, str] | None:
    """Re-run an allowed command; (exit code, capped output), or None on timeout."""
    reason = check(command, root)
    if reason:
        raise ValueError(reason)
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(root), "LANG": "C.UTF-8"}
    try:
        proc = subprocess.run(shlex.split(command), cwd=root, env=env, capture_output=True,
                              text=True, timeout=timeout, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return None
    return proc.returncode, (proc.stdout + proc.stderr)[:OUTPUT_CAP]


def matches(got: tuple[int, str] | None, recorded: tuple[int, str]) -> bool:
    """Same exit code and the same output once whitespace is normalized; a timeout never matches."""
    norm = lambda s: re.sub(r"\s+", " ", s).strip()
    return got is not None and got[0] == recorded[0] and norm(got[1]) == norm(recorded[1])


def scan(plan_dir: Path) -> list[str]:
    """Names of secret patterns found in any plan file (proof output included); values never shown."""
    patterns = _guard_secrets().SECRET_PATTERNS
    hits = []
    for path in sorted(p for p in plan_dir.rglob("*") if p.is_file()):
        text = path.read_text(errors="replace")
        hits += [f"{path.relative_to(plan_dir)}: {name}" for name, rx in patterns if rx.search(text)]
    return hits


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("check", "run"):
        p = sub.add_parser(name)
        p.add_argument("command")
        p.add_argument("--root", default=".")
    sub.add_parser("scan").add_argument("plan_dir")
    a = ap.parse_args()
    if a.cmd == "scan":
        hits = scan(Path(a.plan_dir))
        for h in hits:
            print(h)
        return 1 if hits else 0
    root = Path(a.root).resolve()
    reason = check(a.command, root)
    if reason:
        print(f"DENY {reason}", file=sys.stderr)
        return 1
    if a.cmd == "check":
        return 0
    got = run(a.command, root)
    print("timeout" if got is None else f"{got[0]}\n{got[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
