# Judge 210: R3 code, part A: shadow accounts, own terms, isolation, Test B path (judge G)

- **Judged:** `story/r3-shadow-accounts` at `872f7f21` (code `84e4d230`; tests and claims added on top; builder
  session 0145TfSwzmpk6MBrH92f5h4G; claims `response_211_r3-code-part-a.md`).
- **Text:** judge 208 addendum 1 PASS; the owner chose build order A. Lane 1. 210 was the next free number on main.
- **Verdict: FAIL.** The code is correct, but three of its fixes are untested where they actually take effect: in the
  composition root and the tracker. My mutations there survive. One should-fix and 2 notes.

## What I checked

- **Gates:** ruff check, ruff format and `check_imports` are clean. Full suite with `-n auto`: **6,793 passed, 0 failed**.
- **The two old tests changed their call shape only.**
  - `tests/book1/test_commit_failure.py`: `lambda cfg` became `lambda cfg, files=None`.
  - `tests/desk/test_shadow_books.py`: `{}` became `lambda account: {}`, four times.
  - The assertions are identical, so no test is weakened.
- **Code read:**
  - `Book1.decide` opens `shadow_on(day)` versions before `inputs.day(day)`, which closes judge 208's crash path.
  - The opener is `start_shadow_books` with E2c's `files` from `cmd_book1`'s shared download.
  - `_chosen` keeps a record only when `(mode == shadow) == reader is a shadow`.
  - `opening_runs`, `opening_trades` and `recorded_terms` take `decider`.
  - `_parts` gives each shadow `recorded_terms(root, account, BOOK1_RULES)`.
  - Test B's R3 input points at `journal/shadow`.
  - E5b's one-decision rule (`decided_runs.py`) only finds runs, so a shadow record in the same run changes nothing.
  - Only `build_book1` constructs `Book1` in production, so the opener is always passed there.

## My mutations (each alone, then reverted)

I ran `tests/book1 tests/desk tests/budget tests/scoreboard tests/decisions`, deselecting one test that needs `.git`
in my copy.

**Caught:**

- the open call removed;
- shadows opened after the inputs are read;
- the mode check made shadow-only, so Book 1 would take shadow records again. The wrong-mode test catches this.

**Survived (finding 1):**

- in `_parts`, shadows given Book 1's terms (`shadow_terms = lambda account: terms`);
- in `build_book1`, the opener not passed, so production falls back to the default no-op `lambda strategies, day: []`;
- Test B's path dropped (`StopRuleInput(..., "R3")` without `SHADOW_ACCOUNTS`).

## Findings

### Should fix

