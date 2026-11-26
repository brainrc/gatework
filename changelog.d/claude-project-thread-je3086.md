---
bump: patch
---
- A pack can add reviewers: `[[extensions.gatework.reviewers]]` names one of its agents, the
  domain skills that bring it in (none: every run) and whether it has `veto`. It runs beside
  Gatework's reviewers, never in place of one, so naming one of Gatework's roles fails validate.
  With veto, its CRITICAL/HIGH findings get fix tasks like Gatework's; without, they are listed at
  the Deliver gate. Subagent mode launches it by name; inline, fallback and a harness without the
  agent read its file from brainrc core's Pack roles (core 0.8.30 and later). A veto reviewer that
  can't run is a stop (brainrc/brainrc#143).
- A pack, or this machine through brainrc core's `brainrc.local.toml` (core 0.8.30 and later),
  can set `mode` (`auto`, `inline` or `subagent`) and `forbid_writing_subagents` under
  `[extensions.gatework]`, without a rule that overrides Gatework. This machine's mode wins; packs
  that disagree mean `auto`. With `forbid_writing_subagents`, roles that edit or write files run in
  the main context and there are no parallel waves (brainrc/brainrc#144).
- A pack's `unavailable_gates = ["iac-scan"]` names planned checks that don't run yet. Each is
  listed in `verify.md` and at the Deliver gate as `not run, unavailable`, never as passed, and the
  new `scripts/unavailable_gates.py check` trips on any line of `verify.md`, `pr-body.md` or
  `ticket-comment.md` that names one and claims a pass (brainrc/brainrc#145).
