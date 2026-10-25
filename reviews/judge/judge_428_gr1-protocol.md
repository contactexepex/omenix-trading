# Judge 428: study GR1 "sharper ranges", the protocol before any result (story/gr1-sharper-ranges at c835ce08)

Judge B, 22 Oct 2026 (IST).
- Builder: G13b/GR1 (session_01UkTaDeTRF9ksDgQB9cTU5C).
- Requested by the orchestrator on 21 Oct: a strict, pharma-style review of the protocol before any result is read.
- Files reviewed:
  - `research/gr1/PROTOCOL.md` (commit 54bb5a42);
  - `research/gr1/FREEZE.md` (c835ce08);
  - ledger rows 56-70 (`research/ledger.csv`, `LEDGER.md`);
  - `research/DATA_SPEND.md` rows;
  - the register row.
- Number claimed with `tools/claim_number.py`.

## Verdict: FAIL (4 should-fix, no blocking)

The design is sound, and most of it is better than most studies I have judged here:
- it states first, plainly, that every result is exploratory;
- the centre stays fixed and only the width changes, so one thing is tested;
- it trains, selects and then makes one final look;
- one winner per cell, with Holm only on those winners, which is the right two-stage logic;
- calibration is a hard constraint;
- an untested data set (FII/DII) is counted openly.

Four things must be settled in the frozen text before any code runs. If they are left open, the code would decide
them after the builder has seen the data, or a result could not be read honestly. None is large.

## What I verified myself

| Item | Result | Evidence |
|---|---|---|
| Freeze record | MET | `PROTOCOL.md` has SHA-256 `ab67f3b6...0e` at 54bb5a42 and at c835ce08, as `FREEZE.md` says; no commit after the freeze changes it |
| Registration before results | MET | the decision 3b03e2c5 (20:48 UTC) came first, then the protocol 54bb5a42 (20:52) and the freeze c835ce08 (20:53). No GR1 code or output exists on the branch (6 files: protocol, freeze, ledger, LEDGER.md, DATA_SPEND, register) |
| Ledger numbering | MET | main's `ledger.csv` ends at 55, so 56-70 are free today; the 15 rows name 54bb5a42 |
| Data spend | MET | implied's end-of-day ranges are `spent` (their scores were read); VIX and events are `exposed`; global cues are `registered`; A16b's RV is `exposed`. Each matches what has been read |
| FACTORY_RULES section 4 | MET | "a test on a data set marked `spent` or `exposed` ... is labelled exploratory and cannot pass G6; it can at most justify a fresh test". Section 2 of the protocol states exactly this |
| Input data exists | MET | `receipts/data/price_ranges/v1/backfill/backfill_eod_8d7d7301` covers 2019-01 to 2026-10; the BANKNIFTY closes have their receipt (`price_ranges/v1/closes`) |
| Bootstrap | MET, note 6 | G4's `block_bootstrap.compare`: moving blocks of L = 20, 10,000 resamples, a **two-sided** p-value |
| The N0 arithmetic | MET | sqrt(0.607) = 0.779, about 22% narrower by construction, as stated |

## Should-fix 1: the calibration band rejects a perfectly calibrated candidate often, and the protocol does not say so

The rule is that a candidate's coverage must lie within [0.87, 0.93] for the 90% band and [0.45, 0.55] for the 50%
band, on 2024 and again on the final period.

I computed how often a candidate that is **exactly** calibrated still fails it:
- N1: exact binomial.
- N3: a simulation of overlapping 3-session windows (iid normal moves; 20,000 runs).

| Period (days) | Cell | Fails the 90% band | Fails the 50% band | Fails either |
|---|---|---|---|---|
| 2024 (246) | N1 | 13.5% | 11.1% | about 23% |
| 2024 (246) | N3 | 25.6% | 19.4% | 36.8% |
| final (447) | N1 | 3.3% | 3.7% | about 7% |
| final (447) | N3 | 10.4% | 8.9% | 16.8% |

Real markets have fat tails and volatility clusters, so the true rates are higher. A perfect N3 candidate passes both
looks only about 53% of the time (0.632 x 0.832).

**Why this is normal running, not imagined:** it is what the rule does on the very data the protocol names. It has
two effects:
- "No candidate beat implied" can come from noise alone.
- With 11 candidates per cell, selection on 2024 favours candidates whose coverage happened to land inside the band.
  That is selection on noise, which the final look then partly undoes.

**Fix.** Keep the owner's hard constraint, but state in the frozen text, before any run:
- (a) these false-rejection rates, per cell;
- (b) that C0 is checked against the same bands and reported, so a reader sees whether implied itself would pass;
- (c) that a cell with no winner is reported as "not shown at this sample size", never as "implied cannot be beaten".

