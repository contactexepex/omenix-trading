# Judge 106: story STR1, one- and two-leg structures (branch, before merge; judge C)

Date: 15 Oct 2026 (UTC). Branch `story/str1-structures` at **0ba5edcc35321d3e037fcdd0e7029303e881801e** (round 2; it
includes a merge of `main`). Claims: `reviews/claude/response_106_str1-structures.md`. Story:
`docs/stories/B-research-engine.md`, STR1. Lane 1. By quality rule 9 it goes to ChatGPT after this verdict.

## Verdict: PASS, no blocking and no should-fix findings; 6 minor findings and 3 notes

- **The first item, experiment 1, is MET by my own runs.** I laid STR1's engine files over a worktree of `0c1c957` and
  ran both periods. Discovery gives `814a79a5…` and challenge gives `4826897e…`, both equal to the published hashes. My
  own plant (condor offset 0.025) changes the hash, so the overlay was live.
- **No naked short leg gets through.** I planted naked shorts at B2, C2 and C4: B2 raises, C2 fails closed and C4
  refuses under all nine codes.
- **My hand arithmetic matches.**
  - Three maximum losses equal the app to the paisa (formula typed from `config.yaml`).
  - Seven A14 rows equal the app to the paisa. I computed them with my own parser on NSE's real 14 Oct SPAN file, and
    that parser reproduces judge 77's SF 100 row exactly.
- **20 of 20 of my own mutations are caught.**

## Gates (my runs, `python -B`, no bytecode cache, `FNO_SLACK_BOT_TOKEN` unset, at the exact SHA)

- Full suite: **3,344 passed** (435 s).
- `ruff check fno tests tools`: clean.
- `ruff format --check fno tests tools research`: 773 files formatted.
  - A bare `ruff format --check` with my ruff 0.16.8 flags one file:
    `reviews/chatgpt/review_2_…backtest-analysis….md`.
  - That file was last changed in dfc7e48 (12 Oct). It is not STR1's.
- `tools/check_imports.py`: clean (728 files).
- Trial merge with `origin/main` (c49f486): `git merge-tree` is clean. `main` has changed only documents since the
  branch's merge (decisions, judge 104, the log), so the tested tree is the merge's code.

## The orchestrator's six items

| # | Item | My evidence | Result |
|---|---|---|---|
| 1 | Both regressions | **(a) Overlay run.** Worktree of `0c1c957`; I copied STR1's `structures.py`, `one_side.py` and `cycle_costs.py` over it. `sha256sum -c` of FREEZE.md fails on exactly those 2 listed files; the other 43 are OK. I reset `research/ledger.csv` before each run. Results: discovery `814a79a56db4…3c98b`, challenge `4826897ed4d7…9b6`, both equal. **Plant:** `CONDOR_OFFSET` 0.025 gives discovery `005f5653…`. **(b) In the suite:** `test_structures_match_frozen.py` loads the frozen `structures.py` and `cycle_costs.py` with `git show 0c1c957:` (I read the loader; they are not copied). It compares legs, bounds and max loss on every 2019-26 cycle and asserts more than 1,000 comparisons; it passes in my suite run. **Weekly study:** it imports only `fno.costs`, which STR1 does not touch. | MET (strong evidence) |
| 2 | The new C4 anchor check | **Four-leg decisions unchanged:** `BodyWithWings` is the old `shape_problem` logic rewritten (I compared both line by line), and it ignores `atm`. Every existing C4, desk, timetable and decision test passes unchanged; the only test edits add an optional `spot=` to two fixture builders. **Real snapshot (14 Oct, 14:55):** meta spot 22,620.00, the same as D2's `Market.spot` (both read meta `spot`). D2's ATM and C4's re-derived ATM are both 22,600 on the Oct and Nov expiries. Every new code at widths 0-300 built by D2's structures on the real chain passes C4's shape. **Boundaries** (full C4 check, LC 300 on the fixture chain): spot 25,024.99 and 25,025.00 pass; 25,025.01 fails (ATM 25,050); 24,975.00 fails (tie goes to the lower, 24,950); 24,975.01 passes. **Empty:** no spot fails `shape` for all 5 codes I tried; no usable quote or another expiry gives no ATM (builder test). **Cannot refuse a valid D2 trade wrongly in the loose direction:** both sides use A4-valid mids. C4 also requires sizes on both sides and D2 requires an implied volatility, so they differ only in the fail-closed direction (builder's stated limit, accepted) | MET |
| 3 | Zero margin only for LC/LP, never a sold leg at 0 | C4 `stressed_per_lot` and C2 `_positive` allow 0 only for `STRUCTURES_BOUGHT_ONLY`. **My probes:** a 0 row for CDS, CCS, PDS or PCS fails C4's `margin_room` (4 of 4). A credit spread's legs labelled LC, with a 0 LC row, fail C4's `shape`. The LC/LP shape rule requires exactly one **bought** leg (my M19, which drops the side check, is caught). **Not closed in C2 alone:** C2 looks margins up by the code label, so a hand-built mislabelled proposal would get 0 there (minor 3). C4 is the gate: E3 fills only on a recorded C4 pass | MET |
| 4 | Strict config `structures` list | `IndependentCheck.from_margins_block`, my run: `'LC'`, `[]`, `['LC','XX']`, `None`, `['lc']`, `('LC',)`, `{'LC':1}`, `0` and `False` are all refused. `['LC','LC']` gives `{LC}`. No list gives SF, SC, BF; no block gives not passed. Plants: covers-all (M10) and a default covering all codes (M11) are both caught | MET (minor 2 on the design) |
| 5 | New-code trades refused until the owner's check lists them | The job writes only `covers()` rows and prints the rest. `margins.csv` has no new-code row, so C2's `MarginTable` raises (`_checked` fails closed) and C4 raises `MarginProblem`. My M10 and M11 are caught | MET |
| 6 | Samples: HISTORICAL, entry only, no P&L, no unregistered trial | `samples.py` reads only the last discovery cycle's **entry-day** closes (2026 panel). It prints the exit **date** only; no exit price is read or priced. Its numbers are structural (legs, bounds, max loss at entry). No ledger or `DATA_SPEND.md` change. The frozen-match test reads 2019-23 entry-day chains for an identity check of the old structures, not an outcome; that holdout is already used (experiment 1 ran) | MET |

