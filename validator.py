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
EXTENSION_KEYS = frozenset({"domains", "intake_context", "ticket", "deliver_checks", "reviewers", "mode",
                            "forbid_writing_subagents", "unavailable_gates"})
MODES = ("auto", "inline", "subagent")  # references/efficiency.md, Execution mode
GATE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")  # an unavailable gate's name: one shell word
# Words unavailable_gates.py reads as a pass claim, so never a gate's name.
PASS_WORDS = frozenset({"pass", "passes", "passed", "passing", "ok", "green", "succeeded", "success",
                        "successful", "done", "clean", "verified"})
# The only keys Gatework reads from this machine's table (brainrc.local.toml, through core 0.8.30+).
MACHINE_KEYS = frozenset({"mode", "forbid_writing_subagents"})
# The skills in SKILL.md's Domains table: the domains a run can have besides a pack's own domains rows.
DOMAIN_SKILLS = frozenset({"brainrc-ci-pipelines", "brainrc-observability", "brainrc-scripting"})
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
             "clone with `git checkout -- skills/brainrc-gatework/roles`; or, with a brainrc that copies "
             "git's stand-ins for links, set link_mode = \"copy\"")
CONNECTOR = re.compile(r"^(brainrc-)?ticket-")
REQUIRED_CONNECTOR_OPS = ("fetch", "comment", "transition", "link_pr")  # references/connectors.md
H2 = re.compile(r"^## +(.+)$", re.M)


def check_extensions(ext: dict, where: str, skill_names: set[str], agent_names: set[str]) -> list[str]:
    errors = [f"{where}: unknown extension `{k}`" for k in sorted(set(ext) - EXTENSION_KEYS)]
    if where.endswith("brainrc.local.toml"):  # this machine's table, from core: Gatework reads only these
        errors += [f"{where}: [extensions.gatework] `{k}` belongs in a pack; this machine sets only "
                   f"{', '.join(sorted(MACHINE_KEYS))}" for k in sorted((set(ext) & EXTENSION_KEYS) - MACHINE_KEYS)]
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
    if "mode" in ext and ext["mode"] not in MODES:
        errors.append(f"{where}: mode must be one of {', '.join(MODES)}")
    if not isinstance(ext.get("forbid_writing_subagents", False), bool):
        errors.append(f"{where}: forbid_writing_subagents must be true or false")
    gates = ext.get("unavailable_gates", [])
    if not isinstance(gates, list) or not all(isinstance(g, str) and GATE.match(g) for g in gates):
        errors.append(f"{where}: unavailable_gates must be a list of check names such as \"iac-scan\" "
                      "(letters, digits, - and _)")
    else:
        errors += [f"{where}: unavailable_gates can't name `{g}`: unavailable_gates.py reads that word as "
                   "a pass" for g in gates if g.lower() in PASS_WORDS]
    return errors


def _reviewer_errors(reviewers, where: str, skill_names: set[str], agent_names: set[str]) -> list[str]:
    """[[extensions.gatework.reviewers]]: a pack's agent that reviews beside Gatework's (#143)."""
    if not isinstance(reviewers, list) or not all(isinstance(r, dict) for r in reviewers):
        return [f"{where}: reviewers must be a list of tables ([[extensions.gatework.reviewers]])"]
    errors, seen = [], set()
    for i, r in enumerate(reviewers):
        at = f"{where}: reviewers[{i}]"
        if isinstance(r.get("name"), str) and r["name"] in seen:
            errors.append(f"{at}: `{r['name']}` is listed twice; list each reviewer once, with all its domains")
        seen.add(r.get("name") if isinstance(r.get("name"), str) else None)
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
    """A pack naming a skill or reviewer by its old name: read as the new name, until REMOVED_IN.
    A reviewer domain that isn't a domain skill here: the reviewer may never run."""
    refs = [(n, RENAMED_SKILLS) for n in _skill_refs(ext)] + [(d.get("reviewer"), RENAMED_AGENTS)
                                                             for d in ext.get("domains", [])]
    warnings = [f"{where}: `{n}` was renamed `{table[n]}` and Gatework 0.8.0 no longer installs it; "
                f"use the new name (the old one is read until {REMOVED_IN})"
                for n, table in refs if n in table]
    current = _current(ext)
    domains = DOMAIN_SKILLS | {s for d in current.get("domains", []) if isinstance(d, dict)
                               for s in d.get("skills", []) if isinstance(s, str)}
    for r in current.get("reviewers", []) if isinstance(current.get("reviewers"), list) else []:
        if isinstance(r, dict) and isinstance(r.get("domains"), list):
            warnings += [f"{where}: reviewer `{r.get('name')}` runs on `{d}`, which isn't a domain skill in "
                         "Gatework's Domains table or this pack's domains; it runs only if another pack "
                         "makes it one" for d in r["domains"] if isinstance(d, str) and d not in domains]
    return warnings


