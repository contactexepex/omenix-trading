# Judge 98: G6 forecast protocol v4 (draft, not frozen): `story/g6-protocol-v4` 51334da (lane 1, response 99)

**What I did:**
- read `PROTOCOL_v4.md`, every module of `fno/forecast_v4/`, the G6 story entry and response 99;
- checked them against design v2 sections 5 and 8.2, the owner's 15 Oct decisions and the A7 calendar;
- re-derived the V4 golden example by hand;
- recomputed the disclosed base rates and the special-session list from the committed files;
- rebuilt one bootstrap p-value with my own plain loop;
- planted 13 mutations of my own;
- ran the full gates on a trial merge with `main`.

The holdout was respected: I opened no 2019-2023 row of `golden_iv30_rv20.csv` or the back-fill. I read only
`warmup_closes.csv`, the A7 calendar and panel file names.

## Gates

On a trial merge of 51334da with `origin/main` (8d96afa, full history, Slack token unset): **3282 passed**. `ruff
check`, `ruff format --check` (723 files) and `check_imports` are clean. The largest new file is 155 lines and the
protocol is 286.

## Independent checks

| Check | Result |
|---|---|
| QLIKE ranking loss | `ln f + RV/f` = textbook + `ln RV + 1`, so paired differences are equal when RV > 0. It is defined at RV = 0, and RV is never floored (`loss.py`). The gate denominator is the baseline's **textbook** QLIKE (`pairs.py` passes `textbook_qlike` as the baseline loss), which is always >= 0. If the ranking loss were used there, the sign of the 3% could flip; my mutation of exactly that was caught |
| Two date sets | Scored set: resolved, not void, both values present, zeros kept. Gate set: the same dates with RV > 0, with the excluded count reported. This matches the owner's confirmed unit (DESK_DECISIONS, 15 Oct) |
| Bootstrap p | My own loop, using the same SeedSequence([20261015, 4]), ceil(n/L) starts from 0..n-L and a cut to n, gives p = 0.0046995 on 137 synthetic differences with L = 10. `one_sided_test` gives the same value to every digit. The direction is right: the null-centred values `D* - D` are compared with a negative D |
| Futility bound | Percentile bound of the ratio of means, with pairs kept together and the 9,500th of 10,000. "Every member futile" as an intersection-union test at 5% each is valid (Berger 1982) |
| V4 golden | 0.00037 x 252/5 gives 13.656%. 0.138^2 x 7/365 / (5/252) gives 13.567%, so "no". With 9 days, 15.384%, so "yes". Both reproduced by hand |
| Base rates | From `warmup_closes.csv`, regular sessions only: 2,410 sessions and 2,409 returns. 100 returns have abs >= 2% (4.15%); 331 of 2,405 five-return windows contain one (13.76%). Zero returns on 31 Mar 2017 and 8 May 2024. All match section 8 |
| Special sessions | The calendar has 6 `special` sessions in 2017-26: 1 Feb 2020, 20 Jan 2024, 2 Mar 2024, 18 May 2024, 1 Feb 2025 and 1 Feb 2026, plus 9 muhurat sessions. This matches section 2's "6, of which 2 short DR sessions and 4 with normal timings" |
| V5 | Outcome only from `NseFinalSettlement` of the frozen expiry, from that expiry day's file. The source path, SHA-256 and first-seen time are kept, and a level first seen before 15:30 IST on the expiry is refused. "Inside" is strict |
| Stop rule | Matches design 8.2 as amended. Zero shadows gives `no_economic_test`. A with nothing counted is undecided. A "no" needs every counted member futile |
| Mutations | 13 planted; 12 caught (sign of the p count, the uncentred p, the gate denominator, the Holm step, p = 1, the V5 boundary, the session set, the look rates, the percentile rank, zero shadows, the block range, the one-way switch). **One survived:** dropping near-zero positive RV (<= 1e-12) from the gate set. See follow-up 1 |

## The questions asked

- **Two looks at 0.02 and 0.03.** This is a proper split.
  - By the union bound, P(any false claim) <= 0.02 + 0.03 = 0.05 however the looks correlate, given Holm controls each
    look at its rate. Holm with unjudged members at p = 1 is still valid: they only enlarge m.
  - It is a pre-registered alpha-spending rule (Bonferroni over looks), which is what design 03 §3.1 requires for
    anything judged more than once. That paragraph is written for factory shadows, but the principle is the same.
  - It is needed: design 8.2 already has two looks (the review, and the re-run on the projected date), and running 5%
    at each would allow up to about 10%.
  - But it changes how owner decision 7 operates. See must-fix 2.
- **Fixed 15-member family with p = 1 for unjudged members.** Correct and conservative. Leaving V3, V5 and V4 out is
  reasoned (about 12 independent outcomes a year) and stated. It keeps the design's "m of about 15".
- **V2 and V3 on the close proxy.** Agreed. The target is defined on the proxy itself, and QLIKE ranks correctly
  under a conditionally unbiased proxy (Patton 2011). It costs power, not validity.
- **Strict "inside" for V5.** Immaterial in practice and conservative. Agreed.
- **Special sessions excluded.** It matches the A7 calendar and judge 96 addendum 2's "one set". Excluding them is
  right for v4. G1 v1-v3 stay as frozen.
- **"No power report means option 2".** This is a reasonable default, but it interprets owner decision 7. See must-fix 2.

## Must-fix

**1. The premium-adjusted baseline's history is not specified, and that decides whether V2 can be judged at the
review.**
- What the protocol says: V2's (and V3's) primary baseline needs the median of `RV_h / raw implied_h` over 750 resolved
  sessions (at least 500), with raw implied built from "IV30 from the 15:00 pack".
- Why that is a problem: live 15:00 IV30 exists only from 13 Oct 2026. On that source alone, the primary is not
  eligible until about late 2028. Every V2 pair is then missing, and V2's three members cannot be judged at the
  review of about 31 May 2027, which design 8.2 lists as judgeable.
