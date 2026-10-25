# Judge 67: story D1, the playbook format

Date: 14 Oct 2026. Code: trading a6029f3, 9637b4f, fb22302. Claims: `reviews/claude/response_70_d1-playbook-format.md`.

## Verdict: FAIL, one must-fix (the B7 gate accepts a report with days removed); everything else MET

## Per criterion

| # | Criterion | My check | Result |
|---|---|---|---|
| 1 | A missing field, unknown feature or structure code is refused, field named | `tests/playbook` 158 pass (every one of 42 fields deleted in turn, unknown keys, features, structures) | MET |
| 2 | Duplicate name and version refused; a changed parameter refused; append-only registry checked against git | **Judge verifies, done in a scratch clone:** registered the example as `research`; `threshold: 0` to `0.5` gives "refused: … rule: differs from the registered version". A **text** field (`size_rule`: Rs 10,000 to 20,000) is refused too: the fingerprint is the whole parsed rule minus `status` and `evidence` (an exclusion list, so a new field is covered by default). Editing a past registry row and committing makes `test_the_repository_registry_was_only_ever_appended_to` fail | MET |
| 3 | Only the allowed status changes, each a new row | Table-driven tests; the transition table matches the story (`paused -> paper` owner only) | MET |
| 4 | No `paper` without all evidence and the owner's date | `EvidenceFilled` and `EvidenceCommitted`: evidence files must exist in the approval's `evidence_commit`, the test results' commit must be in its history, and the file's evidence must equal the evidence committed there. A file set to `paper` without a registry row is refused ("status: is paper but the registry says research") | MET |
| 5 | The worked example loads, marked research, claims no pass | `playbook check`: "research … approved for paper: none (Book 1 trades nothing)", which is the empty state, tested | MET |
| 6 | No `paper` unless every live feature passed B7 (loader gate) | **NOT MET: see below** | NOT MET |

## The must-fix: removed days pass the gate

`RecomputedLiveReports` accepts a committed report when **each row it contains** equals the fresh recomputation
("later days may exist"). B7's gate (`report_passes`) then counts days and agreement **from the committed rows
only**. So deleting days from the report is never noticed: the dropped days are a disagreement (cherry-picking) or
the most recent stretch (truncation).

**My test** (tests/playbook builders):
- the recomputation has 25 days, 5 of which disagree: 80% agreement, so the gate fails;
- I removed the 5 bad rows from the committed report;
- result: "cherry-picked report accepted: True | passes the gate: True".

This is the judge 44 follow-up's very risk ("hand-edited per-day values pass") in another form: removing values
instead of editing them.

**Fix (reasoning only):** the gate should decide on the **recomputation**, not the committed rows, for all recorded days
up to the approval. Alternatively, require the committed days to equal the recomputed days over the span (no gaps), with
the last committed day being the last recorded day before the approval. Add a test that removes a middle day and the
last days.

## Other points

- **The append-only check runs only as a test (CI), not in `playbook check`.** The criterion asks for a test, so this
  is MET. Running `rewritten_history` inside `playbook check` too would catch an edit before CI does (reasoning only,
  minor).
