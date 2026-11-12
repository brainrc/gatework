#!/usr/bin/env python3
"""Gatework's own release tooling (stdlib only, no brainrc needed).

Usage:
  gatework.py plugin                write the plugin manifests from the pack
  gatework.py check                 manifests current, CHANGELOG matches VERSION, fragments valid
  gatework.py release [--dry-run]   fold changelog.d/ into CHANGELOG.md, bump VERSION, rewrite the manifests
  gatework.py release --notes X.Y.Z print a version's CHANGELOG section (the GitHub Release body)
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAME = "gatework"
AUTHOR = {"name": "brainrc contributors"}
DESCRIPTION = ("Spec-driven work from a ticket to a reviewed PR through approval gates: the spec-agent "
               "engine, its roles, ticket connectors and domain skills. A brainrc pack.")
FRAGMENTS = "changelog.d"
BUMPS = ("patch", "minor", "major")
VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
CHANGELOG_VERSION = re.compile(r"^## (\d+\.\d+\.\d+)\b", re.M)
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n(.*)\Z", re.S)


class Error(Exception):
    pass


def version(root: Path = ROOT) -> tuple[int, ...]:
    text = (root / "VERSION").read_text().strip()
    m = VERSION_RE.match(text)
    if not m:
        raise Error(f"VERSION: `{text}` is not MAJOR.MINOR.PATCH")
    return tuple(int(n) for n in m.groups())


def manifests(root: Path = ROOT) -> dict[str, str]:
    """Claude Code's plugin and marketplace (Codex reads them too), Cursor's plugin, and
    Antigravity's root plugin.json. The repo root is the plugin."""
    v = ".".join(map(str, version(root)))
    agents = sorted(f"./agents/{p.name}" for p in (root / "agents").glob("*.md")
                    if p.name != "README.md" and not p.name.endswith(".local.md"))
    plugin = {"name": NAME, "version": v, "description": DESCRIPTION, "author": AUTHOR, "license": "MIT",
              "skills": "./skills/", "agents": agents}  # one path as a string: the form Codex documents
    market = {"name": NAME, "owner": AUTHOR, "description": DESCRIPTION,
              "plugins": [{"name": NAME, "source": ".", "description": DESCRIPTION, "version": v}]}
    cursor = {"name": NAME, "version": v, "description": DESCRIPTION, "author": AUTHOR, "license": "MIT",
              "skills": "./skills/", "agents": "./agents/"}
    # Antigravity loads skills/ at the root; its schema requires `name` and rejects unknown keys.
    found = {".claude-plugin/plugin.json": plugin, ".claude-plugin/marketplace.json": market,
             ".cursor-plugin/plugin.json": cursor, "plugin.json": {"name": NAME}}
    return {rel: json.dumps(data, indent=2) + "\n" for rel, data in found.items()}


def cmd_plugin(root: Path = ROOT) -> int:
    changed = False
    for rel, text in manifests(root).items():
        path = root / rel
        if path.is_file() and path.read_text() == text:
            continue
        path.parent.mkdir(exist_ok=True)
        path.write_text(text)
        print(f"WROTE {rel}")
        changed = True
    if not changed:
        print("Plugin manifests up to date.")
    return 0


def fragment_paths(root: Path = ROOT) -> list[Path]:
    d = root / FRAGMENTS
    return sorted(p for p in d.glob("*.md") if p.name != "README.md") if d.is_dir() else []


def parse_fragment(text: str, rel: str) -> tuple[str, str]:
    """(bump, entry) from `---\\nbump: patch\\n---\\n- entry`."""
    m = FRONTMATTER.match(text)
    if not m:
        raise Error(f"{rel}: needs frontmatter `---` / `bump: patch|minor|major` / `---`")
    fields = dict(line.split(":", 1) for line in m.group(1).splitlines() if ":" in line)
    bump = fields.get("bump", "").strip()
    if bump not in BUMPS:
        raise Error(f"{rel}: `bump` must be one of {', '.join(BUMPS)}, got `{bump}`")
    entry = m.group(2).strip()
    if not entry.startswith("- "):
        raise Error(f"{rel}: the entry must be a changelog bullet starting with `- `")
    return bump, entry


def next_version(current: tuple[int, ...], bump: str) -> tuple[int, ...]:
    major, minor, patch = current
    if bump == "major":
        return major + 1, 0, 0
    if bump == "minor":
        return major, minor + 1, 0
    return major, minor, patch + 1