- The alternative is not settled either. Using the panel's end-of-day IV30 as history is a different estimator. A
  750-session window from late 2026 also reaches into 2023, near the forecast holdout years, and the protocol says
  nothing about either.
- Fix: name the history source.
  - If it is a labelled point-in-time proxy, for example the panel's end-of-day IV30, say why it is acceptable and keep
    the window inside 2024 onwards. 2024 to Oct 2026 is about 690 sessions, so the 500 minimum holds without touching
    2019-2023.
  - If no proxy is used, say plainly that V2 has no primary pairs before about 2028, and put that consequence to the
    owner.

**2. Two choices that change how owner-decided rules work are put to the judge and ChatGPT, not to the owner.**
- **(a)** Test A's "yes" at the review now needs Holm at family-wise **0.02**. Design 5.5, approved by the owner,
  says 5%. At r = 3 that is 134 outcomes instead of 114, so a "yes" at the review is harder to reach.
- **(b)** "No power report, so option 2" decides what owner decision 7's rule (option 1 within 2 years, else
  option 2) does when there is no projected date.
- Both are sound, and I would recommend them. But they belong in an owner flag, as I required for decisions 4, 7 and 8
  in judge 96.
- Fix: in protocol section 11 and response 99, mark (a) and (b) "for the owner's confirmation before the freeze", and
  add them to the freeze's preconditions. No code change is needed.

## Follow-ups (not blocking)

1. **Test gap:** add a test that a near-zero positive RV (for example 1e-300) stays in the gate set. My mutation that
   dropped RV <= 1e-12 from the gate survived.
2. A "next session" return that spans a special session (for example Friday to Monday across a Saturday budget day)
   covers two real sessions. It is disclosed in section 2. The reports should count such dates.
3. The 5% spread limit for weekly ATM legs rests on one session of monthly spreads. G7 must report weekly spreads
   before the freeze, as section 1.4 says. I will check it then.

## Project rules

Lane 1 (rule document, executable rules, constants, tests). Pure functions; no I/O; no orders. Names live in
`constants.py`. Every file is under 350 lines. Nothing is frozen and no ledger row is written, which is correct for a
draft. No secrets, emails or model names.

**Verdict: FAIL for 51334daf6703fd85f3f4c9ccf0b601c5772b022c**, on must-fixes 1 and 2. The statistics are right. The
loss, the date sets, the bootstrap, the futility bound, the family, the look split, V4's units, V5's source, the
session set and the base rates all check out. A re-check needs only protocol sections 3.1, 3.2, 6 and 11 and
response 99. The code stays unless must-fix 1's choice needs an eligibility rule in `eligibility.py`.

## Addendum 1 (15 Oct 2026): 3aa781848c456a6db5151438f1a3b88b7c06bd70 (51334da..3aa7818)

One commit (parent 51334da). It changes the protocol, `eligibility.py`, `constants.py`, two test files and response 99.

| Item | Status | Evidence |
|---|---|---|
| Must-fix 1: the premium-ratio history | MET | Protocol 3.1 names the source: `iv30_eod_close_proxy` is G1 v1's frozen `PanelAtmIv30` on A3's first-archived end-of-day chains, unflagged days only. The window runs from 1 Jan 2024 only (outside the 2019-2023 holdout). It is labelled point in time by content, not by archive time (said plainly), and the 15:00-vs-EOD mismatch is named as noise. `eligibility.premium_ratio_window` keeps t >= 1 Jan 2024 with the outcome resolved before the refit day, the latest 750, and None below 500. My count: **685 regular sessions** from 1 Jan 2024 to 14 Oct 2026 in `warmup_closes.csv`, as the protocol says. (It names "2 Jan 2024" as the first; the first is 1 Jan 2024. The count is right.) |
| Must-fix 2: owner flags | MET | Section 11 lists A (0.02 at the review), B (no power report, so option 2) and C (the EOD proxy, and that without it V2 waits until about late 2028), each "for the owner's confirmation before the freeze". Section 10 makes the owner's written confirmation of A-C a freeze precondition |
| Follow-up 1: near-zero RV in the gate | MET | My earlier surviving mutation (gate drops RV <= 1e-12) now fails a test |

**Checks on 3aa7818:**
- `tests/forecast_v4`: 94 passed. A trial merge with `origin/main` gives **3285 passed**; ruff, format (723 files) and
  `check_imports` are clean.
- **Merge note:** the trial merge conflicts in `reviews/claude/README.md` (both sides added rows). It is resolved by
  keeping both rows. The merger must do the same.
- **New mutations:**
  - Dropping the 2024 start: caught.
  - The 500 minimum written as > 500: caught.
  - Allowing outcomes resolved **on** the refit day (`<=` for `<`): **survived**. The code is right (`<`), but the
    boundary has no test. See follow-up A.

## Follow-ups (not blocking)

- **A.** Add a test that an outcome resolving on the refit day itself is not in that refit's window (point in time).
- **B.** In section 3.1, write "1 Jan 2024" instead of "2 Jan 2024" as the first session.
- **C.** Judge 98's remaining follow-ups stand: count dates whose "next session" spans a special session, and G7's
  weekly spread report before the freeze.

**Verdict: PASS for 3aa781848c456a6db5151438f1a3b88b7c06bd70** (the draft, not frozen). The freeze still needs
ChatGPT's review, G7 and G8's code, the owner's written A-C, and then my check of the freeze record against these
hashes.

**On merging the unfrozen draft:** I have no objection; nothing counts under v4 before its freeze, and the file says
DRAFT. But ChatGPT's review may change it, and any change after this PASS needs a judge re-check. Waiting avoids a
second merge round.

## Addendum 2 (15 Oct 2026): revision 1 at dbba5744ea675b6bc4ba50ec63cf2071ce1b6e34 (3aa7818..dbba574)

Range: ChatGPT's review 99 (89d7419, 5d18cbc) and dbba574, which adds `confirmatory.py`, `student_t.py`,
`diagnostics.py`, the calibration tool and its committed results, two-look futility, and protocol and test changes.

