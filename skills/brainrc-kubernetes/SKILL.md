---
name: brainrc-kubernetes
description: Kubernetes manifests, Helm charts, and Kustomize overlays. Offline rendering and schema validation, production-readiness conventions, and review checklist. Use when writing, changing, or reviewing Kubernetes YAML, Chart.yaml/values*.yaml/templates, or kustomization.yaml.
---

# brainrc-kubernetes

## Validate (offline, always allowed)
Render first, then validate the rendered output, since templates alone prove little:
```bash
helm lint <chart> -f <values>
helm template <release> <chart> -f <values> > specs/<slug>/.runs/rendered.yaml
kustomize build <overlay> > specs/<slug>/.runs/rendered.yaml       # or: kubectl kustomize
kubeconform -strict -summary -ignore-missing-schemas specs/<slug>/.runs/rendered.yaml
yamllint -s <changed files>        # if the repo has a yamllint config
```
Use conftest/kyverno/polaris only if the repo already has policies. Render **every**
values file or overlay the change affects (dev and prod), not just the default.

## Cluster reads (only against the context approved at intake)
Always name the context: `kubectl --context <ctx> diff -f ...`, `helm diff upgrade`
(plugin). Evidence = the diff summary. Never rely on the current-context default.

## Conventions
- Resource requests on every container; memory limits; CPU limits only if the platform wants them.
- Readiness and liveness probes (startup probe for slow starts); probes don't share failure modes with dependencies.
- `securityContext`: `runAsNonRoot`, `readOnlyRootFilesystem`, `allowPrivilegeEscalation: false`,
  `capabilities.drop: [ALL]`, `seccompProfile: RuntimeDefault`.
- Images pinned by version (digest where the platform supports it), never `:latest`.
- `app.kubernetes.io/*` labels; explicit namespaces; PodDisruptionBudget for replicated workloads.
- Secrets via External Secrets / Sealed Secrets / SOPS, never plain `Secret` manifests with data.
- Helm: values documented, defaults safe, `required` for mandatory values, no logic-heavy templates.

## Review checklist
- **Immutable fields**: Deployment/StatefulSet `selector`, `volumeClaimTemplates`, Service `clusterIP`,
  Job templates. Changing them forces delete/recreate, so flag it.
- Rollout safety: `maxUnavailable`/`maxSurge`, PDB vs replica count, HPA vs fixed `replicas` conflicts.
- RBAC: no `*` verbs/resources, no cluster-admin bindings for workloads, no default ServiceAccount token automount where not needed.
- Network exposure: new `LoadBalancer`/`NodePort`/Ingress hosts, missing NetworkPolicy.
- `hostPath`, `hostNetwork`, `privileged`: CRITICAL unless the spec requires them.
- CRD/API versions still served by the target cluster version.

## Never without explicit approval
`kubectl apply|create|delete|patch|edit|replace|scale|rollout|drain|cordon|label|annotate|exec`,
`helm install|upgrade|uninstall|rollback`, `argocd app sync`, `flux reconcile`: any cluster mutation.
