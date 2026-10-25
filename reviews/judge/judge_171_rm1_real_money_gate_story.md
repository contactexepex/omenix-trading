# Judge 171: RM1 real-money gate, story text and draft gate (judge A)

**Checked:** `story/rm1-real-money-gate` at `d29934f5` (one commit on main 35e999af). The files are:
- `docs/stories/RM-real-money.md`
- `research/evaluation/REAL_MONEY_GATE.md` (12 items)
- `reviews/claude/response_163_rm1-real-money-gate.md` (claims, trace table, Q1-Q10)
- the WORK_REGISTER row

I read them against:
- design v2 8.3 and 8.4 (`docs/design_v2/08_budget_and_stop_rules.md:77-109`);
- DESK_DECISIONS decision 8 and its amendment (rows 113 and 118), principle 4 (row 94) and decision 168;
- the S1 code: `fno/evaluation/order.py`, `completeness.py` and `freeze.py`.

**Numbering:** judge 163 and 167-170 are taken (168 and 169 by other judges while this was written), so this is judge 171. No code in this
round.

**Verdict: FAIL, 3 should-fix, no blocking.** The text never enables an order, and the one-freeze design is the right,
minimal choice. But two items would decide real money differently from what the owner accepted, and the evidence
record is not tied to the freeze.

## Criteria

| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Every 8.3 condition and 8.4 element has an exact rule, traced | PARTLY | 10 of 12 sound; `real_test_sample` drops 8.4's registered number (SF3); slippage in `real_test_pass`/`real_test_stops` has no reference price (SF2) |
| 2-4 | `check`, `freeze` refusal, the gate's hash in `FREEZE_v<n>.md`, `verify` | MET as design | The reuse fits `freeze.py`'s target hashing and `verify`; see the note on completeness format |
| 5 | Owner numbers before the freeze | MET | Q1, Q2 and the status rule make the freeze refuse until decided |
| 6 | Never an order, no broker import | MET | The scope item and the hard line in the header; the import test is planned. Nothing reads the gate to act; eligibility is "a report line, never an order, a setting or a switch" |
| 7 | 350 lines | MET for text | Code later |
| — | Freeze "before the first counted paper decision" | NOT MET | SF1 |
| — | Owner questions complete and neutral | PARTLY | Q1-Q2 and Q4-Q10 neutral, each with real options and a labelled recommendation; Q3 lacks the 8.4 option (SF3) |

## Should-fix

**SF1. The evidence record is not tied to the freeze, and a shadow record is outside S1's order check.**
- **Evidence:**
  - The gate's "Terms" say the evidence record is "the version's completed forward paper positions in Book 1 … or its
    registered shadow account", with no condition on when they happened.
  - S1's order check proves only that the freeze commit is a strict ancestor of "every book's first counted decision"
    (a D3 run of a book; earlier runs are pilot evidence; `fno/evaluation/order.py:1-10`).
  - Book 1 paper-trades before the freeze as pilot evidence (DESK_DECISIONS row 83).
  - An `exploratory_shadow` may start collecting before rung 1 (`docs/design_v2/01_overview.md:125`). It is a
    recorded decision "never in a book", so no D3 book run and no order check covers it.
- **Path in normal running:** S1 v1 waits for the S2/S3/F8/F9 code and the owner's Q1-Q10. Meanwhile Book 1's pilot
  positions and a shadow's positions accumulate. They are then counted toward `paper_evidence` by a gate written while
  they were visible. That is principle 4's risk (a pass mark written after seeing results), and response 163 claim 3
  ("the order check already proves it") does not hold for shadows.
