---
name: work
description: Take a work item from ticket to reviewed PR with spec-agent (gh:<n>, jira:<KEY-n>, issue URL, local:<path>, free text, or --campaign <epic>)
argument-hint: <gh:42 | jira:PROJ-7 | issue URL | local:path.md | free text | --campaign <epic|query>> [--local] [--batch-size N] [--dry-run] [--shape playbook|ordered] [--auto]
disable-model-invocation: true
---

Use the `spec-agent` skill to work on this item end to end:

$ARGUMENTS

If a spec for this item already exists under `specs/`, resume it instead of starting over.
A spec at `stage: watch` runs `watch.md` § Resume pass (spec-agent `references/watch.md`).
If `--local` is given, use `delivery: local-only`: no push, PR, or ticket updates; drafts only.
If `--campaign` is given, run campaign mode (spec-agent `references/campaign.md`) over the
epic, query, or list of refs; `--dry-run` stops at the Campaign gate. `--shape playbook|ordered`
overrides the detected shape. `--campaign <ref>` on an existing ordered campaign resumes it
(`campaign.md` § Ordered shape).
Stop at every gate for my approval. Never push, open PRs, or update the ticket before the
Deliver gate is approved.
If `--auto` is given, run without gate stops instead (spec-agent SKILL.md § Auto mode): hard stops
still stop, and delivery is a draft PR only. Without the flag, no wording of mine means `--auto`.

If `$ARGUMENTS` appears literally above, this tool didn't fill it in: use what the user typed
with this skill instead.
