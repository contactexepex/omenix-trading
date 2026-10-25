# Judge 96: design v2 and re-plan: `story/x-design-v2` d48bdfc87f0e85c62be7dbed109a5c2710f4157e (PR #100, response 95)

**What I did.**
- Read all 15 files in full: `docs/design_v2/` and response 95.
- Checked each claim against `docs/DESK_DECISIONS.md`, `research/evaluation/PROTOCOL.md`, response 92, judges 93-95 and
  my own merge records.
- Re-derived every formula the design uses.
- **Scope:** documents only. Every file is under 350 lines; the longest, `REPLAN.md`, has 159.

## Claims

| # | Claim | Result | Evidence |
|---|---|---|---|
| 1 | Forecasts settle skill in months; trade P&L takes years | **PARTLY (must-fix 1)** | "Trades take decades" is right: 1,200-2,000 trades for +153 (response 92, judge 93). The 5.5 power formula is right: n = (2.49 × r)², with 1.645 + 0.842 = 2.487; r 5 gives 155 and r 10 gives 620. But it uses an unadjusted one-sided 5%, while 5.5 tests with Holm across the family. See must-fix 1. |
| 2 | Protocol v4: QLIKE and Brier scores, implied vol as the primary baseline, Holm, minimum effects, power check after 60 outcomes; G1 v3 stays frozen | MET as a design | QLIKE = RV/f − ln(RV/f) − 1, as in Patton 2011. Brier and log scores, reliability table, block bootstrap with the block length at least the horizon. Implied vol is the primary baseline for V2, V3 and V5. v4 is a new version; no frozen file is edited. Open question for ChatGPT (response 95 asks it): HAC t-test against block bootstrap at small n. |
| 3 | Weather becomes a scored large-move forecaster, with response 94 as v0 baseline | MET | p_big_1d and p_big_5d, v0 checklist as the baseline, thresholds registered before use, "price of calm" reported. The owner's "red means no new trade" (decision row of 14 Oct, trading principles) is kept. |
| 4 | Cost wall at 2× full cost; B6 history scan replaced | MET | The cost figures match judges 93 and 95: four-leg 810-940; weekly 100-384 including pads; two-leg about 410. 2 × 820 = 1,640 stops the condor's best gross of 978. Replacing B6 is right: a scan of spent 2019-26 history would be one more trial on spent data. |
| 5 | Desk: Rs 20 lakh, bucket cap Rs 30k, account cap Rs 1.5L, brake Rs 1.2L, consistent with the Rs 10,000 per trade | MET | Owner row "Paper account Rs 20 lakh, Rs 10,000 maximum loss per trade" (=> YES). The bucket cap is 3 × 10,000. The brake is 6% of 20 lakh, the same 6% as Rs 30,000 on Rs 5 lakh. All caps are labelled proposals, for the owner to decide. |
| 6 | T1 card replaces P4; the advocate's code checks can block, its AI objections cannot | MET | Matches the owner's "devil's advocate attacks every call" (row of 14 Oct). Not letting it veto keeps the paper record a test of the registered rule. Its objections are scored. |
| 7 | REPLAN keeps built work; slice A 15 Oct - 4 Nov; stop review about 31 May 2027 | PARTLY (should-fix 1, 3) | Nothing built is dropped. Only B6's scan and F4's owner overrides are dropped, both by owner rows ("never override on paper"). "The last session of the 6th full month after an early-November freeze" is 31 May 2027. Statuses and dates: see below. |
| 8 | S1: 8 open items change; decided items are not reopened | **PARTLY (must-fix 3)** | `PROTOCOL.md` has 18 items: 5 decided, 13 open, matching REPLAN section 4's list. Seven open items change, plus the open t-check. But REPLAN section 4's note adds G8 and E8 to the decided `frozen_files` list. |
| 9 | 11 owner decisions in REPLAN section 5 | MET as a list, but incomplete (must-fix 3) | The 11 lines are there. The `frozen_files` extension is missing from them. |

Also verified:
- CUSUM: k 0.5 gives one-sided ARL0 of about 930 at h 5 and about 340 at h 4. The text says "about 900" and "about 340".
- Straddle: 0.8 × S × σ × √T gives Rs 790 a unit and Rs 51k a lot (30 days), Rs 21k a lot (5 days), at NIFTY 25,000.
- Expected false passes: 52 trials × 1% = 0.52.
- Every decision quoted (eight layers, volatility focus, 20 lakh, the ten differentiators and eight missing pieces,
  trading principles, judge plus ChatGPT, future slices follow v2) matches a 14 Oct owner row.

## Must-fix

