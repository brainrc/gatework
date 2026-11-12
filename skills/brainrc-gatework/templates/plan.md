# Plan: <title>

Spec: [spec.md](spec.md) · Status: draft | approved

## Callouts
Must be empty or explicitly approved at the Plan gate:
- **New dependencies:** none | <name@version: why, alternatives considered>
- **Public API / contract changes:** none | <what changes, who is affected>
- **Migrations / data changes:** none | <what, how to roll back>
- **Security triggers touched:** none | <which, see brainrc-security-checklist>
- **Domains:** <e.g. brainrc-go-service, terraform, aws>
- **Environments affected on deploy:** <which envs/clusters/accounts change after merge, via what (apply, Atlantis, GitOps sync)>
- **Destructive or replacing changes:** none | <resources deleted/replaced and why>

## Approach
<How the change works, in 1–3 short paragraphs. Name the existing modules and
functions it reuses. Explain the one or two real design choices and why this option won.>

## Files
| File | Change |
|---|---|
| `path/to/file` | <new / modify: what> |

## Risks
- <risk>, mitigated by <how>

## Test strategy
<Which criteria get unit, integration, or manual tests. Where the tests live.>

## Tasks
Ordered; one commit each. `files` is the scope fence: only these files (new ones included)
may change. Keep each task under ~200 changed lines. Default agent is `brainrc-implementer`
(writes its own failing test first). Use `brainrc-test-writer` only when independent test
authorship matters (security logic, public contracts). Add `review: each` to tasks that
touch security logic, a public contract, IAM, network exposure, migrations, or prod config, or
that exceed ~150 changed lines; all others are reviewed once, in a batch. Add `after: T1` when a
task needs another task's code; tasks with no `after:` and no shared files may run in parallel.

- [ ] **T1** [agent: brainrc-implementer] <vertical slice 1>
  - files: `src/feature.py`, `tests/test_feature.py`
  - criteria: AC1, AC2
- [ ] **T2** [agent: brainrc-test-writer] Contract tests for <public API>
  - files: `tests/test_api_contract.py`
  - criteria: AC3
  - review: each
- [ ] **T3** [agent: brainrc-implementer] Implement <public API> to pass T2
  - files: `src/api.py`
  - criteria: AC3
  - review: each
  - after: T2
