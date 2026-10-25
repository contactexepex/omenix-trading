# Judge 214: LR3 story text, drift detection with a CUSUM (quality rule 1; judge E)

Date: 16 Oct 2026. Branch `story/lr3-drift-cusum`. The orchestrator named 2b9f2500; the tip is now **1452b398**,
which adds only the placement agreed with LR1's builder and a merge of `main`, and that is what I judged
(`docs/stories/LR-learning.md` LR3, response 216, `research/2026-10-16-lr3-drift-evidence/`).

## Verdict: FAIL (story text): 4 should fix, 2 minor. The statistics are right; the wiring to the desk is not complete

### The evidence: re-run, identical

I re-ran all four scripts from the repository root. Each output is **byte-identical** to the committed `.out`
(`arl`, `strategy_arl`, `calibrate_h`, `backfill_cusum`).

| Claim | Check (mine) | Status |
|---|---|---|
| k 0.5: h 4 gives 334, h 5 gives 925 between false alarms | `arl.out`. The text's "40, not about 230" compares a median with the 334 mean (median about 0.69 × mean); correct | MET (strong) |
| A fixed h = 4 is wrong both ways | SF challenge (skew -2.63): in-control median 40 trades; BF challenge (skew +2.38): 3,000 (the cap) | MET (strong) |
| Per-version h, ten-year median target, floor 4: h 4.0-5.5 | `calibrate_h.out`: h* 4.5, 4.5, 4.0, 5.5, 4.0 and 1.0, so 4.0-5.5 after the floor | MET |
| Design 5.8's forecaster rule as written fails | First-60 SD 0.0001 against 0.0822 over the whole history: 287-503 alarms. The diagnosis is right | MET (strong) |
| 20-outcome blocks: 0 alarms in 95; 1 s worse caught in about 7 blocks | Reproduced. **In-sample:** `s` comes from the same blocks the CUSUM runs on (see minor 2) | MET (some evidence) |

The design choice is sound: the CUSUM catches a collapse of about 1 SD, and lost edge stays the scheduled review's
job. The catastrophic-loss rules remain the faster first line.

### Should fix

1. **Nothing runs the monitor, so no alarm can pause anything.**
   - The text never says when the strategy CUSUM runs.
   - I checked that nothing schedules E6's own pause run either: no workflow and no O1 step (`git grep scorecard` on
     `main`, `.github/` and `story/o1-daily-run`'s `fno/daily` finds nothing).
   - A pause that only runs with the weekly post-mortem would come days after the trade that broke the strategy.
   - **Fix:** name the trigger. For example, an O1 step after the exits, the same step that should run E6's pauses,
     agreed with O1's builder. Say that a version reaches `paper` only once that step is live.
   - Today nothing is at `paper`, so no money is at risk; but this must be settled before the first approval.
2. **The D1 change is larger than the text says.** It names only `expected_sd_per_opportunity`. It also needs:
   - `trades_per_year`: the text reads it "from its plan", but `PLAN` in `fno/playbook/schema.py:28` has no such
     field;
   - the calibrated `h`, "frozen in the plan": a plan field too;
   - the approver `drift_rule`: `fno/playbook/transitions.py:18` lets only `owner` and `hard_loss_rule` move
     `paper -> paused`, and E6's `AutoPauser.apply` hard-codes `APPROVER_HARD_LOSS_RULE`
     (`fno/scorecard/pauses.py`).

   List all four in Scope and Depends (D1's transitions, E6's pauser), through the orchestrator. Or reuse
   `hard_loss_rule` and say so: the record should show which rule paused a version.
3. **A forecaster h = 4 is evidenced for V6a's Brier only.**
   - The back-fill check covers three V6a forecasters. The text applies h = 4 to every forecaster, including V1's
     QLIKE, whose loss differences are heavier-tailed and have no back-fill here.
   - That is an unsourced number for V1-V3.
   - **Fix:** monitor V6 now, and show V1-V3 as "drift not monitored" until each is calibrated the same way. Or add
     the evidence.
4. **The alert's wording is not specified.** Design 6.5 requires every alert's first line to say what to do or
   "information, no action", and an owner-delay line (what the paper record assumes if the owner acts 60 minutes
   later), on a PAPER ONLY record. Add that, as M2 and LM1 do.

### Minor

1. "A 1 SD collapse flagged in 8-12 trades" holds at the calibrated h. BF challenge, raised to the floor of 4, flags
   in a median of 6 (`strategy_arl.out`, h = 4). Say 6-12.
2. Label the forecaster back-fill result **in-sample**: `s` is the SD of the same 95 blocks, so 0 alarms is partly by
   construction. The criterion 6 check is fine as a regression test.

### The owner's questions (judged as slots)

- **Q1 (calibrate h):** supported by strong evidence.
- **Q2 (blocks):** supported for V6; see should-fix 3 for V1-V3.
- **Q3 (pause):** matches design 4.3 and 5.8. If the owner chooses "alert only", should-fix 1 shrinks to the alert's
  trigger.
- **Q4 (require the SD for `paper`):** consistent; it makes every approved version monitored.

None of the four options changes the four should-fix items, except Q3 as noted.