1. **The "months" claim uses the wrong significance level.**
   - Section 5.5 tests with Holm at 5% family-wise, but its power arithmetic uses one-sided 5% per comparison.
   - With k registered comparisons, Holm's first step is at 5%/k. Say k is 15: judgeable questions V1, V2, V6 (two
     parts) and V7, times 3 forecasters. Then z = 2.71, and n = ((2.71 + 0.84) × r)² = (3.55 r)².
   - That gives 315 outcomes at r 5 (V1: about 15 months) and 1,260 at r 10 (about 5 years). The text says 8 months to
     2.5 years.
   - V1 also starts only after A16 has run 20 sessions, and A16 waits on the owner's host decision. Its primary
     baseline, HAR on intraday data, needs about 250 sessions.
   - Fix: redo the arithmetic at the family's actual level. Restate "months" as "about a year or more for the daily
     questions, at favourable r", in `01_` 1.3, `OWNER_SUMMARY.md` and response 95. "Faster than trades" still holds,
     with strong evidence; "months" is not shown.
2. **The stop rule's Test A treats "not shown" as "no skill".**
   - On 31 May 2027, about 6 months after v4's freeze, most comparisons will be underpowered by must-fix 1's
     arithmetic.
   - As written, "no" on Test A plus "no" on Test B leads to stop or pivot. So the owner could stop for lack of data, not
     lack of skill.
   - Fix: use the 60-outcome power report section 5.5 already defines. A comparison whose projected date is past the
     review is "undecided". Test A then has three answers: yes, no (adequately powered and not shown), or undecided.
     State the owner's choice for "undecided" in 8.2 (for example, continue at reduced AI cost to the projected date,
     or stop).
3. **A decided S1 item is changed without an owner decision.**
   - REPLAN section 4 says "the new scoring code (S2's change, G8, E8) joins the hashed list before the freeze".
   - The owner decided `frozen_files` on 14 Oct (option A): the S2, S3, F8 and F9 code joins the list, and version 1
     waits for it.
   - Adding G8 (forecast scoring) and E8 (fills) changes that decided value. It also lengthens the wait before
     counting.
   - It may well be right, but it is a change to a decided item. Fix: put it to the owner as decision 12 in section 5,
     with the delay it adds, or drop it.

## Should-fix

1. **REPLAN section 1 statuses are stale.** They were read from `docs/stories/*`, not from the judge record. Already
   PASSed and merged: A12 (judge 51, merges 09e51a7 and 510b5c6), C4 (83, dafbebe and b03c4ef), E3 (82, 85c570a and
   e6484cc), E5 (84, 58f5781), S1 (85, bdd46ff and 35f6f46; owner batch 1 e46e3d8) and A14 (77, 6568315). Slice A week
   1's "judge rounds of the built queue" is smaller than the table implies. Take statuses from
   `reviews/judge/README.md`.
2. **Decisions are cited by row number** ("decision 94", "60", "56", "55", "52"). Those are line positions in
   `DESK_DECISIONS.md`; they change when rows are inserted, and two already point one row off (55 and 56). Cite each by
   date and bold title.
3. **Slice A dates.** About 10 M-sized and 5 S-sized stories, for two builders, in 15 working days, plus judge rounds,
   is at the edge of possible (reasoning only). The critical path depends on others:
   - G6 needs ChatGPT agreement before G7, G8 and M1;
   - the host decision gates A16, E8's real fills and LM1;
   - C5 waits for the owner's numbers.

   Mark the dates as targets and name these dependencies. Otherwise a slip will look like a broken promise.
4. **"88-93% of F&O traders lost money FY22-FY26 (SEBI)".** SEBI's published studies cover FY22-FY24 (and FY25 in a
   2025 update). Cite the exact studies, or drop FY26.
5. **Prices at NIFTY 25,000 are illustrative.** NIFTY was 22,722 on 14 Oct; the straddle is then about Rs 46k a lot.
   The conclusion is the same, but say "illustrative".

## What is right and worth keeping

Throughout, the design separates what is decided, what is a proposal and what is reasoning. Its limits file is candid.
It also keeps every frozen protocol untouched by making v4 a new version.

## Verdict: FAIL for d48bdfc

Three must-fixes, all in the text, no code:
1. redo the power arithmetic at Holm's level;
2. a third "undecided" answer for the stop rule;
3. the `frozen_files` extension put to the owner.

After a PASS on the fixed SHA, ChatGPT reviews via response 95, and the owner approves.

## Addendum 1 (15 Oct 2026): revision 1, tip 13e256061bd8d73106c56623e5548d53d8b1d52b

7789288 carries the content. 13e2560 only rewraps lines: a word-level diff of 7789288 against 13e2560 shows no changed
word. Only `docs/design_v2/` and response 95 change.

