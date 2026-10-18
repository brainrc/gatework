# Fallback: role-switch execution

Used when the harness cannot launch named subagents (Codex, Antigravity CLI, Cursor, or
Claude Code without these agents installed). Same roles, same artifacts, same gates,
just sequential in one context.

For each dispatch:

1. Announce: `▶ Role: <agent> · <task>`.
2. Read `roles/<agent>.md` (next to this skill's SKILL.md; if `roles/` is missing,
   `../../agents/<agent>.md` from there). Its **Must not** and **Tools**
   lines bind you for the duration of the role, e.g. as `code-reviewer` you do not edit files.
3. Read only the artifacts the dispatch prompt names ([handoff.md](handoff.md)).
   Don't rely on details you remember from other roles; if it isn't in an artifact, it
   isn't part of the handoff.
4. Do the work, write the handoff block, and append it to `log.md`.
5. Announce: `■ End role: <agent>`, then return to engine duties.

Cost control: in a long run, drop working detail after each role. The artifacts
hold what matters. If the harness supports compaction, compact after each completed
task.

## Review isolation

In one session the reviewer has already seen the implementer's reasoning, so limit what it reads:

- `code-reviewer`, `security-reviewer`, `infra-reviewer`, and `verifier` read only `spec.md`, the
  diff (`git diff <base>...HEAD`, or the task diff), and what their role file's **Reads** names
  (for a task, its `plan.md` entry: files and criteria, not the approach).
  Never `log.md`, handoff blocks, or your notes from earlier roles.
- Judge the code as written. If you remember why a line was written, ignore it; the reason
  isn't in the diff, so a reviewer can't rely on it.
- The verifier re-runs every command it cites; it never copies an implementer's evidence.
- Size standard or large: before batched review, checkpoint-commit, stop, and tell the user
  that `/spec-resume` in a **new session** gives an independent review. If the user says to
  continue here, record `review_context: shared` in `state.json` and in `retro.md`.
