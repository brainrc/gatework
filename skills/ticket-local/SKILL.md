---
name: ticket-local
description: Ticket connector for work items stored as markdown files in the repo, for offline work, personal projects, and testing spec-agent. Use when spec-agent works on a local:<path> ref or a free-text request, or when asked to create or update a local ticket file.
---

# ticket-local

Implements the ticket connector interface: `fetch`, `comment`, `transition`, `link_pr`.

## File format

```markdown
---
id: 7
title: Add --shout flag
status: open            # open | in-progress | done
pr:                     # filled by link_pr
---
Free-form description of the request.
```

Only `title` is required. Missing `id` → use the file name's leading number, or the next
unused number under `specs/`.

## Refs

- `local:path/to/ticket.md`: an existing file.
- Free text (`/work add a --shout flag`): create `specs/tickets/<NNN>-<slug>.md` with the text
  as the body and `status: open`, then treat it as `local:` that file.

## fetch

Read the file and write `ticket.md` per the spec-agent state reference (body inside the
untrusted-content fence, same as any other source).

## comment / transition / link_pr (Deliver stage, after the gate)

These edit a file in the repo, not an external system, but still wait for the Deliver gate
so every connector behaves the same.
- **comment:** append `## Update <ISO date>` plus the text of `ticket-comment.md`, replacing
  `<PR_URL>` with the PR URL, or with `none (branch <branch>)` when no PR was opened.
- **transition:** set `status:` (`in-progress` at intake is allowed without a gate; `done` at deliver).
- **link_pr:** push and open the PR as with ticket-github when a GitHub remote exists (outward,
  gated). Otherwise skip the PR, and record the branch name in `pr:`.
