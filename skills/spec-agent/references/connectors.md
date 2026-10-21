# Ticket connector contract

A connector is a skill that lets spec-agent read and update one ticket system. Core ships
`ticket-local`, `ticket-github`, and `ticket-jira`. A pack can name its own in
`[extensions.ticket]` (one per pack).

## Operations

Each operation is a `##` heading in the connector's SKILL.md. One heading may cover several
(`## comment / transition / link_pr`). `validate` fails when a required one has no heading.

| Operation | Required | Kind | Allowed | Does |
|---|---|---|---|---|
| `fetch` | yes | read-only | any stage | Reads one ticket. Writes `ticket.md` (state.md format), body and comments fenced as untrusted. Stops and asks if the ticket is closed. |
| `list` | for campaign mode | read-only | any stage | Lists candidate tickets (epic, label, query). Light fields only until one is chosen. |
| `dependencies` | no | read-only | any stage | Ordered campaigns only. Per child returns `{ "source": "api" \| "body" \| "frontmatter" \| "none", "depends_on": ["<ref>", ...] }`, refs in `members[].ref` form (`gh:12`, `local:tickets/005-x.md`). Also gives the epic's child order (`list`) and a predecessor PR's merged state. Without it, ordered shape is unavailable. |
| `claim` | no | outward | intake, with approval | Assigns the ticket and moves it to an in-progress status. |
| `comment` | yes | outward | after the Deliver gate | Posts `ticket-comment.md` with `<PR_URL>` filled in. |
| `transition` | yes | outward | after the Deliver gate | Applies only the status or labels approved at the gate. Never sets a status only a human may set. May be a documented no-op. |
| `link_pr` | yes | outward | after the Deliver gate | Pushes the branch, opens the PR from `pr-body.md`, records the URL in `state.json` → `ticket.pr`. |

## Local-only delivery

With `delivery: local-only`, outward operations don't run. The connector finalizes the drafts
instead (`PR: none (local-only, branch <branch>)`) and says how it blocks pushes, if at all.

## Implementation

An operation can use a CLI (`gh`, `glab`) or an MCP server's tools. If a connector supports
both, list each operation's equivalent so a session without the CLI can still run it.
Credentials stay with the CLI or server: a connector never reads or prints tokens.

`validate` checks headings only. It can't tell whether an operation works. Run a sandbox
ticket through the connector before relying on it.
