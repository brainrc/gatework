# Efficiency: speed and token budget

Token cost is dominated by what enters context, and how often. These rules apply
to the engine and every role.

## Execution mode (decided once, at intake)

| Mode | When | How |
|---|---|---|
| **inline** | size `trivial` or `small` | Engine does every step itself in one context. No subagents; spawning costs more than the work. |
| **subagent** | `standard`/`large` and the harness can launch named subagents (Claude Code, OpenCode) | Each role runs in its own context; the main thread holds only `state.json` + newest handoff. |
| **fallback** | `standard`/`large`, no subagent tool | Sequential role-switch in one context ([fallback.md](fallback.md)). |

Record it as `state.mode`.

## Fewer, cheaper agent runs

- **Implementer writes its own failing test first** by default. `test-writer` only runs on tasks
  the plan assigns it (security logic, public contracts).
- **Batched review.** One code-review pass over the whole branch diff after all tasks, not
  one per task. Exception: tasks marked `review: each`.
- **Parallel read-only work.** Run `code-reviewer` and `security-reviewer` concurrently when
  both are needed. Never run writers in parallel.
- **Re-review only fixes.** After a fix task, reviewers see only the fix diff plus prior findings.
- **Model tiering.** Agent files set `model:`. Judgment-heavy roles (architect) use the
  strongest tier; routine roles (verifier, doc-writer) use the cheapest. Harnesses without
  per-agent models ignore the field.

## Output discipline

Never stream long command output into context. Save it, then read the summary:

```bash
mkdir -p specs/<slug>/.runs
<test command> > specs/<slug>/.runs/test.log 2>&1; echo "exit=$?"
tail -n 25 specs/<slug>/.runs/test.log        # summary + last failure
```

On failure, `grep -n -m 20 -E "FAIL|Error|assert" .runs/test.log` before reading more.
At intake, add `specs/*/.runs/` to `.git/info/exclude` (local-only ignore, no repo change).

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
