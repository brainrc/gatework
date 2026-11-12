# Changelog

Gatework follows semver. While it is `0.x`, a change that breaks how packs extend it
(`[extensions.gatework]`) or removes a skill or agent name bumps MINOR; new skills, fixes and
docs bump PATCH. Each version pins the brainrc core versions it works with in `pack.toml`
(`requires_core`).

## 0.7.0 (2026-11-12)

- Gatework moves to its own repository, brainrc/gatework, from brainrc 0.7.0's `packs/gatework`,
  with its history. Its content is unchanged. brainrc installs it from here as its default pack
  (`[gatework]` in brainrc's `packs.toml`, pinned to a tag).
- Gatework is its own plugin for Claude Code, Codex, Cursor and Antigravity CLI. Claude Code names
  its roles `gatework:<role>`; spec-agent still tries `brainrc:<role>` and `ai-config:<role>`.
- The proof guard reads core's secret patterns from the hooks `brainrc apply` installs, or from the
  brainrc checkout `$BRAINRC_CORE` names.