**First, my own miss.** In judge 98 I rebuilt the centred bootstrap's p to every digit and checked its direction, but I
never checked its **size** under a true null. ChatGPT's review 99 did, and the builder's simulation confirms it: the
test rejected 13-32% at a nominal 5% with n = 2L. "The code matches the formula" is not "the test is valid". From now
on, I check the null size of any new confirmatory test myself.

## Gates

Trial merge with `origin/main`: **3308 passed**. As before, the trial merge conflicts in `reviews/claude/README.md`;
keep both rows. Ruff, format (728 files) and `check_imports` are clean. Largest files: the protocol at 320 lines and
the tool at 107.

## What I verified

| Item | Result |
|---|---|
| Simulation code and seeds | Read in full. Every cell is seeded by `SeedSequence([20261015, 99, cell])`, and the null series have mean zero: centred lognormal `exp(Z) - e^0.5`, AR(1) with a 200-step burn-in, moving-sum overlap. I re-ran the cell skew_right, L = 5, n = 125 (cell 19). Its rates match the committed JSON **exactly**, and it took 9 s |
| max(t, studentized) | It is a valid conservative combination: rejecting needs both p <= alpha, so its size is at most the smaller of the two sizes, and it is valid whenever either part is. It cannot repair a case where **both** parts over-reject, which is the right-skew case |
| Futility, 97.5% per look | Correct Bonferroni over two looks for the futility "no". The seed has a look word, there are golden tests for both looks, and a futile verdict at look 1 is final |
| `proxy_drift` | Descriptive only and never feeds the ratio, as review 99 asked |
| Refit-day test, 1 Jan 2024, A-C marked confirmed | Done. My earlier surviving mutation (`<=` refit day) is now covered |

## The question asked: does "p at most a quarter of the Holm step" fix right skew? No, not fully.

The committed calibration cannot answer this: its bootstrap uses B = 2,000, so p cannot fall below 1/2,001 = 0.0005,
and 0.0013/4 = 0.00033 is below that. So I simulated it myself.
- Same centred-lognormal null as the tool.
- **100,000 series per cell**, production **B = 10,000**, the repository's own `batch_means_p` and
  `studentized_bootstrap_p`.
- The bootstrap runs only where the t-test already rejects at the loosest threshold. The max rule needs both, so this
  is exact, not an approximation.

Max-rule rejection rates. "Real step" is Holm's first step at that look: 0.00133 at look 1, 0.002 at look 2.

| L, n | Look 1, at the step | Look 1, quarter rule (0.00033), vs the real step | Look 2, at the step | Look 2, quarter rule (0.0005), vs the real step |
|---|---|---|---|---|
| 5, 125 | 0.00539 (4.0x) | 0.00221 (**1.7x** the real step) | 0.00718 (3.6x) | 0.00297 (**1.5x**) |
| 10, 125 | 0.00512 (3.8x) | 0.00190 (**1.4x**) | 0.00680 (3.4x) | 0.00255 (**1.3x**) |
| 20, 125 | 0.00354 (2.7x) | 0.00102 (0.8x) | 0.00529 (2.6x) | 0.00161 (0.8x) |
| 5, 10 | 0.00298 (2.2x) | 0.00078 (0.6x) | 0.00455 (2.3x) | 0.00118 (0.6x) |

Each rate rests on 102-718 rejections out of 100,000, so the Monte Carlo SE is 0.0001-0.0003.

The quarter rule brings L = 20 and n = 2L inside the real step. It does **not** fix L = 5 or 10 at n = 125 (V1, V6a:
L = 5; V2, V6b, V7: L = 10). Those are 13 of the 15 members, about 125 outcomes is what the stop review will have,
and they stay 1.3-1.7x over the real Holm step. For reference, the batch-means t on its own (200,000+ series) is
4-10x over at n = 125. The bootstrap half is what helps.

## Must-fix

**1. Item D offers a remedy the numbers do not support.** Section 11 D puts "for example p at most a quarter of
Holm's step" to ChatGPT and the owner as the stricter option. As measured above, it still over-rejects for the members
with L = 5 and 10 at about the review's sample size. Fix:
- Item D must state the measured size of every option it offers, with enough simulations to resolve it (the
  conditional method above is cheap: about 40 s a cell at 100,000 series and B = 10,000).
- It must offer at least one option that is measured within tolerance at the real Holm steps for every member's L at
  n = 125. Candidates, all reasoning only until measured: a stricter divisor (1/8 or a per-L calibrated critical
  value); a skew-corrected statistic (Hall's or Johnson's modified t); a minimum number of batches or outcomes before
  a claim.
- It must say how the simulated skew (centred lognormal, sigma 1, skewness about 6) relates to real QLIKE differences.
  Measuring the skewness of a **baseline-vs-baseline** difference on already exposed close-proxy data (2024-26) would
  show whether D matters in practice; that disclosure belongs in the protocol. I have not done this myself, to avoid
  new data analysis on the judge's side.

**2. The calibration overstates its own resolution.** Section 5.3 says the measured size is "within nominal + 2 Monte
Carlo SE" in almost every cell (strong evidence). At 1,000 series and Holm's first step (0.00133), that tolerance is
0.0036, which is **2.7x nominal**. A test 2.5x over size passes it. The same holds at 0.002 and 0.004. Fix: either
re-run the small thresholds with enough series (at least about 50,000 per cell; the conditional method keeps this
cheap) and B = 10,000, or label the claim "some evidence" for thresholds below 0.01 and say why.

## Follow-ups (not blocking)

- The AR(1) L = 5, n = 125 cell (7.6% at 5%) is disclosed. The large re-run of must-fix 2 should include it.
- The calibration's B = 2,000 differs from the scoring B = 10,000. State that the size claims hold for B = 10,000, or
  run them at B = 10,000 (cheap with the conditional method).

**Verdict: FAIL for dbba5744ea675b6bc4ba50ec63cf2071ce1b6e34**, on must-fixes 1 and 2. Both are about measuring and
stating the size honestly; the code changes are sound. Replacing the centred bootstrap was the right call, and the
two-look futility is right. A re-check needs section 5.3, section 11 D, the calibration files and any new test. If the
chosen remedy changes `confirmatory.py`, I re-run my 100,000-series check on it.

