# Planning mode

`/plan <topic> [--web] [--dry-run] [--oneshot]` turns a topic into proven tickets. State lives
in `specs/plan-<slug>/` (`state.json`, `log.md`, `plan-report.md`, `proof/`), in the run's
worktree like any run. Offline only; `--web` lets the researcher use the web.

1. **Research:** dispatch `researcher` with `Web: on|off`. It writes `plan-report.md` from the
   template and proof under `proof/`.
2. **Re-verify:** the engine itself, never the researcher, re-runs each proof command with
   `python3 <skill>/scripts/proof_guard.py run "<command>" --root <worktree>`. Only a narrow
   allowlist runs: grep/rg/cat/head/tail/wc/ls with fixed flags on named files, and
   `git log --oneline [-N]`; every path resolves inside the worktree and is not a secret, key,
   or git-internal file. A denied
   command, a timeout, or a different exit code or normalized output moves the candidate to
   `## Needs evidence`. Test runners are never re-run: a failing-test proof stays under
   `## Needs evidence` until a human runs it. A spike also needs an allowlisted command proof,
   and its branch must be local (`plan-<slug>/spike-<n>`, no upstream).
3. **Trust:** the plan is tainted, and creates no tickets, if `## Flagged content` has an
   entry, a candidate quotes untrusted text, `## Sources` is not empty while `Web: off`, or
   `proof_guard.py scan specs/plan-<slug>` finds a secret (proof output included).
   Titles are at most 80 characters, and every `Code` cell is a `path:line` that exists.
4. **Ticket gate:** § Ticket gate below.

Spikes stay on local branches, linked by commit hash. Nothing in planning pushes.

## Ticket gate

After re-verify, present a ⛔ Ticket gate (lifecycle.md § Gate presentation). It lists each proven
candidate as an outward action: title, proof summary, target tracker (`local` or `gh`), and
the epic, if any (creating an epic is a separate listed action, only when asked). At most 10
are offered, in report order; the rest are listed as deferred and stay in the report. Nothing
is created until the user approves after the gate was presented. Record `gates.ticket` and
`metrics.gates.ticket.presented_at` / `approved_at` like any gate. On approval, call the
connector's `create` per ticket (connectors.md; a connector without it: the drafts are listed
for the user to create) and record each returned ref under `state.json` `created`. On resume,
re-present the gate unless it was approved, and skip candidates already in `created`. A tainted
plan (step 3) never calls `create`, in any mode.
- `--dry-run` wins over every other flag: present the gate and stop; it never calls `create`,
  and the report says nothing was created.
- `--auto` alone never approves the Ticket gate: it stops and waits for the user.
- `--oneshot`: the gate is auto-approved and logged (SKILL.md § Auto mode), but only for proven
  local tickets (`ticket-local`). A `gh` or other tracker target is refused: log
  `github create refused` and create nothing there. A tainted plan creates nothing at all.
- `delivery: local-only`: list the drafts and call no `create` at all, local ones included.