def _skill_refs(ext: dict) -> list:
    reviewers = ext.get("reviewers") if isinstance(ext.get("reviewers"), list) else []
    return ([s for d in ext.get("domains", []) for s in d.get("skills", [])]
            + [s for r in reviewers if isinstance(r, dict) and isinstance(r.get("domains"), list)
               for s in r["domains"] if isinstance(s, str)]
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
        ext["reviewers"] = [{**r, "domains": [skill(d) if isinstance(d, str) else d for d in r["domains"]]}
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


def stand_in(path) -> str | None:
    """The target git wrote into a plain file in a link's place (core.symlinks off), else None."""
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 4096:
            return None
        return path.read_bytes().decode("utf-8").strip().replace("\\", "/")
    except (OSError, UnicodeDecodeError):
        return None


def brainrc_copies(path) -> bool:
    """True when the brainrc loading Gatework copies what the stand-in at path points to: copy mode,
    a brainrc with brainrc/gitlinks.py (#120), and git's index records path as a link. An older
    brainrc, or a bad link_mode (brainrc reports that itself), counts as not."""
    try:
        from brainrc import copies, gitlinks
        real = Path(os.path.realpath(path.parent)) / path.name  # gitlinks keys real paths
        return copies.copying() and real in gitlinks.stand_ins(path.parent)
    except Exception:  # noqa: BLE001 - any failure means the copy isn't certain
        return False


def roles_error(me) -> str | None:
    """Gatework reads its role files through roles/ -> ../../agents. A checkout without symlink
    support writes a plain file holding that target instead; brainrc's copy mode copies agents/ in
    its place, and link mode would leave every role link broken."""
    path = me.root / ROLES
    if path.is_symlink() and links_to_agents(os.readlink(path)):
        return None
    if not path.is_symlink() and not path.exists():
        return f"{me.rel(path)} is missing"
    target = stand_in(path)
    if target is not None and links_to_agents(target):
        if brainrc_copies(path):
            return None
        return (f"{me.rel(path)} is git's plain-file stand-in for its link to ../../agents (cloned without "
                "symlink support), which only brainrc's copy mode installs")
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

    merged: dict[str, dict] = {}  # one row per agent, even when two packs name it
    for p, e in ext.items():
        for r in e.get("reviewers", []):
            if not isinstance(r, dict):
                continue
            row = merged.setdefault(r.get("name"), {"name": r.get("name"), "packs": [], "domains": [],
                                                    "every": False, "veto": False})
            row["packs"].append(p)
            row["domains"] += [d for d in r.get("domains") or [] if d not in row["domains"]]
            row["every"] |= not r.get("domains")
            row["veto"] |= bool(r.get("veto"))
    reviewers = list(merged.values())
    if reviewers:
        out += ["", "## Reviewers", "",
                "Pack reviewers run beside Gatework's reviewers, never in place of one: in batched",
                "review and for `review: each` tasks, when the run's domains include one of theirs (no",
                "domains: every run). Veto `yes`: CRITICAL/HIGH findings get fix tasks, as Gatework's do.",
                "Veto `no`: list its findings at the Deliver gate as advisory. Subagent mode launches it",
                "by name; inline, fallback, or a harness without that agent reads its file from Pack roles",
                "below, with Review isolation. A reviewer that can't run either way: veto `yes` is a stop",
                "(guardrails.md), in an auto run too; veto `no` is listed at the Deliver gate as not run.", "",
                "| Reviewer | Runs when the run touches | Veto | Pack |", "|---|---|---|---|"]
        out += [f"| {r['name']} | {'every run' if r['every'] else ', '.join(r['domains'])} | "
                f"{'yes' if r['veto'] else 'no'} | {', '.join(r['packs'])} |" for r in reviewers]

    modes = [(p, e) for p, e in ext.items() if "mode" in e or "forbid_writing_subagents" in e]
    if modes:
        out += ["", "## Run mode", "",
                "Packs' execution mode settings (references/efficiency.md, Overrides). This machine's,",
                "below, wins over them.", "", "| Pack | Mode | Writing subagents |", "|---|---|---|"]
        forbid = {True: "forbidden", False: "allowed"}
        out += [f"| {p} | {e.get('mode', '—')} | {forbid.get(e.get('forbid_writing_subagents'), '—')} |"
                for p, e in modes]

    checks = [(p, c) for p, e in ext.items() for c in e.get("deliver_checks", [])]
    if checks:
        out += ["", "## Deliver checks", "",
                "List these in the Deliver gate, each marked done, not applicable, or not run.",
                "Never mark a check done that did not run.", ""]
        out += [f"- ({p}) {c}" for p, c in checks]

    gates = [(p, g) for p, e in ext.items() for g in e.get("unavailable_gates", [])]
    if gates:
        out += ["", "## Unavailable gates", "",
                "Planned checks that don't run yet. Never report one as passed or done: give each a",
                "Checks row in `verify.md`, and a line at the Deliver gate, reading `not run, unavailable`.",
                "Before the Deliver gate, run `python3 <skill>/scripts/unavailable_gates.py check",
                f"specs/<slug> {' '.join(dict.fromkeys(g for _, g in gates))}` and fix each line it names.", ""]
        out += [f"- ({p}) {g}" for p, g in gates]
    return "\n".join(out).rstrip() + "\n"
