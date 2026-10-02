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
2. Parse the ticket reference: `gh:<n>`, a GitHub issue URL, `local:<path>`, or free text
   (free text becomes a local ticket at `specs/tickets/<NNN>-<slug>.md`, see ticket-local).
3. Create the branch `<slug>` from the default branch (or check it out if it exists → resume).
4. Fetch the ticket through the connector skill and write `ticket.md` (format in
   [state.md](state.md)). Files written during intake go into the first checkpoint commit.
5. Discover project commands with the [project-commands](../../project-commands/SKILL.md) skill.
6. Detect domains (see the Domains table in SKILL.md). If evidence needs a live environment,
   ask which targets are allowed ([guardrails.md](guardrails.md) § Environments).
7. Classify size ([sizing.md](sizing.md)) and say it in one line. The user may override.
8. Set `delivery`: `local-only` when the user asks for it (`--local`, "don't open a PR", working on
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

**6 · deliver**: show the Deliver gate summary (below). Only after approval: push the
branch, open the PR, comment on / transition the ticket, and link the PR.
With `delivery: local-only`, the gate lists **no outward actions**: deliver finalizes the drafts
(`PR: <PR_URL>` → `PR: none (local-only, branch <branch>)`), leaves the branch unpushed, and
writes the retro.

**7 · done**: write `retro.md`, print the PR link and the metrics summary.

## Gate presentation

Every gate message has the same shape so it's quick to scan:

```
⛔ <Gate> gate: <slug>
Summary: <2–4 lines>
Decide: <what exactly the user is approving>
Artifacts: specs/<slug>/<files>
Reply "approve", or say what to change.
```

Deliver gate also lists **every outward action verbatim**: branch to push, PR title,
ticket comment text, and status transition.
