#!/usr/bin/env python3
"""Open the git worktree a spec-agent run works in, outside the main checkout.

Usage:
  run_worktree.py open <slug> --branch <branch> [--base <base>]

The path is `<main parent>/.brainrc-worktrees/<main name>/<slug>`; the main checkout is the first
entry of `git worktree list`, so this works from inside any worktree. A worktree already on
<branch> at that path is reused; a missing one is pruned and recreated from <branch>. If <branch>
does not exist it is created from --base (intake); without --base (resume) that is an error.
Prints only the absolute path. Exit 0 ok, 1 refused (main has <branch> checked out, branch missing
without --base, path taken by something else), 2 if git fails or the arguments are invalid.
Stdlib only, Python 3.11+.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

SLUG = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


class Refused(Exception):
    pass


def git(*args: str, cwd: str | Path = ".", check: bool = True) -> subprocess.CompletedProcess:
    out = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True)
    if check and out.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {out.stderr.strip()}")
    return out


def worktrees() -> list[tuple[Path, str]]:
    """(path, branch ref or '') for each worktree, main checkout first."""
    entries = []
    for block in git("worktree", "list", "--porcelain").stdout.split("\n\n"):
        fields = dict(line.partition(" ")[::2] for line in block.splitlines())
        if "worktree" in fields:
            entries.append((Path(fields["worktree"]).resolve(), fields.get("branch", "")))
    return entries


def open_worktree(slug: str, branch: str, base: str | None) -> Path:
    entries = worktrees()
    main, main_branch = entries[0]
    ref = f"refs/heads/{branch}"
    if main_branch == ref:
        raise Refused(f"the main checkout has '{branch}' checked out; switch it away first: "
                      f"git -C {main} switch <other branch>")
    path = (main.parent / ".brainrc-worktrees" / main.name).resolve() / slug
    for wt, wt_branch in entries[1:]:
        if wt == path and wt_branch == ref and path.is_dir():
            return path
    if path.exists():
        raise Refused(f"{path} exists but is not a worktree on '{branch}'")
    git("worktree", "prune")
    if git("rev-parse", "--verify", "--quiet", ref, check=False).returncode == 0:
        git("worktree", "add", str(path), branch)
    elif base is None:
        raise Refused(f"branch '{branch}' does not exist and no --base was given")
    else:
        git("worktree", "add", "-b", branch, str(path), base)
    return path


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    o = sub.add_parser("open", help="create or reuse the run's worktree and print its path")
    o.add_argument("slug")
    o.add_argument("--branch", required=True)
    o.add_argument("--base", help="create the branch from this ref if it does not exist")
    args = parser.parse_args(argv)
    if not SLUG.fullmatch(args.slug) or ".." in args.slug:
        parser.error(f"invalid slug {args.slug!r}")
    if args.base is not None and args.base.startswith("-"):
        parser.error(f"invalid base {args.base!r}")
    try:
        if args.branch.startswith("-") or git("check-ref-format", f"refs/heads/{args.branch}",
                                              check=False).returncode != 0:
            parser.error(f"invalid branch {args.branch!r}")
        path = open_worktree(args.slug, args.branch, args.base)
    except Refused as e:
        print(f"ERROR {e}", file=sys.stderr)
        return 1
    except (RuntimeError, OSError) as e:
        print(f"ERROR {e}", file=sys.stderr)
        return 2
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
