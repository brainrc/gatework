# Retro: <slug>

Ticket: <ref> · Size: <tier> · PR: <url>

## Metrics
| Metric | Value |
|---|---|
| Duration (intake → deliver) | <h:mm> total = <h:mm> agent + <h:mm> waiting at gates |
| Time per stage | spec <m>, plan <m>, implement <m>, verify <m> (agent time, gate waits excluded) |
| Gate rework (spec / plan / deliver) | <n> / <n> / <n> |
| Tasks | <n> (parallel waves: <count>, widest <max_width>; <task_minutes> task-min in <wall_minutes> wall-min) |
| Review first-pass rate | <first_pass>/<total> (<%>) |
| Retries | <n> |
| Interventions | <n> |
| Review context | fresh / shared (fallback mode only; omit otherwise) |
| Criteria passed | <n>/<n> |

## Reflections
Ask the user these three; record answers verbatim (or "skipped"):
1. If the user wrote the ticket: did the result match what you meant? Otherwise (someone
   else's issue): would you ship this as-is, and if not, what's missing?
2. Where did you have to step in, and why?
3. One change to a skill, agent, or rule that would have prevented that?

## Proposed improvements
<Concrete edits to brainrc skills/agents/rules, derived from the answers and metrics.
These are suggestions; nothing is changed automatically.>

## After delivery
<!-- Appended by watch when the PR merges or closes; omit until then. -->
- Outcome: <merged | abandoned>
- Merged at: <ISO timestamp> · Time to merge: <m> min
- Post-merge verify: <pass | regression | unverified> (see `verify-merged.md`)
- CI failures: <n> own / <n> external
- Review rounds: <n>
- Caught by reviewers, missed by the run's own: <list, or none>
- Follow-up title: <title, or none>
- Follow-up body: <body, or none>
