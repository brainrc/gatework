# Instructions for AI assistants editing this repo

This repo is public. It is Gatework, brainrc's default pack; brainrc core is
[brainrc/brainrc](https://github.com/brainrc/brainrc), and its AGENTS.md applies here too.

- Never add secrets, tokens, personal emails, internal hostnames, or absolute paths like
  `/Users/<name>`. Keep it generic: no employer or client names; examples use "acme".
- Skills: `skills/<name>/SKILL.md` with frontmatter `name` (equal to the directory name) and
  `description` (what it does and *when* to use it). New names start with `brainrc-`.
- Agents: `agents/<name>.md` with frontmatter `name` (equal to the file stem), `description`,
  `model` (`haiku|sonnet|opus|inherit`) and least-privilege `tools`. New names start with `brainrc-`.
- Domain skills (`skills/brainrc-<stack>/`) follow: Validate (offline commands) / Conventions /
  Review checklist / Never without approval. Register each in the Domains table of
  `skills/brainrc-gatework/SKILL.md`, with a positive and a negative case in `evals/triggers.toml`.
- `skills/brainrc-gatework/roles` is a symlink to `../../agents`; keep every link inside the repo.
- Keep `validator.py` and `scripts/` stdlib-only (Python 3.11+). `validator.py` may import the
  `brainrc` package that loads it; nothing else here imports brainrc outside `tests/`.
- Keep files short: they are loaded into model context.
- After changes, with brainrc cloned at `../brainrc`: `python3 ../brainrc/scripts/brainrc.py
  validate --pack .`, `python3 scripts/gatework.py check` and `python3 -m unittest discover -s tests`.
- Every PR adds one fragment, `changelog.d/<branch>.md` (`bump:` + bullets, see its README).
  Don't edit `VERSION`, `CHANGELOG.md` or the plugin manifests (`.claude-plugin/`,
  `.cursor-plugin/`, `plugin.json`): the release workflow updates them and tags on merge.
