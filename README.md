# Gatework

brainrc's default pack: spec-driven work that takes a ticket to a reviewed pull request through
approval gates. It holds the engine skill, its roles (`agents/`), the ticket connectors and the
domain skills. Registry ID `brainrc/gatework`. The engine is the `brainrc-gatework` skill;
`spec-agent` is a deprecated alias for it until brainrc 0.8.0.

brainrc ships it inside core and turns it on unless `packs.local.toml` says otherwise
(`[gatework] enabled = false`, which `brainrc init` offers). Without it, brainrc installs only
core's rules and guard hooks.

This folder is self-contained so it can move to its own repository unchanged. Its links stay
inside it, apart from this page's link to the docs; `validator.py` imports the `brainrc` package
that loads it; and the proof guard finds core's secret patterns through the installed hooks when
core's checkout isn't beside it. How it works: [docs/spec-agent.md](../../docs/spec-agent.md).
