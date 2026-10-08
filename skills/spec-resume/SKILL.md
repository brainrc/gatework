---
name: spec-resume
description: Resume an interrupted spec-agent run from its saved state
argument-hint: [ticket ref or slug]
disable-model-invocation: true
---

Using the `spec-agent` skill, resume the run for $ARGUMENTS (default: the spec on the
current branch) following the Resume rules in its state reference. Start by showing a
one-line status, then continue.

If `$ARGUMENTS` appears literally above, this tool didn't fill it in: use what the user typed
with this skill instead.
