# Changelog

Gatework follows semver. While it is `0.x`, a change that breaks how packs extend it
(`[extensions.gatework]`) or removes a skill or agent name bumps MINOR; new skills, fixes and
docs bump PATCH. Each version pins the brainrc core versions it works with in `pack.toml`
(`requires_core`).

## 0.9.1 (2026-11-28)

- The roles check accepts git's stand-in for `roles/` (a plain file holding `../../agents`, what a
  checkout without symlinks leaves) when brainrc copies what it points to: copy mode, from the brainrc
  release with `brainrc/gitlinks.py` (#120). Link mode, or an older brainrc, still fails and names the
  stand-in.

## 0.9.0 (2026-11-26)

- Removes the stack skills that moved to brainrc's official packs (brainrc/brainrc#318):
  `brainrc-go-service` and `brainrc-db-migrations` (now `brainrc/go`), `brainrc-terraform` and
  `brainrc-aws` (`brainrc/terraform-aws`), and `brainrc-kubernetes`, `brainrc-gitops` and
  `brainrc-containers` (`brainrc/kubernetes`), all folders of brainrc/packs under the same names.
  Enable those packs to keep the skills; their `[[extensions.gatework.domains]]` rows put them back
  in the Domains table.
- The README, AGENTS.md, `pack.toml`, the engine's Domains table and the eval cases say where stack
  skills live now.
- The validator's built-in domain skills shrink to the Domains table's three, so a reviewer on a
  moved skill warns unless its pack is enabled and adds the skill as a domain.

## 0.8.1 (2026-11-26)

- A pack can add reviewers: `[[extensions.gatework.reviewers]]` names one of its agents, the
  domain skills that bring it in (none: every run) and whether it has `veto`. It runs beside
  Gatework's reviewers, never in place of one, so naming one of Gatework's roles fails validate.
  With veto, its CRITICAL/HIGH findings get fix tasks like Gatework's; without, they are listed at
  the Deliver gate. Subagent mode launches it by name; inline, fallback and a harness without the
  agent read its file from brainrc core's Pack roles (core 0.8.30 and later). A veto reviewer that
  can't run is a stop (brainrc/brainrc#143).
- A pack, or this machine through brainrc core's `brainrc.local.toml` (core 0.8.30 and later),
  can set `mode` (`auto`, `inline` or `subagent`) and `forbid_writing_subagents` under
  `[extensions.gatework]`, without a rule that overrides Gatework. This machine's mode wins; packs
  that disagree mean `auto`. With `forbid_writing_subagents`, roles that edit or write files run in
  the main context and there are no parallel waves (brainrc/brainrc#144).
- A pack's `unavailable_gates = ["iac-scan"]` names planned checks that don't run yet. Each is
  listed in `verify.md` and at the Deliver gate as `not run, unavailable`, never as passed, and the
  new `scripts/unavailable_gates.py check` trips on any line of `verify.md`, `pr-body.md` or
  `ticket-comment.md` that names one and claims a pass (brainrc/brainrc#145).

## 0.8.0 (2026-11-18)

- Removes the deprecated unprefixed aliases, due in 0.8.0: the skills `spec-agent`,
  `spec-status`, `spec-approve`, `spec-resume`, `unslop`, `kubernetes`, the `ticket-*` connectors
  and the other domain skills, and the agents `analyst`, `verifier` and the rest. Only the
  `brainrc-*` names install. brainrc's next `apply` or `update` prunes the old links from each tool.
- A pack whose `[extensions.gatework]` still names an old skill or reviewer keeps working: it is
  read as the new name, with a warning that names it, until Gatework 0.9.0. So are the old
  `[extensions]` keys and `[extensions.spec-agent]` table, which were also due to go in 0.8.0.
- Skill and agent text says Gatework, or the `brainrc-gatework` skill, where it said spec-agent.
- `validator.py` no longer imports the alias tables from `brainrc.naming`, so core can drop them.

## 0.7.3 (2026-11-18)

- The README links brainrc's docs site: Gatework's page for how it works, and Extensions on the
  packs page for `[extensions.gatework]`, in place of the old `docs/spec-agent.md` and
  `docs/packs.md` files on GitHub.
- The plugin description names the `brainrc-gatework` engine, not spec-agent.

## 0.7.2 (2026-11-14)

- `requires_core` allows brainrc core 0.8 (`>=0.7, <0.9`). Core 0.8.0 moved the lock to version 2
  for pack permissions and changes nothing Gatework depends on; with the old `<0.8`, `apply` on
  core 0.8.0 refused the default pack.

## 0.7.1 (2026-11-12)

- The roles link check accepts `..\..\agents`, the form git on Windows stores, so a Windows clone with symlinks enabled validates.

## 0.7.0 (2026-11-12)

- Gatework moves to its own repository, brainrc/gatework, from brainrc 0.7.0's `packs/gatework`,
  with its history. Its content is unchanged. brainrc installs it from here as its default pack
  (`[gatework]` in brainrc's `packs.toml`, pinned to a tag).
- Gatework is its own plugin for Claude Code, Codex, Cursor and Antigravity CLI. Claude Code names
  its roles `gatework:<role>`; spec-agent still tries `brainrc:<role>` and `ai-config:<role>`.
- The proof guard reads core's secret patterns from the hooks `brainrc apply` installs, or from the
  brainrc checkout `$BRAINRC_CORE` names.
