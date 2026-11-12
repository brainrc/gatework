---
name: brainrc-containers
description: Dockerfiles and Compose files. Lint, build checks, image hardening, and caching conventions. Use when writing, changing, or reviewing Dockerfile*, Containerfile, .dockerignore, or compose*.yaml.
---

# brainrc-containers

## Validate
```bash
hadolint Dockerfile                               # if installed
docker compose config -q                          # compose syntax/interpolation
docker build -t local/<name>:dev . > specs/<slug>/.runs/build.log 2>&1; echo "exit=$?"   # local only
trivy image --severity HIGH,CRITICAL local/<name>:dev   # if the repo uses trivy
```
Building locally is allowed; pushing images is an outward action.

## Conventions
- Multi-stage builds; the final stage contains only the runtime artifact.
- Base images pinned (tag + digest where practical); minimal bases: `distroless`/`scratch` for
  static Go (`CGO_ENABLED=0`), slim/alpine otherwise, consistent with the repo.
- Non-root `USER` with a numeric UID; no `sudo`; read-only-friendly (writes to declared volumes/tmp).
- Layer order for caching: copy dependency manifests → download deps → copy source → build.
  Use BuildKit cache mounts (`--mount=type=cache`) for module/package caches.
- `.dockerignore` excludes `.git`, local env files, build outputs, and `specs/*/.runs`.
- Exec-form `ENTRYPOINT`/`CMD`; one main process; handle SIGTERM (graceful shutdown).
- `HEALTHCHECK` for Compose/standalone use (Kubernetes uses probes instead).
- OCI labels (`org.opencontainers.image.source`, `.revision`).

## Review checklist
- Secrets in `ARG`/`ENV`/copied files or left in layers. Use `--mount=type=secret`: CRITICAL if violated.
- `curl | sh` installs, unpinned package versions, `apt-get` without `--no-install-recommends` and list cleanup.
- Running as root, `--privileged` / `cap_add` in Compose, host network, docker.sock mounts.
- `latest` tags; a build context sending the whole repo (missing `.dockerignore`).

## Never without explicit approval
`docker push`, `docker login`, registry tag deletion, `docker system prune -a` on shared hosts.
