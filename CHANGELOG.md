# Changelog

Gatework follows semver. While it is `0.x`, a change that breaks how packs extend it
(`[extensions.gatework]`) or removes a skill or agent name bumps MINOR; new skills, fixes and
docs bump PATCH. Each version pins the brainrc core versions it works with in `pack.toml`
(`requires_core`).

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
