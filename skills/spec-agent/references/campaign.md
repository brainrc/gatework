# Campaign mode

A **campaign** is a set of near-identical tickets that differ only in parameters: the same
migration per service, the same upgrade per cluster, the same cleanup per repo. Running them
one by one pays the research cost N times. Campaign mode pays it once.

Start: `/work --campaign <epic ref | query | ref list> [--batch-size N] [--dry-run]`.

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

`members[].status`: `todo` `in_progress` `delivered` `blocked` `deviant` (needs a normal run).
Each member also gets its own `specs/<slug>/` as in a normal run.

## 1. Enumerate and check the template

1. List members with the connector's `list` (epic children, a label, or the query given).
   Skip closed and assigned-to-someone-else tickets, and say which.
2. Read three members spread across the list. They must share one template: same criteria
   shape and repo pattern, differing only in parameters. If they don't, stop and list the
   deviants. They get normal `/work` runs.
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
`--dry-run` stops after presenting this gate.

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
