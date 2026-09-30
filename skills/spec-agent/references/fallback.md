# Fallback: role-switch execution

Used when the harness cannot launch named subagents (Codex, Gemini CLI, Cursor, or
Claude Code without these agents installed). Same roles, same artifacts, same gates,
just sequential in one context.

For each dispatch:

1. Announce: `▶ Role: <agent> · <task>`.
2. Read `roles/<agent>.md` (next to this skill's SKILL.md). Its **Must not** and **Tools**
   lines bind you for the duration of the role, e.g. as `code-reviewer` you do not edit files.
3. Read only the artifacts the dispatch prompt names ([handoff.md](handoff.md)).
   Don't rely on details you remember from other roles; if it isn't in an artifact, it
   isn't part of the handoff.
4. Do the work, write the handoff block, and append it to `log.md`.
5. Announce: `■ End role: <agent>`, then return to engine duties.

Cost control: in a long run, drop working detail after each role. The artifacts
hold what matters. If the harness supports compaction, compact after each completed
task.
