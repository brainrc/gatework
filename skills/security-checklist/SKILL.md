---
name: security-checklist
description: Security triggers and review checklist for code changes (injection, authn/authz, secrets, input handling, filesystem, deserialization, crypto, dependencies). Use to decide whether a change needs security review, and as the checklist when performing one.
---

# security-checklist

## Triggers
A change needs security review (and is at least `standard` size in spec-agent) if it touches:
authentication or authorization · user or external input parsing · database queries ·
shell/process execution · filesystem paths from input · network calls or URL fetching ·
HTML/template rendering · deserialization · cryptography, tokens, sessions · secrets or
config loading · dependency manifests or lockfiles · CI/CD workflows · permissions/roles.

## Checklist
| Area | Look for |
|---|---|
| Injection | String-built SQL/shell/LDAP/XPath; use parameterized queries and arg arrays, never `shell=True` with input |
| Paths | Traversal (`../`), symlink following, writes outside intended dirs; normalize, then check the prefix |
| AuthZ | Checks on every entry point, object-level ownership (IDOR), no trust in client-supplied roles/ids |
| AuthN / sessions | Constant-time compares, expiry checked, tokens not logged, secure cookie flags |
| Input | Size limits, type/format validation at the boundary, regex DoS (nested quantifiers) |
| Output | HTML escaping by default, no raw `innerHTML`/`| safe` with input, correct content types |
| SSRF | Fetching user-supplied URLs: allowlist hosts, block internal ranges and redirects to them |
| Deserialization | No `pickle`/`yaml.load`/`eval`/Java native deserialization on untrusted data |
| Secrets | None in code, tests, logs, errors, or fixtures; read from env/secret store |
| Crypto | Vetted libraries, no custom crypto, no MD5/SHA1 for security, CSPRNG for tokens |
| Dependencies | New packages: maintained, expected name (typosquats), pinned via lockfile, license compatible |
| Errors | No stack traces or internals returned to clients; failures closed, not open |
| CI/CD | No secrets echoed, pinned action versions, least-privilege `permissions:` |

Report only what applies to the diff.

## Infrastructure and delivery
| Area | Look for |
|---|---|
| Cloud IAM | Wildcard actions/resources, broad `PassRole`/`AssumeRole`, OIDC trust without `sub` pinning (see `aws` skill) |
| Network | `0.0.0.0/0` ingress, public DBs/buckets, missing NetworkPolicy for sensitive workloads |
| Kubernetes | privileged, hostPath/hostNetwork, root containers, `*` RBAC, default SA token automount |
| State and secrets | Secrets in tfvars/values/manifests/plan files, unencrypted state backends, SOPS keys committed |
| Pipelines | Script injection from event data, `pull_request_target` with PR code, unpinned third-party actions, long-lived cloud keys |
| Supply chain | Unpinned base images/charts/modules, pipe-to-shell installs, registries or module sources outside the org's allowlist |
