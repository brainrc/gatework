#!/usr/bin/env python3
"""Write or read the active-run pointer: the absolute path of the current spec-agent run.

Usage:
  active_run.py write <run-dir>
  active_run.py read

The pointer is one line (path + newline) in `active-run` under the brainrc home
(`$BRAINRC_HOME`, else absolute `$XDG_CONFIG_HOME/brainrc`, else `~/.config/brainrc`), outside any repo. `write` creates the directory if needed and
warns on stderr but exits 0 if it cannot write. `read` prints the pointer's run if it names an
existing directory, else the newest run by state.json mtime among `<cwd>/specs/*/` and the `specs/*/`
of every branch worktree in `git worktree list`, skipping detached ones (cwd only if git fails); with neither it prints
nothing to stdout, notes it on stderr, and exits 1. Stdlib only, Python 3.11+.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def _expand(value: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(value)))


def pointer_file() -> Path:
    """Same resolution as settings_home() in brainrc/config.py (skills ship without the package):
    BRAINRC_HOME, absolute $XDG_CONFIG_HOME/brainrc, or ~/.config/brainrc. Silent."""
    if os.environ.get("BRAINRC_HOME"):
        return _expand(os.environ["BRAINRC_HOME"]) / "active-run"
    xdg = os.environ.get("XDG_CONFIG_HOME", "")
    home = Path(xdg) / "brainrc" if xdg and os.path.isabs(xdg) else Path.home() / ".config" / "brainrc"
    return home / "active-run"


def write(run_dir: str) -> int:
    try:
        target = pointer_file()
        target.parent.mkdir(parents=True, exist_ok=True)
        # temp file + replace: a concurrent reader never sees a partial line
        fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=".active-run.")
        try:
            with os.fdopen(fd, "w") as f:
                f.write(f"{Path(run_dir).resolve()}\n")
            os.replace(tmp, target)
        except BaseException:
            os.unlink(tmp)
            raise
    except (OSError, RuntimeError) as e:  # RuntimeError: Path.home() with no HOME or passwd entry
        print(f"WARN: could not write the active-run pointer: {e}", file=sys.stderr)
    return 0


def _roots() -> list[Path]:
    """cwd plus every branch worktree from `git worktree list --porcelain`, deduped by resolved
    path. Detached worktrees (task and verify checkouts) are skipped: their committed state.json
    carries a checkout mtime. Any git failure (missing, not a repo, timeout) leaves cwd only."""
    roots = [Path.cwd().resolve()]
    try:
        out = subprocess.run(["git", "worktree", "list", "--porcelain"], capture_output=True,
                             text=True, timeout=10, check=True).stdout
    except (OSError, subprocess.SubprocessError):
        return roots
    for entry in out.split("\n\n"):  # one blank-line-separated block per worktree
        lines = entry.splitlines()
        if "detached" in lines:
            continue
        for line in lines:
            if line.startswith("worktree "):
                path = Path(line[len("worktree "):]).resolve()
                if path not in roots:
                    roots.append(path)
    return roots


def read() -> int:
    try:
        line = pointer_file().read_text().strip()
    except (OSError, RuntimeError, UnicodeDecodeError):
        line = ""
    if line and Path(line).is_dir():
        print(line)
        return 0
    states = []
    for root in _roots():
        for p in (root / "specs").glob("*/state.json"):
            try:
                states.append((p.stat().st_mtime, p))
            except OSError:  # vanished or broken symlink
                continue
    if states:
        print(max(states, key=lambda s: s[0])[1].parent.resolve())
        return 0
    print("no active run: no pointer and no specs/*/state.json in the current directory or its worktrees",
          file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("write", help="record a run directory").add_argument("run_dir")
    sub.add_parser("read", help="print the active run directory")
    args = parser.parse_args(argv)
    return write(args.run_dir) if args.cmd == "write" else read()


if __name__ == "__main__":
    sys.exit(main())
