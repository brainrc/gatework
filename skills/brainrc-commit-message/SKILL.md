---
name: brainrc-commit-message
description: Write a clear git commit message for staged changes. Use when the user asks to commit, or asks for a commit message.
---

# Commit message

1. Run `git diff --staged` (fall back to `git diff` if nothing is staged, and say so).
2. Identify the single main purpose of the change. If there are several unrelated
   purposes, suggest splitting the commit.
3. Write:
   - Subject: imperative mood, 72 chars or fewer, no trailing period
     (e.g. "Fix token expiry check").
   - Blank line.
   - Body: *why* the change was made and any non-obvious consequences. Wrap at 72.
4. Show the message and wait for approval before running `git commit`. Exception: inside a
   spec-agent run (`/brainrc-work`), commits on the run's own feature branch are already authorized,
   so commit without asking.
