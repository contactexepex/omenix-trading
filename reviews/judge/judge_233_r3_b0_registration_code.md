# Judge 233: R3 B0's registration code, criterion 8 (judge G)

- **Judged:** `story/r3-b0-registration` at `e352fcba` (code `496e74fd`, claims in `response_236_r3-b0-registration-code.md`,
  builder session 0145TfSwzmpk6MBrH92f5h4G). Lane 1. The text is the R3 addendum, PASSed at `7f94dbdf` (judge 226
  addendum 1). The orchestrator gave the go. 233 was the next free number on main (first written as 227, which another judge had already taken).
- **Verdict: FAIL (claims only).** The code is correct, and all 13 of my mutations are caught. Two should-fixes are in
  the claims file, with no code change needed: the date of the first B0 decision is wrong, and the builder
  self-review that quality rule 3 requires is missing. There are also 4 notes.

## What I ran

- **Gates:** ruff check, ruff format and `check_imports` are clean.
  - Full suite in a git worktree of `e352fcba` with `-n auto`: **6,933 passed, 0 failed**.
  - `python -m fno playbook check` lists `b0-monthly-sc-v1.yaml: research (rule sha256 039a6e0733b1)`, which equals the
    registry row. The registry hash is of the parsed rule (`schema.parameters_sha256`), not the file's bytes.
- **Plan numbers, recomputed from `results_challenge.json`:**
  - P1 has 58 traded SC nets summing to -34,485.57.
  - The nearest-rank 10th and 90th percentiles are **-5,084.43 and +4,155.54**, matching -5,084 and +4,156.
  - -23,140 / 60 = **-385.7**, matching -386.
  - 67,595 is response 92's SC 300 initial margin (`response_92:142`).

## The orchestrator's points

| # | Point | Judge's own evidence | Result |
|---|---|---|---|
| 1 | Criterion 8 against the text at `7f94dbdf` | Idea card, ledger row (prospective, hypothesis `no`, "B0 measurement: never promoted"), the version file, and the registry row `research`/`desk`. The title and both alerts are labelled; the escalation starts at the second loss; the cumulative wording says "expected ... not a defect". The test of a day where both alerts fire sends the single-trade wording | MET |
| 2 | The version file equals P1 exactly | SC, ×1.02 / ×0.98, widths 300-100 within Rs 10,000, monthly 30-45 days, exit at 21 or more days, `entry_conditions: []`. P1 centres on **spot** (`PROTOCOL.md:68`, `research_engine/structures.py:28,155`), and D2 builds legs with `market.spot` (`candidates.py:65`), so "spot" in the file is right. See note 1 on the text's word "forward" | MET |
| 3 | `edge_family: measurement`, with `is_measurement` the only source | `fno/playbook/measurement.py` holds one predicate, and the scorecard, both alerts and the title all call it. Test: only B0 is a measurement. Mutations of the predicate or of B0's `edge_family` fail 5 and 4 tests | MET |
| 4 | Date logic | `status_on` counts rows dated before the day, so B0 is not shadowed on 16 Oct and is shadowed on 19 Oct (17-18 Oct are a weekend, 20 Oct is Dussehra). Moving the row to 19 Oct fails 2 tests. Re-dating the row if the merge slips is right. **But the first B0 decision is not on 19 Oct** (should-fix 1) | MET for the code |
| 5 | Pinned bytes for non-measurement versions | `ALERT` and `SHADOW_ONLY` are pinned to literal strings, along with a non-measurement shadow's alert and title. Applying the measurement wording to every version fails 3 tests (single-trade) and 2 tests (cumulative) | MET |
| 6 | Ledger-guard test extended to 55: a weakening? | **No.** The exact-list equality `range(1, 55)` becomes `range(1, 56)`, still exact, and three new assertions pin B0's row. Nothing is loosened | MET |
| 7 | B0 never enters Test B and is never approved | The Test B code is unchanged (it is not computed yet; criterion 12 is part B). B0 is `research`, and the test checks it is not in `approved_on(19 Oct)`. Only the owner can move it from research to paper (`transitions.py:17`) | MET |

## My mutations (each alone, then reverted)

I ran `tests/scorecard tests/playbook tests/research tests/books tests/desk tests/decisions`. All 13 are caught:

- `is_measurement` always False;
- no single-loss text;
- no cumulative text;
- no `(measurement)` in the title;
- the scorecard flag forced False;
- the cap test made strict (`<`);
- the escalation count off by one;
- the escalation threshold at 3;
- `trigger.text` ignored;
- the registry row dated 19 Oct;
- B0's `edge_family` changed;
- the measurement wording applied to every version (two mutations, one per alert).

## Findings

### Should fix