1. **Three of the fixes are tested only below the place they take effect.**
   - `test_each_account_takes_only_its_own_records_and_terms` tests `recorded_terms(..., decider)`, but not that
     `_parts` passes it to the shadow books (criterion 2).
   - The order test replaces `decider.open_shadows` by hand, so nothing checks that `build_book1` wires
     `start_shadow_books` (criterion 1).
   - Nothing checks the tracker's R3 path (criterion 7).

   Each mutation brings back the defect R3 exists to fix:
   - the crash on the first registration (opener not wired);
   - the crash once a shadow holds a trade (Book 1's terms, `RiskInputError` at `book_view.py:37-39`);
   - Test B reading nothing.

   That happens on the real path in normal running. **Fix:** three small tests:
   - `_parts(root, market)` gives a shadow book holding only its own trade's terms, with one Book 1 trade and one
     shadow trade on disk;
   - `build_book1(cfg, root)` opens a registered research version's account on `decide` (no Drive: `files=None`);
   - the tracker's R3 input path is `journal/shadow`.

### Notes

1. **Criterion 9 for E6 and S2:** this rests on code reading, and is right for part A. Both read only
   `journal/book1_rules/account/`, which R3 never writes, and nothing fills a shadow yet. The with-and-without tests
   for E6's Book 1 section and S2's Book 1 board belong with part B (E8's fills), when a shadow fill first exists.
2. The S3 isolation test passes partly by construction: a shadow candidate is not in the common set, so
   `MatchedDays` never looks it up. It is still a useful guard.

## Addendum 1: `18486b05` after ChatGPT review 129 (judge G)

**Verdict: FAIL. Should-fix 1 still stands.** The code is unchanged from `84e4d230`. The new tests:

- a same-session run through Book 1's real D2, where Book 1's opening trades, exits, counts, run finder and account
  bytes are equal with and without a shadow;
- S2's Book 1 section equal with a shadow record present;
- a shadow with an open trade, which raises on terms that lack its trade and loads on its own terms.

These are good tests, but **none of them goes through the three places finding 1 named.** I re-planted the same
three mutations on `18486b05`, running `tests/book1 tests/desk tests/budget tests/scoreboard` (413 passed clean):

| Mutation | Result |
|---|---|
| `_parts`: `shadow_terms = lambda account: terms` (Book 1's terms to every shadow) | **survives** (413 passed) |
| `build_book1` without `opener`, so production falls back to the no-op default | **survives** |
| The tracker's R3 input without `SHADOW_ACCOUNTS` | **survives** |
| The mode check made shadow-only (control) | caught |

Why the new tests miss them:

- The D2-run test builds `Book1` through the test builder `tests/book1/builders.book1`, not through `build_book1`.
- The own-terms test builds `JournalShadowBooks` directly, not through `_parts`.
- No test reads `stop_rule_tracker.INPUTS`.

**Fix (unchanged from finding 1):** three small tests that call:

- `_parts(root, market)`;
- `build_book1(cfg, root, files=None).decide(...)` with a registered research version;
- the tracker's R3 input.

### The builder's three pushbacks

1. **No overlapping opportunity IDs: accepted.** An ID is `<name>-v<n>:<expiry>`, and one version has one status on a
   day: `approved_on` is paper, `shadow_on` is research. So a book record and a shadow record never share an ID in one
   run, and the `DecisionStore` overwrite cannot happen.
2. **Run documents cannot be byte-identical: accepted.** D2 records the shadow books in `inputs.json` for replay.
   Comparing which runs exist and where (the finder) is the right check of E5b's one-decision rule.
3. **E6 is checked through its only input, the account bytes: accepted.** E6's Book 1 section reads only
   `journal/book1_rules/account/`, and the test compares those bytes.

## Addendum 2: `b73fb49e` (judge G)

**Verdict: PASS.** I ran my mutations on `tests/book1 tests/desk tests/budget tests/scoreboard tests/decisions`,
which give 467 passed clean.

**Should-fix 1 is accepted.** The three wiring tests now go through the real places, and the three mutations I
re-planted each fail one test:

| Mutation | Test that catches it |
|---|---|
| `_parts` giving every shadow Book 1's terms | `test_book1_s_parts_give_each_shadow_book_its_own_trade_terms` |
| `build_book1` without the opener | `test_book1_as_the_app_builds_it_opens_a_registered_research_version_s_account`, which calls `build_book1(cfg, root)` with `files=None` |
| The tracker's R3 input without `SHADOW_ACCOUNTS` | `test_test_b_reads_resolved_shadow_trades_from_the_shadow_accounts_folder` |

**The decision-store change is correct and caught.**

- A shadow record is now written as `shadow_<id>.json`, so a book record and a shadow record of the same opportunity
  can never share a file.
- `DecisionStore.write` refuses a run with a same-file clash (`RecordClash`), and nothing is written.
- Replay names its fresh records the same way.
- Both of my mutations here fail a test: dropping the prefix, and not refusing a clash.

**Gates:** ruff check, ruff format and `check_imports` are clean. Full suite with `-n auto`: **6,800 passed, 0 failed**.

**Notes:**

1. `book1_orders.py:62` and `desk/recorded_c4.py:28` still look records up with `record_file(id)` and no mode. That is
   right for book orders. R3's part B (shadow orders through E8) must pass the mode when it reads a shadow's record.
2. Replaying an older stored run that holds unprefixed shadow records would now report a mismatch. No such run exists:
   no research version has been registered, and `journal/` holds no `"mode": "shadow"` record. So this is not live.