| Item | Result | Evidence |
|---|---|---|
| Must-fix 1: power at Holm's level | MET | Section 5.5 now plans at α/m (0.05/15 = 0.0033, z 2.71) and 80% power: n = (3.55 r)². I recomputed every cell of the new horizon table: r 3 → 114 (5.5 months, 2.3 years, 9.5 years); r 5 → 316 (15 months, 6.3 years, 26 years); r 10 → 1,264 (5 years, 25 years, 105 years). "Skill in months" is gone from 01 §1.3 and §1.7, `OWNER_SUMMARY.md` and response 95. They now say "no question is known to settle in months; r is measured after 60 outcomes". V1's dependence on A16 and on intraday HAR is stated. |
| Must-fix 2: stop rule | MET | Tests A and B each have yes, no and undecided. "No" for Test A needs a projected settle date on or before the review, or an interval that already rules out the minimum effect. Underpowered never counts as "no". The owner chooses in advance among three options for "undecided": (1) continue to the projected date, at most 2 years, with AI cut to the forecasters at half budget, after which undecided counts as no; (2) code only; (3) stop. The text gives a recommendation, and states plainly that "undecided" is the most likely result on 31 May 2027. |
| Must-fix 3: `frozen_files` | MET | The note adding G8 and E8 is dropped. G8 is left to v4's own freeze, which is correct: it is G-protocol code. Adding E8 is now owner decision 12, with its reason and its cost in delay. |
| Should-fixes | MET | REPLAN §1 statuses now come from the judge record; I checked every cited merge commit and each is an ancestor of `main` (e3506ec, f314254, c12137e, b4f1e1b, 374ad67, 58f5781). Decisions are cited by date and title. Slice A dates are marked "targets, not commitments", with the ChatGPT, host and C5 dependencies named. SEBI loss figures are cited by study and year and labelled as secondary summaries, matching `reports/Retail FnO losses and safeguards.md`. |
| Size | MET | The longest file is now `REPLAN.md` at 168 lines; every file is under 350. |

**Two corrections to my own judge 96.**
1. **The NIFTY level.** The orchestrator is right that my "22,722 on 14 Oct" was wrong: 22,721.95 is the 13 Oct close.
   14 Oct closed at 22,622.70 (`warmup_closes.csv`; index-close manifest). The design now uses about 22,620. I
   recomputed the straddle: 0.8 × 22,620 × 0.138 × √(30/365) = Rs 716 a unit, about Rs 46,500 a lot; the 5-day straddle
   is about Rs 19,000 a lot. Both are correct.
2. **The SEBI figures.** My should-fix doubted any FY26 figure. The repository's own report cites an August 2026 SEBI
   study (87.7% of individuals lost in FY26), through secondary sources. The revision labels it that way, which is right.

**Verdict: PASS for 13e256061bd8d73106c56623e5548d53d8b1d52b.** Next, ChatGPT reviews it via response 95 and the
owner approves. Nothing merges before that.

## Addendum 2 (15 Oct 2026): revision 2, tip af604ed056d0308ab1478a1d2a504808476323ab (answer to ChatGPT review 95)

One commit after 65d07af, which is ChatGPT's review 95. It changes `docs/design_v2/`, response 96 and the README. The
largest file is response 96 at 204 lines.

| Claim | Result | Evidence |
|---|---|---|
| (a) G1 v3 uses a two-sided, null-centred test; v4 states the one-sided form; HAC is a sensitivity only | MET | `fno/forecast_scoring/block_bootstrap.compare` counts `abs(means - observed) >= abs(observed)`: two-sided and null-centred, as stated. v4's p = (1 + #{D*−D ≤ D})/(B+1) is the matching one-sided form; negative D favours the forecaster, so the direction is right. The block scheme (ceil(n/L) starts from 0..n−L, cut to n) and "fewer than 2L pairs: not tested" are well defined. The Newey-West HAC t-test, at lag L−1, is predeclared as a sensitivity check and never used to choose. v3 is untouched. |
| (b) 2 exact zero-return days; the QLIKE floor binds on 132 of 2,174 days | MET (reproduced) | From `warmup_closes.csv`: 2,425 closes give 2,424 log returns. The zero returns fall on 2017-03-31 and 2024-05-08. With a floor of 1% of the trailing-250 median of squared returns, 2,174 days are evaluable and the floor binds on 132 (6.1%). The smallest 5-day sum is 4.55e−6, never zero. |
| (c) Base rates and weather floors | MET (reproduced) | A 2% day: 4.13% of sessions; 16.7% in 2020, 0.0% in 2017, 0.4% in 2023. At least one in the next 5 sessions: 13.7%. 2.5× gives about 10.3% and 34%, consistent with the RED floors of 10% and 35%. The 15% maximum RED frequency is frozen with the thresholds, and breaching it means a new version, never an in-place retune. |
| (d) Primary baselines declared now; V5 relabelled; P&L target rejected | MET | The table declares premium-adjusted implied as primary for V2 and V3, with the reason: raw implied is biased upward, and choosing on 2019-26 outcomes would expose the targets. V5 is now a terminal intrinsic proxy against an option-implied probability scored by Brier, labelled "risk-neutral" and "not evidence of money". V4 is marked diagnostic, and the text notes that P(RV<IV) is not the variance premium. The one rejection gives a reason, and the decision is ChatGPT's to contest. |
| (e) Stop rule | MET | There is a decision unit: v4's registered primary comparisons only, and Test B counts only registered shadows. "No" needs futility: the one-sided 95% upper bound of improvement is below the minimum effect, so failing to reject zero is never enough. Both tests must say "no" to stop. The owner's "undecided" choice is recorded in `DESK_DECISIONS.md` before the first v4 score. |
| (f) E8 | MET | It is still owner decision 12, with two options, (a) frozen_files or (b) a separate freeze record, and it is not decided in the text. |
| (g) Slice A reduced | MET | Slice A is now a sequence, not a calendar. C5, E8, T2 and G7 phase 2 move to slice B. LM1 starts only when the first position is open. R2 and LR1 stay, with stated reasons. |
| (h) 04 §4.4 contracts | MET | Issuance time comes from Slack's server time, with GitHub's push receipt as a second witness; committer time is never evidence. A Groww terms gate comes before A16, with raw quotes private in Drive. A UTC clock contract with a 5-second skew warning. Owner-unavailable handling. |
| Decided items untouched | MET | REPLAN §4 still changes only open S1 items. The five decided items are listed as not reopened, and E8 is left to the owner. No owner decision is restated differently. |

