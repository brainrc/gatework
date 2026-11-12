---
name: brainrc-observability
description: Monitoring and alerting as code. Prometheus recording/alerting rules, Grafana dashboards, OpenTelemetry collector config, SLO-based alerts, and instrumentation in services. Use when changing alert rules, dashboards, OTel/collector config, or adding metrics/traces/logs to a service.
---

# brainrc-observability

## Validate (offline)
```bash
promtool check rules <rules.yaml>
promtool test rules <tests.yaml>            # unit tests for alerts, if present (add them for new alerts)
amtool check-config alertmanager.yml         # Alertmanager config
otelcol validate --config <collector.yaml>   # or the distro binary, e.g. otelcol-contrib
jq empty <dashboard>.json                    # dashboards are valid JSON; jsonnet/grafonnet: build then check
```
PrometheusRule CRDs: extract `.spec` and run promtool on it.

## Alert quality
- Alert on symptoms users feel (error rate, latency, saturation), not every cause. Prefer SLO
  multi-window burn-rate alerts over static thresholds for services with SLOs.
- Every alert has `for:` (no flapping), `severity` label matching routing, and annotations
  `summary`, `description` with current value, and `runbook_url`. The runbook exists before
  the alert ships (the brainrc-runbook skill); a placeholder URL is a blocker.
- Paging alerts must be actionable by the on-call person; everything else is a ticket or dashboard.
- New alerts ship with a `promtool test rules` case covering fire and no-fire.

## Metrics and instrumentation
- Label cardinality: no user IDs, request IDs, raw paths, or unbounded values as labels (CRITICAL
  for Prometheus stability). Route templates, not raw URLs.
- Naming: `<namespace>_<name>_<unit>` with base units (`_seconds`, `_bytes`), `_total` for counters.
- Histograms for latency, with buckets that match SLO thresholds.
- Services: RED metrics on every endpoint, OTel traces with context propagation across calls,
  structured logs carrying the trace ID. Never log secrets or full request bodies.

## Review checklist
- Recording rules used by dashboards/alerts still exist after renames.
- Queries: `rate()` over counters (not `irate` for alerts), range ≥ 4× scrape interval,
  `sum by` keeps the labels routing needs.
- Dashboard changes: datasource variables, not hardcoded UIDs; panels have units.
- Collector pipelines: memory_limiter first, batch processor, no debug exporter left in prod.
