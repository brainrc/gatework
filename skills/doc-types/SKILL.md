---
name: doc-types
description: Classify a document into one of the four Divio documentation types (tutorial, how-to guide, reference, explanation) and write it in that type's shape, splitting mixed docs and linking instead of copying. Use before writing or restructuring any README section, wiki page, guide, runbook, ADR, or reference table, or when asked "what kind of doc is this" or to apply Divio or Diataxis.
---

# Doc types (Divio)

Every doc serves exactly one reader need. Mixing needs is the most common reason docs fail: a
how-to that stops to explain history, or a reference table buried in a tutorial. Pick the type
first, write to its shape, and link to the other types instead of copying them.

## 1. Classify

Ask what the reader is doing when they open the doc:

| The reader is... | Type | Example |
|---|---|---|
| learning, new to this, guided by you | **Tutorial** | onboarding walkthrough, first deploy |
| at work, trying to get a specific thing done | **How-to guide** | runbook, migration steps, "add a new service" |
| at work, looking up a fact | **Reference** | config keys, account/profile tables, API, CLI flags |
| studying, trying to understand why | **Explanation** | ADR, architecture overview, design rationale |

State the type in one line before writing. If the request covers more than one, it is more than
one doc: write each separately and link them (step 3).

## 2. Write to the type's shape

| | Tutorial | How-to guide | Reference | Explanation |
|---|---|---|---|---|
| Goal | the reader succeeds once, learning by doing | the reader's goal is done | the reader finds the fact | the reader understands |
| Shape | numbered lesson with a visible result at each step | prerequisites → numbered steps → verify → rollback | structured lists and tables, ordered like the thing described | prose, argued, with context and alternatives |
| Must have | one safe, fixed path that works | one action per step, expected output, the error path | completeness and accuracy | the why, trade-offs, what was rejected |
| Must not have | choices, alternatives, deep explanation | background, history, design rationale, full fact tables | instructions or opinions | steps to follow, exhaustive facts |
| Title | "Get started with X", "Your first X" | "How to <do X>" | "<X> reference" | "About X", "Why X", ADR-NNNN |

Shape rules that are easy to break:

- **How-to:** assume the reader is competent and busy. A fact they need to act on (one limit, one
  name) can appear inline in a sentence. A list of everything the system can do belongs in the
  reference doc: link it. "Why we do it this way" belongs in the explanation: link it.
- **Reference:** describe, don't instruct. A one-line usage example per entry is fine; a procedure
  is a how-to.
- **Explanation:** no numbered steps. If the reader must act, link the how-to.
- **Tutorial:** never offer options ("you can also..."). The reader isn't ready to choose.

## 3. Split mixed docs and link them

When a draft has content from another type, move it to that type's doc (create it if needed)
and leave one sentence plus a link: "For every account and profile, see <reference>." Never keep
two copies of the same facts. One place to update is the point.

Common splits:
- New alert → runbook (how-to) + its ADR or design note (explanation).
- Migration → how-to steps + the reference table of what changed.
- README → a short how-to (install, first use) + links to reference and explanation pages.

## 4. Project conventions

Projects often set title prefixes (`How To:`, `Reference:`), folders per type, labels, a page
template (e.g. a table of contents first), and where each type lives. Look for them in the repo's
docs and rules (or a pack's facts) before writing, and follow them over the defaults above. If a
convention is missing and the doc will be published, ask.

## Checklist

- [ ] Type stated, and the doc contains only that type
- [ ] Other types' content moved out and linked, not copied
- [ ] Title follows the type's pattern (and the project's prefix, if any)
- [ ] How-to: prerequisites, one action per step, expected output, rollback
- [ ] Reference: complete, no instructions
- [ ] Explanation: reasons and alternatives, no steps
- [ ] Project conventions applied (prefix, folder, template, labels)

Then run the unslop skill on the prose.
