---
bump: patch
---
- `requires_core` allows brainrc core 0.8 (`>=0.7, <0.9`). Core 0.8.0 moved the lock to version 2
  for pack permissions and changes nothing Gatework depends on; with the old `<0.8`, `apply` on
  core 0.8.0 refused the default pack.
