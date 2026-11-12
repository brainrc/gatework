---
name: brainrc-gitops
description: GitOps delivery with Argo CD and Flux. How changes flow through config repos, safe promotion across environments, sync ordering, and review of Application/Kustomization/HelmRelease resources. Use when changing GitOps config repos, Argo CD Applications/ApplicationSets, Flux Kustomizations/HelmReleases, or image promotion.
---

# brainrc-gitops

In GitOps the **merge is the deploy**. The controller reconciles `main` into the cluster, so a
PR to a config repo is a production change even though no one runs `apply`.

## Workflow implications for spec-agent
- The Deliver gate for a config repo PR must state **which clusters/environments reconcile
  from the target branch and path**, and whether auto-sync/prune is enabled for them.
- Promote through environments in separate commits or PRs (dev → staging → prod), never one
  change that touches all environments at once unless the spec asks for it.
- Evidence = rendered manifests for every affected environment (see the `brainrc-kubernetes` skill),
  plus `argocd app diff` / `flux diff kustomization` against the approved context when allowed.

## Validate (offline)
```bash
kustomize build <env overlay> | kubeconform -strict -summary -ignore-missing-schemas
helm template ... (for HelmRelease/Application helm sources, with the env's values)
flux build kustomization <name> --path <path> --kustomization-file <file> --dry-run   # Flux, if CLI present
```

## Review checklist
- **Prune and auto-sync**: removing a resource from Git deletes it from the cluster when prune is on.
  Deletions of stateful resources (PVCs, namespaces, CRDs) are CRITICAL.
- Argo: `syncPolicy` changes, `sync-wave`/hook ordering (CRDs and namespaces before workloads),
  `ignoreDifferences` hiding real drift, ApplicationSet generators matching more clusters than intended.
- Flux: `dependsOn` ordering, `interval`/`timeout`, `prune: true`, HelmRelease `upgrade.remediation`,
  `suspend` left on.
- Image updates: tags/digests pinned per environment; automation policies scoped to the right semver range.
- Secrets: SOPS/Sealed Secrets/External Secrets only; decryption keys never in the repo.
- Source revisions: `targetRevision`/`ref` pinned for prod, not floating `HEAD`.

## Never without explicit approval
`argocd app sync|delete|rollback|set|terminate-op`, `flux reconcile|suspend|resume|delete`,
disabling auto-sync or prune, editing cluster secrets. Break-glass changes bypass Git and
must be reconciled back into Git afterwards.
