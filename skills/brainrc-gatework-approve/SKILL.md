---
name: brainrc-gatework-approve
description: Approve the pending spec-agent gate and continue
argument-hint: [optional notes]
disable-model-invocation: true
---

Using the `brainrc-gatework` skill: approve the gate currently awaiting approval for the spec on
this branch. Record it in `state.json`, then continue the run. Notes to apply first, if any:
$ARGUMENTS

If no gate is pending, say so and do nothing.

If `$ARGUMENTS` appears literally above, this tool didn't fill it in: use what the user typed
with this skill instead.