1. **The first B0 decision is on Mon 16 Nov 2026, not Mon 19 Oct** (strong evidence, code read and calendar).
   - D2 records a shadow only when it finds an opportunity (`evaluate.py:52-58`), and an opportunity exists only on the
     first session inside the 30-45 day window (`opportunities.py:_first_day_in_window`).
   - The November expiry is 23 Nov (24 Nov is a holiday). Its window opened on 9 Oct, before B0's registration, so B0
     misses the November cycle.
   - The December expiry is 29 Dec. Its window opens on Sat 14 Nov, so the first session in it is **Mon 16 Nov**.
   - From 19 Oct, B0 is shadowed (its account is opened in each run), but no B0 decision record exists until 16 Nov.
     Its first time exit is 8 Dec.
   - Claim 4 ("the first shadow decision is recorded on Mon 19 Oct") and the owner effect ("records B0's decision
     daily") are therefore wrong. The orchestrator's rule-8 check after the merge, and the owner, would look for a B0
     record that cannot exist yet.
   - **Fix:** correct claim 4 and the owner effect in response 236. No code change.
2. **The builder self-review that quality rule 3 requires is missing.** Response 236 reports mutations but no
   independent review agents (correctness and silent failures) on the diff. **Fix:** run them and add the section.

### Notes

1. **My miss in judge 226:** the R3 addendum says P1 centres on the "forward × 1.02 / × 0.98", copying response 92.
   P1 and D2 use **spot**. The version file is right; the text and response 92 carry the wrong word. A one-word
   correction belongs with R3's next text edit.
2. **`expected_range` is a range of single trades** (the 10th to 90th percentile trade net), but E6's review compares
   the **mean** with its low (`review.py:103`), and the unit says "per opportunity". No effect before about 2028:
   E6's gate needs 20 completed positions, and B0's 2027 review dates come with at most about 6. It is worth stating
   in the file's comment if it is ever kept past then.
3. **`funding.margin_per_lot` 67,595** is NSE's initial margin. C2's stressed margin is k × that (about 98,013 at
   1.45), and funds at entry are about Rs 1,00,784. No code reads the field (only `schema.py`), so it is informational.
   Saying "initial, not C2's stressed" would avoid a misreading.
4. Ledger trial 55 has an empty `protocol_commit`. That is consistent: it is filled only at a freeze, and a
   measurement has none.

## Project rules

- **Size:** new files of 13 and 30 lines; `pauses.py` at 139 lines.
- **Design:** `PauseTrigger.text` defaults to `""`, so E6's other triggers are unchanged. The constants are at the top
  of their own module, because `constants.py` is at its size limit.
- **Safety:** no order path and no secret. B0 stays `research` and cannot be promoted by code.

## Addendum 1: `f96cf009` (judge G)

**Verdict: PASS.** This head arrived under the orchestrator's standing go for R3 and B0 work, and I told the
orchestrator before judging. The code fix is `56f1ede3`. `f96cf009` adds only the gates line in response 236.

- **Should-fix 1 is accepted.** `test_b0_s_first_decision_is_on_16_nov_the_first_session_of_december_s_window` runs
  the real `OpportunityFinder` with the NSE calendar from 17 Oct to 30 Nov. The only opportunity day is 16 Nov, for
  the 29 Dec expiry. Claim 4 and the owner effect now say so. Keeping the 19 Oct test is right, because it checks
  `shadow_on` (the account is opened), not that a record exists.
- **Should-fix 2 is accepted.** The self-review section is present, and both defects it found are real.
  1. **A measurement at paper got "not paused" wording.** The single-trade path now uses the measurement text only at
     `research`. Reverting that guard fails `test_a_measurement_approved_to_paper_is_paused_with_e6_s_own_wording`.
  2. **The same-day escalation was lost.** E6 sends one alert per version a day, and the first of two cap losses
     closing the same day carried count 1. The count is now the number of cap losses closed on or before that close
     day. Two mutations each fail one test: `index + 1`, and a strict `<` plus 1.
- **Notes 1-3 are done.** The R3 text says spot. The version file's comments state that `margin_per_lot` is the initial
  margin, and that `expected_range` is per trade against E6's mean. The rule fingerprint is unchanged (`039a6e0733b1`,
  checked).
- **Gates:** ruff check, ruff format and `check_imports` are clean. Full suite in a worktree of `f96cf009`:
  **6,936 passed, 0 failed**.

**Note:** the matching research-only guard in `cumulative_losses` is untested: my mutation dropping it survives (346
passed). The path needs the owner to approve B0 to paper, which its label forbids, so this is not a normal path. A
one-line cumulative case beside the paper test would close it whenever `pauses.py` is next touched.
