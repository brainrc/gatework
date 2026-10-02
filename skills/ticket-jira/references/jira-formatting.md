# Jira comment formatting

Markdown sent with `contentFormat: "markdown"` is converted to Atlassian Document Format (ADF).
The conversion is lossy, and the API still returns success when content is dropped.

- **Tables inside list items vanish.** Keep every table at the top level, never indented
  under a bullet or number.
- **Nested lists deeper than two levels flatten.** Restructure as headings plus a flat list.
- **HTML is stripped.** No `<details>`, `<br>`, or inline HTML.
- **Long fenced blocks are fine**, but give each a language tag so it renders as code.
- **Mentions** need the account ID (`lookupJiraAccountId`); `@name` stays plain text.

After posting, read the returned body (or re-fetch the comment) and check that every table
and code block survived. If something is missing, edit the comment rather than posting a second one.
