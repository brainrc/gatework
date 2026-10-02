---
name: runbook
description: Write or refresh an incident-response runbook from a strict 10-section template - when to use it, when not to, copy-pasteable diagnosis, reversible mitigation with verification, rollback, escalation. Use for a new alert (its runbook link must resolve before the alert ships), a newly found failure mode, an incident follow-up, or a runbook older than six months.
---

# Runbook

A runbook is a how-to guide: task-oriented, no background, no design history. The reader is
on call and resolving the alert now. Design rationale goes in an ADR, linked from section 9.

## Conventions come from the project

Before writing, find the project's (or pack's) conventions: severity scale, paging and incident
tool, alert-routing channel, where runbooks live, the runbook index page, and who reviews
runbooks for sensitive systems. Look in the repo's docs and rules first. Ask for anything
missing. Never invent a channel, URL, schedule, or severity name.

## Required inputs

Stop and ask if any is missing:

1. **Service** and the label it carries in logs and metrics.
2. **Symptom**: what the on-call engineer sees.
3. **Detecting alert(s)** and their severity.
4. **Owner** and on-call schedule.
5. **Mitigation steps**, verified, each with a rollback. For GitOps-managed services, prefer the
   GitOps rollback over editing cluster state by hand.
6. **Escalation path** for the top severities.
7. **Where to publish** (repo path or wiki space and parent page).

## Template

Fixed section order. Do not add, remove, or reorder top-level sections. No `<...>` placeholder
may survive in the finished runbook.

````markdown
# Runbook: <Service>: <failure mode>

> **Status:** DRAFT | ACTIVE | DEPRECATED
> **Last verified:** YYYY-MM-DD by <name>
> **Owner:** <team> (on-call: <schedule>)
> **Pages:** <severity> via <paging tool>, routed to <channel>
> **Escalation:** <how to declare an incident and who to involve>

## 1. Summary
One paragraph: what is failing, who notices, what this runbook fixes.

## 2. When to use this runbook
- Alert: `<alert-name>` (severity <S>)
- Service: `<service>` (label `<label>=<value>`)
- Environment: `<cluster / account / region>`
- Symptom: <symptom>

## 3. When NOT to use this runbook
The wrong runbook causes outages. List the conditions that send the reader elsewhere.
- If <other symptom> is also present → use <other runbook>
- If <sensitive system> is affected → involve <reviewer> before any mitigation

## 4. Diagnosis
Numbered, copy-pasteable, read-only commands. Each says what to look for.
1. <check>:
   ```bash
   <command>
   ```
   **Look for:** <signal>

## 5. Mitigation
Each step is reversible unless marked `IRREVERSIBLE` with the preconditions that must hold.
Each lists its expected effect and how to verify it.
1. **(Reversible)** <action>:
   ```bash
   <command>
   ```
   **Expected:** <effect, and whether GitOps will revert it on next sync>
   **Verify:** <command and expected output>

## 6. Rollback
How to undo each mitigation if it makes things worse.

## 7. Post-mitigation
Incident record, status page if customers were affected, metrics window captured, follow-up
ticket for the root cause.

## 8. Root-cause hypotheses
- **<hypothesis>:** confirm with <command or dashboard>

## 9. Related runbooks and ADRs
- <links>

## 10. Change log
| Date | Author | Change |
|---|---|---|
| YYYY-MM-DD | <name> | Initial draft |
````

## Procedure

1. Confirm the inputs and conventions.
2. Write the runbook from the template.
3. Prefix every step you have not seen work on a comparable environment with `UNVERIFIED:`.
4. Keep `Status: DRAFT` until someone walks it through in a non-production environment or a
   real incident.
5. Run the unslop skill on it in the procedural register; the section order must survive.
6. If an alert is waiting on it, set the alert's runbook link to the runbook's final location.
7. Add it to the runbook index, if the project has one.

Publishing to a wiki or posting a link is outward: do it only with approval naming the target.
Default: write the file in the repo.

## Guardrails

- **Section 3 is required.** An empty "When NOT to use" goes back to whoever asked for the runbook.
- **No step without a rollback,** unless it is marked `IRREVERSIBLE` with preconditions.
- **Stale:** "Last verified" older than six months means regenerate it, even if it looks fine.
- **No freestyle:** the template is the contract.
- **An alert must not ship with a placeholder runbook link** (`#TODO`, empty). The runbook ships
  with or before the alert.
- Diagnosis commands are read-only. Mitigation commands that change state say so.