- **Expected fix (text):**
  - Define the evidence record as positions counted under the frozen protocol version that holds the gate (the
    decision's commit has that version's freeze as a strict ancestor, `order.py`'s "version of a decision").
  - For a shadow: either extend the order rule to registered shadow records in RM1's scope, or restrict the gate to
    Book 1 until a shadow has the same proof.
  - Pilot positions are shown, never counted.

**SF2. Real slippage has no reference price, so the pass and stop rules can be looser than 8.4.**
- **Evidence:**
  - 8.4: "real slippage per unit must be no worse than the paper pad plus Rs 0.50"; stop at "slippage twice the paper
    pad over 5 trades".
  - The gate: "the mean of real-minus-paper fill slippage per unit is at most the paper pad + Rs 0.50"; stop (b) "mean
    real slippage per unit … exceeds twice the paper pad".
  - A paper fill carries a price and a pad separately (`fno/desk/execution.py:52`,
    `Order(quote.side, quote.price, quote.units, FILL_PAD_RS)`). `fill_honesty` says "paper price before pad" explicitly;
    these two items do not.
- **Path:** if "paper" means the padded paper fill, a real buy may sit 2 × pad + Rs 0.50 above the quote and still
  pass, which is about double what 8.4 allows. If it means the quote, it matches 8.4. A real-money pass or stop decision
  depends on which one the builder picks.
- **Expected fix (text):** in both items, define real slippage per unit as the real fill minus the paper price before
  pad (sells: the reverse), signed so that worse is positive. That is the same reference as `fill_honesty`.

**SF3. `real_test_sample` replaces 8.4's registered number of trades with a fixed 20.**
- **Evidence:**
  - 8.4: "Duration: its registered number of trades or 6 months, whichever is later" (owner-accepted, decision 8).
  - The gate: "the later of 20 trades placed and 6 months".
  - Q3 offers 20, 30 or 12 and no "the version's registered number" option.
  - `paper_evidence` keeps the analogous rule ("the larger of S1's paper_gate and the sample the version's
    registration named").
- **Path:** a version registered for 40 trades finishes its real test at 20 trades or 6 months. That changes when a
  real-money verdict is given, against an owner-accepted row (coordination rule: a contradiction is a FAIL).
- **Expected fix (text):** "the later of max(20, the version's registered number of trades) placed and 6 months from
  the first real entry", and Q3 asks only the floor, stating 8.4's rule.

## The one-freeze design (asked: sound and minimal?)

**Sound and minimal, with SF1's caveat.**
- One more `frozen_files` entry reuses S1's hashing, refusal and `verify`, with no second freeze tool or record (DRY,
  KISS).
- The cost (a gate change is a new S1 version) is stated in "Known limits". It is the intended cost of principle 4.
- Q10 rightly goes to the owner, because `frozen_files` is owner-decided (14 Oct).
- The order check proves the gate precedes every book's counted decision, but not that it precedes the gate's own
  evidence (SF1).

## Notes (one line each, no fix asked)

- `completeness.py` accepts only the exact status "proposal, owner decides" or "decided by the owner on YYYY-MM-DD",
  and only the three bare evidence labels. Six gate items carry extra text ("owner number (Q1, Q2)",
  "reasoning only (a point comparison …)"), and the gate has no version line. So the test plan's "the real draft gate
  passes `check`" fails as written: move the question references to the Reason line, and exempt the version line by
  parameter.
- `fill_honesty`: A16 records only the nearest weekly and nearest monthly NIFTY chains (G10, `expiry_plan.py`). A
  version trading any other expiry gets no snapshot and can never reach 20 legs. Tell the owner.
- `real_cap_fit` "the last 20 sessions' 15:00 quotes": name the source. The 3 pm recorder captures at 14:55 today and
  moves to 14:30 at v4 go-live.
- Condition 6's fact checks out: Rs 5,000 / 65 = 76.9 points. An ATM monthly NIFTY premium is well above that (some
  evidence, as labelled).
- The prediction-interval formula, paper mean − t(0.95, m−1) × SD × √(1/n + 1/m), is the correct one-sided bound for
  the mean of n new trades. Route (b)'s 0.05/m is Holm's first step, as stated.
- The branch conflicts with main in `docs/WORK_REGISTER.md` and `reviews/claude/README.md`, rows only. Keep both
  sides.
- Coordination: no other row covers the real-money gate. S6's later `PROTOCOL.md` change is on other lines, as
  response 163 §4 says, so there is no duplicate.

## Gates

