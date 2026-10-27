# P5: the Record contract — what the code guarantees today (PLAN)

PLAN for the orchestrator's check before any writing. Phase 5 of [PIPELINE_DESIGN.md](../PIPELINE_DESIGN.md) is "harden + document: finalise
the Record contract with the forecasting engine". The engine's needs are not known (owner decision 2), so this plan covers only the slice
that does not depend on them: **a contract built from what the code already guarantees, each claim tied to a test that fails when the
claim is broken.** The engine-dependent parts are listed as OPEN, not guessed.

## What the deliverable is

One owning document, `docs/RECORD_CONTRACT.md` (under 500 lines; the design document keeps a one-line pointer, per "one functionality, one
owning document"). A table of claims, each with: the claim in plain words; what enforces it (file and class); the test(s) that pin it; and
a **strength** mark, as the project rules require: *tested* (a named test, and I ran a plant that makes it fail), *tested, no plant run*, or
*stated only* (no test; said plainly, not claimed).

## Method (so the table is evidence, not prose)

1. List the candidate claims from the code, not from memory: write-once at the store; a SHA-256 receipt per Drive file and the order Drive,
   then receipt, then row; the manifest rows (articles, clusters, the NSE datasets) and their torn-line refusal; first-copy-wins and the
   revisions area; the gate's checks (session, exception, content, identity) and what stays in Staging; the commit guard; idempotent
   re-runs; the privacy rule (hash ids and counts only for news; values private for Yahoo); the record scan on every commit.
2. For each claim, find the test that pins it. **Run it, then make a small plant that breaks the claim and confirm the test fails.** A
   claim with no biting test is written as *stated only* or dropped.
3. A claim the code does NOT make is written as such, not omitted. What is already known and accepted: no credential separation between
   Staging and the Record (an accepted owner decision); the gate checks format and identity, not authenticity, so a well-formed forged file
   passes; only five datasets go stage-then-promote and every live workflow still writes the Record directly; the NSE index-close dataset is
   not promotable; recovery is limited to Drive's trash and version history; the shared Drive token has full scope.

## What stays OPEN (not decided here)

Where the forecasting engine lives and what it needs (owner decision 2); the freshness windows and cross-source tolerances (decision 1); the
tolerance of any Yahoo or BSE cross-check (P4 and P3 are paused on the owner); the corroboration definition, and any use of cluster counts
(untrusted until the P2c threshold is re-tuned on real data); the receipt volume and the cluster-file cadence (owner go-live).

## Lane and judges

The document describes write-once data, receipts and the privacy rule, which are hard lines, so it takes **lane 1** ("functional documents are
reviewed like code"). A text-only change: the gates are the record scan, `check_numbers` and the doc-reading tests. One judge is
proposed, whose job is to try to falsify rows: pick a claim, break it, see whether the named test fails.

## Risks, said plainly

- A contract is only as good as its weakest row. Where a guarantee is weaker than it sounds, the document says so; I expect several rows to
  read *stated only*, and I will not round those up.
- The claims will drift as code changes. Mitigation: each row names its test, and a small test can assert that every named test still
  exists (cheap, optional, my suggestion for the judge).
- Writing this before the engine's needs are known risks a second pass; the OPEN list is where that second pass will land.

## Not in this plan

Any code change (a weak row is reported, not fixed here), the engine's read interface, the tolerances.
