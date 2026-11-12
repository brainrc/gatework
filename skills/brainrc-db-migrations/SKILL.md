---
name: brainrc-db-migrations
description: Safe database schema and data migrations (Postgres-first; golang-migrate, goose, Atlas, Alembic, Flyway), expand/contract changes, locking risks, and backfills. Use when adding or reviewing migration files, changing schemas, or writing data backfills.
---

# brainrc-db-migrations

## Rules
- Migrations run **only against local/ephemeral databases** during a work item (docker/testcontainers).
  Running them against any shared environment is a deployment: explicit approval only.
- Every migration is tested up **and** down (or documented as irreversible in the plan).
- Schema changes that affect running code use **expand → migrate → contract** across separate
  deploys: add the new column/table (nullable or defaulted) → dual-write/backfill → switch reads →
  drop the old one in a later release. Never rename or drop in the same release that stops using it.
- Migrations are immutable once merged; fix forward with a new migration.

## Local verification
```bash
docker run -d --rm --name mig-pg -e POSTGRES_PASSWORD=dev -p 55432:5432 postgres:16
# then run the repo's tool against localhost:55432: up → down → up, and the app's tests
```
Use the repo's migration tool and version; don't introduce a new one.

## Postgres locking review
- `CREATE INDEX` → `CREATE INDEX CONCURRENTLY` (outside a transaction; most tools need a flag or
  a no-transaction directive).
- Adding a column with a volatile default, changing column types, or adding `NOT NULL` rewrites or
  scans the table under `ACCESS EXCLUSIVE`. Instead: add nullable → backfill → add
  `CHECK (...) NOT VALID` → `VALIDATE CONSTRAINT` → set `NOT NULL`.
- Foreign keys: `ADD CONSTRAINT ... NOT VALID`, then `VALIDATE CONSTRAINT` separately.
- Set `lock_timeout` (e.g. `SET lock_timeout = '5s'`) in migrations touching hot tables.

## Backfills
Batched (by primary key range), idempotent, resumable, throttled, run as a job, not inside the
schema migration. Report row counts before/after.

## Review checklist
- Data loss: `DROP`/`TRUNCATE`/type narrowing/`DELETE` without a spec requirement → CRITICAL.
- Long locks on large tables, missing `CONCURRENTLY`, one transaction containing both DDL and backfill.
- ORM model and migration out of sync; down migration that doesn't restore the previous state.
- Sensitive columns: encryption/masking, and excluded from logs and fixtures.