### Checked against E6, O1 and E8

- **E6:** the pause path exists and fits (`AutoPauser` takes triggers, alerts shadows only, pauses once), apart
  from the approver (should-fix 2). A restart is owner-only (`PAUSED -> PAPER`), as the text says.
- **O1:** see should-fix 1.
- **E8:** not touched. LR3 decides no fill and no reaction time.
- **Duplicates:** none. LR1 reads the alarms; G8's scores are read, not recomputed.

**Verdict: FAIL for 1452b398** (story text). Fix should-fix 1-4 (minor optional), then re-judge.

---

## Addendum 1 (judge E): final head 9a738de6: PASS (story text)

Diff `1452b398..9a738de6`: docs only (`LR-learning.md`, response 216). The owner's four answers are written in, and
match the decision row "LR3 drift detection: the four design answers accepted as recommended" (16 Oct,
`docs/DESK_DECISIONS.md:232`).

| Should-fix | Fix | Accepted? (my evidence) |
|---|---|---|
| 1 Trigger | Runs every session in O1's `reviews` step after `exits`: E6's `ScorecardReview` first, then LR3's `DriftReview` (`review(day, marks) -> ReviewResult`). It uses the run's one sender, and an append-only `journal/drift/alarms.csv` makes reruns do nothing twice (criterion 9). "No version reaches `paper` until that step is live" | Accepted. The interface is real: `fno/daily/reviews.py` at e57046f3 (on `story/o1-daily-run`) has `Review`, `ReviewResult(lines, open_positions=0)`, `ScorecardReview` and `ReviewsStep`. This also closes the gap I noted for E6's own pauses: the same step runs them |
| 2 D1 and E6 changes | A "changes owned elsewhere" section: three plan fields (`expected_sd_per_opportunity`, `trades_per_year`, `drift_h`, all required for `paper`); `drift_rule` added to `paper -> paused` (`transitions.py:18`); `AutoPauser` takes the approver from the pause. Depends updated | Accepted. All four gaps I listed are named, each through the orchestrator |
| 3 V1-V3 | Only V6 is monitored. V1-V3 show "drift not monitored until calibrated" (criterion 11), and each joins after its own back-fill check | Accepted |
| 4 Wording | Strategy: the first line says what to do; forecaster: "Information, no action"; both with the 60-minute line and PAPER ONLY (criterion 10) | Accepted. Matches design 6.5 |
| Minor 1 and 2 | "6-12 trades"; the forecaster result labelled in-sample | Accepted |

**Verdict: PASS for 9a738de6** (story text). Code may start. Its O1 wiring line lands with LR3's own code commit, as
agreed.

## Addendum 2 (16 Oct 2026, judge B, delta re-check): f6716b56, after ChatGPT review 134 (response 233)

The delta since 9a738de6 (judge 214 addendum 1) is docs and research evidence, plus a `main` merge: the LR3 story
text, `calibrate_h_blocks.py` and its output, and the README row. There is no code.

- **(1) `drift_h = max(4, h_iid, h_block)`** with chronological circular blocks of 3. **I re-ran the evidence script
  myself** (`python3 research/2026-10-16-lr3-drift-evidence/calibrate_h_blocks.py`), and its output is
  **byte-identical** to the committed `.out`.
  - The story's numbers match it: `h_iid` 1.0-5.5, `h_block` 1.5-6.0, frozen 4.0-6.0. Only challenge SF rises, from
    5.5 to 6.0.
  - "Fewer than 30 research trades is uncalibrated and refused `paper`" is consistent with the samples (the smallest,
    discovery BF, has n = 30 and is calibrated).
  - The text says plainly that block length 3 is a stress check and that the median is not a ten-year guarantee
    (criterion 13).
  - Note for the code round: the registration's 10th and 90th percentile run lengths at `drift_h` are promised by the
    text, but the evidence script does not compute them yet.
- **(2)** The name "research-to-paper performance drift"; `mu0` and `sigma` never re-estimated; E8's no-fill and
  opportunity rate beside the CUSUM (criterion 14). Correct: re-estimating from paper results would erase the failure
  it is meant to catch.
- **(3)** AI slots are not monitored until 12 live blocks (criterion 11).
- **(4)** S1's `immediate_pauses` names the drift exception before any activation. It is a dependency on S1's text
  owner, stated.
- **(5)** The pause scope is one version in every book. Other versions keep opening, the drifted version's open
  positions still exit, and the restart row records its provenance, with the CUSUM restarting at 0 (criterion 12).
  Correct, and narrower than a whole-book halt, which would need its own owner decision.

**The builder's correction to review 134: confirmed.** Review 134 says "SF already has an unacceptable 40-trade median
at h=4". The 40 comes from `strategy_arl.out` at the **fixed** design value h = 4 (challenge SF: in-control median
40). Under LR3's per-version calibration, SF already had h = 5.5, with an in-control median of 172 trades
(`calibrate_h.out`). So the floor of 4 was never SF's operative threshold. The block check still adds a margin for
clustered losses (5.5 to 6.0), which is the useful part of point 1.

**PASS for f6716b56 (text).**
