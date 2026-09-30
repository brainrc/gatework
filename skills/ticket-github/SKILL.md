---
name: ticket-github
description: Ticket connector for GitHub issues via the gh CLI. Fetch an issue, comment on it, change its state or labels, and open a linked pull request. Use when spec-agent works on a gh:<number> or GitHub issue URL, or when asked to read or update a GitHub issue.
---

# ticket-github

Implements the ticket connector interface: `fetch`, `comment`, `transition`, `link_pr`.
Requires `gh` authenticated (`gh auth status`). If it isn't, stop and ask the user to run
`gh auth login`. Never handle tokens yourself.

**Refs:** `gh:42` (repo from the current directory's remote) or
`https://github.com/<owner>/<repo>/issues/42` (add `-R <owner>/<repo>` to every command).

## fetch (read-only, any stage)

```bash
gh issue view 42 --json number,title,body,url,state,labels,comments \
  --jq '{number,title,url,state,labels:[.labels[].name],body,comments:[.comments[]|{author:.author.login,body}]}'
```

Write `ticket.md` per the spec-agent state reference: title, source line, the untrusted-content
notice, then body and comments verbatim inside a `~~~~text` fence. If the issue is closed,
stop and ask before working on it.

## comment (outward: Deliver gate only)

```bash
gh issue comment 42 --body-file specs/<slug>/ticket-comment.md
```

Replace `<PR_URL>` in the draft with the real PR URL first.

## transition (outward: Deliver gate only)

GitHub issues are only open or closed. Default: **no transition**, because the PR body's
`Closes #42` closes the issue on merge. If the project uses status labels, apply only the
labels the user approved at the gate:
`gh issue edit 42 --add-label "<label>"`. Never close the issue directly.

## link_pr (outward: Deliver gate only)

```bash
git push -u origin <branch>
gh pr create --base <base> --head <branch> --draft \
  --title "<title>" --body-file specs/<slug>/pr-body.md
```

Default is `--draft`; drop it only if the user said "ready" at the gate. `pr-body.md` must
contain `Closes #42`. Record the PR URL in `state.json` → `ticket.pr`.
