---
bump: patch
---
- A pack can add reviewers: `[[extensions.gatework.reviewers]]` names one of its agents, the
  domain skills that bring it in (none: every run) and whether it has `veto`. It runs beside
  Gatework's reviewers, never in place of one, so naming one of Gatework's roles fails validate.
  With veto, its CRITICAL/HIGH findings get fix tasks like Gatework's; without, they are listed at
  the Deliver gate. Subagent mode launches it by name; inline and fallback read its file from
  brainrc core's Pack roles (core 0.8.30 and later) (brainrc/brainrc#143).
