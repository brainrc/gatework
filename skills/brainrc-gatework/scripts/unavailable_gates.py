#!/usr/bin/env python3
"""Tripwire for a pack's unavailable gates: a planned check that doesn't run yet is never reported
as passing.

Usage:
  unavailable_gates.py check <specs/<slug>> <gate> [<gate> ...]

The gates are those `extensions.md` lists under Unavailable gates (a pack's
`unavailable_gates`). Exit 1, naming file and line, when `verify.md` doesn't list a gate as
`not run`, or when any line of `verify.md`, `pr-body.md` or `ticket-comment.md` that names a gate
also claims a pass (pass, ok, green, done, a check mark). Report each gate on a line of its own.
Exit 0 when clean. Stdlib only, Python 3.11+.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

FILES = ("verify.md", "pr-body.md", "ticket-comment.md")
PASS = re.compile(r"(?<![\w-])(pass(es|ed|ing)?|ok|green|succeeded|success(ful)?|done)(?![\w-])|[✅✓✔]", re.I)
NOT_RUN = re.compile(r"\bnot run\b", re.I)


def names(line: str, gate: str) -> bool:
    return re.search(rf"(?<![\w-]){re.escape(gate)}(?![\w-])", line, re.I) is not None


def check(run: Path, gates: list[str]) -> list[str]:
    hits = []
    for name in FILES:
        path = run / name
        if not path.is_file():
            continue
        for n, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for gate in gates:
                if names(line, gate) and PASS.search(line):
                    hits.append(f"{path}:{n}: `{gate}` is unavailable, but this line claims a pass; "
                                "write `not run, unavailable` on a line of its own")
    verify = run / "verify.md"
    text = verify.read_text(encoding="utf-8", errors="replace") if verify.is_file() else ""
    for gate in gates:
        if not any(names(line, gate) and NOT_RUN.search(line) for line in text.splitlines()):
            hits.append(f"{verify}: doesn't list `{gate}` as `not run, unavailable` under Checks")
    return hits


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("check",))
    parser.add_argument("run", type=Path)
    parser.add_argument("gates", nargs="+")
    args = parser.parse_args(argv)
    hits = check(args.run, [g.strip() for g in args.gates if g.strip()])
    for h in hits:
        print(h)
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