def check(root: Path = ROOT) -> list[str]:
    errors = []
    try:
        v = ".".join(map(str, version(root)))
    except (Error, OSError) as e:
        return [str(e)]
    changelog = root / "CHANGELOG.md"
    m = CHANGELOG_VERSION.search(changelog.read_text()) if changelog.is_file() else None
    if not m:
        errors.append(f"CHANGELOG.md: no `## X.Y.Z` heading (expected `## {v}`)")
    elif m.group(1) != v:
        errors.append(f"CHANGELOG.md: newest version {m.group(1)} doesn't match VERSION {v}. "
                      "`gatework.py release` updates both.")
    for p in fragment_paths(root):
        try:
            parse_fragment(p.read_text(), f"{FRAGMENTS}/{p.name}")
        except Error as e:
            errors.append(str(e))
    for rel, text in manifests(root).items():
        path = root / rel
        if not path.is_file():
            errors.append(f"{rel}: missing; run `python3 scripts/gatework.py plugin`")
        elif path.read_text() != text:
            errors.append(f"{rel}: stale (VERSION or agents changed); run `python3 scripts/gatework.py plugin`")
    return errors


def cmd_check(root: Path = ROOT) -> int:
    errors = check(root)
    for e in errors:
        print(f"ERROR {e}")
    print("FAILED" if errors else "OK")
    return 1 if errors else 0


def cmd_release(root: Path = ROOT, dry_run: bool = False) -> int:
    """Bump VERSION by the largest fragment bump, prepend the entries, delete the fragments."""
    paths = fragment_paths(root)
    if not paths:
        print(f"No fragments in {FRAGMENTS}/: nothing to release.")
        return 0
    try:
        parsed = [parse_fragment(p.read_text(), f"{FRAGMENTS}/{p.name}") for p in paths]
        current = version(root)
    except Error as e:
        print(f"ERROR {e}")
        return 1
    bump = max((b for b, _ in parsed), key=BUMPS.index)
    new = ".".join(map(str, next_version(current, bump)))
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    section = f"## {new} ({today})\n\n" + "\n".join(entry for _, entry in parsed) + "\n\n"
    print(f"{'Would release' if dry_run else 'Releasing'} {new} ({bump}) from {len(paths)} fragment(s)")
    if dry_run:
        print(section, end="")
        return 0
    changelog = root / "CHANGELOG.md"
    text = changelog.read_text()
    m = CHANGELOG_VERSION.search(text)
    at = m.start() if m else len(text)
    changelog.write_text(text[:at] + section + text[at:])
    (root / "VERSION").write_text(new + "\n")
    for p in paths:
        p.unlink()
    return cmd_plugin(root)


def release_notes(text: str, v: str) -> str | None:
    """The body of CHANGELOG.md's `## <version>` section, stripped; None if there is none."""
    head = re.search(rf"^## {re.escape(v)}\b.*$", text, re.M)
    if not head:
        return None
    end = CHANGELOG_VERSION.search(text, head.end())
    return text[head.end():end.start() if end else len(text)].strip()


def cmd_notes(v: str, root: Path = ROOT) -> int:
    if not VERSION_RE.match(v):
        print(f"ERROR `{v}` is not MAJOR.MINOR.PATCH")
        return 1
    notes = release_notes((root / "CHANGELOG.md").read_text(), v)
    if notes is None:
        print(f"ERROR CHANGELOG.md has no section for {v}")
        return 1
    print(notes)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="gatework.py", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("plugin", help="write the plugin manifests")
    sub.add_parser("check", help="check the manifests, CHANGELOG.md and changelog.d/")
    p = sub.add_parser("release", help="fold changelog.d/ into CHANGELOG.md and bump VERSION")
    group = p.add_mutually_exclusive_group()
    group.add_argument("--dry-run", action="store_true", help="print the release, write nothing")
    group.add_argument("--notes", metavar="VERSION", help="print that version's CHANGELOG section")
    args = parser.parse_args(argv)
    try:
        if args.cmd == "plugin":
            return cmd_plugin()
        if args.cmd == "check":
            return cmd_check()
        return cmd_notes(args.notes) if args.notes else cmd_release(dry_run=args.dry_run)
    except (Error, OSError) as e:  # an ERROR line and exit 1, never a traceback
        print(f"ERROR {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
