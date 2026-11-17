---
bump: minor
---
- Removes the deprecated unprefixed aliases, due in 0.8.0: the skills `spec-agent`,
  `spec-status`, `spec-approve`, `spec-resume`, `unslop`, `kubernetes`, the `ticket-*` connectors
  and the other domain skills, and the agents `analyst`, `verifier` and the rest. Only the
  `brainrc-*` names install. brainrc's next `apply` or `update` prunes the old links from each tool.
  A pack that still names an old skill or reviewer in `[extensions.gatework]` now fails `validate`
  and `apply` with the name to use instead (`validate` used to warn).
- Skill and agent text says Gatework, or the `brainrc-gatework` skill, where it said spec-agent.
- `validator.py` no longer imports the alias tables from `brainrc.naming`, so core can drop them.
- The old `[extensions]` keys and `[extensions.spec-agent]` table are still read, with a warning,
  until 0.9.0.
