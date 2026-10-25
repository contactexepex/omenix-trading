# Judge 306: the O11 end-to-end acceptance harness (story/o11-e2e-acceptance at 5fc86cce)

**Verdict: FAIL, 1 blocking finding (the suite is stale on today's `main`) and 2 minor. Lane 1.** The design is
sound and honest. The fix is the builder's own criterion 4: replace the strict xfails that have turned real with real
checks.

## Run myself
- **At 5fc86cce, alone:** `pytest tests/e2e_acceptance -rxX` gives 10 passed and 16 xfailed (strict), in 6.3 s.
- **At 5fc86cce merged with `origin/main`** (c03d353b, after O1, D3, D4 and D5 merged):
  - **collection error**: `test_expected_missing.py:11` imports `WaitsFor` from `fno.checks.validity_modes`, and that
    class no longer exists (D4 and D5 replaced it with `EnvelopeMode` and `ConstitutionMode`, `fno/checks/wiring.py:84-92`);
  - with that import stubbed, **5 strict xfails now pass**, so the suite fails as designed:
    - O1, twice: the routine steps, and the refused-step alert;
    - D4: Book 2's C4 mode;
    - D5: Book 3's C4 mode;
    - D3c: the override refusal.
  - The replay and failure modules pass on the merged tree: 10 passed.
- `ruff check` and `ruff format --check` on `tests/e2e_acceptance`: clean. Largest file 213 lines;
  `tests/test_code_size.py` passes. No skips.

## My break of a stage (quality rule 4)
I made C4 skip the listing check (`fno/checks/validity.py`: removed `self._listing(proposal)` from the results). Two
tests failed:
- `test_book1_chooses_a_trade_on_the_pack_that_passes_risk_and_every_c4_check`;
- `test_no_nse_file_blocks_the_trade_in_c4_with_its_failure_row_and_c3_alerts`.
Restored; `git status` clean.

## Inputs table against the files (strong evidence)
- **The 3 pm chain is real:** `real_day.py` reads `nifty_20261016_145500.csv`. Contract IDs are restated, with
  prices, sizes and times unchanged (`restated`).
- **Margins and stress factor are real:** the folder `research/data/margins` (`margins.csv`, `stress_factor.csv`,
  `stress/`) is copied.
- **Session calendar is real:** `build_session_calendar()` (`tests/checks/builders.py:16-19`).
- **Charges are real:** `config.yaml`'s (`tests/desk/builders.py:28`).
- **Synthetic or test only, and labelled so:** NSE's F&O file (`nse_file(...)`), the approved strategy
  (`book1_doc()`), and the live features.
- Nothing is called real that is not.

## Findings
**Blocking 1. The suite is stale on today's `main`.** Strong evidence (above). Before the merge, the builder must, on
the branch with `main` merged in:
1. Drop the `WaitsFor` import.
2. Turn the five passing xfails into real checks on the recorded day:
   - O1: run the day's steps through the merged daily run, and show a refused step alerted while the run goes on;
   - D4 and D5: Book 2's and Book 3's C4 modes refuse a trade outside the envelope or constitution;
   - D3: a record with `owner_override` is refused.
3. Show `pytest tests/e2e_acceptance` passing with 0 XPASS.

**Minor.**
1. The F8c xfail names a story under judge B's review. Keep it, but mark the owner in the reason so the next update
   goes to the right builder.
2. Plan finding 2 (NSE contract IDs parse as `OPTIDXNIFTY` in C5's bucket map): I did not reproduce it (reasoning only
   for me). Whoever builds the NSE fallback must re-check it.

## Addendum 1: 982cc6c6

**Verdict: FAIL, 1 blocking and 1 should-fix.** The rework is good:
- O1's steps run through O1's real `Alerted` and `ReviewsStep`;
- a new failure test proves that the routine's stored 14:33 start refuses both forecast steps every day (a real
  finding);
- the D4/D5 xfails became a check;
- new xfails track the owner's `live_from` dates, the 14:05 start, T1c and the card step.

**Blocking 1. The branch is 40 commits behind `main`, and the D3 xfail now passes there.** Run myself: 982cc6c6 merged
with `origin/main` gives `[XPASS(strict)] not built yet: D3 no override`, 1 failed, 11 passed, 15 xfailed. D3 merged
as e5906769. Merge `main`, turn that xfail into the real check (a record with `owner_override` is refused, on the
recorded day), and show 0 XPASS on the merged tree. The builder reported 7,691 passed on the branch alone; that does
not cover today's `main`.

**Should-fix 2. The D4/D5 check proves the wiring, not the behaviour.** Strong evidence (code read).
`test_books_2_and_3_trades_are_checked_against_the_envelope_and_the_constitution` asserts only
`isinstance(modes[BOOK2_HYBRID], EnvelopeMode)` and the same for `ConstitutionMode`. An `EnvelopeMode` that passed
every trade would still pass it. Criterion 2 asks each built stage to show its output.

Fix: on the recorded day's chain, send one Book 2 proposal outside the envelope and one Book 3 proposal with an
unregistered strategy through the real `build_trade_validator`, and assert both are blocked with D4's and D5's
reasons. That is two small cases on fixtures the suite already has.

## Addendum 2: 9601a13e (main merged)

**Verdict: PASS. It may merge (tests and the story text only); the merged tree is gated again at the merge.**

Run myself on 9601a13e merged with today's `origin/main` (local merge c151b041):
- `pytest tests/e2e_acceptance -rX`: 12 passed, 15 strict xfails, **0 XPASS**.
- Full suite: **7,724 passed, 15 xfailed** (217 s).
- `ruff check` and `ruff format --check` on `tests/e2e_acceptance`: clean. `check_imports` ok. `check_records`: clean
  (6,722 files). Files total 746 lines, each under 350.

Findings:
- **Blocking 1: closed.**
  - The `WaitsFor` import is gone.
  - O1's steps run in O1's `DailyRun` in `DAILY_RUN_STEPS` order (`test_replay_day.py:93`).
  - The refused-step and stored-14:33 cases are alerted, and the run goes on.
  - D3: a decision with `owner_override` fails the `book1` step with D3's message, is alerted, and gives no decision
    and no fill (`test_replay_failures.py:111`).
- **Should-fix 2: closed.** The day's real chosen trade is sent through C4 as a Book 2 and a Book 3 trade. It is
  refused with "envelope: no trade envelope for sc-a v1" and "constitution: no constitution file matches the
  registered D6 component" (`test_replay_day.py:129-146`). **My plant:** `EnvelopeMode.checks` returning `[]`
  (permit everything) fails that test. Restored. These refusals come from missing files, not from a breach of an
  existing envelope. That is the honest state today, because no envelope or constitution file exists. When F5 and F6
  land, their xfails become the in-envelope and out-of-envelope checks.
- Builder's other mutations (`ALWAYS_NULL` emptied, Book 2 mode set to `PlaybookMode`, O1's alert send dropped): their
  claims are consistent with the tests I read. I re-ran only the envelope plant.

## Addendum 3: bc6a9ec1 (plan and main merged)
Still PASS. On the tree merged with today's `main`: e2e 12 passed, **18 strict xfails, 0 XPASS**; ruff and format
clean. The three new xfails are for F5 and F6 (Book 2's and Book 3's orders and exits), F1t (model reporting) and
O10+A14 (a never-started job alerted as stale). They track the plan's new rows, so the not-implemented list stays
honest. The builder reported the full suite on this tree at 7,724 passed and 18 xfailed. My own full run at 9601a13e
(addendum 2) gave 7,724 passed and 15 xfailed; this head adds only xfail tests.
