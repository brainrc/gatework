---
name: brainrc-review
description: Review uncommitted changes for bugs and security issues
argument-hint: [extra focus]
disable-model-invocation: true
---

Review the uncommitted changes in this repository (`git diff` and `git diff --staged`).
Rank findings most severe first, each with `file:line`, the problem, and a fix.

Extra focus, if any: $ARGUMENTS

If `$ARGUMENTS` appears literally above, this tool didn't fill it in: use what the user typed
with this skill instead.
