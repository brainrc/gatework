---
bump: patch
---
- The roles check accepts git's stand-in for `roles/` (a plain file holding `../../agents`, what a
  checkout without symlinks leaves) when brainrc copies what it points to: copy mode, from the brainrc
  release with `brainrc/gitlinks.py` (#120). Link mode, or an older brainrc, still fails and names the
  stand-in.
