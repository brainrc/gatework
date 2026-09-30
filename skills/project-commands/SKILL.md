---
name: project-commands
description: Discover a project's test, lint, typecheck, build, and format commands from its manifests and docs, and record a verified baseline. Use at the start of spec-agent work, or whenever you need to know how to test or build an unfamiliar project.
---

# project-commands

Goal: one command per purpose, verified to run, recorded in `state.json` → `commands`.

## Precedence (first match wins per purpose)

1. **Project instructions**: `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`, README "Development" sections.
2. **Task runners**: `Makefile` / `justfile` / `Taskfile.yml` targets named test, lint, build, fmt/format, check.
3. **Manifests:**

| File | test | lint | build |
|---|---|---|---|
| `package.json` | `<pm> test` (if a `test` script exists) | `<pm> run lint` | `<pm> run build`; also `typecheck` if present |
| `pyproject.toml` / `setup.cfg` | `pytest -q` if pytest is configured or a dependency, else `python3 -m unittest` | `ruff check .` if configured | — |
| `go.mod` | `go test ./...` | `go vet ./...` | `go build ./...` |
| `Cargo.toml` | `cargo test` | `cargo clippy -- -D warnings` | `cargo build` |
| `*.csproj` / `*.sln` | `dotnet test` | — | `dotnet build` |

Infra and config domains fill `validate` (offline) and `plan` (live, targets only) instead;
exact commands are in each domain skill:

| Signal | validate | plan |
|---|---|---|
| `*.tf` / `terragrunt.hcl` | `terraform`: fmt -check, validate, tflint, test | terraform/terragrunt plan |
| `Chart.yaml` / `kustomization.yaml` / k8s YAML | `kubernetes`: helm lint, render + kubeconform | kubectl/helm diff |
| `.github/workflows/` | `ci-pipelines`: actionlint, zizmor | — |
| `Dockerfile` | `containers`: hadolint, local build | — |
| Prometheus rules / collector config | `observability`: promtool, otelcol validate | — |
| `*.sh` | `scripting`: shellcheck | — |
| `.pre-commit-config.yaml` | `pre-commit run --files <changed files>` (covers many of the above) | — |

In monorepos, record a list (one command per stack/module) and scope runs to changed paths.

`<pm>` comes from the lockfile: `pnpm-lock.yaml` → pnpm, `yarn.lock` → yarn,
`bun.lockb`/`bun.lock` → bun, otherwise npm.

## Baseline

Run the test command once (output to `.runs/baseline.log`, read the summary only).
- Passing → record the command.
- Failing before any change → record `commands.baseline_failures` (test names) so later
  stages don't blame the new work. Tell the user in one line.
- Won't run (missing toolchain) → stop and ask. Never install toolchains or dependencies
  without approval.

Don't guess commands that the project doesn't define. Record `null` and say so.
