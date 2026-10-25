# Campaign mode

A **campaign** is a set of near-identical tickets that differ only in parameters: the same
migration per service, the same upgrade per cluster, the same cleanup per repo. Running them
one by one pays the research cost N times. Campaign mode pays it once.

Start: `/work --campaign <epic ref | query | ref list> [--batch-size N] [--dry-run] [--shape playbook|ordered]`.

Two shapes: `playbook` (this file, steps 1-4) for near-identical tickets, and `ordered` for
different, dependent children built in dependency order (§ Ordered shape, last section).

## State

```
specs/campaign-<slug>/
  campaign.json   members, parameters, batch, playbook version (schema below)
  playbook.md     the shared steps with {param} holes, verification, rollback, review checklist
  log.md          batch reports, playbook corrections
```

```json
{ "ref": "PROJ-100", "batch_size": 3, "playbook_version": 1, "started_at": "<ISO>",
  "members": [ { "ref": "PROJ-101", "params": { "service": "svc-a", "repo": "org/svc-a" },
                 "status": "todo", "slug": null, "pr": null } ] }
```

`members[].status`: `todo` `in_progress` `delivered` `blocked` `deviant` (needs a normal run),
and in `ordered` shape `verified` and `waiting`. Each member also gets its own `specs/<slug>/` as in a normal run.
Absent `shape` means `playbook`. The `ordered` schema is in § Ordered shape.

## 1. Enumerate and check the template

1. List members with the connector's `list` (epic children, a label, or the query given).
   Skip closed and assigned-to-someone-else tickets, and say which.
2. **Detect the shape.** Read each member's links with the connector's `dependencies` op. Read
   three members spread across the list: they share one template if they have the same
   criteria shape and repo pattern, differing only in parameters.
   - Shared template and no links: `playbook`. Any link, or members that differ: `ordered`.
   - `--shape` overrides the detection. `--shape ordered` on an epic with no links is allowed:
     the order is the epic's sub-issue order.
   - `playbook` with a template mismatch: stop and list the deviants. They get normal `/work`
     runs. `ordered` follows § Ordered shape and skips § 2 and § 4 below (§ 3 applies).
3. Build the parameter table (`ref | <param> | ... | notes`) and save `campaign.json`.

## 2. Hydrate shared context once

- The epic or parent ticket, and any design doc it links.
- Two or three **already-finished** members and their merged PRs: diff two of them to separate
  per-member parameters from shared boilerplate.
- Review feedback that repeated across those PRs, and any approach that was rejected.
- Pack intake-context skills (`extensions.md`), run once for the campaign.

Write `playbook.md`: steps with `{param}` holes, verification commands, rollback, and the
review checklist the finished PRs had to pass. Size the campaign from the playbook
(`sizing.md`); the floors still apply.

## 3. Campaign gate ⛔

Present the parameter table, the playbook, the size, and the proposed batches. Approval here
stands in for each member's Spec and Plan gates, because the playbook is the spec and plan.
A member that needs a different spec or plan is a deviant: take it out of the campaign.
`--dry-run` stops after presenting this gate. The gate always states the shape, and for
`ordered` the child order and the dependency source (no playbook or parameter table).

## 4. Batches

For each member in the batch (default size 3):

1. Create its `specs/<slug>/` with `ticket.md`, a `spec.md` and `plan.md` instantiated from the
   playbook, and `state.json` with `gates.spec` and `gates.plan` set to `approved` (note
   "campaign gate" in `log.md`).
2. Run implement and verify as normal. Per-member reviews, scope fence, retries, and stop
   conditions all apply.
3. Write the drafts. Every PR body links the parent ticket and its sibling PRs: reviewers
   approve visibly identical siblings faster.

**Batch Deliver gate ⛔:** one gate for the batch, listing every outward action for every
member verbatim. After approval, deliver each member through its connector. One PR per member.

**Batch checkpoint:** report PRs opened, members blocked, and playbook corrections found. Apply
corrections to `playbook.md` (bump `playbook_version`) before the next batch. Early review
feedback is the cheapest quality signal. Wait for the user before the next batch unless they
said to run through.

## Stops

- A member hits something the playbook doesn't cover (unexpected layout, missing prerequisite):
  mark it `blocked` or `deviant`, draft a ticket comment for the Deliver gate, continue the batch.
- Two members fail the same way: stop the campaign. The playbook is wrong. Fix it, re-check it
  against a finished member, then resume.
- Open, unreviewed campaign PRs ≥ 2 × batch size: pause and say so. Don't outrun review.

## Report