## Per criterion

| # | Criterion | Builder's claim | My evidence | Result |
|---|---|---|---|---|
| 1 | Each code builds as scoped; None when unlisted; SF/SC/BF unchanged | 8 code-width pairs, tie, empty chain | **By hand on the real 14 Oct chain** (spot 22,620, ATM 22,600): LC 300 = buy 22,900 CE; LP 300 = buy 22,300 PE; CDS 200 = buy 22,600 CE, sell 22,800 CE; PCS 300 = sell 22,600 PE, buy 22,300 PE; all 20 code-width pairs as the scope says. My M15 (negative LC width allowed) and M5 are caught. SF/SC/BF: item 1 | MET |
| 2 | No naked short can be built; cost model refuses | 5 planted shapes | **My 6 shapes** (short call; short put; short call over a bought put; 1×2 call ratio; condor missing a wing; put spread plus an extra short put): B2's `Structure.legs` raises `NakedShortLeg` (6/6). C2's `MaxLossPerTrade` through `_checked` refuses "more … sold than bought" (5/5; my sixth plant repeats a contract, and C2 refuses it earlier). M5 and M18 are caught. **By algebra:** per-type count coverage (sold ≤ bought) bounds the loss for any strikes. A covered call's slope above the top strike is at least 0. A put's loss is bounded at index 0 anyway, and the count rule still refuses a naked put | MET |
| 3 | `payoff_bounds` for every shape | LC (0, ∞), LP (0, K), verticals | My hand values: LC (0, ∞); LP (0, 25,000); CCS 25,000/25,200 (−200, 0); PDS (0, 200); a covered call pair with inverted strikes (0, 200). M12 (no ∞) and M13 (level 0 dropped, so LP's top would read 0 and every LP would be "cannot win") are caught | MET |
| 4 | C4 shape per code; `bounded_loss` refuses every naked short | 9 wrong shapes, 5 naked | **My 6 naked shapes × 9 codes = 54 cases:** each fails both `bounded_loss` and `shape`. M6, M19 and M20 are caught | MET |
| 5 | C4's max loss equals B2's (Rs 1) | < Rs 0.01 on fixtures | Every correct one-side trade passes C4's `max_loss` (tolerance Rs 1) in my anchor probes. **My hand calculation, typed from `config.yaml` charges, on the 16 Sep 2026 sample:** PCS 200 Rs 9,088.78, CDS 200 Rs 7,895.26, LC 300 Rs 20,489.13, each equal to the app to the paisa (GST on brokerage, exchange, SEBI and IPFT) | MET |
| 6 | D1 codes; width 0 only for LC/LP | tests | M14 (width 0 for every code) caught; the suite's refusals of nan, inf, bool and −50 read | MET |
| 7 | D2 candidates, widest within cap first | tests | Read `CandidateBuilder`: unchanged logic over `build_tradable_structures()`; `(lowest < value < highest)` holds with ∞ for LC. The builder's 3 tests pass | MET |
| 8 | A14 rows; uncovered printed not written; 0 margin LC/LP only | hand fixture rows | **Real NSE file** `nsccl.20261014.i1.zip` (my download, SHA-256 `d85b883a…0e8b5b` = judge 77's), my own regex parser, no `fno` import. Nov 2026 series, index 22,721.95, ATM 22,700, (scan, NOV, exposure): SF 100 (822.25, −6,071.00, 59,077.07) equals judge 77; PCS 100 (3,563.30, −2,135.25, 29,538.53); CCS 100 (2,957.50, −3,935.75, 29,538.53); CDS 200 (7,939.75, 7,939.75, 29,538.53); PDS 300 (5,827.25, 5,827.25, 29,538.53); LC 0 (35,174.75, 35,174.75, 0); LP 300 (13,224.25, 13,224.25, 0). The app's `build_row_builder` on the same file gives **all 7 equal to the paisa**. M7, M8, M9, M10 and M17 are caught | MET |
| 9 | Four-leg results identical | overlay + frozen match + discovery | Item 1. `tests/research/test_experiment_1_frozen.py` passes. No existing assertion changed | MET |
| 10 | C4 refuses off-anchor or no spot | tests | Item 2. M1, M2, M3, M4 and M16 are caught | MET |

## My mutations (20, all caught; each restored, `git status` clean)

Runner: `tests/checks`, `risk`, `research_engine`, `playbook`, `nse_margins`, `desk`, `-x`.

| Plant | Result |
|---|---|
| M1 C4 ATM tie to the higher strike | caught |
| M2 C4 ATM counts unusable strikes | caught |
| M3 vertical anchor always passes | caught |
| M4 LC/LP anchor direction flipped | caught |
| M5 B2 coverage allows one naked leg | caught |
| M6 C4 `bounded_loss` allows one naked leg | caught |
| M7 C4 zero margin for every code | caught |
| M8 C2 zero margin for every code | caught |
| M9 C2 width 0 for every code | caught |
| M10 A14 writes uncovered rows | caught |
| M11 A14 default covers all codes | caught |
| M12 bounds without ∞ | caught |
| M13 bounds without level 0 | caught |
| M14 D1 width 0 for every code | caught |
| M15 B2 negative LC width | caught |
| M16 C4 evidence drops the spot | caught |
| M17 A14 no width-0 rows for LC/LP | caught |
| M18 cost model skips coverage | caught |
| M19 C4 LC side not checked | caught |
| M20 vertical width sign ignored | caught |

## Beyond the claims: E4 with one- and two-leg trades (the builder's "reasoning only")

My probe in `tests/desk`'s fixtures (not committed):
- PCS, CCS, LC and PDS orders **open** at the touch and **close** under a `TimeExit` at the next session.
- A PCS whose short put has no quote unwinds the bought put: "not_opened_partial_fill", legging cost Rs 88.96. Nothing
  stays open.

**Not run by me:** E7 expiry settlement and E5's exit review with one or two legs. No version can use the new codes
before the owner's broker check (item 5), so this is a follow-up, not a defect.

## Claims vs reality

| Claim | Reality |
|---|---|
| Overlay reproduces both hashes; offset plant changes it | Reproduced; my own plant also changes it |
| Frozen-match test loads the frozen files from git | True (read; `git show 0c1c957:`) |
| "All 17 mutations fail their test" | Not re-run; my independent 20 are all caught |
| C4 anchor uses the same meta spot as D2 | True on the real 14 Oct snapshot (22,620.00) |
| "LC/LP margin 0" | True at factor 1. With the owner's 1.45 on the real file, a long option's stressed margin is 0.45 × premium (minor 1) |
| Weekly study and G1 untouched | True: the study imports only `fno.costs`. The 43 G1 files were not checked by me one by one; the suite passes |
| §7 "mutation script … scratchpad, not committed" | It **is** committed at `research/2026-10-15-str1-samples/mutate.py` (minor 4) |
| E4/E5 leg-generic, reasoning only | E4 entry, unwind and time exit confirmed by my probe; E5/E7 not run |

## Findings (minor; none blocks)

1. **The stressed margin of a long option or debit spread is not 0 under the owner's 1.45 factor.**
   - On NSE's real file, a long option's scan equals its NOV (LC 0: 35,174.75 both). So
     `max(0, 1.45 × scan − NOV)` = 0.45 × premium: Rs 15,828.64 for the ATM call. The same 0.45 × debit is added on
     CDS and PDS, on top of their exposure.
   - No broker blocks that: a long position cannot lose more than its premium under any stress. So C2 and C4 are
     stricter than reality. That is the safe side, but it overstates funds tied up, which S2's "per rupee tied"
     benchmark will use.
   - `test_bought_only` uses scan 975 < NOV 7,800, which hides this.
   - Expected (follow-up, reasoning only): cap the stressed scan at the position's maximum terminal loss, at least for
     bought-only codes. Or state the over-reservation in the story.
2. **One `passed_on` covers every listed code.**
   - Adding a code later either back-dates its check to the first check's date, or moves the date for all codes.
   - A list naming only new codes stops SF/SC/BF rows (fail closed, surprising).
   - Expected: a date per code, or a stated rule for extending the list.
3. **C2 trusts the code label for its margin lookup.** A hand-built PCS labelled LC gets LC's 0 row in C2. C4's shape
   rule refuses it, and only D2's structures build proposals. This was already true for SF/SC/BF. Expected (later): C2
   asserts the label matches the legs, or the note stays that C4 is the only shape gate.
4. **Text:**
   - Response 106 §7 says the mutation script is not committed, but it is.
   - `samples.py`, a research script, imports test helpers (`tests.checks…`, `tests.playbook…`). Acceptable for a
     sample, but say so.
5. **`fno/composition.py` is at 312 of 350 lines.** The next story that adds to it should split it, as judge 43 said.
6. **E5 exit review and E7 settlement with one or two legs are untested.** Add one test each before any version uses a
   new code.

## Notes for the owner (strategist and risk manager; reasoning only)

- "ATM" is the strike nearest **spot**, as for the iron flies. On a later expiry the forward is higher: Nov's future was
  22,760 vs spot 22,620 on 14 Oct. A Nov CDS "ATM" call is then about 160 points in the money against the forward.
  That is consistent, but a strategy should know it.
- For LC/LP, "widest within the cap first" means the furthest out of the money, the cheapest. That is the opposite sense
  from spreads (the builder's flag).
- PCS sells the ATM put. Response 92's put spread sold about 3% below spot, which would be a new code.

## Project rules

- Files within 350 lines (the size test passes).
- New behaviour sits in new classes behind `Structure` and a new C4 `Shape` interface. Wiring is in the existing roots
  (`fno/composition.py`, `fno/checks/wiring.py`, `fno/nse_margins/wiring.py`, `fno/playbook/wiring.py`). Codes live in
  `fno/constants.py`.
- C4 restates CE/PE and ±1 locally to keep its independence from B2 (as before).
- No orders, secrets, Slack posts or ledger rows.

**Verdict: PASS for 0ba5edcc35321d3e037fcdd0e7029303e881801e.** Next, ChatGPT reviews it (quality rule 9). Then the merge
must be a merge commit with the full suite run on the merged tree, and I check `main` against this SHA and CI.

## Addendum 1 (15 Oct 2026): merge check, STR1 merged to `main` as abc23d3

**MET.**
- **Parents.** abc23d3's parents are 3707cf6 (`main`) and 0ba5edc (the passed tip).
- **Merge content.** My `git merge-tree --write-tree 3707cf6 0ba5edc` conflicts only in `reviews/claude/README.md`.
  abc23d3 differs from that tree only there: the conflict markers are removed and both sides' rows are kept.
- **Code unchanged.** `git diff 0ba5edc abc23d3` over `fno`, `tests`, `tools`, `config.yaml`, the STR1 sample folder
  and `docs/stories` is empty.
- **ChatGPT step done.** Rule 9's step was done before the merge: review 100 PARTIAL, accepted in response 114 as
  inactive infrastructure, with activation gates in story STR1b.
- **CI.** `checks` is green on abc23d3 (run 38668321325) and on db07101, 9b52507 and the commits after them.

**Note for STR1b and C5 (found while judging C5 addendum 1):**
- `config.yaml` maps none of STR1's six codes in `risk.profiles.books.bucket_sides`. Every new-code trade is
  therefore refused as "unmapped bucket": fail closed, consistent with inactive infrastructure.
- The owner's 1 B row gives the mapping for the four verticals. LC and LP have no owner mapping yet.
