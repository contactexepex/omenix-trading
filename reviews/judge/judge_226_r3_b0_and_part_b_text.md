# Judge 226: R3 addendum, B0's registration and part B, story text (judge G)

- **Judged:** `story/r3-part-b` at `371932fe` (builder session 0145TfSwzmpk6MBrH92f5h4G). It is `894f58c2` with the
  claims file renamed to `response_232_r3-b0-and-part-b-text.md`. The diff is docs only: the "R3 addendum (16 Oct
  2026)" in `docs/stories/R-factory.md`, the R3 work-register row, and the claims file with its README row. Lane 1.
  The orchestrator gave the go. 226 was the next free number on main.
- **Verdict: FAIL (text).** One should-fix: B0's cumulative-loss alert has no measurement wording, and our own data
  shows that alert firing. There are also 4 notes. Everything else is right and simple.

## The orchestrator's points

1. **Criteria 10-12 against response 229 (review 132 points 1, 3, 4): MET, with one omission (note 1).**
   - 10 lists C2, C4, E6, S2, S3 and Book 1's ledger files byte for byte, after E8's real fills, and gates the merge.
     That is review 132 point 1.
   - 11 covers both readers (`_stored_action`, `recorded_c4`), explicit mode and account, a same-ID test, and failing
     closed with no fallback to Book 1's file. That is point 3.
   - 12 bases readiness on resolved closed trades read after E2c's download, never on `exists()` (`stop_rule_tracker.py:41`
     is the `exists` method, as I checked). Zero resolved shadows gives `undecided / no_economic_test`, and a run
     before the download reports "data not loaded". That is point 4.
2. **One `is_measurement` source: MET** (strong evidence, code read).
   - `edge_family` is an existing D1 field (`schema.py:22,80,126`), as free text. The worked example's value is
     "short premium, defined risk", so B0 is the only `measurement`.
   - No other story or module defines a measurement predicate: `is_measurement` and other uses of `edge_family`
     appear nowhere in `fno/` or `docs/` except D1's field list.
   - Putting it in `fno/playbook/measurement.py` is right: `fno/constants.py` is at 348 lines.
3. **B0 kept out of Test B and G6: MET.**
   - In Test B, a measurement shadow is listed, never counted (criterion 12).
   - G6 and positive-candidate counting have no code yet, so the exclusion is honestly held by the label, the card and
     the ledger row until that code reads `is_measurement` (Known limits). I found no promotion code in `fno/`.
4. **The stale-close known limit: MET, and correct** (strong evidence, `research/2026-10-12-experiment-1/RESULTS.md:80`).
   - On 9 May 2019 the 11550 put's close was 415.25 on 45 contracts, against about 248 of intrinsic value. That gives a
     spread of 307.90, above the width of 300, so -11,346 against a modelled 8,152.
   - The limit says the right thing: C2 caps the modelled loss, not the realised one. A live exit at quotes through a
     spread wider than B2's pad can still pass Rs 10,000.
   - The pad reasoning holds: at 21 or more days the spread's mid is at most its width, so the realised loss beats the
     model only when the quote spreads exceed the pad plus the gap between the mid and the width. It is correctly
     marked "reasoning only".
5. **The file split with E6b: accepted on the builders' word** (some evidence).
   - R3 makes the edits to `pauses.py` and `report.py`; E6b changes only the entries line of `card_lines`.
   - A test pins the non-measurement bytes.
   - E8 adds no caller of the two readers.
   - Agreement between sessions cannot be checked from the repository. The E6b row (`docs/WORK_REGISTER.md:31`) does not
     list R3's edits, and R3's own row still says "to agree with E6b" (note 4).

## Other checks

- **Registration by the desk:** `transitions.py:15` allows `(None, RESEARCH)` for owner or desk. MET.
- **B0 = P1 exactly:** matches response 92's B0 row (forward × 1.02 / × 0.98, widths 300 to 100 within the Rs 10,000
  cap, monthly 30-45 days, exit at 21 or more days, no entry condition). The worked example shows that D1 already
  expresses `width_rule`, `widths` and `expiry`. MET.
- **Numbers:** -34,486 over 60 opportunities (58 traded), worst -11,346, and Rs 1,00,784 funds at entry
  (`response_92:143`) all match the sources. MET.
