# Lifecycle

Stages run in this order. [sizing.md](sizing.md) decides which ones run.
`state.json` → `stage` always names the stage in progress.

| # | Stage | Actor | Reads | Writes | Exit |
|---|---|---|---|---|---|
| 0 | `intake` | engine | ticket (via connector) | `ticket.md`, `state.json`, branch | size stated, commands discovered |
| 1 | `spec` | analyst | `ticket.md`, `specs/living/`, code | `spec.md` | ⛔ **Spec gate** approved |
| 2 | `plan` | architect | `spec.md`, code | `plan.md` (incl. tasks), `state.tasks` | ⛔ **Plan gate** approved |
| 3 | `implement` | implementer (or test-writer) per task, then batched review | `plan.md`, `spec.md` | code, tests, one commit per task | every task `done`, review clean |
| 4 | `verify` | verifier | `spec.md`, `state.commands` | `verify.md` | every criterion `pass` with evidence |
| 5 | `document` | engine, doc-writer | all artifacts, diff | `specs/living/`, project docs, `pr-body.md`, `ticket-comment.md` | drafts exist |
| 6 | `deliver` | engine + ticket connector | drafts | push, PR, ticket comment/status, `retro.md` | ⛔ **Deliver gate** approved before *any* outward action |
| 6b | `watch` | engine + ticket connector | `pr_status`, CI logs | `watch` state, C-tasks, ⛔ **Push gate** | `merged`: post-merge verify, then `done`; `closed`: `done` as abandoned; otherwise on resume |
| 7 | `done` | engine | `state.metrics` | closes the run | PR link and metrics printed |

`blocked` is not a stage. It is `state.blocked`, set by any stop condition
([guardrails.md](guardrails.md)). The stage is kept so resume knows where to continue.

## Stage details

**0 · intake**
1. A dirty main checkout is left alone: the run works in its own worktree (step 4) and never
   changes the main checkout's branch, index, or files.
2. Parse the ticket reference: `gh:<n>`, a GitHub issue URL, `jira:<KEY-n>` or a Jira browse
   URL (brainrc-ticket-jira), `local:<path>`, or free text
   (free text becomes a local ticket at `specs/tickets/<NNN>-<slug>.md`, see brainrc-ticket-local).
   A ref that matches a pack connector's `refs` (`extensions.md`, SKILL.md § Packs) uses that connector.
3. If the repo has a `VERSION` file and no `changelog.d/` (fragments don't conflict), list other open PRs that change `VERSION` or `CHANGELOG.md`
   (through the connector's system, e.g. `gh pr list` or its MCP equivalent). If any exist,
   name them and recommend waiting for them to merge before branching, since both will claim
   the same next version. Can't list PRs → say so in one line and continue.
4. Run `python3 <skill>/scripts/run_worktree.py open <slug> --branch <slug> --base <base>`
   (`<base>` is the default branch, or for an ordered-campaign child N the previous child's branch)
   and record its absolute path as `state.worktree`. From here on, `Project root` and every git
   command use `state.worktree`. Exit 1 (the main checkout is on the branch): stop, report its
   stderr, never switch the user's checkout. The engine installs and copies nothing; a
   missing-dependency failure becomes a block naming the cause.
5. Fetch the ticket through the connector skill and write `ticket.md` (format in
   [state.md](state.md)). Run any pack Intake context skills and append their summaries.
   Files written during intake go into the first checkpoint commit. Record the run as active
   (`python3 <skill>/scripts/active_run.py write <worktree>/specs/<slug>`, state.md § Active run pointer).
6. Discover project commands with the [brainrc-project-commands](../../brainrc-project-commands/SKILL.md) skill.
7. Detect domains (see the Domains table in SKILL.md). If evidence needs a live environment,
   ask which targets are allowed ([guardrails.md](guardrails.md) § Environments).
8. Classify size ([sizing.md](sizing.md)) and say it in one line with the mode. The user may
   override. If the harness can run subagents but the named agents aren't installed (Claude
   Code without `~/.claude/agents/brainrc-analyst.md`), say it runs in `fallback` and that
   `python3 scripts/brainrc.py apply` in brainrc installs them.
9. Set `delivery`: `local-only` when the user asks for it (`--local`, "don't open a PR", working on
   someone else's repo without push rights), else `normal`. Record it in state.

**1 · spec**: the analyst turns the ticket into testable acceptance criteria and lists
open questions, and states the requirement delta against the living specs it read (new behavior with no living
area creates one). Before the gate, run `python3 <skill>/scripts/living_specs.py check
specs/<slug>/spec.md` and have the analyst fix any error, so the delta that gets approved is the
one that applies. At the gate, show the criteria and questions. If the user answers questions, the analyst revises (count
one `gate_rework.spec` per revision round).

**2 · plan**: the architect writes the approach and the task list. Each task names its
agent, the files it may touch, and the criteria it satisfies. Any new dependency or
public API change must be called out at the top of `plan.md`.

**3 · implement**: loop over tasks in order (see the per-task loop in [SKILL.md](../SKILL.md)).

**4 · verify**: run the full test, lint, build, and validate commands (and plan/diff against
approved targets). Map every acceptance criterion to
evidence in `verify.md`, written from `templates/verify.md`: its `## Checks` and
`## Acceptance criteria` sections, criteria columns `Criterion | Evidence | Result`. Any `fail` → back to `implement` with a new fix task (counts as a retry).

**5 · document**: first apply the spec's delta to the living specs:
`python3 <skill>/scripts/living_specs.py apply specs/<slug>/spec.md` (`check` first if unsure).
It writes nothing when any block is wrong; fix `spec.md` (a change to the approved spec, so say
so at the Deliver gate) and re-run. Record the areas in `state.living` and commit them with the
docs. Without Python, the doc-writer applies the delta by hand with the same rules. Then update
docs the change affects (README, CHANGELOG, API docs) and draft outward text. Nothing is posted.

**6 · deliver**: re-run the intake `VERSION` check. If such a PR merged meanwhile, merge the
default branch and renumber this run's version before the gate. Show the Deliver gate summary (below). Only after approval: push the
branch, open the PR, comment on / transition the ticket, and link the PR.
With `delivery: local-only`, the gate lists **no outward actions**: deliver finalizes the drafts
(`PR: <PR_URL>` → `PR: none (local-only, branch <branch>)`), leaves the branch unpushed, and
writes the retro.

**6b · watch**: after the PR opens, `/brainrc-gatework-resume` or `/brainrc-work <ref>` reads `pr_status` and handles
a red check (C-tasks) and new review threads (R-tasks, replies). Every fix-commit push and every thread reply it posts needs an approved ⛔ **Push gate**. Procedure: [watch.md](watch.md). A merged PR gets a post-merge verify (`verify-merged.md`); a closed one ends as `abandoned`.

**7 · done**: `retro.md` was already written at the end of deliver (before `watch`); after a merge it gains `## After delivery`, and a closed PR is `abandoned`. Print the PR link and the metrics summary. Commit the done
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