```
Campaign <ref> · <date>
Members: <n> total · <n> delivered · <n> in progress · <n> blocked · <n> deviant
Playbook: v<N> (<corrections this batch, or none>)
Batch <k>: <ref> → <PR | blocked: reason>, ...
Next: <batch k+1 | waiting on review | done>
```

## Ordered shape

Playbook runs skip this section.

Use for children that differ or depend on each other. § 1 (enumerate, detect) and § 3 (the
Campaign gate) apply; § 2 (hydrate) and § 4 (batches) do not. There is no playbook, batch, or
parameter table. `campaign.json` is saved after ordering, before the gate.

```json
{ "ref": "<ref as given>", "shape": "ordered", "dependency_source": "<source>", "started_at": "<ISO>",
  "delivery": "sequential",
  "members": [ { "ref": "<ref>", "order": 1, "depends_on": [], "status": "delivered",
                 "slug": "<slug>", "branch": "<slug>",
                 "pr": "<PR URL, or branch name with no remote>", "base": "main", "merged": false } ] }
```

`members` keep epic order; `order` is the 1-based build and merge order. `dependency_source` is
a `dependencies` result `source` (`api` `body` `frontmatter` `none`). For a mixed result it is
`body` if any child used the body fallback, else the single source. `delivery` is `sequential`
(absent means this) or `stacked`, set at the Deliver gate. `base` (the PR's base branch) and
`merged` are recorded only for `stacked`. Status `verified`: built and verified, waiting for the
stack Deliver gate.

**State home.** `specs/campaign-<slug>/` lives on the child branch in progress, so it moves down
the stack with the branches. While building, a child's commits change only its own member entry
and the campaign-level `gates`. From the Deliver gate on, the last child's branch (the stack tip)
is the home: Deliver-gate writes (every member's `status`, `pr`, `base`) and `merged` flags are
committed there, and resume reads `campaign.json` from it. `main` is merged into a branch before
its PR opens or is retargeted, so earlier PRs show only their own entry; the tip's PR also
carries the campaign-level writes.

**Order.** Per child, `dependencies` returns `{ "source": "api" | "body" | "frontmatter" | "none",
"depends_on": ["<ref>", ...] }`. Sort topologically (Kahn); ties and unlinked children keep epic
order. A cycle, or a link to a ticket outside the epic, stops the run at the Campaign gate,
which lists the offending links. The gate states the shape, the order, and the source used.

**Build.** Each child is a normal run: own `specs/<slug>/`, its own Spec and Plan gates
presented (the Campaign gate does not stand in for them), implement, verify. Child N's branch
starts from child N-1's branch (child 1 from the default branch). The active-run pointer names
the child in progress. A verified child is `verified` until the Deliver gate.

**Deliver gate ⛔.** One gate after every child is verified, listing every child's outward
actions verbatim in merge order. It asks for the delivery, recorded as `delivery`:
- `sequential` (default): after approval only `order: 1` is `delivered` with `pr` set (with no
  remote or local-only: its branch name is recorded as `pr`); the rest are `waiting`, `pr: null`.
- `stacked`: every PR opens at approval, child 1 against the default branch, child N against
  child N-1's branch; all are `delivered` with `base` set. Each later body says "N of M, stacked
  on #X. Retarget to `main` before merging." and links the epic. Not with local-only.

**Retarget rule (both deliveries).** A child PR merges only with base `main`. When its
predecessor has merged: merge `main` into its branch, re-run its tests, then open its PR
(`sequential`; body "N of M, after #X", linking the epic; X is filled in then) or retarget its
base to `main` (`stacked`; `gh pr edit <n> --base main` or MCP `update_pull_request`). GitHub
retargets only when the old base branch is deleted, so never rely on it. If an earlier PR changed
in review, merge that change into the later branches and re-run their tests first.

**Failure.** A child that fails or is blocked pauses every later child; earlier ones are
unaffected. The Stops above still apply.

**Merge detection.** Pull-based, never polled. On `/work --campaign <ref>` or /spec-resume, for
each `waiting` child (or stacked child not yet based on `main`) read its predecessor's PR state
read-only through the connector (`gh pr view <n> --json state` or MCP `pull_request_read` `get`).
Release or retarget the next child only if the state is merged or the user says "merged" (for
`stacked`, set the predecessor's `merged: true`). Otherwise report what is waiting and stop.

**Resume.** `/work --campaign <ref>` with an existing `specs/campaign-*/campaign.json` for that
ref resumes it, without re-running intake. A member `in_progress` resumes first, as that child's
normal run (`state.md` § Resume); `verified` members are skipped, and when every member is
`verified` resume presents the stack Deliver gate. `waiting` and stacked members then follow the
merge rule above.
