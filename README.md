# Gatework

Spec-driven work that takes a ticket to a reviewed pull request through approval gates, for AI
coding assistants. It is [brainrc](https://github.com/brainrc/brainrc)'s default pack: the engine
skill (`brainrc-gatework`), its roles (`agents/`), the ticket connectors and the domain skills.
Registry ID `brainrc/gatework`. `spec-agent` and the other unprefixed names are deprecated
aliases until brainrc 0.8.0.

How it works: [brainrc's docs/spec-agent.md](https://github.com/brainrc/brainrc/blob/main/docs/spec-agent.md).

## Install

With brainrc, there is nothing to do: `brainrc apply` fetches Gatework at the tag core's
`packs.toml` pins and installs it with core. To leave it out, set `enabled = false` under
`[gatework]` in `packs.local.toml` (`brainrc init` offers it). To work on Gatework, point brainrc
at your clone:

```toml
# packs.local.toml in your brainrc checkout or settings home
[gatework]
path = "~/src/gatework"
```

As a plugin, without brainrc's rules and guard hooks:

```text
/plugin marketplace add brainrc/gatework
/plugin install gatework@gatework
```

Codex reads the same `.claude-plugin/` manifest, Cursor reads `.cursor-plugin/`, and Antigravity
CLI installs it with `agy plugin install https://github.com/brainrc/gatework`. In Claude Code the
roles are named `gatework:<role>`.

## Extend it from your own pack

A pack adds domain skills, intake context, a ticket connector and Deliver checks under
`[extensions.gatework]` in its `pack.toml`. Gatework's `validator.py` checks those tables and
renders them into `extensions.md`; brainrc runs it because Gatework is a default pack. The format
is in [brainrc's docs/packs.md](https://github.com/brainrc/brainrc/blob/main/docs/packs.md).

## Develop

Tests and `validate` need brainrc core: clone it beside this repo (`../brainrc`) or set
`BRAINRC_CORE` to a checkout.

```bash
python3 ../brainrc/scripts/brainrc.py validate --pack .
python3 scripts/gatework.py check
python3 -m unittest discover -s tests
```

Rules for changes: [AGENTS.md](AGENTS.md). Each PR adds a fragment to `changelog.d/`.
