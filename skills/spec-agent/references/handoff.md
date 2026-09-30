# Handoff contract

Agents share no memory. Everything one agent needs from another is in a file.
Every agent run ends by returning exactly one handoff block as its final message.
The engine appends it to `specs/<slug>/log.md` (so read-only roles need no write access). **Keep it under ~150 words**
(findings lists excepted). The engine reads only the newest block, never the whole log.

```markdown
## <agent> · <task id or stage> · <done | blocked | changes-requested>
<ISO timestamp>

**Did:** 1–3 sentences.

**Evidence:**
- `<command>` → <summary line only, e.g. "4 passed, 0 failed" or "exit 1: AssertionError in test_x">;
  full output stays in `.runs/<name>.log`

**Changed files:** `path/a.py`, `path/b_test.py` (or "none")

**Findings:** (reviewers only) severity-ranked list, each `SEVERITY file:line: problem → fix`
Severities: CRITICAL, HIGH, MEDIUM, LOW.

**Open issues:** anything unresolved, or "none"

**Next:** what the engine should do next
```

## Rules for the engine

- **Trust evidence, not claims.** A task is `done` only if the handoff's evidence shows
  the relevant command passing. If evidence is missing, re-run the command yourself.
- **Check changed files against the task's `files`.** Anything outside is a scope-fence
  breach ([guardrails.md](guardrails.md)).
- CRITICAL or HIGH findings send the task back to the implementer. MEDIUM/LOW are
  listed in `pr-body.md` under "Follow-ups" unless trivially fixed in the same attempt.
- `blocked` from any agent → set `state.blocked`, stop, ask the user.

## Dispatch prompt

What the engine sends to an agent (subagent or fallback role) is only this, so
agents stay reusable and context stays small:

```
Role: <agent>
Work item: specs/<slug>/
Task: <task id and title, or stage name>
Read: <artifact paths relevant to this role>
Project commands: test=`…` lint=`…` validate=`…`
Domain skills: <e.g. terraform, aws>   Targets: <approved envs/contexts, or "offline only">
Follow your role instructions. End with a handoff block as your final message.
```
