# Judge 158: story S6 text, scorecard measures (quality rule 1; judge E)

Date: 15 Oct 2026 (UTC). Branch `story/s6-scorecard-measures` at **ba61fe04006cf19565df5b5a37c85e918d0bc636**
(`docs/stories/S-scoreboards.md` S6 and S3 criterion 3, an `IMPLEMENTATION_PLAN` row, a `WORK_REGISTER` row).
Builder: R2/G7 session 0185gR5DmoDh2zBAvgRU4CEB. Judged against the owner's rows of 15 Oct (`docs/DESK_DECISIONS.md`
lines 162, 167-170), design v2 03 item 4 (lines 107-120) and 08:83, REPLAN's S2 row, responses 144 and 147, the
"keep the design simple" rule and the work register.

Gates at this SHA (text-only change): `ruff check` clean, `ruff format --check` clean (1,072 files),
`check_imports` clean; pytest 5,852 passed, 8 failed, 1 error, all needing old commits absent from this
shallow clone (`git show 0c1c957...` exit 128). The diff touches only `docs/`, so none can come from it.

## Verdict: FAIL (story text): 2 blocking (rule 2), 5 should fix, 4 minor

The design is mostly sound and its numbers check out. It fails on two owner requirements with no criterion and no
"out" line, plus one empty-section hole and two overlaps with other stories that happen in normal running.

## What I checked and found right

