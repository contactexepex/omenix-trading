# Judge 95: weekly options and market-weather study: `story/x-weekly-weather-study` 188ef58 (lane 1, response 93)

**What I did:**
- read the protocol, freeze record, `study.py`, `report.py`, the ledger rows and response 93;
- checked the hashes at all three commits;
- re-ran the study on the run tree;
- recomputed the claims from `results.json`, `trades.json` and the panel;
- ran the full gates on a trial merge.

## Gates

On a trial merge with `main`:
- 3,152 passed with `FNO_SLACK_BOT_TOKEN` unset;
- `ruff check` (including the study folder), `ruff format --check` and `check_imports` are clean.

The ledger-guard change pins rows 1-52 and adds a count check for the new experiment (10 rows, 10 hypotheses). Nothing
is loosened.

## Claims

| Claim | Result | Evidence |
|---|---|---|
| (a) Freeze order and one run | MET | The SHA-256 of `PROTOCOL.md`, `study.py` and `report.py` match `FREEZE.md`, and they are identical at 650dd8f, ea52245 and 188ef58. 650dd8f (18:07:58 UTC) holds only those three files. ea52245 (18:08:20) adds `FREEZE.md` and ledger rows 43-52, all naming 650dd8f. The results first appear in 188ef58 (18:18:02). My re-run on the 188ef58 tree took 33 s, and `results.json`, `trades.json` and `results.md` came out **byte-identical** (`results.json` SHA-256 starts 8f7b5af2). Git order cannot prove that nothing ran before the freeze; that rests on the freeze record's attestation, as in experiment 1. |
| (b) No edge in W1-W5; RED not significantly worse | MET (strong evidence for "no edge shown") | `results.md` and response 93 match row for row: t from −2.15 to −0.02, Welch t from −1.29 to 1.24, nothing passes. The max-loss hit shares recompute (W1 269/378 = 71%, W2 303/380 = 80%). |
| (c) Data legality and source | MET | NSE's public daily bhavcopy, through A3's panel. The first entry is 1 Feb 2019, the first expiry 14 Feb 2019, and there are 396 opportunities. Weekly NIFTY options began in Feb 2019. |
| (d) Costs of Rs 35-124, against C1 including exercise STT | MET in code; **mislabelled in the text (must-fix 1)** | Entry costs come from `order_charges` and expiry costs from `settlement_charges_breakdown` (E7: STT on an exercised long at `stt_exercise_pct` 0.15%, brokerage and GST per in-the-money leg). That is C1 as built. See must-fix 1. |
| (e) Spent history and labels | MET, with should-fix 1 | Weekly option prices were never used in a P&L trial. Judge 46's weekly/monthly fix read only dates and listings, and desk meeting 1 was monthly, 2024-26. The protocol labels the study "historical test on unused option prices, with exposed predictors". |
| (f) The 2020 and 2024 narratives | MET | Every figure matches `results.md`: RED from 28 Feb 2020; put +76,453 in the 6-12 Mar week; −9,612, −8,195 and −7,782 in April; the bear put spread at about +3,500 in March weeks and about −3,000 in April; the condor from −3,655 to +4,679. 2024: NIFTY 23,263.90 on 3 Jun to 21,884.50 on 4 Jun is −5.93%; it closed 22,821.40 on 6 Jun, above the 31 May entry of 22,530.70. |

## Must-fix

1. **"Costs Rs 35-124 a trade" leaves out the pads, but the comparison with monthly costs includes them.**
   - The Rs 1 pads are inside each fill price, so they sit in "gross", not in "costs". In `study.py`, `fills` add
     `PAD * s` to the close.
   - Response 93 compares Rs 35-124 with the monthly four-leg Rs 810-940, and that monthly figure includes Rs 520 of
     pads.
   - The like-for-like weekly figures are W1 about Rs 102 (37 + 65) and W5 about Rs 384 (124 + 260).
   - Its "mean gross before costs" is likewise after pads.
   - The conclusion still holds, since weekly costs are well below monthly ones. But the numbers the owner reads must be
     labelled: say "charges" for 35-124, and give charges plus pads.
2. **"The third independent 'no edge' result" overstates the evidence.**
   - Response 92 is not an independent test. It re-reads experiment 1's monthly data and adds the cost and
     proof-horizon arithmetic.
   - The independent tests are two: experiment 1 (monthly, 2019-23 holdout) and this study (weekly prices, used once).
   - The owner is asked to weigh whether to continue the whole strategy search on this count, so it must be right.
     Write "the second independent test, after experiment 1; response 92 explains why monthly costs and proof times
     block it".

## Should-fix

