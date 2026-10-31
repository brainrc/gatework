# Planning mode

`/plan <topic> [--web] [--dry-run] [--oneshot]` turns a topic into proven tickets. State lives
in `specs/plan-<slug>/` (`state.json`, `log.md`, `plan-report.md`, `proof/`), in the run's
worktree like any run. Offline only; `--web` lets the researcher use the web.

1. **Research:** dispatch `researcher` with `Web: on|off`. It writes `plan-report.md` from the
   template and proof under `proof/`.
2. **Re-verify:** the engine itself, never the researcher, re-runs each proof command with
   `python3 <skill>/scripts/proof_guard.py run "<command>" --root <worktree>`: read-only argv
   commands only (no shell, network, URL, or path outside the worktree), scrubbed env, 60 s
   timeout, capped output. A denied command, a timeout, or a different exit code or
   normalized output moves the candidate to `## Needs evidence`. A spike also needs a command
   or failing-test proof, and its branch must be local (`plan-<slug>/spike-<n>`, no upstream).
3. **Trust:** the plan is tainted, and creates no tickets, if `## Flagged content` has an
   entry, a candidate quotes untrusted text, `## Sources` is not empty while `Web: off`, or
   `proof_guard.py scan specs/plan-<slug>` finds a secret (proof output included).
   Titles are at most 80 characters, and every `Code` cell is a `path:line` that exists.
4. **Ticket gate:** § Ticket gate below.

Spikes stay on local branches, linked by commit hash. Nothing in planning pushes.