- **Review 129's alert wording** (owner review or retirement, no further promotion, still eligible for entries until
  the owner acts) is in R3's passed text (`R-factory.md:116-118`). The addendum reuses it. MET.
- **Register:** the stale second R3 row is removed, so one row remains. Good.

## Findings

### Should fix

1. **B0's cumulative-loss alert has no measurement wording, and our own data shows it firing.**
   - E6 has two shadow alerts (`fno/scorecard/pauses.py`). The addendum gives measurement wording only to the
     single-trade catastrophic one.
   - The cumulative alert fires for a research shadow on any day one of its trades closes while its realised net is at
     or below -3 × `catastrophic_loss_rs` (Rs -30,000 for B0). It then repeats on every later close day.
   - **In our data:** P1, B0's exact rule, ended 2019-23 at -34,486, with a maximum drawdown of 40,607
     (`RESULTS.md:34`). Its total crossed -30,000, so this alert would have fired, and then fired every month.
   - Today it would read "{version} shadow test, not paused: the owner decides (cumulative loss ...)". That has no
     `(measurement)` label, against criterion 8's "every output showing it carries `measurement`". It also invites the
     owner to read an expected measurement cost as a strategy failure, or as the simulator-defect escalation.
   - **Fix (text only):**
     - state the B0 wording for the cumulative alert: the label, plus "expected for a measurement (no edge), not a
       defect", or the owner's choice of wording;
     - say whether its monthly repeat is kept;
     - add it to test 7 beside the first and second single-trade losses, with a non-measurement shadow's bytes
       unchanged.

### Notes

1. **Criterion 12 omits "checked against the registered trial requirements"** (response 229 point 4, review 132 point
   4). The tracker's separate R1 input row (pass mark and minimum useful net, `stop_rule_tracker.py`) covers it in
   effect. One clause in 12 would make the match exact.
2. **Boundary wording:** the escalation counts trades "at or beyond its cap", which matches E6's `net <= -cap`. The
   alert text says "over Rs 10,000". A loss of exactly Rs 10,000.00 is not a normal path, so no fix is needed. The test
   can pin E6's `<=`.
3. **Honesty of the headline:** the -34,486 includes 7 impossible exits on stale closes. Without them it is -23,140
   (`RESULTS.md:86`), and the clean worst trade is -8,937. Both figures say B0 loses money. A half-line would show
   both.
4. **Register status:** R3's row still says "to agree with E6b". The text says the split is agreed, so the row should
   say "agreed 16 Oct". Lane 3, any time.

## Project rules

- **Scope:** docs only. Part B's code waits for E8 part 1b, and B0's registration is a desk act the owner chose
  (decision 1 A). No order path and no secret.
- **Simplicity:** one existing field, one predicate, and one message constant. No new framework.

## Addendum 1: `7f94dbdf` (judge G)

**Verdict: PASS (text).** The fix reached me from the builder. I re-judged it as part of the judge and builder loop and
report the verdict to the orchestrator. The diff since `371932fe` touches docs only: the R3 addendum, the R3 register
row and response 232.

- **Should-fix 1 is accepted.**
  - The cumulative alert for a measurement has its own message constant. It carries `(measurement)` and says
    "expected for a measurement (no edge), not a defect; the owner decides".
  - Test 7 covers it, and a non-measurement shadow's bytes stay unchanged for both alerts.
  - Keeping the repeat is reasonable. Changing E6's repeat rule would touch other shadows, and about one alert a month
    is the measurement's running cost. It is marked "reasoning only".
  - **The claim about a day where both alerts fire is correct** (code read). `fno/scorecard/run.py:35-36` builds
    drifts, then single-trade triggers, then cumulative ones, and `AutoPauser.apply` sends once per version a day. So
    the single-trade wording, with its escalation, wins. Test 7 pins it.
- **Note 1 is done.** Criterion 12 now adds "checked against the registered trial requirements (R1's pass mark and
  minimum useful net)", so it matches response 229 point 4 exactly.
- **Note 2 is done.** The alert says "Rs 10,000 or more", matching E6's `<=`, and test 7 pins a loss of exactly the cap.
- **Note 3 is done.** The text gives -23,140 without the 7 stale-close exits, and the clean worst trade of -8,937, both
  matching `RESULTS.md`.
- **Note 4 is done.** The register row says the split with E6b was agreed on 16 Oct.