1. **Say what the test could and could not detect.**
   - With n of about 380-394, the 99% one-sided upper bounds on the mean net per trade are: W1 +387, W2 +401, W3 +357,
     W4 +27, W5 +82.
   - So the data rules out a W5 edge above about Rs 82 a trade and a W4 edge above about Rs 27, but it leaves room for a
     W3 edge up to about Rs 357. That is stronger and more precise than "no edge shown".
   - Also say that the outcomes depend on NIFTY's exposed index paths, not only on the fresh option prices. That
     exposure cuts toward false passes, so it does not weaken this fail.
2. **The data window.** The protocol says "sessions to 9 Oct 2026", but the run includes expiries up to 13 Oct 2026,
   because A13 appended 12 and 13 Oct before the run. `study.py` has no end date, so a re-run on a later panel gives
   different results. Record in the README that the run used the panel at 188ef58 (manifest end 2026-10-13), and that a
   re-run must use that tree.
3. **"Weekly options began in February 2019, so the first trade is 1 Feb 2019".** That first trade (1 to 14 Feb) is a
   two-week hold after the January monthly expiry, not a weekly one. It is immaterial, but say so.
4. **Response number collision.** `response_93` is also used by `story/s1-owner-batch1`
   (`response_93_s1-owner-batch1.md`). Renumber one of them before both merge.

## Verdict: FAIL for 188ef58

Two must-fixes, both in response 93's text: the cost labels and the "third independent" count. The study itself is
sound:
- frozen before running;
- reproducible byte for byte;
- C1 costs, including exercise STT;
- every number checked.

Its verdict, that no weekly edge was shown and the RED filter does not help, stands.

## Addendum 1 (14 Oct 2026): ada5f7f (fix commit b062bc7 plus a clean merge of `main`)

| Item | Result | Evidence |
|---|---|---|
| Must-fix 1: charges against charges plus pads | MET | The table splits gross before pads, pads (Rs 1 × legs × 65), charges, and charges plus pads. I recomputed every value from `results.md`: W1 −452+65 = −387, total cost 37+65 = 102; W2 −566, 100; W3 +226, 229; W4 −102, 219; W5 +160, 384. The text now compares Rs 100-384 with the monthly Rs 810-940. The builder also corrected its own claim, correctly: before costs, W3 (+226) and W5 (+160) show a small premium, and their costs (229 and 384) eat it. |
| Must-fix 2: "second independent test" | MET | It now reads "second independent test, after experiment 1". It says response 92 re-read that data. |
| Should-fixes 1-4 | MET | The 99% upper bounds match mine (+387, +401, +357, +27, +82), with what each rules out. The index-path exposure is stated. The data window is stated (13 Oct; reproduce at 188ef58), in the response and the README. The two-week first trade is stated. The response is renumbered to `response_94` with its index row, so there is no longer a collision with `response_93_s1-owner-batch1.md`. |
| Frozen and result files | MET | `PROTOCOL.md`, `study.py` and `report.py` still match `FREEZE.md`. `results.json`, `trades.json` and `results.md` are unchanged since 188ef58. |
| Gates | MET | Trial merge with `main`: 3,161 passed with the Slack token unset. `ruff check`, including the study folder, and `check_imports` are clean. |

**Verdict: PASS for ada5f7f.** Merge it. After the merge I check `main` and CI.

## Addendum 2 (14 Oct 2026): merge e4b0e4c MET

- **Merge matches the recomputation.** Parents are 944468c and ada5f7f. It equals my recomputed `git merge-tree`
  exactly.
- **No unjudged change after it.** The only non-log change is e6c6558, the A8 Action's own data rows. That is lane 3.
- **CI is green** on 2541825 (the first push carrying the merge) and on every commit after it, up to d822189.
- **Observation for A8 (judge 89).** e6c6558 is the first participant-OI row written by the GitHub Action.
  - 14 Oct now counts as a measured day: there are 17 absent checks, the last at 18:28 IST, then present at 00:20 IST on
    15 Oct.
  - NSE wrote the file at 18:52 IST (Last-Modified 13:22 UTC).
  - So the first-seen time is about 5.5 hours after the write. Two things caused that: the routine's checks stopped at
    18:28 IST, and the Action ran late.
  - This errs on the safe side (still next session), as judge 89 said. But it shows that the measured times will
    overstate the release time while the schedule runs late.
- **Follow-up (A8, not this story).** Decision row d822189 says "14 Oct is excluded from the measured release days".
  Nothing in the code excludes it: `first_seen_times` still counts 14 Oct as measured, because it has absent rows and
  then a present row at 00:20 IST.
  - The error is on the safe side: the lag is still the next session, so the rule is unchanged today.
  - But the text and the code disagree. Either the exclusion is built (lane 1: a dated exclusion list read by
    `first_seen_times`, with a test) or the row should say "counted, with a late first-seen".
