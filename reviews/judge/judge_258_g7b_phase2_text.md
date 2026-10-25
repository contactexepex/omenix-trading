# Judge 258: G7b story text, v4 baselines and rule forecasters, phase 2

Trading `story/g7-phase2-baselines` at 59eb8e03 (the G7 builder). The text is `docs/stories/G-forecasts.md` "## G7b".
Lane 1 (forecast and evaluation records). Judge D (G7 phase 1's judge), 16 Oct 2026. The orchestrator's answers to
its questions: part a inside the 22-23 Oct v4 freeze if passed in time; the G7 builder drafts the three PROTOCOL_v4
wordings in the same branch; V4 deferred to G11.

**FAIL: one should-fix.** Everything else is ready for the freeze deadline.

**Met (checked against the protocol and the code on main):**
- **Facts:**
  - `terms.HORIZON_SESSIONS` is V2 5, V3 20 and V7 5, and `terms.POINT_QUESTIONS` is V1-V3.
  - V3, V4 and V5 are `REPORTED_ONLY` and V7 is `DESCRIPTIVE_ONLY` (`fno/forecast_v4/terms.py:42-65`).
  - Primary baselines are as protocol 3.2: V2 and V3 premium-adjusted implied, V7 base rate, V5 option-implied.
  - Phase 1's capture cutoff is already 14:30 (`capture.py:29`, `V4_CAPTURE_START`), so criterion 8 matches the code.
- **V2 and V3 inputs:** trailing, EWMA and HAR daily at h follow phase 1's point-in-time reading. `Ewma.forecast` is
  "h x s2 at the last session before d", and HAR's row for t uses RVs up to t-1. They are missing when not strictly
  positive (protocol 3.1).
- **The blends:** `v2_close_blend` and `v3_close_blend` (the mean of HAR daily and EWMA) carry phase 1's
  `v1_close_blend` argument over and fit no parameter of their own.
- **V7 outcome:** `VIX(d+5) > VIX(d)`, strict, over A7 `regular` sessions (protocol 1.2 and section 2). Its home in
  `series.py` waits on G8's owner (question 3), and G8's tests stay unedited (criterion 3).
- **The split is sound:** parts b and c (pack), c (V5 outcome source) and d (V4, deferred) each get their own text.
  The three protocol wordings needed before the freeze (flagged IV30 missing, V5 and V4 base rates live only, V5's
  `first_seen_at` from A8's check log) are named for the G6 text.
- **Records:** phase 1's layout, phase 1's rows byte-identical (criterion 7), size and method hash (criterion 9).

## Should-fix: `v7_vix_vs_mean20` is not the rival that calibration section 3 measured

The text says the rule "is exactly the rival `PROTOCOL_v4_calibration.md` section 3 already measured. It adds no new
look at spent data and needs no new disclosure." The measured rival (`tools/v4_vix_null.py:44-58`) differs in four
ways:

| | Measured (`v4_vix_null.py`) | G7b's text |
|---|---|---|
| Side test | `VIX(t) < mean20(t)`, the mean over t-19..t **including t**, with t's own close | means "over the 20 sessions before t and before d"; which VIX is compared is not said |
| Tie | equal is "not below", so it counts as above | "strictly above is above; equal is below or equal" |
| Window and minimum | the cell inside the last 750 resolved days; under **100** in the cell, the plain base rate stands in | the most recent 750 **matching** outcomes; under **500**, missing |
| Point in time | at t's close | must hold at d's 14:30 cutoff, where VIX(d)'s close is not known |

So it is a new rule, and the "no new look" justification does not hold as written. The fourth row is a real gap of
its own: the text never says which VIX value stands for d at 14:30. The close of the last session before d is the only
one part a's closes-only inputs have.

**Fix (either):**
- **(a)** Define the rule as the measured rival, adapted only for the cutoff, and state that adaptation as the one
  difference: d's side is VIX(d-1) against its 20-session mean ending at d-1 (and so for t); the tie as measured; the
  cell within the last 750 resolved; and the 100-cell fallback to the base rate. Or:
- **(b)** Keep the new rule, drop "exactly … no new disclosure", and say it is an unmeasured rival. V7 is
  descriptive-only, so this costs no claim, but it must be said.

Either way, make criterion 5 test the chosen side, tie, window and minimum, including the d-1 point in time.

**Note (before the freeze, with the three wordings):** protocol 3.1 writes the trailing baseline as "ending at d" and
EWMA as "h x s2_d". Phase 1's code, which judge G7 phase 1 accepted, and this text read both as the last session
before d, because d's close is unknown at the cutoff. Add a fourth wording saying so, so that the frozen text and the
code agree.

## Addendum 1: head 8976522e (text fix plus part a's code and the three protocol wordings)

**FAIL: one should-fix**, in the back-fill files.

**Met:**
- **Judge 258's V7 should-fix:** option (a). The rule is the measured two-cell rival (`v4_vix_null.py:50-57`).
  - "Below" is strictly below the 20-session mean of that session and the 19 before it, so a tie counts as above, as
    measured.
  - It uses the last 750 resolved outcomes (at least 500), with fewer than 100 on a side falling back to the window's
    plain share.
  - The one change is stated plainly: d takes its side at d-1 and each past t at t-1, and "this lagged rule was not
    itself measured".
  - `vix_rule.py` matches the text line for line.
- **Mutations (each fails tests):** the tie as `<=` (1), no lag (2), no 100-cell fallback (1), a non-strict V7 outcome
  (3), and a trailing look-ahead (2).
- **Part a's code:**
  - `TrailingSum` sums the h sessions before d; `close_blend` is shared by V1, V2 and V3.
  - `vix_up_outcomes` (strict, at t+h's close) is in `series.py`.
  - `records` uses `terms.POINT_QUESTIONS`, and the new ids are in `fno/forecast_v4_rules/constants.py`, because
    `fno/constants.py` sits at 349 of 350 lines.
- **The three PROTOCOL_v4 wordings, read as the G6 judge:**
  - **1.5:** V5's `first_seen_at` falls back to A8's first sighting, and a day with neither stays unresolved.
  - **3.1:** a flagged IV30 gives no raw or premium-adjusted value, missing and counted.
  - **3.1:** V4's and V5's base rates count live outcomes only.
  - All three are sentences added on top of the existing text and do not conflict with G10's planned 15:00 edits.
    They are right. The owner signs them with the freeze.
- **V6's phase-1 rows:** every value, status and inputs hash is unchanged, apart from the new 15 Oct row (script: the
  four V6 files differ only in `method_sha256` and one appended row). That matches the rewritten criterion 7.
- **Gates on 8976522e:** 7157 passed (`-n auto`, Slack token unset), ruff check and format clean, check_imports
  clean.

## Should-fix: the committed back-fill was not made with the committed code

Every committed v4 back-fill row (phase 1's V6 and the new V2, V3 and V7 files) carries `method_sha256` 80c86a8d5885….
The code on this head hashes to **a7d5932795d2** (`METHOD_FILES`: series, baselines, rules, vix_rule, capture).
`python -m fno forecast-v4 backfill` on 8976522e is refused: "base_rate/v6_abs_move_2pct_next_session 2017-01-03: a
different row is already written". So criterion 7's "a re-run writes identical files" fails on the exact SHA. The
text's own freeze rule says "the freeze uses the last regeneration, made with the hashed code", and these files break
it.

**Fix:**
- Regenerate the back-fill on the final code, in the same commit as any method-file change.
- Add a test: every row in `research/forecasts/v4/` from these forecasters has `method_sha256` equal to the
  `METHOD_FILES` hash of the tree. This is the freeze-checklist item the orchestrator asked about, and it catches the
  next edit that forgets to regenerate.

## Notes for the freeze

- The fourth wording (trailing "ending at d" and EWMA "h x s2_d" read as the last session before d) was **not** added.
  It is my suggestion, not a criterion. Add it to 3.1 before the freeze, or record why not.
- Freeze checklist: back-fill hash equal to the frozen method hash (the test above), the three wordings in the hashed
  `PROTOCOL_v4.md`, and phase 1's files regenerated together with the phase 2 files.

## Addendum 2: head 43bceece

**FAIL still: addendum 1's should-fix is open.** The messages crossed. 43bceece answers judge 258's V7 point in the
text and adds the fourth wording, but changes no record file.
- **Met:** the fourth PROTOCOL_v4 wording is in 3.1 ("For both trailing and EWMA, 'ending at d' and s2_d are read as
  the last session before d"), and a test reads all four wordings. The V7 text matches the code and criterion 5's tests.
- **Open:** the committed back-fill rows still carry `method_sha256` 80c86a8d5885, and the code still hashes to
  a7d5932795d2 (my script on 43bceece). Regenerate the back-fill on the final code and add the row-hash test
  (addendum 1).

## Addendum 3: head a33c1d48 (the back-fill regenerated)

**PASS: the G7b text and part a's code may merge before the v4 freeze.**
- **Root cause, as the builder found it:** `ruff format` rewrapped docstrings in the method files after the
  regeneration, which moved the hash. The back-fill is now regenerated on the final code, in the same commit.
- **My script on a33c1d48:** every G7 row carries `method_sha256` a7d5932795d2, equal to `wiring.method_sha256()` of
  the tree. `python -m fno forecast-v4 backfill` adds 0 rows.
- **New test:** `test_every_committed_g7_record_row_carries_this_trees_method_hash`. **My mutation** (a one-line
  comment appended to `baselines.py`) fails it. It is now the freeze-checklist item, named in criterion 7.
- **Gates:** 7158 passed (`-n auto`, Slack token unset).
- **Correction to addendum 1:** I reviewed 8976522e, and the fourth wording came one commit later, at 43bceece. It is
  in 3.1 and tested.