## Addendum 3 (15 Oct 2026): revisions 2 and 3 at 8f233f0eb846631c68e54b0a0be6a0488093e754 (dbba574..8f233f0)

Two commits: 9045dc3 (revision 2: size study and claim rule E+D) and 8f233f0 (revision 3: futility study and rule
F+D).

## Gates

Trial merge with `origin/main`: **3603 passed**, the full suite, which the builder had not re-run after the text fix.
Ruff, format (765 files) and `check_imports` are clean. The trial merge now conflicts in **two** index files,
`reviews/chatgpt/README.md` and `reviews/claude/README.md`; keep both sides' rows.

## What I verified

| Item | Result |
|---|---|
| Calibration code | Read in full: `v4_size_study.py`, `v4_claim_thresholds.py`, `v4_futility_study.py`, `confirmatory.calibrated_p` and `futility_p`. The conditional bootstrap in the size study is exact for a max test. The futility direction is right: e = d + margin x b, futile means mean(e) > 0, and `futility_p` takes the batch t of -e |
| Reproduction | I re-ran V6a, n = 125, look 1. The threshold reproduces exactly (0.000145508...) and so does its held-out size (0.00145). It took 35 s |
| Held-out seed separation | The words are distinct: size study 98, claim calibration 55 vs held-out 77, futility calibration 66 vs held-out 99 (plus cell, n and index words). But "held-out" here only means fresh **resamples of the same 685-day series**. It checks Monte Carlo error, **not** whether the thresholds hold on data from another period. The protocol's "strong evidence for the measured null processes" is accurate only in that narrow sense |
| Bonferroni instead of Holm | Valid and slightly conservative: each member is compared with rate / 15, and the union bound holds whatever the dependence. It is consistent with the calibration, which only calibrated the first step. It makes claims harder than the owner's decision A ("Holm at 0.02") when several members claim at once, which the owner's "3 B" row allows ("a rule shown by the null simulation to hold its error rate"). Accepted |
| Honest cost | Section 11 D says plainly that V1 and V2 cannot be claimed in useful time. Agreed, and it is correctly disclosed |

## The question asked: do 2024-26 empirical nulls bias the thresholds? Yes, for the Brier questions, badly.