Gates at d29934f5 (text only; trial merge conflicts on rows only): pytest 5877 passed; `ruff check` clean; `ruff format --check` 1074 files formatted; `check_imports` clean.

**A re-check needs only:** the Terms line and order rule (SF1), the two slippage definitions (SF2), `real_test_sample`
and Q3 (SF3).

## Addendum 1: revision at c27f8c64: PASS

Scope as asked: SF1-SF3 and notes 1-3. The RM1 diff since the merge of main (c24096c1..c27f8c64) touches the story,
the gate, response 163 §5 and the register row.

- **SF1: MET.**
  - The Terms define the evidence record as Book 1 positions whose decision commit has the gate's freeze record as a
    strict git ancestor. That is S1's version rule (`order.py`).
  - Pilot positions (before the freeze) and shadow positions are "shown, never counted", with the reason given.
  - The story scope, criterion 6 and both Known-limits lists say the same.
  - `index_benchmark` now reads Book 1's record only.
  - "Book 1 only" is the simpler of my two options. The order check proves exactly that set.
- **SF2: MET.**
  - The new term "paper price before pad" is E8's snapshot ask for a buy and bid for a sell, without `FILL_PAD_RS`.
    Worse is positive.
  - `real_test_pass` 2 measures from it: real fill minus paper price before pad, mean ≤ pad + Rs 0.50, matching 8.4.
  - `real_test_stops` (b) uses the same definition over the legs of any 5 consecutive trades, against twice the pad.
  - `fill_honesty` already used the same reference.
- **SF3: MET.**
  - `real_test_sample` is the later of max(20, the registered number) trades and 6 months from the first real entry.
    It quotes 8.4.
  - Q3 now states 8.4's rule and asks only the floor: 20, 30, or none (the registered number alone). The options are
    neutral, and the recommendation is labelled.
- **Note 1: MET, checked by script.** `parse_protocol` on the gate at c27f8c64 finds 12 items and no duplicates.
  Every item has all four fields, the exact status "proposal, owner decides" and a bare evidence label, and no
  undecided words appear. The missing version line is exempted by `require_version` in the expected design.
- **Note 2: MET.** A16's expiry limit is stated in `fill_honesty` and in Known limits.
- **Note 3: MET.** `real_cap_fit` names the 3 pm recorder (A4, `research/data/quotes/`) at S1's timetable capture time.

