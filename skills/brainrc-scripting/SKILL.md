---
name: brainrc-scripting
description: Python and Bash operational tooling. CLIs, automation scripts, and glue code, with linting, testing, safe subprocess and file handling, and conventions for idempotent, dry-run-capable ops scripts. Use when writing or reviewing *.py tooling, *.sh scripts, or ops automation.
---

# brainrc-scripting

## Commands
```bash
ruff check . && ruff format --check .     # if configured (pyproject/ruff.toml)
mypy <pkg> / pyright                      # if configured
pytest -q  (or python3 -m unittest)       # per brainrc-project-commands
shellcheck <changed *.sh>
shfmt -d <changed *.sh>                   # if the repo uses it
```
Use the repo's env manager (uv, poetry, pip-tools, venv); don't introduce another.

## Ops script conventions (both languages)
- **Dry run by default or via `--dry-run`**: print intended changes, and mutate only with `--apply`/`--yes`.
- Idempotent: safe to re-run after partial failure; check state before changing it.
- Explicit targets: account/cluster/env passed as arguments and echoed before acting. No implicit defaults for prod.
- Exit codes: 0 success, non-zero with a clear stderr message; no silent `except: pass`.
- Logs to stderr, machine-readable results to stdout (JSON when consumed by other tools).

## Python
- `argparse` (stdlib) or the repo's CLI library; `main() -> int` with `sys.exit(main())`.
- `subprocess.run([...], check=True, text=True)` with argument lists, never `shell=True` with input.
- `pathlib`, context managers for files, `tempfile` for temp data, timeouts on network calls.
- Type hints on public functions; dataclasses for structured data; no mutable default args.

## Bash
- `#!/usr/bin/env bash` + `set -euo pipefail`; quote every expansion; `[[ ]]` for tests.
- `trap 'cleanup' EXIT`, `mktemp -d` for scratch space, `command -v tool >/dev/null || die "needs tool"`.
- Functions with `local` variables; no parsing of `ls`; `read -r`; arrays for argument lists.
- Past ~150 lines or when it needs data structures, it should be Python.

## Review checklist
Injection via unquoted variables or `shell=True`; destructive commands without a confirmation
or dry-run path; hardcoded account IDs/hosts/paths; secrets in argv (visible in `ps`) or logs;
missing error handling on external calls; non-idempotent retries.
