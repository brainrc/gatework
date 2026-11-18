---
bump: minor
---
- Removes the deprecated unprefixed aliases, due in 0.8.0: the skills `spec-agent`,
  `spec-status`, `spec-approve`, `spec-resume`, `unslop`, `kubernetes`, the `ticket-*` connectors
  and the other domain skills, and the agents `analyst`, `verifier` and the rest. Only the
  `brainrc-*` names install. brainrc's next `apply` or `update` prunes the old links from each tool.
- A pack whose `[extensions.gatework]` still names an old skill or reviewer keeps working: it is
  read as the new name, with a warning that names it, until Gatework 0.9.0. So are the old
  `[extensions]` keys and `[extensions.spec-agent]` table, which were also due to go in 0.8.0.
- Skill and agent text says Gatework, or the `brainrc-gatework` skill, where it said spec-agent.
- `validator.py` no longer imports the alias tables from `brainrc.naming`, so core can drop them.