The empirical nulls use only the regular sessions from 1 Jan 2024. I rebuilt the same nulls with the **builder's own
functions**, changing only the start date to 21 Jan 2019, the first day with at least 500 resolved base-rate outcomes
(the protocol's own minimum).
- These are `warmup_closes.csv` rows. They are exposed and already used for the disclosed 2017-26 base rates, and
  they are not in the golden or back-fill holdout files.
- I then measured the **frozen** thresholds on them: 100,000 series a cell, fresh seeds.

**Claim rule E+D, size against nominal (look 1 = 0.00133, look 2 = 0.00200):**

| Member | n = 125, look 1 / look 2 | n = 250, look 1 / look 2 |
|---|---|---|
| V6a (Brier, L = 5) | **0.392 / 0.427** (about 300x and 210x) | **0.350 / 0.360** |
| V6b and V7 (V6b's thresholds) | **0.0053 / 0.0081** (4x) | **0.0050 / 0.0087** (4x) |
| V1 (QLIKE) | 0.00046 / 0.00079 (within) | 0.00036 / 0.00073 (within) |
| V2 (QLIKE) | 0.00026 / 0.00038 (within) | 0.00012 / 0.00026 (within) |

**Futility rule F+D, false "no" at a true improvement equal to the minimum effect (target 2.5%; 50,000 series):**

| Member | n = 125, as measured / flipped | n = 250, as measured / flipped |
|---|---|---|
| V6a | **57.5%** / 0.1% | **47.6%** / 0.04% |
| V6b | 0.05% / 0.01% | **11.2%** / 0.8% |
| V1 | 0.0% / 1.5% | 0.0% / 2.1% |
| V2 | 0.0% / 0.8% | 0.0% / 0.5% |

The QLIKE thresholds are so strict (1e-9 to 1e-11) that they hold on the wider period too. The Brier thresholds do
not. The likely reason (reasoning only): 2019-26 contains long calm stretches with few or no 2% days (2023 had about
0.4%). In such a window the Brier difference is nearly constant, so a forecaster that always predicts lower
probabilities "wins" every day with a tiny batch standard error. The batch t then reports overwhelming significance,
or, in the other orientation, overwhelming futility, although over the full period there is no skill. 2024-26 had
enough 2% days to hide this.

This is not a remote case. The May 2027 review covers about 6 months that may be calm. On this evidence, a V6a "yes"
or "no" at the review could be wrong with a probability far above the registered 0.13% or 2.5%.

## Must-fix

**1. The Brier claim and futility thresholds do not hold outside 2024-26 (V6a by about 300x on size and 57% false
"no"; V6b and V7 about 4x on size and 11% false "no" at n = 250).**
- The calibration must include regimes like the calm years, with nulls built from all exposed regular sessions that
  have a valid base rate (from about 21 Jan 2019). It must also include a calm-window stress case.
- A rule must be measured within tolerance on those nulls before it is operative.
- Candidates (reasoning only until measured):
  - a minimum number of events (2% days or 2% windows) inside the scored window before any Brier claim or futility;
  - thresholds calibrated on the worst regime;
  - testing within event and non-event days separately.
- If no rule holds, say plainly that V6a, V6b and V7 cannot be judged in calm periods, and put that consequence to the
  owner.
- The QLIKE rules (V1, V2) hold on the wider nulls, as measured above; record that too.

**2. Say what "held-out" proves.** Section 5.3 and 5.5's "strong evidence for the measured null processes" must say
that the held-out check resamples the same series, so it measures Monte Carlo error, not robustness to another period.
The regime check of must-fix 1 becomes the evidence for robustness.

## Follow-ups (not blocking)

- `_quantile` in `v4_size_study.py` takes `ordered[floor(rate x N)]`. With `p <= q` that rejects floor(rate x N) + 1
  series, one more than the target. It is only used in the descriptive table; `conservative_rank` in the operative
  tool errs the safe way.
- V7 borrowing V6b's thresholds stays reasoning only. A VIX-based null should be measured when VIX history is used.
- The orchestrator should tell the owner the cost in plain words before the freeze: V1 and V2 cannot be claimed in
  useful time, and, after must-fix 1, possibly V6 in calm periods. This is what "3 B" turned out to mean.

**Verdict: FAIL for 8f233f0eb846631c68e54b0a0be6a0488093e754**, on must-fixes 1 and 2. The direction of revisions 2
and 3 is right: calibrated thresholds, a minimum of 12 batches, and futility held to the same standard as claims.
The error is calibrating on one period that happens to lack calm stretches. A re-check needs the new nulls, the
re-measured thresholds and both studies. I will re-run this 2019-26 check on whatever rule comes back.

## Addendum 4 (15 Oct 2026): revision 4 at 2490d562da672731be83e83d8eef7e0760f14253 (ae8d563 plus a merge of main)

ae8d563 adds `tools/v4_brier_regimes.py` and its tables, the 5-event gate (`confirmatory.MIN_EVENT_DAYS`,
`brier_judgeable`), protocol text, size-study fixes and tests. The merge commit merges cleanly.

## Gates

On 2490d56 merged with current `origin/main`, the trial merge has no conflicts. **3716 passed**; ruff, format (792
files) and `check_imports` are clean.

## Addendum 3 must-fixes

| Item | Status | Evidence |
|---|---|---|
| 1: Brier rules on all regimes | MET (marginal), with must-fix A below | The nulls run from the first day with 500 resolved base-rate outcomes (15 Jan 2019) to 14 Oct 2026, with calm stress stretches (the calmest 125 and 250 sessions, no 2% day). With no gate (m = 0), the old rule fails (V6b up to 99%). With the 5-event gate, every held-out cell is within tolerance |
| 2: what "held-out" proves | MET | Section 5.3 and the tool's docstring now say it measures Monte Carlo error only, on the same days |
| Follow-ups | MET | The `_quantile` off-by-one is fixed and `calibrated_A` dropped; the VIX null is noted as owed; `outcomes_needed` is exact |

**My re-run of the 2019-26 test**, on the builder's own `brier_series`, with my own seeds and 200,000 series a cell,
at the operative gate-5 thresholds. Unconditional, both orientations:
- **V6a**, n = 125: claim look 1 at most 0.00089, look 2 at most 0.00140; false "no" at most 2.52%.
- **V6a**, n = 250: claim at most 0.00137 and 0.00186; false "no" at most 2.38%.
- **V6b**, n = 125: claim at most 0.00127 and 0.00198; false "no" at most 2.36%.
- **V6b**, n = 250: claim at most 0.00104 and 0.00167; false "no" at most 2.40%.

All are within nominal + 2 Monte Carlo SE, so the builder's table reproduces.

## The question asked: does the outcome gate cause a selection effect? Yes, conditionally, near the gate.

The calm stress stretches hold **zero** 2% days, so the gate simply never judges them; they cannot test a window that
**just** clears the gate. I split the same 200,000 series by the number of 2% days in the window:

| Member, n | Share of windows with 5-7 events | Claim size in 5-7, look 1 / look 2 (nominal 0.00133 / 0.002) | False "no" in 5-7 (target 0.025) |
|---|---|---|---|
| V6a, 125 | 25% | **0.0035 / 0.0055** (2.6x / 2.8x) | **0.086** (3.4x) |
| V6a, 250 | 18% | **0.0059 / 0.0079** (4.4x / 4.0x) | **0.078** (3.1x) |
| V6b, 125 | 25% | **0.0043 / 0.0068** (3.2x / 3.4x) | **0.079** (3.2x) |
| V6b, 250 | 18% | **0.0027 / 0.0042** (2.0x / 2.1x) | **0.058** (2.3x) |

In the 8-12 stratum the rates are mostly near nominal (one false-"no" cell at 3.7%). Above 13 events the rule is
conservative. Each 5-7 stratum holds 36,000-50,000 series, so the excesses are far outside Monte Carlo error.

**What this means.** The rule controls its error rates **on average over windows like 2019-26's**. But the event
count is **seen before the verdict**. When the review window turns out to be near-calm (5-7 big days, about one window
in four or five), the real chance of a false claim is 2-4x the registered rate, and of a false "no" about 6-9% instead
of 2.5%. A false "no" can stop the research programme. The selection effect comes from averaging, not from
forecasts: the thresholds are tuned to the mix of calm and busy windows, so they are too loose for calm ones and too
strict for busy ones. Calibrating on that same observed count fixes this (conditional inference on a count that does
not depend on the forecasts).

## Must-fix

**A. Calibrate the Brier claim and futility thresholds conditionally on the observed event count**, or raise the gate
until the conditional rates are within tolerance in every stratum that can be judged. Then report the conditional
sizes.
- Conditional calibration: thresholds per event-count band (for example 5-7, 8-12, 13+), each calibrated on the nulls
  with that count.
- Measure each band's held-out size and false-"no" rate within tolerance. Without this, section 5.3's "within
  tolerance" claim holds only on average.
- If neither works, say plainly that a V6 or V7 verdict in a near-calm window carries 2-4x the registered error, and
  tell the owner.

## Follow-ups (not blocking)

- V6a's operative claim threshold is about 2.5e-12 at n = 125 and 1e-19 at n = 250, which is honest but effectively
  unreachable. Say plainly to the owner that V6a, like V1 and V2, will almost surely not be claimed. Its futility side
  still works.
- V7 still borrows V6b's rule, and VIX direction has no event structure. Fine as conservative for now; the VIX null
  stays owed.

**Verdict: FAIL for 2490d562da672731be83e83d8eef7e0760f14253**, on must-fix A only. Addendum 3's must-fixes are met on
average, and the builder's tables reproduce with independent seeds. The remaining gap is conditional error near the
gate, which the calm stress cannot show because those stretches hold no events.

## Addendum 5 (15 Oct 2026): revision 5 at 355eae4665b3f3b0adc2fd7ca08dfdb285e683e2 (2490d56..355eae4)

One commit (parent 2490d56). It adds Brier thresholds per event-count band (`tools/v4_brier_bands.py`, its tables),
`confirmatory.event_band`, protocol text and tests.

## Gates

On a trial merge with current `origin/main` (it merges cleanly; `reviews/claude/README.md` auto-merges):
**3824 passed**; ruff, format (820 files) and `check_imports` are clean. `PROTOCOL_v4.md` is exactly 350 lines, at
the limit and not over it. Next time, split it rather than trim it.

## Must-fix A (addendum 4)

| Item | Status | Evidence |
|---|---|---|
| Thresholds by event-count band | MET | Bands 5-7, 8-12 and 13+. Each band's claim and futility thresholds are calibrated on nulls conditioned to that band: the 2019-26 empirical nulls in both orientations, plus Gaussian nulls for claims. Calibration and held-out draws use separate seed words (11/12, 13/14, 15/16). `event_band` returns None below 5 (not judgeable) and the band otherwise; G8 calls `operative_thresholds(question, n, band)` |
| My band split, own seeds | MET | 200,000 series per n and orientation, seed words [4711, n, horizon, flip], different from the builder's, at the committed band thresholds. **All 24 cells are within nominal + 2 Monte Carlo SE.** Worst rates: claim look 1 0.00119 (V6a, n = 250, 8-12); claim look 2 0.00176; false "no" 0.0255 (V6b, n = 250, 13+; tolerance there 0.0261) |
| Identical V6b n = 125 rows for 8-12 and 13+ | Not a bug | Each band's claim threshold is the smallest quantile over the empirical and Gaussian nulls. The Gaussian nulls have no events, so they enter every band unchanged. For V6b at n = 125 the Gaussian quantile is the binding minimum in both bands: I recomputed it at 0.000647573764932622, identical to both rows' threshold to every digit. The worst held-out claim size in both rows is then the Gaussian null's, also band-independent. The futility columns, which have no Gaussian null, differ (2.35% and 2.45%) as expected |
| V6a declared effectively unclaimable; VIX null owed | Done | Stated in the protocol and response 99 |

## Remaining notes (not blocking)

- Every Brier verdict is conditional on a count of outcomes that the forecasts do not influence, so conditioning on it
  is legitimate (conditional inference on a count that carries no information about relative skill). It must stay
  defined exactly as in `brier_series`: 2% days of each forecast day's first outcome session within the scored window.
  G8 must use that same definition.
- **For the owner, plainly:** under v4 as written, V1, V2 and V6a will almost surely never be claimed. V6b and V7 need
  about 150-200 independent outcomes at r = 3, and no verdict at all in a window with fewer than five 2% days. Futility
  ("no") still works for every question. So the most likely May 2027 Test A result is "undecided", and the owner's
  confirmed option B then applies.
- `PROTOCOL_v4.md` is at the 350-line limit; any later change must split it.

**Verdict: PASS for 355eae4665b3f3b0adc2fd7ca08dfdb285e683e2** (the draft, not frozen). The freeze still needs:
ChatGPT's re-review of revisions 1-5, the G7 and G8 code (G8 must use `event_band`, the operative thresholds and the
gate exactly), and then my check of the freeze record's hashes. Merge as a merge commit after ChatGPT, keeping both
READMEs' rows.

## Addendum 6 (15 Oct 2026): revision 6 at e32f89d4c45e22f3f2e25cf3abab6895f0f55dcc (355eae4..e32f89d)

Range: ChatGPT's review 101 (f52d858, 4e76d17) and e32f89d. The calibration text moves to
`PROTOCOL_v4_calibration.md`. The commit adds V7's own VIX null (`tools/v4_vix_null.py`), makes V7 descriptive-only
(`terms.DESCRIPTIVE_ONLY`, excluded in `family.judge_family` and `stop_rule.forecasting_test`), and adds V6b's
busy-regime stress (`v4_brier_busy_stress.json`).

## Gates

On a trial merge with current `origin/main` (clean; `reviews/claude/README.md` auto-merges): **4013 passed**; ruff,
format (852 files) and `check_imports` are clean. `PROTOCOL_v4.md` has 325 lines and the calibration file 97: the
split is done.

## My own-seed checks

| Claim | My result | Verdict |
|---|---|---|
| V6b in the busiest 125 sessions (16 Dec 2019 - 18 Jun 2020, 36 2% days), n = 125, band 13+ | False claim **0.438** (builder 0.436). False "no", flipped orientation, **0.857** (builder 0.857). Opposite orientations about 0. 200,000 series, seeds [9090, ...] | Reproduced |
| V7 own rule R1, n = 125, worst region | False claim look 1 **0.060** (calm 250) against the builder's 0.058; false "no" **0.302** (calm 250, flipped) against 0.299; the full period is near nominal (0.0014 and 0.024). 50,000 series a region | Reproduced |
| V7 descriptive-only | Code checked: its slots are never judged (p = 1), they are not counted in Test A, and the family stays at 15. This is ChatGPT review 101's own alternative remedy | Correct |

## What the stress numbers mean (the question on item E)

**They are not a size failure in the usual sense.** Inside the 2020 crash stretch, the "null" difference (centred on
its 2019-26 mean) has a **local mean of -0.33**, larger than its full-period SD (0.21). In that window the EWMA
forecaster really did beat the base rate, by a lot. The stress resamples only from that stretch; at n = 250 it draws
250 days from 125, so the local mean is fixed. Any consistent test **must** then "reject". What the 44-91% shows is
this: a verdict from one regime-dominated window measures skill **in that regime**. It cannot measure long-run,
all-weather skill. No test on a single window can fix that, because the data in such a window do not contain the
answer (strong evidence: the local mean exceeds the spread). My own addenda 3-5 asked for "regime robustness". That
was right for the calm case, where calm windows hold no information, but it cannot be met in a crash window by any
rule. I say so plainly.

**On item E's options (reasoning only; the owner decides):**
1. **Accept with disclosure.** Statistically defensible **if** the claim is worded as what it is: "V6b beat its
   baseline over the scored window". The registered error rates hold on average over windows like 2019-26's, not
   inside any one regime. A claim from a crash-dominated window is a claim about crash-time skill. This is honest
   and keeps V6b useful.
2. **Exclude crash-dominated windows.** A legitimate **predeclared** gate, not post-hoc selection, only if all of these
   hold:
   - it is frozen now, before any v4 forecast exists;
   - it is defined only on outcome-side data the forecasters do not influence (for example the window's mean VIX or
     its 2%-day count above a fixed level), as the calm gate is;
   - the remaining judgeable bands are re-measured within tolerance;
   - its cost is disclosed.

   Choosing the cut-off after seeing v4 results would be post-hoc and is not allowed. The cost: claims then never
   speak to crash behaviour, which is when the 2% question matters most for risk.
3. **Make V6b descriptive.** The most conservative option. Test A can then never say "yes" (no claimable member), so
   the review is "undecided" or, through futility, "no".

My view (reasoning only): option 1 or a properly frozen option 2. Option 1 is simpler and loses nothing, provided the
card and the review state the regime of the scored window beside any verdict.

## Must-fix

**1. Item E is presented as V6b's alone, but the same regime point applies to every member's futility, and futility
drives Test A's "no".**
- Test A says "no" when **every** counted member is futile, and with B's "no" that means stop or pivot.
- The busy-regime stress was run only for V6b (claims and futility) and for V7. V1, V2 and V6a's **futility** in a
  crash-dominated window is neither measured nor disclosed. By the reasoning above, their futility verdicts there also
  measure that crash.
- Fix (wording, or a short run):
  - either measure V1, V2 and V6a's false-futility rate inside the busiest 125- and 250-session stretches with the
    existing tools;
  - or state in section 11 E and calibration section 4 that the regime caveat applies to **every** member's verdict,
    claims and futility alike;
  - and that a Test A "no" reached in a crash-dominated window measures that crash.
- The owner's choice under E should cover the whole Test A, not only V6b's claims.

## Follow-ups (not blocking)

- Whatever E decides, every report should print the scored window's regime (mean VIX, 2%-day count) beside each
  verdict.
- ChatGPT review 101's blocking item (V7) is resolved by its own alternative remedy. ChatGPT should confirm.

**Verdict: FAIL for e32f89d4c45e22f3f2e25cf3abab6895f0f55dcc**, on must-fix 1 only. The numbers are reproduced and
honest, V7's descriptive-only treatment is correct, and the split is done. A re-check needs only section 11 E,
calibration section 4, and any new stress table.

## Addendum 7 (15 Oct 2026): revision 7 at 41f29d3065a46024e249aba2e202a5031ead3849 (e32f89d..41f29d3)

One commit (parent e32f89d). It adds every member's regime stress (`tools/v4_regime_stress.py`, 100,000 series a cell,
with a "local" true-improvement column), measures item E's option 2 (`tools/v4_crash_cut.py`), adds the window-regime
printout for G8 (`fno/forecast_v4/regime.py`), and updates the protocol, the calibration file and response 99.

