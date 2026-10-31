<Title line is the PR title: imperative, 72 chars or fewer, no ticket prefix.>

## Blocked
<!-- `--oneshot` benign stop only (SKILL.md § Oneshot mode); title `[blocked] <ticket ref>: <fixed phrase>`, draft PR; the body is only this section and the decisions list. Delete otherwise. Cite kinds, ids and locations only: never quote untrusted text, never include secret values. -->
- Blocker: <blocker kind and source location>
- Stop condition: <guardrails.md row>
- Stage: <stage, task>
- Done: <completed work>
- Decision needed: <what you must decide>

## Why
<1–3 sentences from spec.md Problem.>

## What changed
- <bullet per task, user-visible first>

## Acceptance criteria
- [x] AC1: <short form>, verified by `<test or check>`
- [x] AC2: ...

## How to verify
```
<commands a reviewer can run>
```

## Decisions made without you
<!-- `auto` and `--oneshot` runs only (SKILL.md § Auto mode); delete this section otherwise. -->
- Gates auto-approved: <Spec, Plan, Deliver>; see `specs/<slug>/log.md`
- <open question → the default taken, and why>
- <security trigger touched without a CRITICAL/HIGH finding, if any>
- Ticket comment not posted: `specs/<slug>/ticket-comment.md`

## Follow-ups
- <MEDIUM/LOW review findings not addressed, or "none">

Spec: `specs/<slug>/spec.md` · Plan: `specs/<slug>/plan.md`
<Closes #N | Refs PROJ-123>
