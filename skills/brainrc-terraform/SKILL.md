---
name: brainrc-terraform
description: Terraform/OpenTofu and Terragrunt conventions, offline validation, plan evidence, and review checklist. Use when writing, changing, or reviewing *.tf, *.tfvars, .terraform.lock.hcl, or terragrunt.hcl files.
---

# terraform

`tofu` works wherever `terraform` appears below. Use whichever the repo pins
(`.terraform-version`, `.tool-versions`, CI config).

## Validate (offline, always allowed)
Run per changed root/module directory, not the whole repo:
```bash
terraform fmt -check -recursive -diff
terraform init -backend=false -input=false >/dev/null && terraform validate
tflint --recursive              # if .tflint.hcl exists
terraform test                  # if *.tftest.hcl exist
trivy config . / checkov -d .   # only if the repo already uses one
```
Terragrunt: `terragrunt hclfmt --check`, then validate per unit. Never `run-all` without scoping.

## Plan (reads real state and cloud: only against the target approved at intake)
```bash
terraform plan -input=false -lock=false -out=specs/<slug>/.runs/tfplan > specs/<slug>/.runs/plan.log 2>&1
grep -E '^Plan:|^No changes' specs/<slug>/.runs/plan.log
terraform show -json specs/<slug>/.runs/tfplan | jq -c '[.resource_changes[] | select(.change.actions != ["no-op"]) | {a: .address, x: .change.actions}]'
```
Record the `Plan:` line plus the non-no-op actions as evidence. **Any `delete` or
`["delete","create"]` (replace) is a stop**: surface it to the user unless the spec explicitly asks for it.
Never commit plan files; they can contain secrets.

## Terragrunt, Atlantis, Spacelift
- **Terragrunt**: validate/plan per unit (`terragrunt plan --terragrunt-non-interactive` in the unit dir).
  `dependency` blocks need `mock_outputs` (+ `mock_outputs_allowed_terraform_commands = ["validate","plan"]`)
  for offline validation. `run-all` only with `--terragrunt-include-dir` scoping, and never for apply/destroy.
- **Atlantis / Spacelift**: plans run on the PR. After Deliver, their plan output on the PR is the
  authoritative evidence: read it (`gh pr view <n> --comments`) and record the `Plan:` lines in
  `verify.md`. Commenting `atlantis apply` or confirming a Spacelift run is a deployment: explicit approval only.
- Check `atlantis.yaml` / Spacelift stack config when adding new roots, so the new directory is
  actually planned (autoplan `when_modified` patterns, project dirs, workspaces).

## Conventions
- Pin `required_version` and providers (`~>`) in `required_providers`; commit `.terraform.lock.hcl`.
- Variables: `type`, `description`, `validation` where values are constrained; no hardcoded
  account IDs, regions, or ARNs.
- `for_each` over `count` for named collections (stable addresses).
- Refactors that rename or move resources use `moved {}` blocks, never `state mv`.
- `lifecycle { prevent_destroy = true }` on stateful resources (databases, buckets, KMS keys).
- Tags via provider `default_tags`; outputs holding secrets get `sensitive = true`.
- Secrets come from a secret manager or data source. Never from committed tfvars.

## Review checklist
- Address changes that recreate resources (missing `moved`), `force_new` attribute edits.
- IAM: no `*` actions/resources without a justification; least-privilege trust policies.
- Networking: no `0.0.0.0/0` ingress except intended public LBs; no public buckets or DBs.
- Perpetual diffs (timestamps, unordered lists, `ignore_changes` masking real drift).
- Encryption at rest/in transit enabled; backend state encrypted and locked.
- Blast radius: which environments consume this module and would change on next apply.

## Never without explicit approval
`apply`, `destroy`, `import`, `state rm|mv|push|replace-provider`, `force-unlock`,
`workspace delete`, `taint`. Applying is a deployment, not part of implementing a task.