| Check | Status | Evidence (mine) |
|---|---|---|
| Trade measures, criterion 2 | MET | [9,000, -4,000, 1,000, 0]: closed net 6,000 - 9,000 = -3,000; PF 10,000 / 4,000 = 2.5, 2 winners, 1 loser; zero in neither. Strong (arithmetic) |
| Drawdown, criterion 3 | MET | Cumulative 1,000, -2,000, -1,500, -3,500, 500 from a high of 1,000 gives 4,500; worst day -3,000; `config.yaml:57` books' `drawdown_brake_rs: 120000`. Strong |
| t-check | MET | t(0.95,5) = 2.015 correct; the ratio linearisation z_b = (net_b - R·risk_b)/mean(risk) is the standard ratio-estimator variance, better than PROTOCOL.md:317-326's "block means' mean". Using the 30-df value above 30 is wider, so cautious. 39 sessions = 1 block = null. Strong |
| Index source | MET | `ind_close_all_12102026` (tests/fixtures/nse/revisions) has "Nifty 50" with Div Yield 1.53, "Nifty50 TR 1x Inverse", "Nifty50 TR 2x Leverage", "Nifty 50 Futures TR Index", and no NIFTY 50 TR row. `read_index_figures` reads "Div Yield" (`fno/market_read_models/nse_files.py:93-104`); manifest has files to 14 Oct 2026. Strong |
| Code references | MET | `daily_run.py:65-78` (exits only inside a run), `sections.section`, `_risk`'s `no_capital` and MARGIN_AT_ENTRY, `CommittedRuns` (decisions step per book, `run_id`), `price_leg` (`fno/desk/pricing.py:55`), `ExecutionSnapshotSource` (`fno/desk/snapshot.py:128`), `REQUIRED_ITEMS` (`protocol.py:27`), block 20 and seed 20261014 (`PROTOCOL.md:127`), option A (`PROTOCOL.md:306`), open question 2 closed by row 167. All exist as cited |
| Owner rows 167, 169, 170 | MET | t-check never changes `claim_allowed` (crit. 4, 9); PF null "no losing trade", counts printed (crit. 2); B as it ran, A observed with the 10% cap via S3 crit. 3 (G9's figure) |

## Answers to the orchestrator's questions

**(a) Extends S1 and S2?** Mostly yes: new modules under `fno/scoreboard/`, fields added to `section` and
`uncertainty`, existing ports reused, no new composition root. Two exceptions, should-fix 4 and 5 (E2c and E6).

**(b) No NIFTY 50 TRI: acceptable.** Price change plus trailing Div Yield/365 a day is close over a year (the trailing
yield is last year's paid dividends over price). Over one quarter the error is dividend timing (NIFTY dividends
bunch in Jun-Aug): a few tenths of a percent of capital either way, which could only flip a near-tie, and the gate is
already a labelled point comparison. Some evidence. If RM1 ever decides on a near-tie, niftyindices.com's daily TRI
history is the exact source and fits behind the same `IndexLevels` port (one adapter). Keep the approximation now.

**(c) Tax leans against the book: yes, for every tax item.** F&O at 31.2% (top slab plus cess), no loss carried
forward (Indian law allows 8 years for non-speculative business losses), the fund keeps its Rs 1.25 lakh exemption,
LTCG 13% = 12.5% plus cess (design 03:111 says 12.5%; adding cess matches 31.2% = 30% plus cess), cash at the repo
rate (above a liquid fund's net yield). All favour the benchmarks. Strong (tax rules) for direction, reasoning only
for size. One non-tax item leans **for** the book: see minor 2.

**(d) Random control: sound for what it claims** (selection luck, same dates), seeded, descriptive, outside Holm, and
it matches response 147 item 7. Its risk replay is the costliest part (per-run open twins over time for three caps).
Twins keep the trade's widths and lots, so their maximum loss differs from the real trade's only by the credit; the
only cap a flip really changes is the bucket (PCS to CCS changes side). Cut proposed in (f).

**(e) Drawdown and worst day: no other owner.** B4's `metrics.py` max drawdown is over backtest cycles; C-roles' "worst
day" is a stress scenario; C2/C5's brake is a rule on closed equity. S6 labels its figures "marked daily, not the
brake's closed equity". No duplicate (my grep of `docs/stories/`, `fno/scorecard/`, `fno/scoreboard/`).

**(f) What to cut (owner's simplicity rule):**
1. Random control risk replay: keep the per-trade maximum-loss cap and the bucket cap; drop the open-risk and new-risk
   replay with a Known-limits line. Removes per-run portfolio state for two caps a flip barely moves.
2. Order, not scope: no paper fill exists yet (E2c's text), so the random control has nothing to rank for months. Its
   definition must be in S1 now (response 144 red team 7); its code can be the last piece built, if the orchestrator
   wants a smaller first merge. Optional.
3. Drop the `strategies` block from scoreboard B if E6 carries the per-version gate value (should-fix 5).
Do not cut view (b) or cash: design 03:114-118 requires both.

## Findings

### Blocking (quality rule 2: a requirement in no criterion and no "out" line)

1. **Scoreboard A gets no do-nothing comparison or measures.** Owner row 168: "Do-nothing comparison **shown on
   every scoreboard**"; row 162: measures "added on the scoreboards". S6 adds them to S2 sections only and amends S3
   for the miss rule only. Fix: amend S3's text (as done for criterion 3) to carry `measures` and `do_nothing` per
   book, or list it as out with the owner's word. Strong (owner text).
2. **View (b), the whole account, has no acceptance criterion.** Design 03:116-118 requires it; S6 designs it (section
   4) but criteria 5-6 test view (a) only. Fix: a hand-calculated criterion for view (b) (idle cash credited at the
   after-tax cash rate; fund and cash on the whole Rs 20 lakh), with an empty and a boundary case. Strong.

### Should fix

3. **No gap list.** Rule 2 wants each requirement of the cited design paragraphs (03 item 4, 08:83, REPLAN's S2 row,
   rows 162/167-170, response 147 items 3-7) mapped to a criterion or "out, because". Other stories do this
   (A15 at `A-data-foundation.md:1131`, A16, A16b). Blocking 1 and 2 are what such a list catches. REPLAN's
   "independent bucket-weeks" is "out" with no reason and no owner: name who builds it.
4. **Empty sections give 0 ÷ 0 in view (a).** Criterion 9 puts `do_nothing` on every section, including
   "overridden" and "unscored". Today `RecordedOwnerOverride` is always false until F4 (`fno/scoreboard/sources.py`),
   so the overridden section is empty in normal running, and so is any section before its first trade. S6 defines
   null for missing index days and `no_capital`, not for zero capital-days. Fix: null with reason "no capital tied",
   plus a criterion. Strong.
5. **Overlap with E2c, not named.** E2c (text PASS, judge 148) moves scoreboard B to Drive and adds a shared Drive
   download wired through `fno/scoreboard/wiring.py`; S6 wires two new sources in the same file and still reads
   `journal/<book>/account/` as committed. Both are in the register but S6 never names E2c. Fix: S6 depends on E2c
   (built on its shared download and Drive board), and the register row says so. Strong (both texts).
6. **Second per-version view beside E6.** S6's `strategies` block groups trades by `<name>-v<n>` across books and holds
   RM1's `beats_index_after_tax`. E6 (`fno/scorecard/`, merged) is already the per-version scorecard with the
   "gate to any real-money discussion". Two places counting a version's trades can disagree (overridden, pilot,
   shadow). Fix: either put `do_nothing` on E6's per-version card and drop the block, or state why scoreboard B owns
   it and add a criterion that its trade IDs and closed net per version equal E6's. Some evidence.
7. **Boundary cases missing (rule 5).** Listed: just-under for t-check (39 sessions). Missing: exactly 40 sessions
   (two blocks, defined bound); random control at exactly 10% missing (computable) and just over; miss cap at exactly
   10% (S3 text says "over"). Cheap; add them.

### Minor

1. **Fund tax timing.** "Tax per financial year" with "12 months or more uses 13%" mixes a yearly tax with a holding
   period. State one rule (e.g. the fund is sold at the section's end, one exemption per financial year, losses
   untaxed). Either reading leans against the book.
2. **View (a) capital is entry capital only.** Margin is not re-marked when the exchange raises it, and C2's stress
   reserve is excluded, so capital-days are understated and the book's return per rupee is overstated. View (b)
   covers it; add a Known-limits line, since the "leans against the book" sentence covers tax only.
3. **Random control universe.** "Within 10 strike steps of the money" must contain the books' real strikes; if a book
   ever trades outside it, the real trade is not one of its own twins. One sentence: the real trade's strike must be in
   the window, else widen to include it.
4. **Row citations by line number** ("row 170") drift when rows are inserted; cite the bold titles too.

## Claims vs reality

| Builder claim | Check |
|---|---|
| "extends S1 and S2 and builds nothing beside them" | Partly: true within `fno/scoreboard/`; not true against E6 (should-fix 6) and silent on E2c (5) |
| "No new composition root" | True |
| "Each simplification leans against the book" (tax) | True for tax; one non-tax lean for the book (minor 2) |
| No TRI in `ind_close_all`, checked 14 Oct | True (12 Oct file, my read) |
| `read_index_figures` already reads Div Yield | True |
| S3 criterion 3 matches row 170 | True |
| Measures "on every scoreboard" | Not true: B only (blocking 1) |

## Project rules

Lane 1 (new story, scoring and the real-money gate). Register row updated in the first commit (true). Owner's
simplicity rule: see (f). Rule 9 applies at code time (the do-nothing comparison is a real-money gate input).

**Verdict: FAIL for ba61fe04006cf19565df5b5a37c85e918d0bc636** (story text). Fix blocking 1-2 and should-fix 3-7, then
re-judge; code waits.

---

## Addendum 1: re-judge at a18a6bed167fa916f9ae557abfda25f9dc8c6fca

Diff `ba61fe04..a18a6bed`: `docs/stories/S-scoreboards.md` (S6, S3), the register row, plus a merge of `main`. Gates:
ruff, format and `check_imports` clean. `tests/forecast/test_backfill.py` fails 2 of 3 here, identically on
`origin/main` and on `ba61fe04` in this container, so it is not from this branch (orchestrator to check it on main).

| Finding | Fix | Accepted? (my evidence) |
|---|---|---|
| B1 scoreboard A | S3 text: per book `measures` (rupees only, no brake on a shadow) and view (a), S3 criterion 5 "computed by S6's functions" | Accepted. No view (b) on A is right: A has no account, only one-lot positions |
| B2 view (b) | Criterion 6: real October days, Rs 20 lakh, two boundaries (no trade, all tied) | Accepted (minor 2 below) |
| S3 gap list | Table of 21 requirements to sections and criteria; bucket-weeks out, orchestrator assigns | Accepted; I traced each row to the text. One label slip (minor 1) |
| S4 0 ÷ 0 | Null "no capital tied"; criterion 7 with the overridden and pre-trade sections | Accepted |
| S5 E2c | "Built after E2c", adds its port to E2c's wiring; Depends lists E2c | Accepted |
| S6 E6 | Gate stays on board B per book and version; criterion 11 checks trade IDs and closed net equal E6's card | Accepted. The reason holds: E6 has no capital, index or daily series, and `fno/scorecard/review.py` is in S1's frozen list (`PROTOCOL.md:303`) |
| S7 boundaries | 40 sessions; exactly 10% and one over (random control); exactly 10% miss cap (S3 crit. 3) | Accepted |
| Minors 1-4 | One fund sale at the section end, one exemption, loss untaxed (crit. 8); capital-at-entry Known limit; strike window widened to the real strike (crit. 10); bold titles cited | Accepted |
| Cut (f) | Only per-trade and bucket caps replayed (Known limit); random control code built last | Accepted |

**BR1 "luck control":** no overlap today. BR1 is a register row only (design proposal first, no text in the repo);
its luck control belongs to cross-sectional prediction tests across underlyings, while S6's ranks a book's own closed
trades against direction and strike twins. Reasoning only. If BR1's proposal ever adds a random-trade control on
paper trades, it must reuse S6's.

### New minor notes (no re-judge needed)

1. The gap list says scoreboard A is covered by "criterion 4b"; it is S3 criterion 5.
2. Criterion 6's "no trade: view (b) equals the cash benchmark exactly" holds only with zero operating costs (the
   section's net subtracts them). Say "with zero operating costs" in the fixture.
3. Per book and version: a version traded by two books gives RM1 two `beats_index_after_tax` values. RM1 (out of
   scope) must say how it combines them; one line in RM1's text when it is written.

**Verdict: PASS for a18a6bed167fa916f9ae557abfda25f9dc8c6fca** (story text). Code may start, E2c first; rule 9
(ChatGPT after the judge) applies to the code, since the do-nothing view feeds the real-money gate.
