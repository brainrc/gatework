#!/usr/bin/env python3
"""Planning mode (/plan): gate the proof commands the engine re-runs, and scan plan files for secrets.

Usage:
  proof_guard.py check <command> [--root <worktree>]   exit 0 allowed, 1 denied (reason on stderr)
  proof_guard.py run <command> [--root <worktree>]     re-run an allowed command; prints exit code then output
  proof_guard.py scan <specs/plan-<slug>>               exit 0 clean, 1 on any hit (names only, never values)

A proof command is untrusted: a researcher wrote it after reading untrusted content. Only a
narrow allowlist is re-run: grep/rg/cat/head/tail/wc/ls with fixed flags on named files, and
git log/show with fixed flags. Every path must resolve (symlinks followed) inside the worktree
and not be a secret file. Test runners are never re-run. `run` uses argv (no shell), a pinned
environment, a process-group timeout and an output cap. Stdlib only, Python 3.11+.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import re
import shlex
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

# program -> (allowed flags, flags that take a value, path args must be regular files)
PROGRAMS = {
    "cat": (set(), set(), True),
    "head": ({"-n"}, {"-n"}, True),
    "tail": ({"-n"}, {"-n"}, True),
    "wc": ({"-l", "-c", "-w"}, set(), True),
    "ls": ({"-l", "-a", "-1"}, set(), False),
    "grep": ({"-n", "-i", "-c", "-F", "-E", "-w", "-v", "-o"}, set(), True),
    "rg": ({"-n", "-i", "-c", "-F", "-w", "-v", "-o", "--no-heading"}, set(), True),
}
PATTERN_FIRST = {"grep", "rg"}
GIT = {"log": {"--oneline", "--stat", "--name-only"}, "show": {"--stat", "--oneline", "--name-only", "--no-patch"}}
REV = re.compile(r"^[A-Za-z0-9_.~^/-]+$")
SHELL_CHARS = re.compile(r"[;&|`$<>\n\\]")
URL = re.compile(r"(?i)\b[a-z][a-z0-9+.-]*://")
TIMEOUT, OUTPUT_CAP, SCAN_CAP, MAX_LINES = 60, 64_000, 1_000_000, 10_000


def _guard_secrets():
    path = Path(__file__).resolve().parents[3] / "overrides/claude/hooks/guard_secrets.py"
    if not path.is_file():
        raise RuntimeError(f"secret patterns not found at {path}")
    spec = importlib.util.spec_from_file_location("guard_secrets", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _path(arg: str, root: Path, regular_file: bool, secrets) -> str | None:
    """Why this path arg is refused, or None."""
    if not arg or arg.startswith(("~", "/")) or ".." in Path(arg).parts:
        return f"`{arg}` is outside the worktree"
    real = (root / arg).resolve()
    if not real.is_relative_to(root) or not real.exists():
        return f"`{arg}` is missing or resolves outside the worktree"
    rel = str(real.relative_to(root))
    if secrets.is_secret_file(arg) or secrets.is_secret_file(rel):
        return f"`{arg}` is a secret file"
    if regular_file and not real.is_file():
        return f"`{arg}` is not a regular file"
    return None


def check(command: str, root: Path) -> str | None:
    """Why `command` may not be re-run as proof, or None when it may."""
    try:
        argv = shlex.split(command, posix=True)
    except ValueError:
        return "does not parse as an argv list"
    if not argv:
        return "empty command"
    if SHELL_CHARS.search(re.sub(r"'[^']*'|\"[^\"]*\"", "", command)):
        return "shell syntax (pipe, ;, &, $, redirect, backslash) is not allowed"
    if any(URL.search(a) for a in argv):
        return "URLs are not allowed"
    try:
        secrets = _guard_secrets()
    except RuntimeError as e:
        return str(e)
    prog, args = argv[0], argv[1:]
    if prog == "git":
        if not args or args[0] not in GIT:
            return "git only as `git log` or `git show`"
        for a in args[1:]:
            if a.startswith("-"):
                if a not in GIT[args[0]] and not re.fullmatch(r"-[1-9][0-9]?", a):
                    return f"git {args[0]} flag `{a}` is not allowed"
                continue
            rev, _, path = a.partition(":")
            if not REV.match(rev):
                return f"`{a}` is not a plain revision"
            if path and (path.startswith(("/", "~")) or ".." in Path(path).parts or secrets.is_secret_file(path)):
                return f"`{a}` names a secret or outside path"
        return None
    if prog not in PROGRAMS:
        return f"`{prog}` is not in the re-run allowlist (test runners are never re-run)"
    flags, valued, regular = PROGRAMS[prog]
    rest, i = [], 0
    while i < len(args):
        a = args[i]
        if a.startswith("-"):
            if a not in flags:
                return f"{prog} flag `{a}` is not allowed"
            if a in valued:
                i += 1
                if i >= len(args) or not args[i].isdigit() or int(args[i]) > MAX_LINES:
                    return f"{prog} {a} needs a count up to {MAX_LINES}"
        else:
            rest.append(a)
        i += 1
    if prog in PATTERN_FIRST:
        if len(rest) < 2:
            return f"{prog} needs a pattern and at least one named file"
        rest = rest[1:]
    for a in rest:
        reason = _path(a, root, regular, secrets)
        if reason:
            return reason
    if regular and not rest:
        return f"{prog} needs a named file"
    return None


def run(command: str, root: Path, timeout: int = TIMEOUT) -> tuple[int, str] | None:
    """Re-run an allowed command; (exit code, capped output), or None on timeout."""
    reason = check(command, root)
    if reason:
        raise ValueError(reason)
    argv = shlex.split(command)
    if argv[0] == "git":
        argv = ["git", "-c", "core.pager=cat", "-c", "core.fsmonitor=false", "--no-pager",
                argv[1], "--no-ext-diff", "--no-textconv", *argv[2:]]
    env = {"PATH": "/usr/bin:/bin", "HOME": str(root), "LANG": "C.UTF-8", "GIT_CONFIG_GLOBAL": os.devnull,
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0"}
    with tempfile.TemporaryFile() as out:
        proc = subprocess.Popen(argv, cwd=root, env=env, stdout=out, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, start_new_session=True)
        try:
            code = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
            return None
        out.seek(0)
        return code, out.read(OUTPUT_CAP).decode(errors="replace")


def matches(got: tuple[int, str] | None, recorded: tuple[int, str]) -> bool:
    """Same exit code and the same output once whitespace is normalized; a timeout never matches."""
    norm = lambda s: re.sub(r"\s+", " ", s).strip()
    return got is not None and got[0] == recorded[0] and norm(got[1]) == norm(recorded[1])


def scan(plan_dir: Path) -> list[str]:
    """Hits in any plan file (proof output included): pattern names only, never values. Fails closed."""
    if not plan_dir.is_dir():
        return [f"{plan_dir}: missing"]
    files = sorted(p for p in plan_dir.rglob("*") if p.is_file())
    if not files:
        return [f"{plan_dir}: no files"]
    try:
        patterns = _guard_secrets().SECRET_PATTERNS
    except RuntimeError as e:
        return [str(e)]
    hits = []
    for path in files:
        if path.stat().st_size > SCAN_CAP:
            hits.append(f"{path.relative_to(plan_dir)}: too large to scan")
            continue
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
