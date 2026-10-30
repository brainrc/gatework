---
name: spec-resume
description: Resume an interrupted spec-agent run from its saved state
argument-hint: [ticket ref or slug]
disable-model-invocation: true
---

Using the `spec-agent` skill, resume the run for $ARGUMENTS (default: the spec on the
current branch) following the Resume rules in its state reference. Start by showing a
one-line status, then continue.

Find the run through `state.worktree` and continue in that worktree, never in the main
checkout. If the directory is missing, recreate it with
`python3 <skill>/scripts/run_worktree.py open <slug> --branch <branch>` (no `--base`), using
`state.branch`. If the pointer's directory is gone and no state is readable, find the branch
(the pointer path's `<slug>`, or the ticket ref against `git branch --list`), read
`git show <branch>:specs/<slug>/state.json`, and open with that branch. If that exits 1 (the branch is gone), stop and say so.

If `$ARGUMENTS` appears literally above, this tool didn't fill it in: use what the user typed
with this skill instead.
