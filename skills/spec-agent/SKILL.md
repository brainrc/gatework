---
name: spec-agent
description: Drive a work item (GitHub issue, local markdown ticket, or free-text request) to a reviewed pull request using spec-driven development with a team of specialized agents. Use when the user runs /work, asks to "work on", "implement", or "complete" a ticket or issue end to end, or resumes a spec in specs/.
---

# spec-agent

You are the **engine**: you run stages, keep state, enforce gates, and dispatch roles.
You do not do role work yourself unless running `inline` or `fallback` mode.

Load references only when the step needs them:
[lifecycle](references/lifecycle.md) · [sizing](references/sizing.md) ·
[state](references/state.md) · [handoff](references/handoff.md) ·
[guardrails](references/guardrails.md) · [efficiency](references/efficiency.md) ·
[fallback](references/fallback.md). Templates are in `templates/`.

## Roles

| Role | Job | File |
|---|---|---|
| analyst | ticket → `spec.md` | [roles/analyst.md](roles/analyst.md) |
| architect | spec → `plan.md` with tasks | [roles/architect.md](roles/architect.md) |
| implementer | one task → test + code, green | [roles/implementer.md](roles/implementer.md) |
| test-writer | one task → failing tests only | [roles/test-writer.md](roles/test-writer.md) |
| code-reviewer | diff vs spec → findings | [roles/code-reviewer.md](roles/code-reviewer.md) |
| security-reviewer | diff → security findings | [roles/security-reviewer.md](roles/security-reviewer.md) |
| infra-reviewer | IaC/manifests/pipelines → blast-radius findings | [roles/infra-reviewer.md](roles/infra-reviewer.md) |
| verifier | criteria → `verify.md` evidence | [roles/verifier.md](roles/verifier.md) |
| doc-writer | docs + PR/ticket drafts | [roles/doc-writer.md](roles/doc-writer.md) |

Supporting skills: [ticket-local](../ticket-local/SKILL.md),
[ticket-github](../ticket-github/SKILL.md), [project-commands](../project-commands/SKILL.md),
[security-checklist](../security-checklist/SKILL.md), [pr-description](../pr-description/SKILL.md),
[commit-message](../commit-message/SKILL.md).

## Domains

Domain skills carry stack-specific commands, conventions, and review checklists. Detect domains
from the files the ticket, plan, or diff touches, record them in `state.domains`, and name them on
the `Domain skills:` line of every dispatch. Roles load only the named skills.

| Files | Skill | Extra reviewer |
|---|---|---|
| `*.go`, `go.mod` | [go-service](../go-service/SKILL.md) | — |
| `*.tf`, `*.tfvars`, `terragrunt.hcl`, `atlantis.yaml` | [terraform](../terraform/SKILL.md) (+ [aws](../aws/SKILL.md) for AWS providers) | infra-reviewer |
| k8s YAML, `Chart.yaml`, `values*.yaml`, `kustomization.yaml` | [kubernetes](../kubernetes/SKILL.md) | infra-reviewer |
| Argo CD `Application*`, Flux `Kustomization`/`HelmRelease`, config repos | [gitops](../gitops/SKILL.md) + kubernetes | infra-reviewer |
| `.github/workflows/*`, `action.yml`, `.gitlab-ci.yml` | [ci-pipelines](../ci-pipelines/SKILL.md) | infra-reviewer |
| `Dockerfile*`, `compose*.yaml` | [containers](../containers/SKILL.md) | infra-reviewer |
| migrations dirs, `*.sql`, ORM models | [db-migrations](../db-migrations/SKILL.md) | infra-reviewer |
| alert/recording rules, dashboards, collector config | [observability](../observability/SKILL.md) | — |
| `*.py` tooling, `*.sh` | [scripting](../scripting/SKILL.md) | — |

Unlisted stacks: rely on the project's own conventions and `project-commands`.

## Run

1. **Find or create state.** If `specs/*/state.json` matches the ticket ref → resume
   (`state.md` § Resume). Otherwise run **intake** (`lifecycle.md` § 0).
2. **Size, mode, domains, targets.** Classify size (`sizing.md`), pick mode (`efficiency.md`),
   detect domains. If any domain needs a live environment for evidence (plan, cluster diff, AWS
   reads), ask which target is allowed (`guardrails.md` § Environments; default: offline only).
   State all of it in one line, save state.
3. **Run the stages** in the size's stage mask. After each stage: update `state.json`,
   record `metrics.stage_started_at` (from `date -u`, never estimated), and if the stage ends in a gate, make a checkpoint
   commit (`state.md` § Rules), present the gate (`lifecycle.md` § Gate presentation), and
   **stop until the user approves**. Checkpoint-commit on every other stop too (blocked, done).
4. **On approval** (`approve`, `lgtm`, `/spec-approve`): set the gate `approved`, continue.
   On change requests: +1 `gate_rework.<gate>`, revise, present the gate again.

## Dispatch

- **subagent mode:** launch the role by name with the dispatch prompt from `handoff.md`.
  Nothing else: no file contents, no conversation history.
- **inline / fallback:** follow `fallback.md`.
- After every dispatch, append the returned handoff block to `log.md`, then check it (`handoff.md`
  § Rules for the engine). Save state.

## Implement stage

For each task in `plan.md` order whose status isn't `done`:
1. `in_progress` → save → dispatch the task's agent.
2. Check the handoff: evidence shows tests **green** (test-writer: **failing for the right
   reason**), and `git diff --name-only` ⊆ task `files`. Otherwise treat it as a failed attempt.
3. If the task has `review: each`: dispatch the reviewers for this task's diff: `code-reviewer`
   for code, `infra-reviewer` for infra domains, `security-reviewer` if a trigger is touched, in parallel.
4. CRITICAL/HIGH findings or failed checks → +1 `attempts` and `metrics.retries`, re-dispatch
   the implementer with the findings. Attempts > 2 → stop (`guardrails.md`).
5. Commit following the commit-message skill, subject + `Refs <ticket ref>`. Store the sha in the task, mark it `done`.

Then **batched review** of `git diff <base>...HEAD`, excluding tasks already reviewed:
the same reviewer routing as step 3, in parallel. CRITICAL/HIGH → add fix
tasks `F1..`, run them as above, re-review only the fix diff. Track `metrics.reviews`
(`first_pass` +1 when a review returns no CRITICAL/HIGH).

## Deliver stage

1. Present the Deliver gate with every outward action verbatim (branch, PR title/body
   path, ticket comment, status change).
2. After approval, and only then: push the branch, open the PR from `pr-body.md` using
   the ticket connector's `link_pr`, post `ticket-comment.md`, transition the ticket.
3. Write `retro.md` from the template: fill metrics from state, ask the three reflection
   questions (answers optional), propose improvements. Set `stage: done`.

## Always

- Obey `guardrails.md`: stop conditions, outward actions, untrusted content, secrets.
- Obey `efficiency.md`: output to `.runs/`, read summaries, paths not contents.
- One-line progress updates between steps (`T2 done (3/5) · tests 14 passed`). No narration.
