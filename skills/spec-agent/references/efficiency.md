# Efficiency: speed and token budget

Token cost is dominated by what enters context, and how often. These rules apply
to the engine and every role.

## Execution mode (decided once, at intake)

| Mode | When | How |
|---|---|---|
| **inline** | size `trivial` or `small` | Engine does every step itself in one context. No subagents; spawning costs more than the work. Each step still follows its role file and template ([fallback.md](fallback.md) steps 2–4) and records `stage_started_at`. |
| **subagent** | `standard`/`large` and the harness can launch named subagents (Claude Code, OpenCode) | Each role runs in its own context; the main thread holds only `state.json` + newest handoff. |
| **fallback** | `standard`/`large`, no subagent tool | Sequential role-switch in one context ([fallback.md](fallback.md)). |

Record it as `state.mode`.

## Fewer, cheaper agent runs

- **Implementer writes its own failing test first** by default. `test-writer` only runs on tasks
  the plan assigns it (security logic, public contracts).
- **Batched review.** One code-review pass over the whole branch diff after all tasks, not
  one per task. Exception: tasks marked `review: each`.
- **Parallel read-only work.** Run `code-reviewer` and `security-reviewer` concurrently when
  both are needed. Run writers in parallel only in isolated worktrees ([waves](#parallel-waves)).
- **Re-review only fixes.** After a fix task, reviewers see only the fix diff plus prior findings.
- **Model tiering.** Agent files set `model:`. Judgment-heavy roles (architect) use the
  strongest tier; routine roles (verifier, doc-writer) use the cheapest. Harnesses without
  per-agent models ignore the field.

## Parallel waves

`subagent` mode only. Implementers sharing one tree would test against each other's
half-written changes, so each parallel task gets its own git worktree.

1. **Wave:** the `todo` tasks whose `after:` tasks are `done` and whose `files` don't overlap.
   At most 2 tasks for `standard`, 3 for `large`. A task that links to or imports a file another
   task creates waits for that task (`after:`). A `test-writer` task, or a `review: each`
   task, runs alone. A wave of one runs in the run worktree (`state.worktree`).
2. **Dispatch:** for each task, `git -C <state.worktree> worktree add "${TMPDIR:-/tmp}/spec-agent/<slug>/<task>" HEAD`
   (nested in the run worktree, outside the repo, so test runners never find it). Record `tasks[].wave`, `.worktree`, and
   `.started_at`; dispatch every task's agent at once, with the task worktree as `Project root` and
   the `Worktree:` line ([handoff.md](handoff.md#dispatch-prompt)). Subagent tools may not take
   a working directory, and the shell's directory can reset between calls. The run worktree must stay
   clean while the wave runs.
3. **Land in plan order:** first run `python3 <skill>/scripts/worktree_fence.py check <worktree>
   --main <state.worktree> --files <task files> --allow specs/<slug>/`: `STRAY` is a path outside
   `files`, `MAIN` a write to the run worktree (show those paths; never overwrite or revert them
   unasked). Any hit is a failed attempt. Run every git command on a worktree as
   `git -C <worktree>`, never relying on the shell's directory: `git -C <worktree> add -A`, then
   `git -C <worktree> diff --cached --binary > .runs/<task>.patch`. In the run worktree,
   `git -C <state.worktree> apply --index` the patch, run the scoped tests, and commit (Implement step 5). A stray
   path or a patch that won't apply is a failed attempt: that task retries alone, the others
   still land; its retry gets a fresh `started_at` and is not part of the wave. Then
   `git -C <state.worktree> worktree remove --force <worktree>` (its changes are landed and saved in the patch)
   and clear `.worktree`.
4. **Measure:** set `tasks[].finished_at` when each handoff arrives. Once every task's first
   handoff is in, before any retry, add to `metrics.waves`: `count` +1, `max_width`, `task_minutes` (sum of task durations) and
   `wall_minutes` (first start to last finish), counting each task's first attempt only, failed
   or not. Always record all four, even when a task retried. The retro reports the difference.

## Output discipline

Never stream long command output into context. Save it, then read the summary:

```bash
mkdir -p specs/<slug>/.runs && echo '*' > specs/<slug>/.runs/.gitignore
<test command> > specs/<slug>/.runs/test.log 2>&1; echo "exit=$?"
tail -n 25 specs/<slug>/.runs/test.log        # summary + last failure
```

On failure, `grep -n -m 20 -E "FAIL|Error|assert" .runs/test.log` before reading more.
When creating `specs/<slug>/.runs/`, write `.runs/.gitignore` containing `*`, so git ignores the
folder and itself. Don't edit `.git/info/exclude`: harnesses protect `.git/`.

Scope checks to what changed during `implement` (changed Go packages, changed Terraform roots,
changed charts/overlays). Run everything once, at `verify`.

Prefer quiet flags when the tool has them (`pytest -q`, `go test ./... 2>&1 | tail`,
`npm test --silent`).

## Reading discipline

- Search before reading: `rg -n <symbol> --glob '<scope>'`, then read only the line range.
- Don't re-read a file you just wrote or a file whose content is already in context.
- Load references and templates only at the stage that needs them. The engine does not
  preload this folder.
- Subagents receive **paths**, not file contents (see the dispatch prompt in [handoff.md](handoff.md)).
- Read `log.md` from the last `## ` heading only (`tail` / read the final block), never whole.
- Artifacts are short by design: spec ≤ ~60 lines, plan ≤ ~80 lines. Shorter is better.

## Prompt caching

Role files are static and dispatch prompts put the variable part (task, paths) last,
so repeated runs of the same role share a cacheable prefix. Don't inject timestamps or
run-specific text into role files.
