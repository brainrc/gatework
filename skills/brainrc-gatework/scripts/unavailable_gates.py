#!/usr/bin/env python3
"""Tripwire for a pack's unavailable gates: a planned check that doesn't run yet is never reported
as passing.

Usage:
  unavailable_gates.py check <specs/<slug>> <gate> [<gate> ...]

The gates are those `extensions.md` lists under Unavailable gates (a pack's
`unavailable_gates`). Exit 1, naming file and line, when `verify.md` doesn't list a gate as
`not run, unavailable` in its `## Checks` table, or when any line of `verify.md`, `pr-body.md` or
`ticket-comment.md` that names a gate also claims a pass (pass, ok, green, done, clean, verified,
no findings, a ticked box or a check mark). Report each gate on a line of its own.
Exit 0 when clean. Stdlib only, Python 3.11+.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

FILES = ("verify.md", "pr-body.md", "ticket-comment.md")
PASS = re.compile(r"(?<![\w-])(pass(es|ed|ing)?|ok|green|succeeded|success(ful)?|done|clean|verified"
                  r"|no findings)(?![\w-])|\[[xX]\]|[✅✓✔☑]", re.I)
UNAVAILABLE = re.compile(r"\bnot run, unavailable\b", re.I)


def gate_re(gate: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![\w-]){re.escape(gate)}(?![\w-])", re.I)


def claims_pass(line: str, gate: str) -> bool:
    """The line names the gate and, with the gate's own name taken out, claims a pass."""
    pattern = gate_re(gate)
    return pattern.search(line) is not None and PASS.search(pattern.sub(" ", line)) is not None


def cells(line: str) -> list[str]:
    return [c.strip().strip("`").strip() for c in line.strip().strip("|").split("|")]


def listed(verify: str, gate: str) -> bool:
    """verify.md's `## Checks` table has a row for the gate whose Result says `not run, unavailable`."""
    in_checks, result = False, None
    for line in verify.splitlines():
        if line.startswith("#"):
            in_checks = line.lstrip("#").strip().lower() == "checks"
            result = None
            continue
        if not in_checks or not line.lstrip().startswith("|"):
            continue
        row = cells(line)
        if result is None:  # the header row: find the Result column
            lowered = [c.lower() for c in row]
            result = lowered.index("result") if "result" in lowered else len(row) - 1
            continue
        if row and row[0].lower() == gate.lower() and len(row) > result and UNAVAILABLE.search(row[result]):
            return True
    return False


def check(run: Path, gates: list[str]) -> list[str]:
    hits = []
    for name in FILES:
        path = run / name
        if not path.is_file():
            continue
        for n, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for gate in gates:
                if claims_pass(line, gate):
                    hits.append(f"{path}:{n}: `{gate}` is unavailable, but this line claims a pass; "
                                "write `not run, unavailable` on a line of its own")
    verify = run / "verify.md"
    text = verify.read_text(encoding="utf-8", errors="replace") if verify.is_file() else ""
    for gate in gates:
        if not listed(text, gate):
            hits.append(f"{verify}: `## Checks` has no row for `{gate}` with Result `not run, unavailable`")
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
