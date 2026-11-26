---
bump: minor
---
- Removes the stack skills that moved to brainrc's official packs (brainrc/brainrc#318):
  `brainrc-go-service` and `brainrc-db-migrations` (now `brainrc/go`), `brainrc-terraform` and
  `brainrc-aws` (`brainrc/terraform-aws`), and `brainrc-kubernetes`, `brainrc-gitops` and
  `brainrc-containers` (`brainrc/kubernetes`), all folders of brainrc/packs under the same names.
  Enable those packs to keep the skills; their `[[extensions.gatework.domains]]` rows put them back
  in the Domains table.
- The README, AGENTS.md, `pack.toml`, the engine's Domains table and the eval cases say where stack
  skills live now.
