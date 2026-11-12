# Structure tells (pass 1)

Sections A to E of the [brainrc-unslop](../SKILL.md) skill. Structure is the stronger signal and harder to spot.

## A. Staging instead of stating (act on one sighting)

1. **Not X but Y.** Including "not just / not only X, but Y", "it's not X, it's Y", the split
   form ("This does not mean X. It means Y."), and the clipped tail ("..., no guessing"). The
   negative half names something nobody claimed. State the point. Keep the contrast only when
   it corrects a belief the reader actually holds.
   - Before: "This isn't just a Terraform change, it's a change to how we own state."
   - After: "This change moves state ownership from the service repo to the platform account."
2. **One-line closers and dramatic fragments.** "That's the real win." "No manual steps. No
   drift. No surprises." Cut a closer that repeats; merge fragments into one specific claim.
3. **Sayings that sound deep.** "The real question is", "at its core", "X is the Y of Z".
4. **Staged run-up.** "Let's dive in", "here's what you need to know", "Here's the thing".
5. **Arguing with no one.** "To be clear", "you might think X, but". Cut defenses against
   objections that appear nowhere. Keep a rejected alternative only if a reviewer would weigh
   it, and say why it lost.
6. **Rhetorical question then answer.** Lead with the answer.
7. **Heading repeated in the first sentence.** Delete the restatement.

## B. Rhythm by rule

8. **Forced triads.** Two real items beat three padded ones.
9. **Repeated openers.** Three sentences in a row starting "This means / This allows / This ensures".
10. **Scaffolding paragraph openers** ("However,", "Additionally,"). Lead with the claim.
11. **Mirror structures.** "Engineers want clarity. Managers want context." Break the symmetry.
12. **Em and en dashes.** None in prose, spaced or ` -- `. Use a period, comma, colon, or
    parentheses. Leave dashes in code, commands, paths, and URLs.
13. **Colon reveals.** "The result: total outage." Colons introduce a list or example only.
14. **Stacked qualifiers.** "could potentially possibly" → one hedge, if the source has one (see 44).
15. **Hyphenated pairs everywhere.** Hyphen before a noun ("a real-time view"), not after. *Weak alone.*

## C. Inflation and borrowed authority

Keep the fact, drop the dressing.

16. **Puffery:** "pivotal moment", "testament to", "evolving landscape", "sets the stage".
17. **Promotional words:** "groundbreaking", "seamless", "robust" (figurative), "best-in-class".
18. **-ing riders:** "ensuring reliability", "fostering collaboration". Delete or name the mechanism.
19. **Vague attribution:** "teams have found", "experts recommend". Name the source or cut. Never invent one.
20. **Vague connection:** "associated with", "tied to". Name the relationship (fires on, routes through, mentions).
21. **False ranges:** "everything from IAM to networking". List the topics.
22. **Generic conclusions:** "the future looks bright". End on the last fact or the next step with an owner.

## D. Formatting by rule

23. **Bold as decoration.** Bold only a lead-in followed by new detail.
24. **Inline-header lists** where the label restates itself ("**Performance:** performance improved").
25. **Title Case Headings.** Use sentence case.
26. **Decorative emojis and arrows.** A `→` in a technical mapping is fine.
27. **Curly quotes.** Straight quotes only.
28. **Horizontal rules between every section.**

## E. Leftovers from the chat and the draft (remove outright)

29. **Chatbot residue:** "I hope this helps", "Certainly!", "Let me know if...".
30. **Sycophancy:** "Great point".
31. **Knowledge-limit disclaimers and guesses.** State what the source doesn't show. Never present
    a guess as fact. An unverified runbook step keeps its `UNVERIFIED:` marker.
32. **Writing about the previous version** in docs about current behavior. That belongs in a
    changelog, migration guide, PR, or ADR context (and see 58).
33. **Redundant restatement** of a heading, table, or the prior sentence. Say each fact once.
34. **Fabricated specifics.** Flag any number, quote, or named source you can't trace.
