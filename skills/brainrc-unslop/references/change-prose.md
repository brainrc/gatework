# Change prose

Section I of the [brainrc-unslop](../SKILL.md) skill: PR descriptions and commit bodies.

## I. PR descriptions and commit bodies

The reader is a reviewer deciding whether to approve, or an engineer running `git log` during an
incident. Both want the reason, not a retelling of the diff.

**Never touch:** the commit subject line (the brainrc-commit-message skill owns it), trailers
(`Co-Authored-By:`, `Refs:`, `Closes #12`), ticket keys, links, SHAs, branch names, pasted
plan or test output, PR template headings and checkboxes, review-request mentions.

56. **Lead with the change, then the reason.**
57. **Don't narrate the diff.** Say what behavior changed.
58. **Rule 32 is inverted here:** name the old behavior, the new one, and what forced the move.
59. **Budget:** PR = change, reason, blast radius, verification, rollback. Commit body: 2 to 5
    lines, only when the subject doesn't carry the why.
60. **Blast radius, plainly:** which environments and resources change, and whether anything is
    destroyed or recreated. "Low risk" is not a blast radius.
61. **No selling the PR.**
62. **No summary section that repeats the body.**
63. **Keep the caveats** ("not tested against staging", "apply dev before prod") at full strength.
