# Changelog fragments

Each PR adds one file here instead of editing `VERSION` or `CHANGELOG.md`. On merge to `main`,
the release workflow runs `python3 scripts/gatework.py release`. That folds every fragment into
`CHANGELOG.md` under the next version, bumps `VERSION` by the largest `bump`, regenerates the
plugin manifests, and tags `v<VERSION>`.

Name the file after your branch (`living-specs.md`). Format:

```markdown
---
bump: patch
---
- What changed and why, as one changelog bullet (several bullets are fine).
```

`bump` follows the policy at the top of `CHANGELOG.md`. `python3 scripts/gatework.py check`
checks every fragment.