**Coordination:** WORK_REGISTER row 38 (S1's text owner) lists RM1's `frozen_files` line as a pending edit "after S6".
RM1 no longer edits `PROTOCOL.md` itself. That is one builder per file, with no duplicate.

**Gates (trial merge with origin/main 96edbb15, tree 7cd16ee, clean merge):**
- pytest: 5878 passed;
- `ruff check`: clean;
- `ruff format --check`: 1074 files formatted;
- `check_imports`: clean.

**Note (one line, no fix asked):** response 163 §1 claim 4 still says "Book 1 or the version's shadow account". §5
supersedes it, but ChatGPT reads §1 first.

**Verdict: PASS.** Next come ChatGPT (rule 9), then the owner's Q1-Q10, then the code round.

## Addendum 2: delta re-check at 2945dbd8 (ChatGPT review 118 revision): FAIL (2 should-fix)

Asked by the builder directly, with the orchestrator copied, and reported to the orchestrator. The delta
f8cbbc6c..2945dbd8 touches the gate, the story's criterion 6 and status, and response 163 §3 (Q11-Q13) and §6.

**Sound:**
- **"Valid quote" and "execution slippage"** (the real fill minus the valid quote at the owner's order time) separate
  execution from the market's move. E8's fill at about 10:15 next session is confirmed in `G-forecasts.md` (G10 table).
  Unknown never counts as zero.
- **Paired net now binding** (`real_test_pass` 1): mean − t(0.95, n−1) × SD(d) / √n ≥ the Q11 margin. That is the
  paired test 8.4 names; the prediction bound stays as a floor and is labelled model-based.
- **`real_cap_fit`** uses the last 20 issued cards, re-priced with their own contracts, lot size, quotes and charges,
  plus the next proposed trade.
- **Numbers checked:**
  - 5,000/65 = 76.9 points and 4,000/65 = 61.5 points, before charges;
  - the credit vertical: 65 × (100 − 30) + 200 = Rs 4,750 and 65 × (200 − 30) + 200 = Rs 11,250;
  - **Q11:** t(0.95, 19) = 1.7291, and 1.7291 × 1,000 / √20 = **Rs 386.6**, so the builder's "about Rs 387" (Q11's
    "about 390") is correct; with a −Rs 500 margin, real must average within about Rs 113 of paper (Q11 says "about
    Rs 110", correct).
- **The Bonferroni wording** (one fixed family, one look) and the daily-settlement proxy label are correct.
- **Format:** `parse_protocol` on the gate at 2945dbd8 finds 12 items, no duplicates, every status exactly "proposal,
  owner decides", bare labels and no undecided words (my script).

**SF1. The unknown-leg rule in `real_test_pass` 3 has no exact rule at or under the 1-in-10 limit.**
- **Evidence:** the text says "a leg with unknown slippage counts against the test (not met if more than one in ten
  legs is unknown)". At 10% or fewer unknown legs it does not say what the mean uses. "Counts against" can mean the leg
  is left out, given the worst observed slippage, or given some other penalty. `real_test_stops` (b) says "left out of
  the mean and listed".
- **Path in normal running:** the owner misses the Groww screenshot on 3 of 40 legs, and A16 is older than 5 minutes.
  The pass on execution then depends on how the builder reads "counts against".
- **On the 10% number (asked):** it is reasonable. At 20 two-leg trades it allows 4 of 40 legs unknown. It sits
  inside Q12 for the owner, labelled reasoning only. The only fault is the missing rule beneath it.
- **Fix (text):** state the rule, for example "unknown legs are left out of the mean and listed; more than 1 in 10
  unknown is not met", the same as stop (b).

**SF2. Q13 is not neutral: it hides that its recommended option drops the owner-accepted test in 8.3 condition 4,
and it omits that test as an option.**
- **Evidence:**
  - 8.3 condition 4 (owner-accepted, decision 8) says "the mean gap between paper fill and the next real snapshot is
    within the pad".
  - The new `fill_honesty` (a) checks the fill against its own snapshot, which the builder rightly calls circular.
    (b) needs a second recorder at fill time.
  - Q13 offers (a) validity alone, (b) strict, which "blocks every version", and (c) a second recorder later.
  - Under (a), condition 4 has no independent comparison at all, and the question does not say that an accepted
    condition is relaxed.
  - The owner-accepted test is feasible: E8 fills from A16 at about 10:15, so the next A16 snapshot (about 10:30) is
    the "next real snapshot" of 8.3. ChatGPT's point, that a later move is no proof, makes it noisy, not impossible.
- **Path:** the owner picks the recommended (a) without being told it removes 8.3 condition 4's only independent
  check. That decides when real money can be put to the owner (coordination rule: a contradiction of an
  owner-accepted row must reach the owner as one).
- **Fix (text):** add option "(d) keep 8.3 as written: the mean gap to the next A16 snapshot (about 15 minutes later)
  within the pad, its noise stated". Say plainly in Q13 that (a) relaxes the owner-accepted condition 4.

**Notes (one line each, no fix asked):**
- `real_test_pass` Reason: "with n = m = 20 and SD Rs 5,000 the prediction floor sits about Rs 2,160 below paper's
  mean". By the gate's own formula it is 1.7291 × 5,000 × √(1/20 + 1/20) = **Rs 2,734**. Correct the number; "a weak
  filter" stands.
- Q11's SD near Rs 1,000 is an assumption. d includes the timing gap when the owner fills at a different time from
  E8's 10:15 model, so SD(d) may be much larger. Q11 says the real SD is unknown, rightly.
- The branch conflicts with main in `reviews/claude/README.md` (rows only). Keep both sides.

**Gates at 2945dbd8 (docs-only delta; the trial merge conflicts on index rows only):** pytest 5878 passed; `ruff check` clean; `ruff format --check` 1074 files formatted; `check_imports` clean.

**A re-check needs only:** `real_test_pass` 3's unknown-leg rule, Q13's options and wording, and the Rs 2,734 figure.

## Addendum 3: final text at d3d577e9 (every item decided by the owner): FAIL (2 should-fix open)

The builder sent this directly, and I reported it to the orchestrator. The three DESK_DECISIONS rows are on main:
946bb8e7 (18:45 UTC), f0f6d2d8 (18:48) and 793aeb54 (18:50). The gate's values match them item by item:
- account Rs 2 lakh, cap Rs 5,000;
- max(30, registered) trades and 6 months;
- the second period as the only route;
- one-sided, with both bounds binding;
- replay cap Rs 5,000;
- 90% discipline;
- stops (a) and (a2) at Rs 20,000;
- the paired margin of −Rs 500;
- valid quotes no older than 5 minutes for real orders and 15 for recorder uses, with the screenshot source and more
  than 10% unknown legs failing;
- Q13 (a).
All 12 items parse with a decided status and exact labels (my script on the trial merge). Depth is available, since
A16's Groww parser keeps bid and offer quantities (`fno/providers/groww.py:82-91`).

**SF1 (addendum 2): NOT MET.** `real_test_pass` 3 still gives no rule for the mean when 10% or fewer legs are unknown.
It now says only "more than 10% of real legs with unknown slippage is not met". Stop (b) says "left out of the mean
and listed". The fix is unchanged: one clause, the same as stop (b). This is a builder text fix, with no owner question.

**SF2 (addendum 2): open, now an owner confirmation.**
- The owner answered Q13 at 18:48. My finding came at 18:54, so the owner chose (a) from the options as asked. Those
  options did not say that (a) relaxes the owner-accepted 8.3 condition 4 ("the mean gap between paper fill and the
  next real snapshot is within the pad"), and they did not offer that test as an option.
- The owner's choice stands; I do not reopen it.
- **Expected:** the orchestrator puts one line to the owner. "Your Q13 answer replaces 8.3 condition 4's accepted
  test (the paper fill against the next A16 snapshot, about 15 minutes later, noisy) with validity only. Keep that, or
  add the next-snapshot gap within the pad?" Record the answer in DESK_DECISIONS. If the owner keeps (a), the row says
  it amends 8.3 condition 4, and SF2 is closed.

**Notes (one line each, no fix asked):**
- The `real_test_pass` Reason still says the prediction floor is "about Rs 2,160 below paper's mean" at n = m = 20.
  The formula gives Rs 2,734. The example also predates the owner's floor of 30: at n = 30 and m = 20 it is
  1.7291 × 5,000 × √(1/30 + 1/20) = Rs 2,496.
- `fill_honesty` (a) says "one invalid leg is not met", and validity now includes depth. The owner's row says
  validity "(fresh, two-sided, depth)" but not that one leg fails the condition. E8 should never fill from an invalid
  quote anyway, so this is a consistency check. State that in the code round, so one thin far strike cannot void a
  record unseen.

**Gates (trial merge with origin/main 1d85ede5, tree be5c907, clean merge):** pytest 5993 passed; `ruff check` clean; `ruff format --check` 1095 files formatted; `check_imports` clean.

**A re-check needs only:** SF1's clause, and the owner's answer for SF2 with its row.

## Addendum 4: final text at 04a80222: PASS

The builder sent 0b47e271 and then 04a80222 directly, and I reported this to the orchestrator. Scope: SF1 and SF2 of
addenda 2-3, and the new Paper-pad term with the items it touches.

**SF1: MET.** `real_test_pass` 3 reads: "more than 10% of real legs with unknown slippage is not met; at 10% or fewer,
unknown legs are left out of the mean and listed". It is the same rule as stop (b). The "valid quote" term now leaves
it to each item how unknown legs count.

**SF2: MET.**
- Row 22df15bf (on main, 18:55 UTC) records the owner re-asked "with the missing option". The owner kept 8.3
  condition 4 as written, replacing the Q13 answer in f0f6d2d8.
- Row 162d8fbf (18:57) records the owner's noise-aware form.
- `fill_honesty` now matches both:
  - (a) quote validity, binding;
  - (b) the gap to the first A16 snapshot after the fill, worse positive. It is not met only when the one-sided 95%
    lower bound of the mean gap exceeds the paper pad;
  - a leg with no next snapshot is left out and listed, and fewer than 20 such legs is not met. The 20 is the original
    draft's number; I checked it at d29934f5.
- The 15-minute noise is stated in the Reason.

**Paper pad (Q14, row 162d8fbf): MET, and the fact is right.**
- The desk's `FILL_PAD_RS = 0.0` (`fno/desk/pricing.py:17`), so "the paper pad in force" would have meant Rs 0: an
  allowance of only Rs 0.50 for real slippage, a stop on any adverse average, and a gap rule failed by noise about
  half the time.
- Research's `PAD = 1.0` rupees per unit (`fno/research_engine/cycle_costs.py:24`).
- The gate's numbers follow:
  - `real_test_pass` 3 allows ≤ Rs 1.50 per unit;
  - stop (b) fires above Rs 2 per unit over 5 trades;
  - the crash replay adds the paper pad;
  - `fill_honesty` (b) compares against Rs 1.
  These match the row.
- The builder found this; it is a real gap that my addenda missed.

**Prediction floor: MET.** Rs 2,734 (1.7291 × 5,000 × √0.1).

**Format and gates:**
- On the trial merge with origin/main 04fa3635 (tree 95a3146, clean auto-merge), `parse_protocol` finds 12 items, no
  duplicates, every status "decided by the owner on …", exact labels and no undecided words.
- pytest: 6086 passed;
- `ruff check`: clean;
- `ruff format --check`: 1120 files formatted;
- `check_imports`: clean.

**Notes (one line each, no fix asked):**
- `fill_honesty` (b)'s t-bound treats every leg as independent. Legs of one position share the same 15-minute move,
  usually offsetting (a spread's bought and sold legs, or a strangle's call and put), so the leg count k overstates
  the independent observations. The bias's direction depends on the structure. In the code round, use one gap per
  position (the mean of its legs) as the unit.
- The 60-minute fill (E8) and A16's 15-minute grid together decide which snapshot is "next". State in RM2 which mark
  counts when the fill time equals a mark.

**Verdict: PASS.** Every gate item is decided by the owner on 15 Oct 2026, with five cited rows, all on main. RM1's
code round follows the orchestrator's go. ChatGPT re-reads only if the orchestrator sends it (rule 9 was met at review
118).

## Addendum 5: efeb49b1 (routed by the orchestrator): PASS stands

Addendum 4 already passed 04a80222, which holds SF1, SF2, the Paper pad and stop (b). The orchestrator asked for
addendum 4; since it exists, this is addendum 5.

**What changed in RM1's files from 04a80222 to efeb49b1:** one Reason line in `real_test_pass`. The rest is main
merged in. The branch differs from main only in RM1's six documents, with no code.
- The floor fact now gives Rs 2,496 at n = 30 and m = 20: 1.7291 × 5,000 × √(1/30 + 1/20) = 2,495.7. I recomputed
  it, and it is correct.
- The n = 20 figure stays at Rs 2,734.

**Re-read at efeb49b1** (unchanged since addendum 4, all still MET):
- `real_test_pass` 3: Rs 1.50; more than 10% unknown legs is not met; at 10% or fewer they are left out and listed;
- `fill_honesty` (a) validity, binding, and (b) the noise-aware next-snapshot gap against the Rs 1 pad;
- Paper pad = research's Rs 1;
- stop (b) at Rs 2 per unit over 5 trades.

**Gates at efeb49b1:**
- pytest: 6086 passed;
- `ruff check`: clean;
- `ruff format --check`: 1120 files formatted;
- `check_imports`: clean.

**Merge:** against main now, only `reviews/claude/README.md` conflicts, on rows only; keep both sides.

**Verdict: PASS.**