Alternatively, choose a rule that accounts for sampling noise, for example coverage measured with the same block
bootstrap. If you do, it must be fixed now, not after run 1.

## Should-fix 2: the global cues' point-in-time rule must be A17's own as-of rule, per series; Brent is at least 10 days stale

Section 3 says each cue is "read as its last value published before 15:30 IST on d". The A17 code shows what that
means for each series:
- **Brent** comes from EIA, which publishes it **weekly**. A17's research rule makes a Brent value usable only "by the
  end of the 10th day after its date" (`fno/global_cues/other_sources.py:38`, `EIA_WORST_LAG = timedelta(days=10)`).
  So C7's "last-published Brent move" is a move at least about 10 days old.
- If the code takes `value_date < d`, which is the natural shortcut, C7 gets Brent values the live tool could never
  have had by 15:30. That is look-ahead against live.
- **USD/INR:** the protocol's d-1 matches A17's README ("first usable on t+1", reckoned from the open) and is
  conservative. A17's `as_of.py` makes the rate of d usable from 13:30 IST on d, so at 15:30 the rate of d was already
  known. Using d-1 is safe; it is just one day staler than it needs to be.

**Fix.** State that every cue is read with A17's `value_for(..., live_only=False)` and the source's `available_at`:
- at 15:30 IST on d for C7;
- at 09:15 (A17's `OPEN`) for N0-C's S&P 500 move.

Also state that Brent is therefore at least 10 days stale, and decide now whether it stays in C7. A stale move is
nearly empty of information but still costs a parameter. Add a test with a planted same-day value for each series that
must not be read.

## Should-fix 3: candidates with missing conditioners are compared on different day sets

Section 7 drops rows "not `ok` for implied" and pairs each candidate with C0. Section 9 then picks "the eligible
candidate with the lowest mean 2024 QS" across candidates. In normal running, the candidates do not cover the same
days:
- C8 needs A16b's `rv_session`, which is missing on some sessions: 1,661 usable of 1,680 rows read in A16b's X sample,
  about 1%.
- C3 and C4 need VIX on d and d-1.
- C7 needs every cue.

A lowest-mean QS taken over different days compares different difficulty, not different skill: a candidate that
misses a few volatile days looks better.

**Fix.** Define the selection's day set per cell. Either:
- use the days on which **every** candidate and C0 have values; or
- select on each candidate's mean **paired difference** against C0 over its own days.

Then report how many days each candidate drops.

## Should-fix 4: N0's decision rule is undefined

Section 11 says N0 is "a measurement, not a hypothesis", yet it gives N0-B and N0-C fitted parameters and "the same
selection rule as section 9". Section 9 compares against C0, and section 10 decides only "a cell's winner".

For N0 the protocol does not say:
- which baseline the selection uses: N1 for the same target, or N0-A;
- whether an N0 winner gets a final-period decision;
- whether it joins the Holm family.

As written, the code would make these choices.

**Fix.** Pick one and write it down. My suggestion, which keeps "measurement":
- report N0-A, N0-B and N0-C against N1 on the same target days, on every period;
- select between N0-B and N0-C on 2024 by the section 9 rule, with N0-A as the baseline;
- decide nothing (no Holm, no "sharper"), only width ratios with block-bootstrap intervals.

## Answers to the builder's five questions

1. **Status.** Yes: a winner can at most justify a live sealed shadow (FACTORY_RULES section 4 says exactly this).
   **Go further for C1 and C2.** Both are suggested by the full-sample finding: 5.9% against 4.1%, final years
   included. If either wins a cell, its final look is not even exploratory evidence; it re-measures a known fact. Mark
   such a winner "known before the study" in the decision table. Its only evidence is then the live shadow. The
   conditioners (C3-C10) are different: no conditioner has been read against an outcome, so for them the final period
   is fresh for the *conditioning* effect even though the baseline is spent.
2. **Form and rule.** Width-only around implied's median is a clean single question. The centre's error is out of
   scope, and the report should say so: the owner asked for a "correct" range, not only a narrower one. The rule order
   is right: calibration, then Holm across at most 4 winners, then width. Points in should-fix 1 and note 1.
3. **Point in time.** VIX, events, expiries and RV are right as written. The global cues need should-fix 2. CLOSE
   against CAPTURE basis is correctly disclosed (section 4), and it is one more reason for the live shadow.
4. **Multiplicity.** Counting FII/DII visibly is right. The 46 is not internally consistent: see note 3. The count is
   descriptive here, because only at most 4 winners are tested.
5. **N0 against N1.** A measurement is the right status, and 0.607 is exposed (measured on 2020-2025). See
   should-fix 4 for the rule.

## Notes (one line each)

1. **C2 can make quantiles cross.** The 5% quantile passes the 25% one when s95/s50 < (q25 - m)/(q05 - m), about
   0.41 for a normal shape. "`s > 0`, so the quantiles stay increasing" is true for one scale, not for two. Add the
   constraint to the fit, or refuse a crossing fit, counted as a failed fit.
2. **C11 chooses its two conditioners on 2024 and is then selected on 2024.** This double use favours C11 at
   selection. The final look still protects validity, but say so, or choose C11's pair on the train period.
3. **The count is not consistent.** The 2 BANKNIFTY cells of C8 are not counted ("42 fitted"), yet C11 is counted
   when not run and FII/DII is counted once rather than per cell. Pick one rule: every registered candidate-cell
   counts, run or not, so 44 + 3 + 4 = 51, or say why not.
4. **Regime breaks fall inside the periods.**
   - BANKNIFTY's weekly options ended in Nov 2024, so they are inside 2024 and in none of the final period.
   - NIFTY's weekly expiry moved from Thursday to Tuesday in Sep 2025, inside the final period.
   - C6 (expiry in horizon) and C9 (weekday) carry train-period meanings that change. Disclose this, with the dates.
5. **"Run once" is enforced only by `final.json` being absent at the committed head.** A local run is not visible.
   - The honest control is a deterministic run 2 that the judge reproduces from the committed `selection.json`.
   - The selection commit must precede the final commit, which GitHub's push times show.
   - Write both into section 12.
6. **The p-value is two-sided.** "Below C0's with p < 0.05" is then a one-sided 2.5% test, which is conservative and
   fine. Say "two-sided p, direction required".
7. **Section 13's "report the gap"** should also say what happens to the cell: not decided.
8. **Merge the registration to main once this passes.** Merging the protocol, the freeze and the ledger rows (they are
   not code) fixes 56-70 and avoids the renumbering risk the builder names.

## To pass

1. Should-fixes 1-4, written into `PROTOCOL.md` as a re-freeze. The protocol has no code and no results yet, so a
   change now is not a deviation. Record it in section 14 as "revision before review, judge 428", with a new hash in
   `FREEZE.md` and the ledger's protocol commit updated.
2. Then I re-check the text, the hash and the ledger rows.

## Addendum 1: revision 2 at a7a1b28a, freeze record 7cd1c3c1 (number 428.1, claimed with `tools/claim_number.py`)

**PASS.** The protocol may proceed to step 2 (code on synthetic data, then hash-freeze before run 1). Nothing has been
fitted or scored, and no study code exists: the branch adds only the protocol, the freeze record and the ledger rows.

### Freeze and ledger
- `PROTOCOL.md` has SHA-256 `ec02703d...3f0` at both a7a1b28a and 7cd1c3c1. `FREEZE.md` records it under "Revision 2"
  and keeps the first freeze's hash above it.
- All 15 ledger rows 56-70 now name a7a1b28a.
- Row 62 (C7) says "Brent dropped, judge 428".
- Section 14 dates the revision as before review.

### The four should-fixes
| Should-fix | Result | Where |
|---|---|---|
| SF1, band costs | MET | Section 9 states the rates. N1: about 23% on 2024 and 6-7% on the final period; the builder's own exact binomial gave 23.1% and 6.2% at n = 440. N3: 37% and 17%. Both looks together: 72% and 53% pass. The bands stay hard, C0 is checked and reported on both periods, and no winner means "not shown at this sample size" |
| SF2, cue timing | MET | Every cue is read by A17's `value_for(live_only=False)` with its `available_at`, at 15:30 on d (C7) and 09:15 (N0-C), and the text says "never a raw `value_date < d`". Brent is dropped as at least 10 days stale. A planted same-day test per series is in section 12 step 2 |
| SF3, day sets | MET | Selection uses each candidate's paired mean QS difference against C0 on its own days, and dropped days are reported with reasons (sections 7 and 9) |
| SF4, N0's rule | MET | N0-B and N0-C are compared against N0-A on 2024 under the bands, and the better eligible one goes to the final period. There is no Holm and no "sharper". All three are reported against N1, with width-ratio bootstrap intervals (section 11) |

### Notes from the verdict
All are in the text:
- the count of 51 (48 candidate-cells including FII/DII, 42 fitted, plus 3 N0);
- C2's crossing guard;
- C11's pair chosen on train;
- the regime breaks, with C9 reported split at them;
- run 2 deterministic, refusing if `final.json` exists in any commit, and recording its input hashes;
- the two-sided p-value, with direction required;
- a gap means the cell is not decided;
- a C1 or C2 winner is marked "known before the study".

The figures are consistent: 0.769 x 0.938 = 0.72.

### New notes (one line each, none blocking)
1. C2's guard refuses crossings on **train** days only. Implied's shape varies by day, so a fitted C2 could still
   cross on a 2024 or final day. The code should check every scored day and count a crossing as a failed fit.
2. `DATA_SPEND.md`'s global-cues row still names Brent among the registered series. Brent is now unused, so drop it
   from that row when the code commit lands.
3. The builder's honest limit (the 2025-26 records sit in Drive and implied's own 2025-26 scores were read; what is
   sealed is every candidate's 2025-26 performance) is not yet in section 2. Section 2 already says the final period
   is not fresh for the baseline, so this is wording only.

### Next steps for me
- The code commit with its hash freeze, before run 1: I check the synthetic tests, the planted 2025 row, the planted
  same-day cues, and that the hashes match.
- After run 2: I reproduce `final.json` from the committed `selection.json`, then judge the results file.

## Addendum 2: revision 2 final at eb8d061a, freeze record 5bb4ea95 (number 428.2, claimed with `tools/claim_number.py`)

**PASS, and this is the frozen protocol.** It supersedes a7a1b28a, which I passed in addendum 1.

### What changed since a7a1b28a
The diff to `PROTOCOL.md` holds only the additions I asked for:
- Section 2 now carries the honest limit: the sealing is code plus process, and what is sealed is every candidate's
  2025-26 performance, not the data. This was new note 3.
- Section 12 now carries steps (a)-(d) word for word:
  - (a) the load-time filter on issue date < 2025-01-01, with the planted-2025-row test;
  - (b) `selection.json` committed before run 2;
  - (c) run 2 never refits, refuses unless the selection file is unchanged since its commit, refuses if `final.json`
    is in any commit, and refuses a second invocation;
  - (d) both runs refuse a hash mismatch or uncommitted changes.
- Section 12 also says run 2 is deterministic (inputs sorted by day, G4's seeds, no clock or random state, input
  hashes recorded), so I can reproduce `final.json`.
- Section 14 records the change.

### Freeze and ledger
- The SHA-256 is `8ed575b3...2eaa` at both eb8d061a and 5bb4ea95, as `FREEZE.md` records.
- `FREEZE.md` states that the a7a1b28a freeze was superseded before review.
- All 15 ledger rows name eb8d061a.

### Still open for the code commit
- New notes 1 and 2 from addendum 1 stay open: check C2's crossing on every scored day, and drop Brent from the
  `DATA_SPEND.md` row.
- Then I judge the code and its hash freeze before run 1.

## Addendum 3: the final freeze at 9c67a3c7, freeze record 13241191 (number 428.3, claimed with `tools/claim_number.py`)

**PASS, and this is the frozen protocol to merge.** It supersedes eb8d061a, which I passed in addendum 2. Its delta
holds only addendum 1's notes 1 and 2:
- C2: a crossing on any scored select or final day now counts the cell as a failed fit for C2.
- `DATA_SPEND.md`'s global-cues row now reads "S&P 500, US 10-year, USD/INR (Brent dropped, judge 428)".
- Section 14 records both changes.

### Freeze and ledger
- The SHA-256 is `89de9cf4...dfaa` at both 9c67a3c7 and 13241191, as `FREEZE.md` records.
- All 15 ledger rows name 9c67a3c7.
- I re-read the full delta from a7a1b28a: apart from the C2 rule, it is wording and process only (section 2's honest
  limit, section 12's (a)-(d), section 14).

### Merge
The registration (protocol, freeze record, ledger rows 56-70, `LEDGER.md`, `DATA_SPEND.md`) may merge to main as a
**merge commit**, so the freeze commits stay in history for B4's guard. Run `check_numbers` and the suite on the
merged tree.

Next I judge the study code and its hash freeze, before run 1.

## Addendum 4: the ledger-guard test at 8ffcc78c (number 428.4, claimed with `tools/claim_number.py`)

**PASS.** It is test-only and touches one file, `tests/research/test_ledger_guard.py`, on top of the 9c67a3c7 freeze
I passed in addendum 3.

What the test now checks, following the pattern of R2, FT1 and B0:
- the repository ledger's trial ids run 1-70;
- GR1's 15 rows are prospective, with 11 hypotheses;
- all 15 point to `research/gr1/PROTOCOL.md` under a single protocol commit;
- row 67 is "NOT TESTED".

Checks I ran on 8ffcc78c:
- The file passes: 8 tests.
- My plant (row 62's hypothesis flipped to "no") fails 1 test.

The registration (9c67a3c7 plus 8ffcc78c) may merge to main as a merge commit. Run the full suite on the merged tree.
