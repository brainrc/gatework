#!/usr/bin/env python3
"""Check a wave task's worktree before landing: changed paths stay inside the fence.

Usage:
  worktree_fence.py check <worktree> --main <project root> --files <glob> ... [--allow <prefix> ...]

Every changed path in the worktree (tracked or untracked, from `git -C <worktree> status`; a
rename counts both paths) must match one of the task's `--files` globs (`fnmatch`, so `*` also
matches across `/`), and the main tree must have no changes outside the `--allow` prefixes (the
engine passes `specs/<slug>/` for its own state). Prints `STRAY <path>` for a worktree path
outside the fence, `MAIN <path>` for a main-tree change, else `OK`.
Exit 0 clean, 1 on any problem, 2 if git fails. Stdlib only, Python 3.11+.
"""
from __future__ import annotations

import argparse
import fnmatch
import subprocess
import sys


def changed(tree: str) -> list[str]:
    """Paths `git status` reports in `tree`, untracked files listed one by one."""
    out = subprocess.run(["git", "-C", tree, "status", "--porcelain", "-z", "--untracked-files=all"],
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"git -C {tree} status: {out.stderr.strip()}")
    entries, paths = out.stdout.split("\0"), []
    i = 0
    while i < len(entries):
        entry = entries[i]
        if entry:
            paths.append(entry[3:])
            if entry[0] in "RC":  # the source path follows; a rename also deletes it, a copy doesn't
                if entry[0] == "R" and i + 1 < len(entries):
                    paths.append(entries[i + 1])
                i += 1
        i += 1
    return paths


def check(worktree: str, main: str, files: list[str], allow: list[str]) -> list[str]:
    problems = [f"STRAY {p}" for p in changed(worktree) if not any(fnmatch.fnmatch(p, g) for g in files)]
    problems += [f"MAIN {p}" for p in changed(main) if not any(p.startswith(a) for a in allow)]
    return problems


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="check a worktree against its task's files")
    c.add_argument("worktree")
    c.add_argument("--main", required=True, help="the project root (main tree)")
    c.add_argument("--files", nargs="+", required=True, help="the task's files (globs allowed)")
    c.add_argument("--allow", nargs="*", default=[], help="main-tree path prefixes that may change")
    args = parser.parse_args(argv)
    try:
        problems = check(args.worktree, args.main, args.files, args.allow)
    except (RuntimeError, OSError) as e:
        print(f"ERROR {e}", file=sys.stderr)
        return 2
    print("\n".join(problems) if problems else "OK")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
