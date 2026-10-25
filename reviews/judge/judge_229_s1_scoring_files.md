# Judge 229: S1 item 15, the scoring files in `frozen_files` (judge A, lane 1, before S1's freeze)

**Checked:** `story/s1-scoring-files` at `1ca9fe801d86e2e4920d9686da0c155c2521a435` (the R2/G7 builder). The diff is
2 files:
- `research/evaluation/PROTOCOL.md` `frozen_files` gains a "Scoring files" bullet with 25 `fno/scoreboard` modules;
- a new `tests/evaluation/test_scoring_files_frozen.py`.

The orchestrator asked whether the builder's known limit is acceptable before a freeze: scoring's dependencies in
`fno/desk`, `fno/risk` and `fno/accounting` are left unhashed.

**Verdict: FAIL, 1 should-fix, no blocking.** The list and its test are correct for `fno/scoreboard`. But the limit
is not acceptable as it stands, because scoring recomputes figures at score time with unhashed code.

## What is right

- All 25 modules of `fno/scoreboard` except `__init__.py` and `cli.py` are listed by path. This is needed, because
  `frozen_targets` hashes only the backticked paths.
- The test fails when a scoreboard module is added and not listed (the planted removal of `t_check.py` in its third
  test). It also fails when a listed path is not a file.
- Nothing else in S1 changes. The Status stays "decided by the owner on 2026-10-14", which is right, because the item's
  own rule adds "the scoring code of S2, S3 and S6 … before the freeze".