## Gates

On a trial merge with current `origin/main` (clean; README auto-merge): **4819 passed**; ruff, format (916 files) and
`check_imports` are clean. Protocol 334 lines and calibration file 138, both under 350.

## The three questions

**1. The "local" column: correct.** `local_improvement` = -mean(d) / mean(b) over the stretch. A claim is marked false
only where local <= 0, and a futility "no" only where local >= the margin. That is the right test of whether a
verdict contradicts the regime's own truth. One caveat: the resamples are circular 20-day block draws **inside** the
stretch, not real windows, so each pseudo-window's truth varies around the stretch's local value.

**2. Option 2: the "makes things worse" reading is not supported as written.** The re-measure table judges the
**kept** series against the **whole stretch's** truth. Yet the cut keeps exactly the calmer pseudo-windows of the
crash year, and their own median measured improvement is far lower:
- V6b, busy 250, n = 125, as measured: local +0.305, but the kept median estimate is -0.008 (VIX cut) and -0.186
  (2%-share cut);
- at n = 250: +0.064 and -0.084.

So most of the "false no" rates (10.4% and 16.0%) are "no" verdicts that **agree with the kept windows' own data**:
regime truth again, wrongly marked bold. The same holds in reverse for the flipped claim rows.
- What the cut really costs is in the cost table, which is sound: it removes 7.6-15.6% of real 2019-26 windows.
- What it buys is not measured correctly; that needs each kept set's own truth.

