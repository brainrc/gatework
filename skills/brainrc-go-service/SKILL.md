---
name: brainrc-go-service
description: Go services and CLIs. Build/test/lint commands, idioms for errors, context, concurrency, HTTP servers, and testing, plus a review checklist for common Go bugs. Use when writing, changing, or reviewing *.go files or go.mod.
---

# brainrc-go-service

## Commands
```bash
gofmt -l . | tee /dev/stderr | (! read)      # must print nothing
go vet ./...
golangci-lint run ./...                     # if .golangci.* exists
go test ./<changed pkgs>/... -count=1       # during implement: changed packages only
go test ./... -race -count=1                # verify: everything, with the race detector
go build ./...
go mod tidy -diff                           # Go 1.23+; must print nothing
govulncheck ./...                           # if installed
```
Save output to `.runs/`; for failures, `grep -n -E -- '--- FAIL|panic:|DATA RACE' .runs/test.log`.

## Idioms
- Errors: wrap with context, `fmt.Errorf("load config %s: %w", path, err)`; `errors.Is/As` for checks;
  sentinel or typed errors for callers that branch; no `panic` outside `main`/init invariants.
- `context.Context` is the first parameter on anything doing I/O; honor cancellation; set timeouts.
- Interfaces are defined where they're consumed and kept small; return concrete types.
- Concurrency: `errgroup` for fan-out with error propagation; every goroutine has a way to stop;
  guard shared state or pass ownership over channels.
- HTTP servers: set `ReadHeaderTimeout` (and read/write/idle timeouts), graceful shutdown via
  `signal.NotifyContext` + `srv.Shutdown(ctx)`, health/readiness endpoints.
- Logging: `log/slog` with structured fields; no secrets in logs.
- Config from env/flags, validated at startup, failing fast with a clear message.
- Tests: table-driven with `t.Run`; `t.Parallel()` where there's no shared state; `httptest` for
  handlers; `t.TempDir()`/`t.Setenv()` over manual cleanup; no sleeps for synchronization.

## Review checklist
- Unchecked errors, especially `Close`, `Write`, `json.Unmarshal`, `rows.Err()`.
- `resp.Body` not closed; `defer` inside loops; `time.After` in long-lived loops (leak).
- Data races: maps written from goroutines, captured variables (check `go` version in go.mod; per-iteration loop vars since 1.22).
- Nil map writes, nil interface vs typed-nil pointer returns.
- Goroutines blocked forever on unbuffered channels when the receiver has returned.
- Exported API changes (breaking for importers). Call them out in the plan.
