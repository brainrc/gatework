# Verify: <title>

Run at <ISO timestamp> on commit `<sha>`.

## Checks
| Check | Command | Result |
|---|---|---|
| Tests | `<test command>` | pass: N passed, 0 failed |
| Lint | `<lint command>` | pass / not configured |
| Build | `<build command>` | pass / not configured |
| Validate (infra) | `<validate commands>` | pass / not applicable |
| Plan / diff | `<plan or diff command> @ <target>` | `Plan: 1 to add, 1 to change, 0 to destroy` / offline only |

## Acceptance criteria
| Criterion | Evidence | Result |
|---|---|---|
| AC1 | `tests/test_x.py::test_y` passes; <or manual check: exact steps and output> | pass |
| AC2 | ... | pass / fail |

## Notes
<Anything a reviewer should know: flaky tests, manual-only checks, skipped checks and why.>