Option 2 is therefore **not shown to be worse**; it is shown to be **unmeasured on the right basis**.

**3. V1's calm-window false claims (0.85%): not acceptable as disclosure only; a cheap fix exists.** I reproduced
them with my own seeds (100,000 series):
- calm 125, n = 125: false claim **0.89%** (builder 0.85%) where the local truth is **-0.175**, i.e. the forecaster
  is locally worse;
- false "no" **6.96%** (builder 6.81%) where the local truth is **+0.208**;
- calm 250, n = 250: false "no" 11.4%.

These are **not** regime truth: the verdict contradicts both the full-period and the local truth. Three V1 slots at
0.89% give a union bound of about 2.7% against look 1's whole 2% budget, and a false "no" can stop the project.

The Brier members already have the fix: their 5-event gate makes calm windows undecided. Applying the **same gate to
V1 and V2** (fewer than five 2% days: no claim, no "no") removes every calm-stretch failure. In my run the calm
stretches hold no 2% days, so the rate is 0. On the full period the gate only removes verdicts, so size can only fall:
V1 false "no" 1.48% becomes 0.54% overall at n = 125. The cost is that V1 is judgeable in 53% of real windows at
n = 125 and 90% at n = 250. V1 is effectively unclaimable anyway, so the gate costs only calm-window futility, which
is exactly the unsafe part.

## Must-fix