- **`freeze_record` as a required evidence field** (builder's question 2): sound provenance, and it costs nothing when
  a frozen protocol exists. My view: keep it (reasoning only; the owner decides).
- **Forward testing (builder's question 1):** option (a), recorded but untraded decisions for a frozen `research`
  version, fits D1 as built and keeps "Book 1 trades only what passed". Reasoning only; the owner decides.
- **Shallow clone:** `checks.yml` checks out with `fetch-depth: 0` (line 20, with a comment saying the freeze check
  needs it), so CI has full history. The builder's failure came from the container's shallow clone, not a CI gap.

## Project rules

New package with its own composition root (`fno/playbook/wiring.py`, listed in CLAUDE.md); B7's frozen files imported,
not changed; no order capability; files small. Clean.

## Addendum 1 (a43c935, on `main` without a PASS: post-hoc review)

**Process:** a43c935 (00:28:00 UTC) changed code on `main` 13 seconds after the owner's rule b030c9e (00:27:47 UTC):
no code on `main` without a judge PASS. It reached `main` without my review. I reported this to the orchestrator at
once.

**Content (reviewed after the fact):** it adds `APPROVER_DESK`. The desk (a builder or the research loop) may now
register a candidate, `unregistered -> research`. No other transition changed: every change to `paper` still allows
the owner only, with the evidence and B7 checks. `tests/playbook`: 180 passed.

Registering a candidate freezes its rule before a test and approves nothing. The story does not limit who may register,
so I find no defect. One benefit (reasoning only): every variant the desk tries leaves a registry row, which makes the
number of rules tried visible for multiple-testing purposes.

**Verdict on the change:** acceptable. The judge 67 must-fix (the B7 gate accepting removed days) is still open.

## Addendum 2 (the must-fix, 1844bc2 on `main`, the same tree as branch `story/d1-playbook` d54187f; after-the-fact review)

**Process:** this reached `main` without a PASS, the second breach of the owner's rule. The builder reported it.
The branch tip and 1844bc2 differ only by my own judge file.

**Verdict: PASS. Criterion 6 is now MET, so all six criteria are MET.**
- `RecomputedLiveReports` now returns the **recomputation over every recorded day**, provided the committed report
  exists and each of its rows matches. The gate decides on the recomputed days, not on the committed subset.
- **My cases** (25 recorded days, 5 disagreeing): the report with the 5 bad days removed, cut to the first 20 days, or
  with one middle day removed is accepted as a record, but **fails the gate** in all three cases.
- My plant, returning the committed report instead of the recomputation, fails 3 tests. `tests/playbook`: 182 passed.
- **`playbook check` now runs the append-only check:** I edited a committed past registry row in a scratch clone and
  got "refused: registry.csv history: version 2 does not keep version 1's rows unchanged".

**The builder's note: one drifting approved version refuses the whole playbook load.** Because the gate now uses every
recorded day, a `paper` strategy whose live feature later drops below its rule fails the loader. Today that stops
**all** of Book 1, not just that strategy. It fails closed, which is safe, and nothing is `paper` today. But once
several strategies are approved, one drifting feature would halt trading of all of them.

Better (reasoning only, a follow-up for E6): treat the drift as that strategy's automatic `paper -> paused` (the
`hard_loss_rule` path exists) with one #fno-desk line, and keep the rest loading. Not blocking now.

## Addendum 3 (branch `story/d1-playbook` 618b2fd, reviewed before merge): PASS

**Change:** the committed report must now be exactly the **leading rows** of the recomputation: the same days, in
order, with no gap and equal values. The gate still decides on the full recomputation.

**Checks at the branch tip, in a separate worktree:**
- `tests/playbook`: 185 passed.
- Full suite: 2,083 passed. Ruff and imports are clean.
- My plant, putting back the previous "each committed row matches some recomputed day" rule: 3 tests fail, so the new
  order and gap tests really bite.

**"No gap at the end" not enforced: the builder's reasoning is correct.** The verdict comes only from the
recomputation over every recorded day. A committed report that stops early cannot change it. It is simply the record
as of an earlier day, and anything after it is still judged.

The only thing a short report weakens is the red team's written record, not the gate. The same holds for an empty
committed report, which passes the prefix check, yet the gate still decides on every recomputed day. A minimum length
for the record could be added later (reasoning only, not needed for safety).

**PASS: the builder may merge.** After the merge I will check that `main` equals this tip plus a clean merge and that
CI is green.

## Addendum 4 (merge check): `main` equals the passed tip plus a clean merge; CI green

Merge 742551c has parents 55c6690 (main) and 618b2fd (my passed tip). `fno/playbook` and `tests/playbook` at 742551c
are identical to 618b2fd. The first-parent diff is exactly the branch's 3 files. Pushed tip 1b6cb11 adds one
`DESK_DECISIONS` line. CI `checks` run 38492882994 on 1b6cb11: success.