Should-fix (for G6's freeze record, not this design):
1. **Disclose what was seen.** Revision 2 measured V6-type outcomes on 2017-2026 NIFTY closes (base rates, floors) to
   set the weather floors and the QLIKE floor before v4's freeze. That is acceptable, because only forecasts after the
   freeze count. But G6's freeze record must disclose this exposure, as experiment 1's did. The same applies to any
   G7/G8 back-fill run before the freeze.
2. **Define the session set.** The 2,424 returns include muhurat and special sessions (`session` column), where a
   one-hour session's return is not a normal day's. G6 should define which sessions count, for outcomes and base rates
   alike.

**Verdict: PASS for af604ed056d0308ab1478a1d2a504808476323ab.** It returns to ChatGPT for the PARTIALs, then goes to
the owner.

## Addendum 3 (15 Oct 2026): d80652c0d55d21e6054eb83b119d05773d64905f

- **What changed.** Two commits after af604ed: d373139, which is ChatGPT's review 96 (its own file), and d80652c (4
  files, +15 −6, documents only).
- **The baseline wording is corrected.** Premium-adjusted implied is now "the predeclared physical-variance
  benchmark". The text no longer says "superiority is assumed", and both versions are scored. That is more accurate
  than revision 2's "weaker by construction": the trailing ratio adds its own estimation noise.
- **G6 gains two acceptance criteria.**
  - V5's outcome uses the correct expiry's final settlement or reference level, with its source and timestamp frozen,
    never a later daily close.
  - The freeze record discloses the 2017-26 base rates measured before the freeze, on regular sessions only.
  - Together these cover both should-fixes of my addendum 2: the exposure disclosure, and the session set for base
    rates.
- **A slice A fallback is added.** If A16 is delayed, V6, the NO TRADE card and the budget ship. V1 stays pending and
  shows "not enough data yet", never a failure. This is sound and removes the host and terms from the critical path.
- **Nothing else changed.** No owner decision or decided S1 item is touched.

**Verdict: PASS for d80652c0d55d21e6054eb83b119d05773d64905f.** It now waits only on the owner's approval and
decisions.

## Addendum 4 (15 Oct 2026): the owner's decisions written in, d80652c..7b449547628c920155c617ef4a02ab18d19b87d8

Three commits (e338844, 0f351fc, 7b44954) change 9 files, all under `docs/design_v2/`. I checked each against the 15
Oct rows of `docs/DESK_DECISIONS.md` on `main` (rows 104-115).

