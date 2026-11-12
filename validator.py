"""Gatework's validator plugin. brainrc core loads it through pack.toml `validator` (docs/packs.md,
Validator plugins) to check and render what only Gatework reads: each pack's [extensions.gatework],
the ticket connectors, the roles link and the deprecated agent aliases."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from brainrc import config
from brainrc.naming import AGENT_ALIAS_REMOVED_IN, AGENT_ALIASES
from brainrc.sources import frontmatter, markdown_files, skills

NAMESPACE = "gatework"
EXTENSION_KEYS = frozenset({"domains", "intake_context", "ticket", "deliver_checks"})
LEGACY_KEYS = EXTENSION_KEYS     # top-level [extensions] keys, before the split
LEGACY_NAMESPACES = ("spec-agent",)
REMOVED_IN = "0.8.0"

ROLES = Path("skills/spec-agent/roles")  # a symlink to ../../agents; a wheel holds copies
ROLES_FIX = ("enable symlinks (docs/install.md, Platforms), then restore it with "
             "`git checkout -- packs/gatework/skills/spec-agent/roles`")
CONNECTOR = re.compile(r"^(brainrc-)?ticket-")
REQUIRED_CONNECTOR_OPS = ("fetch", "comment", "transition", "link_pr")  # references/connectors.md
H2 = re.compile(r"^## +(.+)$", re.M)


def check_extensions(ext: dict, where: str, skill_names: set[str], agent_names: set[str]) -> list[str]:
    errors = [f"{where}: unknown extension `{k}`" for k in sorted(set(ext) - EXTENSION_KEYS)]
    for d in ext.get("domains", []):
        if not d.get("files") or not d.get("skills"):
            errors.append(f"{where}: each extensions.domains entry needs `files` and `skills`")
        errors += [f"{where}: domains names unknown skill `{s}`" for s in d.get("skills", []) if s not in skill_names]
        if d.get("reviewer") and d["reviewer"] not in agent_names:
            errors.append(f"{where}: domains names unknown reviewer `{d['reviewer']}`")
    for i in ext.get("intake_context", []):
        if i.get("skill") not in skill_names:
            errors.append(f"{where}: intake_context names unknown skill `{i.get('skill')}`")
    ticket = ext.get("ticket")
    if ticket is not None:
        if ticket.get("connector") not in skill_names:
            errors.append(f"{where}: ticket.connector names unknown skill `{ticket.get('connector')}`")
        if not ticket.get("refs"):
            errors.append(f"{where}: ticket needs `refs` (the ticket refs it handles, e.g. \"PROJ-*\")")
    if not all(isinstance(c, str) for c in ext.get("deliver_checks", [])):
        errors.append(f"{where}: deliver_checks must be a list of strings")
    return errors


def check(me, srcs) -> list[str]:
    errors = [f"{roles}; {ROLES_FIX}"] if (roles := roles_error(me)) else []
    return errors + check_connectors(me, srcs) + check_agents(me)


def doctor(me) -> list[tuple[str, str, str]]:
    return [("FAIL", roles, ROLES_FIX)] if (roles := roles_error(me)) else []


def roles_error(me) -> str | None:
    """spec-agent reads its role files through roles/ -> ../../agents. A checkout without symlink
    support writes a plain file instead, and every role link breaks."""
    path = me.root / ROLES
    if config.installed():
        return None  # a wheel stores the link's files as copies
    if path.is_symlink() and os.readlink(path) == "../../agents":
        return None
    if not path.is_symlink() and not path.exists():
        return f"{me.rel(path)} is missing"
    found = f"a link to {os.readlink(path)}" if path.is_symlink() else "a plain file"
    return f"{me.rel(path)} must be a symlink to ../../agents but is {found} (cloned without symlink support?)"


def _table(src) -> dict:
    ext = src.meta.get("extensions", {})
    found = {k: v for k, v in ext.items() if k in LEGACY_KEYS}
    for ns in (*LEGACY_NAMESPACES, NAMESPACE):
        found.update(ext.get(ns) or {})
    return found


def check_connectors(me, srcs) -> list[str]:
    """Gatework's `ticket-*` skills and each pack's ticket connector need a `##` heading naming
    each required operation. One heading may name several (`## comment / transition / link_pr`)."""
    found = {s.name: (src, s) for src in srcs for s in skills(src)}
    names = {n for n, (src, _) in found.items() if src.root == me.root and CONNECTOR.match(n)}
    names |= {_table(src).get("ticket", {}).get("connector") for src in srcs}
    errors = []
    for name in sorted(n for n in names if n in found):
        src, skill = found[name]
        headings = " ".join(H2.findall((skill / "SKILL.md").read_text()))
        missing = [op for op in REQUIRED_CONNECTOR_OPS if not re.search(rf"\b{op}\b", headings)]
        if missing:
            errors.append(f"{src.rel(skill)}/SKILL.md: connector missing `##` sections for "
                          f"{', '.join(missing)} (see the connector contract, references/connectors.md)")
    return errors


def check_agents(me) -> list[str]:
    """Every agent is `brainrc-*` or a declared alias that runs exactly as its target until removal."""
    errors = [f"{me.rel(f)}: core agent names start with `brainrc-`"
              for f in markdown_files("agents", me)
              if not f.stem.startswith("brainrc-") and f.stem not in AGENT_ALIASES]
    for old, new in AGENT_ALIASES.items():
        path, target = me.root / "agents" / f"{old}.md", me.root / "agents" / f"{new}.md"
        rel = me.rel(path)
        if not path.is_file():
            errors.append(f"{rel}: deprecated alias for `{new}` is missing (keep it until {AGENT_ALIAS_REMOVED_IN})")
            continue
        if not target.is_file():
            errors.append(f"{rel}: alias target `{new}` is missing")
            continue
        meta, want = frontmatter(path), frontmatter(target)
        if not meta.get("description", "").lower().startswith("deprecated"):
            errors.append(f"{rel}: alias `description` must start with `Deprecated`")
        errors += [f"{rel}: alias `{key}` must match `{new}` so it runs with the same access"
                   for key in ("tools", "model") if meta.get(key) != want.get(key)]
        body = path.read_text().split("\n---\n", 1)[-1]
        # A subagent can't tell where its own file is, so the alias carries its target's instructions.
        if not body.endswith(target.read_text().split("\n---\n", 1)[-1]):
            errors.append(f"{rel}: alias body must end with `{new}`'s instructions, unchanged")
        if f"`{new}`" not in body:
            errors.append(f"{rel}: alias body must name `{new}`")
        if AGENT_ALIAS_REMOVED_IN not in body:
            errors.append(f"{rel}: alias body must name the removal release {AGENT_ALIAS_REMOVED_IN}")
    return errors


def render_extensions(tables: list[tuple[str, dict]]) -> str:
    """The pack extension points spec-agent reads at intake, plan, and deliver."""
    out = ["<!-- GENERATED by brainrc from each pack's pack.toml. Edit the pack, not this file. -->",
           "", "# Pack extensions", ""]
    if not tables:
        out.append("No packs enabled. Use only the built-in tables in SKILL.md.")
        return "\n".join(out) + "\n"
    out.append("Enabled packs: " + ", ".join(f"`{p}`" for p, _ in tables) + ".")
    ext = dict(tables)

    rows = [(p, d) for p, e in ext.items() for d in e.get("domains", [])]
    if rows:
        out += ["", "## Domains", "",
                "Extra rows for the Domains table. When both match, use the pack row's skills in",
                "addition to the built-in row's.", "",
                "| Files | Skills | Extra reviewer | Pack |", "|---|---|---|---|"]
        for pack, d in rows:
            out.append(f"| {d.get('files', '')} | {', '.join(d.get('skills', []))} | "
                       f"{d.get('reviewer', '—')} | {pack} |")

    intake = [(p, i) for p, e in ext.items() for i in e.get("intake_context", [])]
    if intake:
        out += ["", "## Intake context", "",
                "After writing `ticket.md` and before sizing, run each skill below and append its",
                "summary to `ticket.md` under `## Context` (outside the untrusted-content fence).", ""]
        out += [f"- `{i['skill']}` ({p}): {i.get('when', 'every ticket')}" for p, i in intake]

    tickets = [(p, e["ticket"]) for p, e in ext.items() if "ticket" in e]
    if tickets:
        out += ["", "## Ticket connectors", "",
                "Use the named connector for refs that match `refs`, passing it this config.", ""]
        for pack, t in tickets:
            out += [f"### {pack}", "", "```json", json.dumps(t, indent=2, sort_keys=True), "```", ""]

    checks = [(p, c) for p, e in ext.items() for c in e.get("deliver_checks", [])]
    if checks:
        out += ["", "## Deliver checks", "",
                "List these in the Deliver gate, each marked done, not applicable, or not run.",
                "Never mark a check done that did not run.", ""]
        out += [f"- ({p}) {c}" for p, c in checks]
    return "\n".join(out).rstrip() + "\n"
