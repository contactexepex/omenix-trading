# Judge 107: quality rules in `docs/JUDGE.md`: `story/x-quality-rules` c158bf49dd69de414492be1611f6a85ecc040be4 (lane 1, rule document)

Judge B. No response file: the orchestrator reserved number 107 for this change.

**What I did:**
- Read the one-commit diff (c158bf4, parent 5ca2e00, which is on `main`): it only appends 33 lines to `docs/JUDGE.md`.
- Traced each item to the owner's words at their source:
  - `conversations/2026-10-15.md` lines 185-209: the owner's quality message, the eight proposed rules, the owner's
    judges message and "rules yes, contract A";
  - the decision rows 7b9f714 (several judges) and 5ca2e00 (quality rules, contract A).
- Read the new text against the existing loop, the lanes, the refinements and the owner's other decisions.

**Gates:**
- No test, tool, workflow or `fno/` file reads `JUDGE.md`.
- `git diff --check` is clean. The new lines are at most 120 characters; the long lines 28, 57 and 58 were already there.
- `git merge-tree` with `origin/main` (032665a) merges cleanly.

## (a) Each item against the owner's words

The owner approved "rules yes" for the eight rules as summarised in the log (line 187-192). The decision row names the
same eight.

| Item | Source | Result |
|---|---|---|
| 1 Story check before code | Proposed rule 1, "judge checks story text and criteria before code" | PARTLY: the text makes it "before the code is **judged**". See should-fix 1 |
| 2 Gap list | Proposed rule 2 | MET. "A requirement in neither list is a blocking finding" sets a severity. It follows from the existing rule that a story passes only with no blocking finding left |
| 3 Builder self-review | Proposed rule 3 | MET |
| 4 Broken-code proof | Proposed rule 4 | MET. "The judge plants its own mutations as before" keeps step 3 of the existing loop |
| 5 Positive, negative, boundary, empty | The owner's judges message (row 7b9f714) | MET. The quote "ensure that all the positive and negative use cases are tackled properly" is word for word. The builder-side half ("the builder's tests cover ...") is the orchestrator's instruction of the same day, not the owner's words. It serves the owner's aim, and I accept it |
| 6 Real output sample | Proposed rule 5 | MET as a source; **contradicts an owner decision as worded** (must-fix 1) |
| 7 Orchestrator check | Proposed rule 6 | MET |
| 8 End-to-end run after merge | Proposed rule 7 | MET as a source; not precise enough to apply (should-fix 2) |
| 9 ChatGPT for money | Proposed rule 8, "money, fills, exits and the real-money gate (C5, E8, RM1)" | MET as a source; one gap against the loop (should-fix 3) |
| Several judges | Row 7b9f714 | MET. The last sentence ("verdict number equals the story's response number") is the orchestrator's numbering convention, not the owner's words (minor 1) |

The numbering is right: there are 9 items because item 5 is the separate judges decision, and the other 8 map one to one
onto the 8 approved rules.

## (b) Contradictions with existing rules and owner decisions

**Must-fix 1. Rule 6 can put a live trade card into a public file.**
- The rule asks every claims file to show "real output of the story (a card, ...)". Claims files are in
  `reviews/claude/`, in a public repository.
- Owner decision of 15 Oct 2026 (design v2 decision 9): card records live in Google Drive only, and the public
  repositories hold no live strikes or entry ranges.
- The dashboard privacy rule keeps strategy internals private, and secrets never go in files.
- As written, a T1 builder following rule 6 with a real `TRADE` card would publish exactly what decision 9 forbids.
- Fix: add one sentence to rule 6. The sample obeys the card rule (no live strikes or entry ranges: use `NO TRADE`, a
  redacted card or a labelled historical example), the privacy rule and the record scan, and it is never produced by a
  live post. It is made in dry-run mode or by a test.

No other contradiction found:
- Rules 1-9 add to the loop and keep the judge's own checks, mutations and the PASS rule.
- Lanes and refinements are untouched. These rules apply to stories, which are lane 1 already.

## (c) Precise enough to apply