| Decision | Row | Design text | Result |
|---|---|---|---|
| 1 Host: Claude routine | 104 ("1 - A") | 6.6 decided (a); Azure only if Groww offers a data-only key; the cost and research-preview status are stated | MET |
| 2 Caps | 105 | 6.2 values accepted: bucket Rs 30,000; open maximum losses at most Rs 1.5 lakh (a cap, not a stop); Rs 50,000 new risk a day; brake Rs 1.2 lakh | MET |
| 3 Weather thresholds | 108 | 2.3 as proposed, with the floors and the 15% maximum RED frequency | MET |
| 4 Minimum effects | 109 | 5.5: 3% QLIKE or Brier skill 0.02, also used as the futility margin | MET |
| 5 Reaction time 5/30/60 | 107 | 3.2: R = 60 primary, R = 30 and R = 5 as sensitivities; the next-session consequence is stated plainly | MET, with should-fix 1 |
| 6 AI budget | 110 | 8.1 as proposed | MET |
| 7 "Undecided" action | 112 | 8.2: option 1 if the projected date is within 2 years, otherwise option 2 | MET |
| 8 Real-money gate | 113 | 8.3 and 8.4 accepted; the exact account size and cap must be confirmed in writing before RM1 freezes (now in RM1's acceptance criteria) | MET |
| 9 Cards in Drive only | 111 | 8.5, 4.1 and T1: Drive only; the public repository holds only hashes and scores | MET |
| 10 Books 2-3 | 114 | Slice E decided | MET |
| 11 S1 changes and the t-check | 115 | REPLAN §4: all accepted; the t-based bound is added | MET |
| 12 E8 in `frozen_files` | 106 | REPLAN §5 and the E8 story | MET |

**Content beyond the decisions (should-fix 2).** These are new rules, sound and honest, but they are design additions,
not owner decisions:
- an E8 fill happens only inside the card's entry range, otherwise the trade is recorded as "missed, price moved";
- an idea or exit rule that needs a reaction of 15 minutes or less is flagged at G0 and judged only at R = 60;
- the remedy if R = 60 costs too much is an earlier decision time, never a shorter assumed R;
- the next-session fill time moves from 09:30 + R to 09:15 + R.

The "missed" rule is material: with a 15:08 card and R = 60, every entry fills the next morning after the overnight
gap, so many entries may be missed. The owner should see it in `OWNER_SUMMARY.md` before approving the whole design.

Should-fix:
1. **Attribution of R = 60.** Row 107 records the owner's 5/30/60 minutes. "R = 60 as the primary fill" is
   attributed there to the orchestrator's proposal, reasoning only. In 4.2, in the E8 story and in REPLAN §5 item 5 the
   design says "owner decision of 15 Oct" for R = 60 primary. Write "the owner's 5/30/60 minutes (decided); R = 60 as
   primary (proposal, reasoning only)", unless the owner confirms it.
2. **Show the additions to the owner.** Name the four additions above in `OWNER_SUMMARY.md` as design choices for the
   owner's approval of the whole design.

**Verdict: PASS for 7b449547628c920155c617ef4a02ab18d19b87d8.** All twelve decisions are written as recorded and no
decided item is changed beyond decision 12. The two should-fixes are wording, to be done before or with the owner's
approval of the whole design.

## Addendum 5 (15 Oct 2026): 2b0da01cefede91f253f165dd01a6b6f9a79d248 (two documentation commits after 7b44954)

- **Both addendum 4 should-fixes are done (0181d5b).**
  - `OWNER_SUMMARY.md` now names the four fill rules in plain words, including "many may be missed": entry range or
    "missed, price moved"; fast-reaction ideas judged at 60 minutes; the next session at 09:15 plus R; an earlier
    decision time as the remedy.
  - It also states the practical consequence: with a 15:08 card and R = 60, every new paper trade fills the next
    morning after the overnight gap.
- **The owner has now decided R = 60.** The owner's words are in `DESK_DECISIONS.md` on `main` (6f012cc, "Reaction
  time => yes, I agree"): every E8 trade fills at 5, 30 and 60 minutes, all three are reported, and the verdict uses 60
  minutes.
- **The text matches that decision in all 5 places (2b0da01):** 03 §3.2, 04 §4.2, `OWNER_SUMMARY.md`, REPLAN §5 item
  5, and the E8 story.
- **Note on the decision log.** 6f012cc also edited the earlier 15 Oct reaction-time row in place, dropping its "R = 60
  primary (orchestrator's proposal)" wording, rather than only appending the new row. The meaning stays correct,
  because the new row supersedes it. But the decision log should stay append-only: next time, add a correction row as
  was done for A8.

**Verdict: PASS for 2b0da01cefede91f253f165dd01a6b6f9a79d248.** It waits only on the owner's "design approved".

## Addendum 6 (15 Oct 2026): revision 3 at 01575a155b44f10b3f397f126986f9ca092ae78c (2b0da01..01575a1)

Scope: all 16 changed files read in full diff (`git diff -w 2b0da01 01575a1`), the 15 Oct owner rows of
`DESK_DECISIONS.md`, and the regular-session closes in `research/data/nifty-panel/warmup_closes.csv`.

| Claim | Status | Evidence |
|---|---|---|
| B1 timing contract | MET | 04 §4.1: data cutoff 15:00, decision final 15:06, card sent 15:08; an advocate timeout gives `advocate_unavailable`, never a delay; matches 07 §7.3 |
| B2 zero shadows give `undecided / no_economic_test` | MET in substance, PARTLY in process | Statistically right (no observations, no bound). But it changes the outcome of owner decision 7 and the text states it as decided; see must-fix 1 |
| B3 primary loss `ln f + RV/f`, no floor | MET | Algebra checked: textbook QLIKE = (ln f + RV/f) - ln RV - 1, so paired differences are equal whenever RV > 0, and the ranking loss is defined at RV = 0. Regular sessions re-counted: 2,409 returns, the old floor would bind 133/2,159; zero-return days 31 Mar 2017 and 8 May 2024 |
| B4 `exploratory_shadow` | MET | Counts only if frozen before collection; promotion and paper eligibility need rung 1 and the economic test (R3, REPLAN slice B). No path found that lets a result shape its own registration |
| 33 ACCEPT, 2 PARTIAL | MET | The remaining edits (6.1a four kinds of loss, monitor-silent rule, 09 limits relabelled, SEBI figures down to "some evidence", A16 operational gates, G6 test list, A11 cue timing in 02) match what response 97 says |
| Owner flag 1, decision 4 ("3%") | MET | Redefined on the ranking loss; equivalent to "3% lower mean textbook QLIKE" on RV > 0 days and flagged. Nuance: on RV = 0 days the textbook form is undefined, so the day set behind the 3% must be frozen in G6 (follow-up) |
| Owner flag 2, decision 8 tightening | MET | 08 says "Proposed tightening, awaiting the owner ... decision 8 is not changed" |
| Owner flag 3, decision 7 zero shadows | NOT MET | See must-fix 1 |

**Must-fix 1: the decision-7 change is written as decided.** Decision 7 (owner, 15 Oct) is "stop or pivot only when
both tests say no". Under revision 2, which the owner read, no shadow reaching rung 2 made Test B "no"; revision 3 makes
it "undecided", so a review with A "no" and no shadows now goes to the continue / code-only options instead of stop or
pivot. That is a change to what decision 7 does. Yet:
- 08 §8.2's heading still reads "decided by the owner on 15 Oct 2026", and the body states the new rule flatly ("Zero
  eligible shadows gives `undecided / no_economic_test`, never 'no'"), with only "correction flagged" in the heading;
- response 97's summary (line 18) says "two accepted changes touch owner decisions 4 and 8", leaving decision 7 out,
  although its own B2 section (line 43) flags it.
The orchestrator's request was that the text decides none of the three. For decision 8 it does not; for decision 7 it
does. Fix: write it like decision 8 ("Proposed correction, awaiting the owner: ... decision 7 is not changed until the
owner says so"), and make response 97's summary name decisions 4, 7 and 8. I expect the owner to accept it: it is
statistically correct, and my addendum-2 PASS missed that revision 2 contradicted its own "underpowered is never no".
That miss is mine.

**Follow-up (not blocking):**
1. G6 freezes the day set for the 3% QLIKE effect (RV > 0 days, or all days on the ranking loss) so numerator and
   denominator use the same days.
2. Process: ChatGPT's 6392951 replaced `reviews/chatgpt/review_95_design-v2.md` instead of appending (the old text is at
   d373139). Review files should be append-only, like the decision log.

Project rules: every file under 350 lines (largest design file 192, response 97 115); no code, tests or frozen files
touched; no secrets, emails or model names found in the diff.

**Verdict: FAIL for 01575a155b44f10b3f397f126986f9ca092ae78c**, on must-fix 1 only (wording, two places). Everything
else in revision 3 passes; a re-check needs only 08 §8.2 and response 97's summary.

## Addendum 7 (15 Oct 2026): a0ac7522ae56f18657af3c9c49694a9e342c1226 (01575a1..a0ac752)

The orchestrator replaced the target SHA. a0ac752 changes only `03` §3.1 and §3.4 point 4 and response 97 (checked:
`git diff --stat 01575a1 a0ac752`, two files, docs only).

| Item | Status | Evidence |
|---|---|---|
| Addendum 6 must-fix 1 (decision 7 written as decided) | NOT MET | `08` is unchanged between 01575a1 and a0ac752; response 97 line 18 still names only decisions 4 and 8 |
| B4 snooping path "best of many shadows" | PARTLY | See must-fix 2 |
| B4 snooping path "tune after looking" | MET | Any change after looking is a new idea and a new row, and records count only from a freeze made before collection; the frozen sample also closes "judge when the numbers look best" |
| Benchmark PARTIAL (per rupee tied as headline, whole account with idle cash at the cash rate) | MET | Consistent with the owner's rows of 14 Oct ("more strategies in parallel, not bigger bets"; Rs 20 lakh "many strategies in parallel"); the whole-account view is still reported, and crediting idle cash at the cash rate is fairer than zero |
| Tally 32 / 3 / 0 | MET | Matches the per-file table |

**Must-fix 2: the Holm family counts only shadows that are still running.** The new text says every
`exploratory_shadow` "running when an idea is judged" belongs to that idea's family. Adversarial path: register 20
shadows on one question, stop the 19 that look poor (stopping a shadow is not forbidden anywhere), then judge the survivor
in a family of 1. That is exactly the "watch many, pick the best" path the paragraph claims to close. The factory-wide
"trial k of K" line is only reported; the pass decision uses the Holm family. Fix: the family is every shadow registered
on that question (or batch) since its last judgement, whether running, stopped or retired; and stopping a shadow before
its frozen sample is recorded with its reason and keeps it in the family. With that wording the builder's argument holds:
the rules are mechanical and the forward data is unseen at freeze time, so I agree that exploratory shadows may feed
promotion.

**Follow-up (not blocking):** "per rupee of capital tied up" needs one frozen definition before S2 or the scoreboard uses
it: return per rupee-day of funds at entry, with the index fund measured over the same rupee-days (or the untied days
credited at the cash rate). Otherwise a strategy tied up for a few days is compared with an index held all year.

**Verdict: FAIL for a0ac7522ae56f18657af3c9c49694a9e342c1226**, on must-fix 1 (still open from addendum 6) and must-fix
2 (family membership). Both are wording fixes; a re-check needs only `08` §8.2, response 97's summary and `03` §3.1.

## Addendum 8 (15 Oct 2026): dd4e1a83df290784243f0c45518eb369bb1123c0 (a0ac752..dd4e1a8)

dd4e1a8 changes `05`, `08`, `REPLAN_new_stories.md` and response 97 (docs only, checked by `git diff --stat`).

| Item | Status | Evidence |
|---|---|---|
| Addendum 6 must-fix 1 (decision 7) | MET | `08` §8.2 keeps decision 7's Test B word for word (compared with 2b0da01 lines 49-51) and adds the zero-shadow rule under "Proposed correction, awaiting the owner; decision 7 is not changed until the owner says so", with its effect stated; the heading says "one proposed correction awaits the owner"; response 97's summary names decisions 4, 7 and 8 |
| Addendum 6 follow-up 1 (3% day set) | MET | `05` item 5 and G6's acceptance: scored, non-void days with RV > 0, the same days as the paired comparison, fixed before any score |
| Addendum 7 must-fix 2 (Holm family) | NOT MET | `03` §3.1 at dd4e1a8 still reads "Every `exploratory_shadow` running when an idea is judged belongs to that idea's family"; response 97 repeats "every shadow running when an idea is judged" |

Must-fix 2 stands as written in addendum 7: stopping weak shadows before judgement shrinks the family to the survivor.
The family must be every shadow registered on that question or batch since its last judgement, running, stopped or
retired, and an early stop is recorded with its reason. The orchestrator's request (sent 21:27 UTC) predates my
addendum 7 message, which explains the gap.

**Verdict: FAIL for dd4e1a83df290784243f0c45518eb369bb1123c0**, on addendum 7's must-fix 2 only. A re-check needs only
`03` §3.1 and response 97's B4 paragraph.

## Addendum 9 (15 Oct 2026): 6367d7354e910b203851f2652a1adca958f5fb3e (dd4e1a8..6367d73; whole range 2b0da01..6367d73)

6367d73 changes `03` §3.1 and §3.2 item 4, REPLAN's S2 row and response 97. The whole range 2b0da01..6367d73 touches
only `docs/design_v2/` and `reviews/` (checked: no other path in `git diff --name-only`); the chain is linear
(6367d73's parent is dd4e1a8, and 01575a1 is an ancestor).

| Item | Status | Evidence |
|---|---|---|
| Addendum 6 must-fix 1 (decision 7) | MET | Addendum 8; unchanged since |
| Addendum 7 must-fix 2 (Holm family) | MET | `03` §3.1: the family is every shadow registered on the question or batch since its last judgement, running, stopped or retired; an early stop is recorded with its reason and stays in the family; the attack is named. Response 97's B4 paragraph says the same |
| Addendum 7 follow-up (per rupee tied) | MET | `03` §3.2 item 4 and REPLAN's S2 row: one definition frozen before use, return per rupee-day of funds at entry, the index over the same rupee-days |
| Project rules | MET | Largest changed file 193 lines; docs only; no secrets, emails or model names in the diff |

**Follow-up (not blocking; for R1 and G6 to freeze):** "since its last judgement" leaves staggered judgements open.
Shadows on one question reach their frozen samples at different times; when the first is judged, the family resets, so a
shadow registered earlier but judged later could be judged in a smaller family than the one it was registered into.
Freeze one rule before the first judgement: either the family is every shadow registered on the question (cumulative,
judged ones included, with Holm's step taken at each judgement), or a batch is judged only together. The factory-wide
"trial k of K" line already shows the whole count, so this is a precision point, not an open snooping path.

**Verdict: PASS for 6367d7354e910b203851f2652a1adca958f5fb3e.** All must-fixes of addenda 6 and 7 are done. Design v2
revision 3 still needs ChatGPT's approval of the whole revision and the owner's approval before it binds or merges
(owner's order, 15 Oct log); after the merge I check that `main` carries exactly this SHA's `docs/design_v2/`.

## Addendum 10 (15 Oct 2026): revision 4 at 658ab3a58402aa34a919e6910aacbdffb8aa3ddd (6367d73..658ab3a)

Range: ChatGPT's review 97 (1d4d9f5, 9585391) and 658ab3a; docs and reviews only (checked with `git diff --name-only`);
largest changed file 195 lines. Owner amendments read at their source: 9003162 appends two rows to `DESK_DECISIONS.md`
(nothing edited in place) and logs the owner's words in `conversations/2026-10-15.md` ("A. Your decision 7 ... => I
accept / B. Your decision 8 ... => I accept").

| Item | Status | Evidence |
|---|---|---|
| Decision 7 amended, one operative Test B | MET | `08` §8.2 has one Test B: "no" only when every counted strategy reached its sample with its upper bound below its useful net; zero eligible or resolved shadows gives `undecided / no_economic_test`; the old wording is gone; matches the amendment row |
| Decision 8 amended | MET | `08` §8.3 condition 5 always applies (second untouched forward period or Holm across the trial count, sample predeclared); §8.4's pass is a paired real-minus-paper test with a prediction interval for the mean of that many new trades; Rs 20,000 stop kept. Matches the amendment row. Note: condition 6 (fits the Rs 4,000-5,000 real cap; SEBI and tax rules re-checked) is not in the amendment row's words; it was in the proposal the owner accepted as "a stricter bar", so I accept it, and the owner sees it at final approval |
| Review 97 fix 2: minimum-effect population | MET | `05` §5.5 item 5: the gate uses only paired dates with RV > 0, the 3% benchmark on the same dates; the primary test uses every scored non-void date; the zero-RV count is reported; G6 freezes both sets. Numerator and denominator now share one population |
| Review 97 fix 3 and my addendum 9 follow-up: shadow family | MET | `03` §3.1: cumulative per research question (active, stopped, retired, judged or new), Holm recomputed at each confirmatory decision without relabelling earlier verdicts, one judgement at the frozen sample unless alpha-spending was registered before collection. Adversarial check: no reset point remains, early stops stay in, and interim peeking needs a pre-registered spending rule |
| PAPER ONLY card label | MET | `04` card table, first row |
| Decision 4's unit stated as unconfirmed | NOT MET | See must-fix 1 |

**Must-fix 1: the design text does not say that decision 4's exact unit is unconfirmed.** Response 97 says it plainly
("still a definitional clarification for the owner to confirm"). The design does not:
- `05` §5.5 item 5 says only "flagged to the owner in response 97", next to "accepted by the owner on 15 Oct 2026";
- REPLAN §5 item 4 says "Decided 15 Oct 2026: minimum effects 3% QLIKE";
- `OWNER_SUMMARY.md` lists "what 'better than baseline' means" among the decisions made, with no word on the unit.
Revision 4 also adds new definitional content (the gate excludes zero-RV dates while the significance test keeps
them), which is exactly the part the owner has not seen. Without this, the owner's approval of the whole design would
not knowingly cover it. Fix: in `05` item 5, "the number 3% is the owner's; its exact unit (this paragraph) awaits the
owner's confirmation"; the same short note in REPLAN §5 item 4; and one line in `OWNER_SUMMARY.md` asking the owner to
confirm it. Self-check: in addenda 6 and 9 I accepted "flagged" as enough. With the population split added in revision 4
and the owner's whole-design approval coming next, it is no longer enough. That is a stricter reading than mine before,
and I say so.

**Verdict: FAIL for 658ab3a58402aa34a919e6910aacbdffb8aa3ddd**, on must-fix 1 only (wording in three places). Everything
else in revision 4 passes, including both owner amendments and ChatGPT's fixes 2 and 3.

## Addendum 11 (15 Oct 2026): 956a805679a9ce115bd92e28491a2d7260ed5e2e (658ab3a..956a805)

956a805 (parent 658ab3a) changes `05`, `OWNER_SUMMARY.md`, `REPLAN.md` and response 97; docs only.

| Item | Status | Evidence |
|---|---|---|
| Addendum 10 must-fix 1 (decision 4's unit) | MET | Owner row appended in a1ed514 (merged on main in 01f6b82): "Decision 4's exact unit confirmed" (owner: "3% confirmed"), stating the RV > 0 paired-date gate, zero-RV dates reported, all dates in the significance test; the log quotes the owner. `05` item 5, REPLAN §5 item 4 and `OWNER_SUMMARY.md` now say "exact unit confirmed by the owner, 15 Oct 2026", and the summary states it in plain words; response 97's "to confirm" lines are updated |
| Nothing else changed | MET | `git diff 658ab3a 956a805`: only those four files and those lines |

**Follow-up (process, not blocking):** the owner's words "3% confirmed" alone do not show whether the owner confirmed
the number or the unit; the log records the orchestrator's reading, not the question the owner answered. Log the
question with the answer next time. The backstop here: `OWNER_SUMMARY.md` now states the unit in plain words, so the
owner's final approval of the whole design covers it knowingly.

**Verdict: PASS for 956a805679a9ce115bd92e28491a2d7260ed5e2e.** Design v2 revision 4 passes with all must-fixes of addenda
6, 7 and 10 done. It waits on ChatGPT's confirmation and the owner's final approval; after the merge I check that
`main`'s `docs/design_v2/` equals this SHA's.

## Addendum 12 (15 Oct 2026): merge check, design v2 merged to main as 414e602

- **Merge is exact.** 414e602's parents are a0c67f2 (main) and ed41414 (the branch). Recomputing the merge with
  `git merge-tree --write-tree a0c67f2 ed41414` gives a tree identical to 414e602's (empty diff).
- **Merged design equals the passed SHA.** `git diff 956a805 414e602 -- docs/design_v2` is empty. ed41414 adds to
  956a805 only ChatGPT's review 98 (`reviews/chatgpt/review_98_design-v2-revision-4.md` and its README row); review 98's
  verdict is APPROVE.
- **Owner approval recorded.** 6eec57d appends the row "Design v2 approved" (owner: "design approved") to
  `DESK_DECISIONS.md`, and the log records the question asked (read OWNER_SUMMARY and reply "design approved" or say what
  to change). That meets addendum 11's follow-up on logging the question.
- **No unjudged code.** Between a0c67f2 and 6eec57d nothing changed outside `docs/design_v2/`, `reviews/`,
  `conversations/` and `DESK_DECISIONS.md`. 1370fd0, after the merge, is a scheduled data commit (announcements
  manifest, lane 3).
- **CI.** checks.yml was green on a0c67f2, whose code tree is unchanged by the merge. The run on 6eec57d (which includes
  414e602) was in progress at writing; its result is in the README row and my report.

**Verdict: merge check PASS.** Design v2 is binding from 414e602, and future work follows `docs/design_v2/REPLAN.md`,
starting with slice A.
