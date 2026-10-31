# Planning mode

`/plan <topic> [--web] [--dry-run] [--oneshot]` turns a topic into proven tickets. State lives
in `specs/plan-<slug>/` (`state.json`, `log.md`, `plan-report.md`, `proof/`), in the run's
worktree like any run. Offline only; `--web` lets the researcher use the web.

1. **Research:** dispatch `researcher` with `Web: on|off`. It writes `plan-report.md` from the
   template and proof under `proof/`.
2. **Re-verify:** the engine re-runs each candidate's proof offline in the run worktree. A
   result that doesn't match the recorded one moves the candidate to `## Needs evidence`.
   A failing-test proof must still fail; a spike commit must exist locally.
3. **Trust:** any `## Flagged content` entry, or a candidate quoting untrusted text, makes
   the plan tainted: no tickets are created. Scan every plan file for secret values first; a
   hit is tainted too.
4. **Ticket gate:** § Ticket gate below.

Spikes stay on local branches, linked by commit hash. Nothing in planning pushes.
