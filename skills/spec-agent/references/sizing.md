# Sizing

Ceremony scales with risk. Score the work item on each signal, take the **highest**
tier any signal reaches, and state it in one line:
`Size: small (1 file, no new deps, behavior is clear). Say "resize <tier>" to override.`

| Tier | Files touched | New dependency / contract | Ambiguity |
|---|---|---|---|
| trivial | 1 file, a few lines | none | none, the change is obvious |
| small | 1–2 files | none | clear once the code is read |
| standard | 3–10 files | maybe an internal module | at least one real design choice |
| large | many / cross-cutting | new external dep, public API, migration | several open questions |

**Changed lines** temper the Files column only. Roughly 30 changed lines or fewer score at most
`small` on that column, however many files they touch. New self-contained example or doc files
(nothing else imports them) and test lines count about half. The other columns still apply, so a short diff
with a real design choice is still `standard`.

**Floors:** at least `standard` for anything touching a security trigger (see the
[security-checklist](../../security-checklist/SKILL.md) skill), a public API, IAM/RBAC, network
exposure, shared Terraform modules or charts, prod environment config, GitOps prod paths, or
schema migrations.

## Stage mask

| Tier | Stages | Gates |
|---|---|---|
| trivial | intake → implement → verify → deliver → done | Deliver |
| small | intake → spec (light) → implement → verify → document → deliver → done | Spec, Deliver |
| standard | all | Spec, Plan, Deliver |
| large | intake → spec, then **propose a split** into smaller tickets | Spec, then stop |

- **Light spec** (small): 1–3 acceptance criteria, no plan stage. The engine writes a
  one-task `plan.md` itself and runs it inline (no subagents; see [efficiency.md](efficiency.md)).
- **Trivial**: the engine still writes a one-line `spec.md` (the criterion) and a one-task
  `plan.md`, so verify and retro work the same way. There is no document stage, so before the
  Deliver gate the engine writes a short `pr-body.md` and `ticket-comment.md` itself from the
  templates. Runs inline, no subagents.
- **Large**: after the Spec gate, write proposed child tickets (title + criteria each) in
  `spec.md` under "Proposed split". Create them only on approval (outward action).
- Record skipped gates as `"skipped"` in `state.gates`.