- On the trial merge with main (judge 227's freezer lines and this bullet merge cleanly),
  `python -m fno evaluation check` prints S1 and the gate complete.

## Should-fix

**SF1. Scoring calls unhashed code that computes the scored figures, so an edit after the freeze changes every
counted score while `verify` stays silent.**
- **Evidence:**
  - `fno/scoreboard/standard_unit.py`, S3's standard unit, which is the score's denominator and is shared with F9,
    calls `price_leg` from `fno/desk/pricing.py` (lines 54 and 71), `SettlementPrices` from `fno/desk/settlement.py`
    and `HeldMaxLoss` from `fno/risk/open_risk.py`, at score time.
  - `random_control.py` calls `price_leg` and `HeldMaxLoss`.
  - `book_trades.py` uses `trade_line` from `fno/accounting/ledgers.py`, which charges with `fno/costs.py`.
  - `sources.py` uses `snapshot_marks` from `fno/scorecard/scorecard.py`.
  - `HeldMaxLoss` in turn rests on `risk/trade_costs.py`, `risk/buckets.py`, `risk/inputs.py`,
    `research_engine/cycle_costs.py` and `research_engine/structures.py`.
  - None of these is in `frozen_files`. Only their settings are: `config.yaml:risk` and `:charges`.
- **Path in normal running:** the risk code changes often (C2, C5, and the C2c whole-margin and C2d stress-factor
  rounds of the last two days). A change to how `HeldMaxLoss` computes a held position's maximum loss after S1's
  freeze would change S3's standard unit, and so every book's matched score, for decisions already counted. The
  freeze's hashes would not move, and `verify` would report "unchanged". That is exactly what the owner's option A
  forbids: "code written after decisions are seen could be shaped by them, so the code is hashed with its rules before
  anything is counted".
- **Why "the owner's rule names S2, S3 and S6's scoring code" does not settle it:** these functions are S3's scoring
  computation. `standard_unit.py` only calls them. A literal reading by package leaves the arithmetic out.
- **Cost, said plainly:** hashing them couples S1 to desk and risk code. Any later edit to those files after the
  freeze then needs a new S1 version, by the item's own rule. That is the price of principle 4, but it is a real
  trade-off. The full import closure of `fno/scoreboard` is about 170 modules, which is far too broad to hash.
- **Expected fix** (one of two; the owner's call, through the orchestrator):
  1. **Recommended (reasoning only).** Add the score-time computation modules to the bullet: `fno/desk/pricing.py`,
     `fno/desk/settlement.py`, `fno/risk/open_risk.py`, `fno/risk/trade_costs.py`, `fno/risk/buckets.py`,
     `fno/risk/inputs.py`, `fno/research_engine/cycle_costs.py`, `fno/research_engine/structures.py`,
     `fno/accounting/ledgers.py`, `fno/costs.py` and `fno/scorecard/scorecard.py`. Then extend the test: every
     `fno` module that `fno/scoreboard` imports a function or class from is either listed or in an explicit
     exemption set with a one-line reason. Data shapes and readers (`desk/records`, `desk/snapshot`, `books/versions`,
     storage) can be exempted.
  2. **Or** the owner accepts the limit in a DESK_DECISIONS row that names the unhashed modules and what they can
     change, and the limit is written into the `frozen_files` Reason, not left in a message. As built, the limit is
     recorded nowhere in the repository: the commit touches only the bullet and the test.

## Gates

- On the trial merge with origin/main fb86612c (tree 430a2c0, clean), `-n auto`: pytest 6924 passed.
- `ruff check` is clean, `ruff format --check` shows 1226 files formatted, and `check_imports` is clean.

**A re-check needs the extended bullet and test (option 1), or the owner's row and the Reason line (option 2).**

## Addendum 1: e70dcf13 (the owner chose option 1, row 07f62385): FAIL (2 should-fix, both about exemptions)

**Checked:** `story/s1-scoring-files` at `e70dcf13bc6f7b9eb13aa6be53008a91a38e7812` (main merged in). The diff since
1ca9fe80, in S1, is the new "Score-time computation" bullet (14 modules and the cost) and the new
`tests/evaluation/test_scoring_closure.py`.

**What is right:**
- The owner's row (16 Oct, "Hash the ~11 modules (Recommended)") is on main.
- My 11 modules are listed, plus `books/equity.py`, `scorecard/execution_costs.py` and `scorecard/touches.py`, which
  the import walk found.
- The cost is written into the bullet: "after the freeze, any edit to one of these files needs a new S1 version".
- The closure test walks imports from the scoring modules through every hashed module. A stale-exemption test and a
  planted removal (`desk/pricing.py`) are included. My plant (`fno/costs.py` dropped from the list) fails 2 tests.
- The wiring exemptions are right: composition roots, and `config.py`, whose scoring sections are hashed as config.
- Most of the data shapes and readers are right too: names, record shapes and readers of committed rows, such as
  the decision store, journal records, versions and the calendar.

**The two calls asked:**

**SF1. (a) Three "readers" are rejected: `fno/fo_bhavcopy.py`, `fno/market_read_models/nse_files.py` and
`fno/desk/snapshot.py` decide which numbers are scored.**
- **Evidence:**
  - `fo_bhavcopy.py` maps NSE's columns to fields, for example `"SttlmPric": "SETTLE_PR"` and `ClsPric` to `CLOSE`
    (lines 23 and 36). `desk/settlement.py` (hashed) reads settlement prices through `read_fo_file`, and those prices
    enter S3's standard unit.
  - `nse_files.py`'s `read_index_figures` gives the index closes behind S6's do-nothing benchmark (`sources.py:18`).
  - `desk/snapshot.py`'s `quote_from_row`, `_number` and `touch()` turn a snapshot row into the bid and ask that
    `price_leg` (hashed) prices at.
- **Why the SHA-256 pin does not cover it:** the archive pins the input bytes, not which column the code takes or
  how it parses it. A post-freeze edit, such as reading `ClsPric` where it read `SttlmPric`, or a changed
  number-parsing rule, changes the figures. The bytes would still match and `verify` would stay silent. That is the
  path judge 229 SF1 closed for `price_leg`.
- **Fix:** move these three from `EXEMPT` to the hashed bullet. The owner's accepted cost already covers desk code.
  The parsers change rarely, but when one does, a new S1 version is the honest consequence.

**SF2. (b) Rejected: `fno/constants.py` is not "names only" for scoring.**
- **Evidence:** walking the hashed modules' imports from `constants`, two are numbers that decide a verdict:
  `PAPER_GATE_MONTHS = 3` and `UNPROVEN_BELOW_COMPLETED_TRADES = 20`, which `fno/scorecard/review.py` (hashed since
  14 Oct) passes into the review rule (lines 25, 29 and 49). Everything else imported is strings, tuples or enums.
- **Path:** an edit of either number after the freeze changes S1's paper gate outcome while `verify` reports
  "unchanged".
- **Fix (the simplest that keeps `constants.py` unhashed, since hashing a file every story edits would force a new S1
  version weekly):**
  - add a test that pins each numeric constant reached from a hashed module to the frozen `PROTOCOL.md` text, for
    example `paper_gate`'s "3 full calendar months and 20 completed positions";
  - extend the closure test so that any numeric (int or float) constant imported by a hashed module must be in that
    pinned set;
  - reword the exemption to "names, plus the pinned numbers in `<test>`".
  - Moving the two numbers into a hashed module also works.

**Note (no fix):** `books/account.py` (exempt as a reader) computes `capital()`, the opening plus top-ups, and
`scoreboard/reconcile.py` uses it. It is a sum of committed rows, used for the reconciliation check, not a scored
figure. That exemption is acceptable.

**Gates:**
- On the trial merge with origin/main d8670cd5 (tree 5eadc5c, clean), `-n auto`: pytest 6937 passed.
- `ruff check` is clean, `ruff format --check` shows 1227 files formatted, and `check_imports` is clean.

**A re-check needs only the three moved modules and the pinned-constants test.**

## Addendum 2: revision 2 at c3e0187d: PASS

The delta e70dcf13..c3e0187d in S1 is the Score-time bullet (three parsers added), `test_scoring_closure.py`'s
exemption lists and a new `tests/evaluation/test_frozen_numbers.py`. The other files are main merged in, item 13
among them.

- **SF1 (the parsers): MET.**
  - `fno/fo_bhavcopy.py`, `fno/market_read_models/nse_files.py` and `fno/desk/snapshot.py` are now hashed, each named
    for what it decides: the settlement columns, the index closes, and the bid and ask touch.
  - They are removed from `EXEMPT`, so the stale-exemption test stays honest.
  - My plant (`fo_bhavcopy.py` dropped from the bullet) fails 2 closure tests.
- **The new exemption, `fno/quotes/recorder.py` as a reader: accepted.** `desk/snapshot.py:21` imports only
  `DATASET` (`"groww/derivatives/quote-snapshots"`) and `QuoteSnapshotRecorder`, for its static `path()`, a file path.
  Neither decides a number.
- **SF2 (`constants.py`): MET.**
  - `test_frozen_numbers.py` walks every hashed module's imports from `fno.constants`. Any int or float imported must
    be in `PINNED`.
  - Each pinned value must appear in the frozen text: `paper_gate`'s "at least 3 full calendar months" and "at least
    20 completed positions" (`PROTOCOL.md:159`).
  - My plant (`PAPER_GATE_MONTHS = 4`) fails 1 test.
  - Leaving `constants.py` unhashed is now safe for scoring.
- **Note (no fix):** the walk sees `from … constants import NAME` only. An `import fno.constants as c` with an
  attribute read would slip past it. No hashed module does that today. Item 8 and 11's return, with its closure walk
  starting at `fno/role_value`, is the moment to keep that pattern out.

**Gates:**
- On the trial merge with origin/main 0f4fe9c3 (tree 6179336, clean), `-n auto`: pytest 6958 passed.
- `ruff check` is clean, `ruff format --check` shows 1234 files formatted, and `check_imports` is clean.
- `evaluation check` prints S1 and the gate complete.

**Verdict: PASS.**

## Addendum 3: B0's `fno/playbook/measurement.py` against item 15's closure test (judge A, the test's judge)

Asked by the R3 builder on the orchestrator's instruction, for `story/r3-b0-registration` at 89fcbbd5 (main merged
in; judge G passed B0's code in judge 233 addendum 1). This judges only the closure-test decision.

**Ruling: the exemption in `DATA_SHAPES` is accepted.**
- **What the module is:** `measurement.py` is one predicate, `is_measurement(strategy)`, which tests whether
  `strategy.edge_family == "measurement"`. It computes no number.
- **Where scoring uses it:**
  - In hashed code, `scorecard/scorecard.py:85` uses it only to set `Scorecard.measurement`.
  - That flag is read in one place, `scorecard/report.py:32`, for the title's " (measurement)".
  - No hashed module reads it for a figure, count or threshold. My grep over `fno/scorecard`, `fno/scoreboard` and
    `fno/role_value` finds no other read.
- **The reason line says when this ends:** "hash it once Test B counts by it". R3 part B's criterion 12, which leaves
  measurement shadows out of Test B's count, must move `measurement.py` into `frozen_files`, through S1's text owner,
  in the same change. The closure test will not catch that by itself, because an exempt module stays exempt. That
  duty belongs to part B's judge.
- **Gates on the trial merge with origin/main 7df28078 (tree e24ca26, clean), `-n auto`:** pytest 6975 passed.
  `ruff check` and `check_imports` are clean.

**Note for the orchestrator (outside item 15, no fix asked of B0):** `fno/scorecard/pauses.py`, E6's pause rules,
is not in `frozen_files`. B0 changes how it treats a measurement version: a research-status measurement is "shadow
test, not paused". S1's `immediate_pauses` item states pause rules, and the code that applies them is unhashed, as
it was before B0. Whether `pauses.py` belongs in S1's hashed list is a question for S1's text owner before the freeze.
