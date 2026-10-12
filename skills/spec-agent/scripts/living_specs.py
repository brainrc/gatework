#!/usr/bin/env python3
"""Apply a spec's `## Requirement changes` delta to the living specs (specs/living/<area>.md).

Usage:
  living_specs.py apply <specs/<slug>/spec.md> [--living DIR] [--run NAME]
  living_specs.py check <specs/<slug>/spec.md> [--living DIR] [--run NAME]

`--living` defaults to the `living/` folder next to the run folder, `--run` to the run folder's
name. Every block is checked before anything is written: an unknown MODIFIED or REMOVED target,
a duplicate ADDED, or a malformed block fails the whole delta. Formats: the spec-agent skill's
templates/spec.md and templates/living.md. Stdlib only, Python 3.9+.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SECTION = "## Requirement changes"
AREA = re.compile(r"^### Area:\s*(.*?)\s*$")
BLOCK = re.compile(r"^#### ([A-Z]+):\s*(.*?)\s*$")
AREA_NAME = re.compile(r"^[a-z0-9][a-z0-9-]*$")
KINDS = ("ADDED", "MODIFIED", "REMOVED")
STAMP = re.compile(r"^_Last changed by .*\._$")


class DeltaError(Exception):
    pass


def parse_delta(text: str) -> list[dict]:
    """[{area, purpose, blocks: [(kind, name, body)]}]; [] for `None`."""
    lines = text.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == SECTION)
    except StopIteration:
        raise DeltaError(f"no `{SECTION}` section (write `None` under it if behavior doesn't change)")
    section = []
    for line in lines[start + 1:]:
        if line.startswith("## "):
            break
        section.append(line.rstrip())
    if [l for l in section if l.strip()] in (["None."], ["None"]):
        return []
    areas, block = [], None
    for line in section:
        if m := AREA.match(line):
            if not AREA_NAME.match(m.group(1)):
                raise DeltaError(f"area `{m.group(1)}`: use lowercase letters, digits and `-`")
            areas.append({"area": m.group(1), "purpose": "", "blocks": []})
            block = None
        elif m := BLOCK.match(line):
            if not areas:
                raise DeltaError(f"`{line}` comes before any `### Area:` line")
            if m.group(1) not in KINDS:
                raise DeltaError(f"`{line}`: the kind must be one of {', '.join(KINDS)}")
            block = [m.group(1), m.group(2), []]
            areas[-1]["blocks"].append(block)
        elif block is not None:
            block[2].append(line)
        elif areas and line.startswith("Purpose:"):
            areas[-1]["purpose"] = line[len("Purpose:"):].strip()
        elif line.strip():
            raise DeltaError(f"unexpected text outside a requirement block: `{line.strip()}`")
    if not areas:
        raise DeltaError(f"`{SECTION}` has no `### Area:` blocks; write `None` if nothing changes")
    for a in areas:
        if not a["blocks"]:
            raise DeltaError(f"area `{a['area']}` has no ADDED, MODIFIED or REMOVED blocks")
        for b in a["blocks"]:
            b[2] = "\n".join(b[2]).strip()
            if not b[1]:
                raise DeltaError(f"area `{a['area']}`: a {b[0]} block has no requirement name")
            if not b[2]:
                raise DeltaError(f"area `{a['area']}`: {b[0]} `{b[1]}` has no text")
            if b[0] == "REMOVED" and not b[2].startswith("Why:"):
                raise DeltaError(f"area `{a['area']}`: REMOVED `{b[1]}` needs a `Why:` line")
    return areas


def read_area(path: Path) -> tuple[str, dict[str, str]]:
    """(purpose, {requirement name: body}) from an area file, in file order."""
    purpose, reqs, name = [], {}, None
    for line in path.read_text().splitlines()[1:]:  # skip the `# <area>` title
        if line.startswith("### "):
            name = line[4:].strip()
            reqs[name] = []
        elif name is None:
            purpose.append(line)
        else:
            reqs[name].append(line)
    return "\n".join(purpose).strip(), {n: "\n".join(b).strip() for n, b in reqs.items()}


def render_area(area: str, purpose: str, reqs: dict[str, str]) -> str:
    parts = [f"# {area}", purpose] + [f"### {n}\n{b}" for n, b in reqs.items()]
    return "\n\n".join(parts) + "\n"


def plan(spec: Path, living: Path, run: str) -> dict[Path, str]:
    """The new text of every area file the delta touches. Raises DeltaError, writes nothing."""
    out = {}
    for a in parse_delta(spec.read_text()):
        path = living / f"{a['area']}.md"
        if path.is_file():
            purpose, reqs = read_area(path)
        elif any(kind != "ADDED" for kind, _, _ in a["blocks"]):
            raise DeltaError(f"area `{a['area']}` doesn't exist yet, so it can only have ADDED blocks")
        elif not a["purpose"]:
            raise DeltaError(f"area `{a['area']}` is new: give it a `Purpose:` line")
        else:
            purpose, reqs = a["purpose"], {}
        for kind, name, body in a["blocks"]:
            where = f"area `{a['area']}`: {kind} `{name}`"
            if kind == "ADDED" and name in reqs:
                raise DeltaError(f"{where} already exists (MODIFY it instead, or was this spec applied already?)")
            if kind != "ADDED" and name not in reqs:
                raise DeltaError(f"{where} isn't in {path.name}; known: {', '.join(reqs) or 'none'}")
            if kind == "REMOVED":
                del reqs[name]
            else:
                reqs[name] = f"{body}\n_Last changed by {run}._"
        out[path] = render_area(a["area"], purpose, reqs)
    return out


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("apply", "check"))
    parser.add_argument("spec", type=Path)
    parser.add_argument("--living", type=Path)
    parser.add_argument("--run")
    args = parser.parse_args(argv)
    spec = args.spec.resolve()
    living = args.living or spec.parent.parent / "living"
    try:
        changes = plan(spec, living, args.run or spec.parent.name)
    except (DeltaError, OSError) as e:
        print(f"ERROR {args.spec}: {e}", file=sys.stderr)
        return 1
    if not changes:
        print("no requirement changes")
        return 0
    for path, text in changes.items():
        if args.command == "apply":
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        print(f"{'updated' if args.command == 'apply' else 'would update'} {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
