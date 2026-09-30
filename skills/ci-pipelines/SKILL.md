---
name: ci-pipelines
description: CI/CD pipeline authoring and review for GitHub Actions (primary) and GitLab CI, plus shell scripts used in pipelines. Linting, security (injection, pinning, permissions), and conventions. Use when changing .github/workflows/*, action.yml, .gitlab-ci.yml, or pipeline shell scripts.
---

# ci-pipelines

## Validate (offline)
```bash
actionlint                         # GitHub Actions; runs shellcheck on run: blocks when installed
zizmor .github/workflows           # GH Actions security audit, if installed
shellcheck <changed *.sh>
yamllint -s <changed files>        # if configured
glab ci lint                       # GitLab, if available
```
Pipelines can't be fully proven locally. Criteria that only CI can prove are recorded as
`verify after push: <job name>` in `verify.md` and checked from the PR's checks after Deliver.

## Conventions (GitHub Actions)
- Third-party actions pinned to a full commit SHA with a version comment
  (`uses: owner/action@<sha> # v4.2.0`); first-party `actions/*` at least to a major tag.
- Top-level `permissions: contents: read`; widen per job only as needed.
- Cloud auth via OIDC (`id-token: write` + role assumption), never long-lived keys in secrets.
- `concurrency` group for deploys; `timeout-minutes` on every job.
- Cache keys include the lockfile hash; matrix only where it buys coverage.
- Deploy jobs gated by `environment:` with protection rules; no deploys from `pull_request`.
- Shared steps → composite actions or reusable workflows, not copy-paste.

## Security checklist
- **Script injection**: `${{ github.event.* }}`, `github.head_ref`, or PR titles/bodies interpolated
  into `run:` are CRITICAL. Pass them via `env:` and quote `"$VAR"`.
- `pull_request_target` or `workflow_run` that checks out or runs PR code: CRITICAL.
- Secrets never echoed, never passed to untrusted actions, never in artifact uploads.
- `GITHUB_TOKEN` write scopes justified; `actions/checkout` with `persist-credentials: false`
  when later steps run untrusted code.
- Self-hosted runners not used for public-repo PRs.

## Shell scripts
Follow the `scripting` skill; `run:` blocks longer than ~10 lines move to a script file.

## Never without explicit approval
`gh workflow run`, re-running deploy jobs, editing repo/environment secrets or protection rules.
