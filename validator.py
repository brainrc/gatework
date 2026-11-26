"""Gatework's validator plugin. brainrc core loads it through pack.toml `validator` (brainrc's
docs/packs.md, Validator plugins) to check and render what only Gatework reads: each pack's
[extensions.gatework], the ticket connectors, the roles link and the skill and agent names."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path, PurePath

from brainrc.sources import markdown_files, skills

NAMESPACE = "gatework"
EXTENSION_KEYS = frozenset({"domains", "intake_context", "ticket", "deliver_checks", "reviewers"})
# top-level [extensions] keys, before the split: the keys from then, never a newer one
LEGACY_KEYS = frozenset({"domains", "intake_context", "ticket", "deliver_checks"})
LEGACY_NAMESPACES = ("spec-agent",)
# Core's warning for the legacy tables above says they are read "until" this. They were due to go
# in 0.8.0 with the aliases; they stay a minor release longer, like the old names in a pack's
# table below, since core would otherwise drop such a table with only a warning.
REMOVED_IN = "Gatework 0.9.0"

# The unprefixed names Gatework shipped as deprecated aliases until 0.8.0, and their new names.
# 0.8.0 stopped installing them. A pack's [extensions.gatework] that still names one is read as the
# new name, with a warning, until REMOVED_IN.
RENAMED_SKILLS = {"spec-agent": "brainrc-gatework",
                  **{f"spec-{n}": f"brainrc-gatework-{n}" for n in ("approve", "resume", "status")},
                  **{n: f"brainrc-{n}" for n in (
                      "ci-pipelines", "commit-message", "containers", "db-migrations", "doc-types", "gitops",
                      "go-service", "kubernetes", "observability", "pr-description", "project-commands",
                      "runbook", "scripting", "security-checklist", "ticket-github", "ticket-jira",
                      "ticket-local", "unslop")}}
RENAMED_AGENTS = {n: f"brainrc-{n}" for n in (
    "analyst", "architect", "code-reviewer", "doc-writer", "implementer", "infra-reviewer",
    "researcher", "security-reviewer", "test-writer", "verifier")}

GATEWORK_AGENTS = frozenset(RENAMED_AGENTS.values())  # tests/test_validator.py: equal to agents/*.md

ROLES = Path("skills/brainrc-gatework/roles")  # a symlink to ../../agents
ROLES_FIX = ("enable symlinks (brainrc's docs/install.md, Platforms), then restore it in the pack's "
             "clone with `git checkout -- skills/brainrc-gatework/roles`")
CONNECTOR = re.compile(r"^(brainrc-)?ticket-")
REQUIRED_CONNECTOR_OPS = ("fetch", "comment", "transition", "link_pr")  # references/connectors.md
H2 = re.compile(r"^## +(.+)$", re.M)


def check_extensions(ext: dict, where: str, skill_names: set[str], agent_names: set[str]) -> list[str]:
    errors = [f"{where}: unknown extension `{k}`" for k in sorted(set(ext) - EXTENSION_KEYS)]
    ext = _current(ext)  # an old name is checked as its new one; warn_extensions names it
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
    errors += _reviewer_errors(ext.get("reviewers", []), where, skill_names, agent_names)
    return errors


def _reviewer_errors(reviewers, where: str, skill_names: set[str], agent_names: set[str]) -> list[str]:
    """[[extensions.gatework.reviewers]]: a pack's agent that reviews beside Gatework's (#143)."""
    if not isinstance(reviewers, list) or not all(isinstance(r, dict) for r in reviewers):
        return [f"{where}: reviewers must be a list of tables ([[extensions.gatework.reviewers]])"]
    errors = []
    for i, r in enumerate(reviewers):
        at = f"{where}: reviewers[{i}]"
        errors += [f"{at}: unknown key `{k}` (keys: name, domains, veto)"
                   for k in sorted(set(r) - {"name", "domains", "veto"})]
        name = r.get("name")
        if not isinstance(name, str) or not name:
            errors.append(f"{at}: needs `name`, the pack agent that reviews")
        elif name in GATEWORK_AGENTS or name in RENAMED_AGENTS:
            errors.append(f"{at}: `{name}` is one of Gatework's roles, which run already; a pack "
                          "reviewer adds its own agent and never replaces one of Gatework's")
        elif name not in agent_names:
            errors.append(f"{at}: names unknown agent `{name}`")
        domains = r.get("domains", [])
        if not isinstance(domains, list) or not all(isinstance(d, str) for d in domains):
            errors.append(f"{at}: domains must be a list of domain skill names")
        else:
            errors += [f"{at}: domains names unknown skill `{d}`" for d in domains
                       if RENAMED_SKILLS.get(d, d) not in skill_names]
        if not isinstance(r.get("veto", False), bool):
            errors.append(f"{at}: veto must be true or false")
    return errors


def warn_extensions(ext: dict, where: str) -> list[str]:
    """A pack naming a skill or reviewer by its old name: read as the new name, until REMOVED_IN."""
    refs = [(n, RENAMED_SKILLS) for n in _skill_refs(ext)] + [(d.get("reviewer"), RENAMED_AGENTS)
                                                             for d in ext.get("domains", [])]
    return [f"{where}: `{n}` was renamed `{table[n]}` and Gatework 0.8.0 no longer installs it; "
            f"use the new name (the old one is read until {REMOVED_IN})"
            for n, table in refs if n in table]


def _skill_refs(ext: dict) -> list:
    reviewers = ext.get("reviewers") if isinstance(ext.get("reviewers"), list) else []
    return ([s for d in ext.get("domains", []) for s in d.get("skills", [])]
            + [s for r in reviewers if isinstance(r, dict) and isinstance(r.get("domains"), list)
               for s in r["domains"]]
            + [i.get("skill") for i in ext.get("intake_context", [])]
            + ([ext["ticket"].get("connector")] if isinstance(ext.get("ticket"), dict) else []))


def _current(ext: dict) -> dict:
    """The table with each old skill and reviewer name replaced by its new one."""
    skill = lambda n: RENAMED_SKILLS.get(n, n)  # noqa: E731
    ext = dict(ext)
    if "domains" in ext:
        ext["domains"] = [{**d, "skills": [skill(s) for s in d.get("skills", [])],
                           **({"reviewer": RENAMED_AGENTS.get(d["reviewer"], d["reviewer"])} if d.get("reviewer") else {})}
                          for d in ext["domains"]]
    if "intake_context" in ext:
        ext["intake_context"] = [{**i, "skill": skill(i.get("skill"))} for i in ext["intake_context"]]
    if isinstance(ext.get("ticket"), dict):
        ext["ticket"] = {**ext["ticket"], "connector": skill(ext["ticket"].get("connector"))}
    if isinstance(ext.get("reviewers"), list):
        ext["reviewers"] = [{**r, "domains": [skill(d) for d in r.get("domains", [])]}
                            if isinstance(r, dict) and isinstance(r.get("domains"), list) else r
                            for r in ext["reviewers"]]
    return ext


def _renamed(name: str, renamed: dict[str, str]) -> str:
    """The hint for one of Gatework's own items still under its old name."""
    return f"; it was renamed `{renamed[name]}` in Gatework 0.8.0" if name in renamed else ""


def check(me, srcs) -> list[str]:
    errors = [f"{roles}; {ROLES_FIX}"] if (roles := roles_error(me)) else []
    return errors + check_connectors(me, srcs) + check_skills(me) + check_agents(me)


def doctor(me) -> list[tuple[str, str, str]]:
    return [("FAIL", roles, ROLES_FIX)] if (roles := roles_error(me)) else []


def links_to_agents(target: str) -> bool:
    """Git on Windows stores the link as ..\\..\\agents; PurePath reads either separator there."""
    return PurePath(target) == PurePath("../../agents")


def roles_error(me) -> str | None:
    """Gatework reads its role files through roles/ -> ../../agents. A checkout without symlink
    support writes a plain file instead, and every role link breaks."""
    path = me.root / ROLES
    if path.is_symlink() and links_to_agents(os.readlink(path)):
        return None
    if not path.is_symlink() and not path.exists():
        return f"{me.rel(path)} is missing"
    found = f"a link to {os.readlink(path)}" if path.is_symlink() else "a directory" if path.is_dir() else "a plain file"
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
    names = {RENAMED_SKILLS.get(n, n) for n in names if n}
    errors = []
    for name in sorted(n for n in names if n in found):
        src, skill = found[name]
        headings = " ".join(H2.findall((skill / "SKILL.md").read_text()))
        missing = [op for op in REQUIRED_CONNECTOR_OPS if not re.search(rf"\b{op}\b", headings)]
        if missing:
            errors.append(f"{src.rel(skill)}/SKILL.md: connector missing `##` sections for "
                          f"{', '.join(missing)} (see the connector contract, references/connectors.md)")
    return errors


def check_skills(me) -> list[str]:
    """Every Gatework skill is `brainrc-*`: the unprefixed aliases went in 0.8.0."""
    return [f"{me.rel(s)}: Gatework skill names start with `brainrc-`{_renamed(s.name, RENAMED_SKILLS)}"
            for s in skills(me) if not s.name.startswith("brainrc-")]


def check_agents(me) -> list[str]:
    """Every Gatework agent is `brainrc-*`: the unprefixed aliases went in 0.8.0."""
    return [f"{me.rel(f)}: core agent names start with `brainrc-`{_renamed(f.stem, RENAMED_AGENTS)}"
            for f in markdown_files("agents", me) if not f.stem.startswith("brainrc-")]


def render_extensions(tables: list[tuple[str, dict]]) -> str:
    """The pack extension points Gatework reads at intake, plan, and deliver."""
    out = ["<!-- GENERATED by brainrc from each pack's pack.toml. Edit the pack, not this file. -->",
           "", "# Pack extensions", ""]
    if not tables:
        out.append("No packs enabled. Use only the built-in tables in SKILL.md.")
        return "\n".join(out) + "\n"
    out.append("Enabled packs: " + ", ".join(f"`{p}`" for p, _ in tables) + ".")
    ext = {p: _current(e) for p, e in tables}

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

    reviewers = [(p, r) for p, e in ext.items() for r in e.get("reviewers", []) if isinstance(r, dict)]
    if reviewers:
        out += ["", "## Reviewers", "",
                "Pack reviewers run beside Gatework's reviewers, never in place of one: in batched",
                "review and for `review: each` tasks, when the run's domains include one of theirs (no",
                "domains: every run). Veto `yes`: CRITICAL/HIGH findings get fix tasks, as Gatework's do.",
                "Veto `no`: list its findings at the Deliver gate as advisory. Subagent mode launches it",
                "by name; inline and fallback read its file from Pack roles below, with Review isolation.", "",
                "| Reviewer | Runs when the run touches | Veto | Pack |", "|---|---|---|---|"]
        out += [f"| {r.get('name')} | {', '.join(r.get('domains') or []) or 'every run'} | "
                f"{'yes' if r.get('veto') else 'no'} | {p} |" for p, r in reviewers]

    checks = [(p, c) for p, e in ext.items() for c in e.get("deliver_checks", [])]
    if checks:
        out += ["", "## Deliver checks", "",
                "List these in the Deliver gate, each marked done, not applicable, or not run.",
                "Never mark a check done that did not run.", ""]
        out += [f"- ({p}) {c}" for p, c in checks]
    return "\n".join(out).rstrip() + "\n"