**Should-fix 1. Rule 1: say when the story check happens.**
- The approved wording, "judge checks story text and criteria before code", reads most naturally as before the code is
  written. That is what the owner's aim ("make sure that we do not build wrong implementation") needs.
- The text says instead that the story text is checked "before the code is judged", within the same review. A wrong
  requirement is then found only after it has been built.
- Fix: for stories started after this rule, the builder pushes the story text alone. The judge checks it at that SHA
  before code starts, and the verdict file gets a story addendum. Stories already being built (today's six) are checked
  first in their code review, as written.
- Alternatively, keep the text and record the owner's acceptance of the narrower reading.

**Should-fix 2. Rule 8 does not say who runs the end-to-end run, or what happens when it cannot run or fails.**
- Name who runs it (the merger, which is the builder under the loop) and where its output is recorded.
- Say what happens when no real-data path exists (a rule document like this one, or a docs-only story) or the sandbox
  lacks the access (Drive, Azure): the merger states it and why, and the judge records it. It is never skipped silently.
- Say what happens on a failure. Proposal: treat it like a lane-2 correctness FAIL (refinement 5): `git revert`, then
  fix on the branch.

**Should-fix 3. Rule 9: changes after the PASS go back to the judge.**
- The ChatGPT review comes after the judge's PASS and before the merge. If its points lead to a code or text change,
  the merged tip is no longer the passed SHA.
- Add: any change made after the judge's PASS returns to the judge before the merge. Following loop step 2, the builder
  answers each ChatGPT point with evidence, and the judge checks those answers.

**Minor:**
1. The numbering sentence is a convention, not an owner decision. Also say how a verdict without a response file gets
   its number (as here: the orchestrator reserves a free number).
2. There is a double blank line before the new heading (cosmetic).

## Project rules

Lane 1 (a rule document). It changes one file and no code. It contains no secrets, e-mail addresses or model names.

**Verdict: FAIL for c158bf49dd69de414492be1611f6a85ecc040be4**, on must-fix 1 (rule 6 against owner decision 9) and
should-fixes 1-3 (precision). All of them are wording in `docs/JUDGE.md` only. A re-check needs only the new section.

## Addendum 1 (15 Oct 2026): 85972d90a830dfab3ba380697d84c0f8e94bdfa8 (c158bf4..85972d9)

One commit. It changes only the new section of `docs/JUDGE.md` (19 lines added, 10 removed). `git merge-tree` with
`origin/main` is clean, `git diff --check` is clean, and no new line exceeds 120 characters.

| Finding | Status | Evidence |
|---|---|---|
| Must-fix 1: rule 6 samples | MET | Samples are only NO TRADE cards, redacted output or labelled historical examples. They are made in a dry run or a test, never by a live post, and never carry live strikes, entry ranges, strategy internals or secrets. The rule names the cards-in-Drive decision, the privacy rule and the record scan |
| Should-fix 1: rule 1 timing | MET | New stories push the story text alone, and the judge checks it at that SHA before code starts. The seven stories already being built are named (A15, T1, P1, A17, F8/BG1, C5, STR1), and their story text is checked first within their code review |
| Should-fix 2: rule 8 | MET | Who runs it: the merger. Where it is recorded: the log, plus the merge message or a follow-up commit. The judge's merge check verifies that record. A change with no data path, or a run without access, states so and why. A failure is reverted at once (refinement 5) |
| Should-fix 3: rule 9 | MET | Any change made after a PASS because of the ChatGPT review returns to the judge before the merge |
| Minors 1-2 | MET | The numbering is labelled the orchestrator's convention, with reserved numbers for verdicts that have no response file. The double blank line is gone |

**New minor (not blocking):** rule 8 says "the person who merged (the orchestrator)". The 14 Oct decision row says the
builder merges after a PASS, and `CLAUDE.md` leaves it open. The rule binds whoever merged, so it still applies. If
builders merge, read the parenthesis as "today usually the orchestrator", or drop it at the next edit.

**Verdict: PASS for 85972d90a830dfab3ba380697d84c0f8e94bdfa8.** Merge it. After the merge I check that `main` carries
exactly this section.
