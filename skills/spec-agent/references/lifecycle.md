# Lifecycle

Stages run in this order. [sizing.md](sizing.md) decides which ones run.
`state.json` → `stage` always names the stage in progress.

| # | Stage | Actor | Reads | Writes | Exit |
|---|---|---|---|---|---|
| 0 | `intake` | engine | ticket (via connector) | `ticket.md`, `state.json`, branch | size stated, commands discovered |
| 1 | `spec` | analyst | `ticket.md`, code | `spec.md` | ⛔ **Spec gate** approved |
| 2 | `plan` | architect | `spec.md`, code | `plan.md` (incl. tasks), `state.tasks` | ⛔ **Plan gate** approved |
| 3 | `implement` | implementer (or test-writer) per task, then batched review | `plan.md`, `spec.md` | code, tests, one commit per task | every task `done`, review clean |
| 4 | `verify` | verifier | `spec.md`, `state.commands` | `verify.md` | every criterion `pass` with evidence |
| 5 | `document` | doc-writer | all artifacts, diff | project docs, `pr-body.md`, `ticket-comment.md` | drafts exist |
| 6 | `deliver` | engine + ticket connector | drafts | push, PR, ticket comment/status | ⛔ **Deliver gate** approved before *any* outward action |
| 7 | `done` | engine | `state.metrics` | `retro.md` | retro written |

`blocked` is not a stage. It is `state.blocked`, set by any stop condition
([guardrails.md](guardrails.md)). The stage is kept so resume knows where to continue.

## Stage details

**0 · intake**
1. Check `git status`. If the working tree is dirty, stop and ask. (Check first: the next
   steps create files, and those are the engine's own.)
2. Parse the ticket reference: `gh:<n>`, a GitHub issue URL, `jira:<KEY-n>` or a Jira browse
   URL (ticket-jira), `local:<path>`, or free text
   (free text becomes a local ticket at `specs/tickets/<NNN>-<slug>.md`, see ticket-local).
   A ref that matches a pack connector's `refs` (`references/extensions.md`) uses that connector.
3. If the repo has a `VERSION` file, list other open PRs that change `VERSION` or `CHANGELOG.md`
   (through the connector's system, e.g. `gh pr list` or its MCP equivalent). If any exist,
   name them and recommend waiting for them to merge before branching, since both will claim
   the same next version. Can't list PRs → say so in one line and continue.
4. Create the branch `<slug>` from the default branch (or check it out if it exists → resume).
5. Fetch the ticket through the connector skill and write `ticket.md` (format in
   [state.md](state.md)). Run any pack Intake context skills and append their summaries.
   Files written during intake go into the first checkpoint commit.
6. Discover project commands with the [project-commands](../../project-commands/SKILL.md) skill.
7. Detect domains (see the Domains table in SKILL.md). If evidence needs a live environment,
   ask which targets are allowed ([guardrails.md](guardrails.md) § Environments).
8. Classify size ([sizing.md](sizing.md)) and say it in one line with the mode. The user may
   override. If the harness can run subagents but the named agents aren't installed (Claude
   Code without `~/.claude/agents/analyst.md`), say it runs in `fallback` and that
   `python3 scripts/aicfg.py apply` in ai-config installs them.
9. Set `delivery`: `local-only` when the user asks for it (`--local`, "don't open a PR", working on
   someone else's repo without push rights), else `normal`. Record it in state.

**1 · spec**: the analyst turns the ticket into testable acceptance criteria and lists
open questions. At the gate, show the criteria and questions. If the user answers
questions, the analyst revises (count one `gate_rework.spec` per revision round).

**2 · plan**: the architect writes the approach and the task list. Each task names its
agent, the files it may touch, and the criteria it satisfies. Any new dependency or
public API change must be called out at the top of `plan.md`.

**3 · implement**: loop over tasks in order (see the per-task loop in [SKILL.md](../SKILL.md)).

**4 · verify**: run the full test, lint, build, and validate commands (and plan/diff against
approved targets). Map every acceptance criterion to
evidence. Any `fail` → back to `implement` with a new fix task (counts as a retry).

**5 · document**: update docs the change affects (README, CHANGELOG, API docs) and
draft outward text. Nothing is posted.

**6 · deliver**: re-run the intake `VERSION` check. If such a PR merged meanwhile, merge the
default branch and renumber this run's version before the gate. Show the Deliver gate summary (below). Only after approval: push the
branch, open the PR, comment on / transition the ticket, and link the PR.
With `delivery: local-only`, the gate lists **no outward actions**: deliver finalizes the drafts
(`PR: <PR_URL>` → `PR: none (local-only, branch <branch>)`), leaves the branch unpushed, and
writes the retro.

**7 · done**: write `retro.md`, print the PR link and the metrics summary. Commit the done
checkpoint, but push it only after CI on the delivered commit finishes: a push while CI runs
can break steps that list the PR's commits.

## Gate presentation

Every gate message has the same shape so it's quick to scan:

```
⛔ <Gate> gate: <slug>
Summary: <2–4 lines>
Decide: <what exactly the user is approving>
Artifacts: specs/<slug>/<files>
Reply "approve", or say what to change.
```

**Ask with buttons when the harness can.** If it has a multiple-choice question tool (Claude
Code: `AskUserQuestion`), print the gate message without the last line, then ask with it:
"Approve" first, then "Request changes", plus one option per open choice in the spec (for
example a design alternative). Any typed answer still counts. Without such a tool, end with
the `Reply` line.

Deliver gate also lists, before `Artifacts:`, a `Changes:` line with the diff stat outside the
spec folder (`git diff --stat <base>...HEAD -- . ':!specs'`), so the work itself comes first,
and **every outward action verbatim**: branch to push, PR title, ticket comment text, and
status transition.
