---
name: plan
description: Research a topic with spec-agent's researcher and turn it into proven tickets (one Ticket gate). Use for /plan <topic>.
argument-hint: <topic> [--web] [--dry-run] [--oneshot] [--local]
disable-model-invocation: true
---

Use the `spec-agent` skill's planning mode (`references/planning.md`) on this topic:

$ARGUMENTS

Web research only with `--web`. Stop at the Ticket gate for my approval; create nothing before
it. `--dry-run` creates nothing. `--oneshot` creates proven local tickets only, without stopping.

If `$ARGUMENTS` appears literally above, this tool didn't fill it in: use what the user typed
with this skill instead.