1. **Extend the 5-event gate to V1 and V2** (claims and futility), or another measured gate that removes the
   calm-window failures. Re-run `v4_regime_stress.py` to show it, and update the Test A text ("undecided" in a calm
   window for every member). If the builder or the owner prefers disclosure only, the owner must accept a measured
   false "no" of up to about 7% (11% at n = 250) for V1 in a calm window, which feeds the stop rule. I advise against
   it: the fix is free.
2. **Correct option 2's description in 11 E and calibration section 4.** The "worse" rates are judged against the
   whole stretch's truth, while the kept series are the calmer sub-parts (kept median estimates -0.19 to +0.06 against
   local +0.305). Either re-mark them against each kept set's own truth, or say plainly that option 2's benefit is not
   measured on the right basis. Keep the cost table (7.6-15.6% of real windows removed). The owner must not choose E
   on a mislabelled comparison.

## Follow-ups (not blocking)

- "Test A's false 'no' is bounded by reasoning from marginal rates; the joint rate is not measured." This is fine as
  disclosed, because a "no" needs **every** counted member futile, so the joint rate is at most the smallest
  member's. After must-fix 1 the calm-window case disappears.
- `regime.py`: the G8 criterion (each verdict prints its window's mean VIX and 2%-day count) is right. Check it at G8.

**Verdict: FAIL for 41f29d3065a46024e249aba2e202a5031ead3849**, on must-fixes 1 and 2. The new stress table is honest
and reproducible, and the local column is right. The remaining issues are one real calm-window failure, which has a
free fix, and one mislabelled comparison that the owner's choice would rest on.

## Addendum 8 (15 Oct 2026): revision 8 at a0c191ed6d2ada87c8ea4e90f698a9ec8869014b (41f29d3..a0c191e)

Scope, as requested and agreed (the owner has raised over-engineering): only addendum 7's two must-fixes. Residual
risk is recorded as disclosure unless it would change what the owner decides.

| Item | Status | Evidence |
|---|---|---|
| Must-fix 1: 5-day gate for every member | MET | `confirmatory.judgeable` (it replaces `brier_judgeable`) now covers every member. Protocol 5.3 line 190: "Every member also needs at least 5 2% days in the scored window ... else it is undecided"; 11 E says a calm window is undecided for every member. The regime stress and crash cut apply the gate to every member. The builder's V1 full-period false "no" of 0.56% matches my own 0.54% (addendum 7). V1/V2 banding was measured and is not needed: 47 of 48 cells are within, and the one marginal cell is band truth |
| Must-fix 2: option 2 re-marked | MET | `v4_crash_cut.md` now judges each kept, judged set against **its own** pooled truth ("set" column), beside the same draws with no cut. "Worse" is withdrawn, and the cost table is kept. Example, V6b busy 250, n = 125, as measured: no cut gives a **bold** 3.48% false "no" (set +0.310); the share cut's 17.32% is *italic* (set -0.158), i.e. that set's truth. That is exactly the correct basis |

## Gates

On a trial merge with current `origin/main` (clean; README auto-merge): **4819 passed**; ruff, format (916 files) and
`check_imports` are clean. Protocol 336 lines, calibration file 159, tool 292: all under 350.

## Residual risk (disclosure, not blocking)

- **Genuine errors remain inside the 2020-21 crash stretches.** For example, V6b busy 250, n = 125, no cut: a 3.48%
  false "no" and a 0.44% false claim, both against their own set's truth. They are disclosed in the tables and in
  11 E. They do not change the owner's E choice beyond what is already written: option 1 accepts them, and the share
  cut removes most of them at the cost shown.
- **`judgeable` is a predicate that G8 must call for every member at every look**, as the family code does not call
  it itself. This goes into G8's acceptance criteria, and I will check it there.

**Verdict: PASS for a0c191ed6d2ada87c8ea4e90f698a9ec8869014b** (the draft, not frozen). I agree with the builder and
the orchestrator that this should be the last revision before ChatGPT's re-review and the owner's item E choice. The
freeze still needs G7 and G8's code and my check of the freeze record's hashes.

## Addendum 9 (15 Oct 2026): merge check, G6 v4 draft merged to main as 597487f (not frozen)

- **Merge is exact.** 597487f's parents are ea18b1f (main) and 093c3ca (the branch). Recomputing the merge with
  `git merge-tree --write-tree ea18b1f 093c3ca` gives a tree identical to 597487f's (empty diff).
- **Merged content equals the passed SHA.** 093c3ca is a0c191e (my addendum 8 PASS) plus only ChatGPT's review 102
  files (`review_102_g6-protocol-v4-final.md` and its README row; verdict APPROVE). Every file the branch touched is
  identical on 597487f.
- **No unjudged code since.** Nothing under `fno`, `tests`, `tools`, `.github` or `config.yaml` changed between
  597487f and current `origin/main`. The later commits are decisions, logs, manifests and judge files.
- **Owner's item E is recorded.** 67105da appends the row "G6 item E: option 2, outcome-side crash-share cut" with
  the owner's words ("merge G6, E option 2") **and the question asked**. A window whose share of 2% days exceeds 10%
  is undecided, with the cut-off frozen now, before any v4 score.
- **CI.** The parent ea18b1f is green. The first run that includes the merge (4e46edc) was in progress; its result
  follows in my report.

**For the freeze check (recorded now):**
- The protocol's section 11 E still lists the three options. The freeze commit must write option 2 in as the
  operative rule.
- `judgeable` (5+ 2% days) and the new cut (2%-day share at most 10%) must both be applied by G8 to **every** member,
  at every look, with the window's mean VIX, 2%-day count and band printed beside each verdict.
- The cut only removes verdicts, so the band thresholds stay valid (conservative); no recalibration is needed. But at
  n = 125 the cut means at most 12 2% days, so the 13+ band is never used at that size. The freeze text should say
  so.
- The freeze record must hash the protocol, the calibration file, `fno/forecast_v4/`, the tools that compute the
  operative thresholds, their committed tables, and the G7 and G8 files.

**Verdict: merge check PASS** (CI on the merge to be confirmed).
