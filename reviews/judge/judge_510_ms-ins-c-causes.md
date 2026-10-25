# Judge 510: MS-INS part c, the 13 root causes

**Scope:** story/ms-ins-causes at f78b9e55 (builder session_01LH7m9r5TCAKgZbeHVYkiTD), diff e1fdbca0..f78b9e55. Story
MS-market-school.md INS-c, "INS-c Claims", `research/school/INSTRUCTOR_V1.md`. Lane 1, one judge. Round 1 of 2.
Judge K (session_019ZApRwkUiNMKDsf1k4W44z).

**Verdict: FAIL.** 1 should-fix, 1 minor. The rules match the story's table, precedence and modifiers as written, and
"not testable" is never guessed. Eight branches that acceptance criteria 1-4 name can be broken with every test
green.

## Criteria
| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | One plant per tag gives it as primary | PARTLY | 13 fixtures; cause 10's impossible-price route is not isolated (finding 1) |
| 2 | At and just beyond each threshold | PARTLY | 1.645 (cause 1), 2, 40%, 1.25x, 1x, 1 sd and 3 of 4 are pinned (plants caught). Cause 2's 1.645 and the 20% directional boundary are not |
| 3 | Winner forms; 6 and 9 never on a winner | PARTLY | 6 and 9 are refused, by the rules and by `Classification`. Cause 5's winner short-premium condition is untested |
| 4 | Precedence | PARTLY | the head order and the 2-5 ranking are caught; the 9-before-12 tail is not |
| 5 | `unclassified` when nothing fires | MET | test |
| 6 | Cause 11's later record names the first | MET | `corrects` passes through to `Classification`; e writes it |
| 7 | Modifiers and "not testable" | MET | hard-road `or` and bad-driver `or` plants caught; `not_testable` emptied: caught |
| 8 | Thresholds file = card | MET | `SHOCK_Z` 2.5 plant caught by the card test |
| 9 | Empty | MET | test |
| - | None = not testable, never guessed | MET | cause 13 by `NotYetReplayable`; cause 8 below 3 measurable; cause 11 until settlement (`SETTLEMENT_NEEDED` gives None, plant to 0.0 caught) |
| - | Cause 6's stop basis | MET | `multiple x abs(entry.cash)` is e's own `basis = abs(position.entry_net)` (`drivers/exits.py:52`) |
| - | Real wiring | MET | `build_classifier()` runs: CS1 stop 2.0, WS1 1.5, others none |
| - | Gates | MET | see Notes |

## Findings
1. **Should-fix: 8 rule branches can be broken with all 161 instructor tests green** (my plants; criteria 1-4
   above). Each one changes a cause on some real path:
   - cause 2's `|z| <= 1.645` made `<` (`rules.py:60`);
   - the winner form of cause 5 without "short premium" (`rules.py:74`), which gives "decay earned" to a debit;
   - cause 11's winner limited to a target exit (`rules.py:95`), dropped;
   - the tail order 9 before 12 swapped (`classify.py:13`);
   - the directional boundary `>=` made `>` (`terms.py:55`);
   - the noise band's lognormal drift term dropped (`terms.py:76`). This moves the band's mean, so cause 12;
   - the ATM strike taken as the lowest strike (`terms.py:30`). This changes `sigma_atm`, so `z` and causes 1, 2, 7
     and 8;
   - the impossible-price half of cause 10 removed (`evidence.py:152`). `test_evidence.py:92` changes the bid and
     ask, so the fill is also off the touch and the other half catches it.
   - Expected: one test per branch that fails when it is broken. The Claims' "28 of 28" did not include these.

**Minor:** the 1.645 boundary in cause 2 and the 20% directional boundary are both listed in criterion 2. Say so in
the Claims table once they are tested.

## Plants
38 planted, 30 caught. Survivors: the eight in finding 1.

## Notes
- **Gates (my run, python3 after routine setup):** pytest -n auto 11,937 passed, 16 xfailed. ruff check and format,
  check_imports and check_records are clean. The largest c file is `test_rules.py` at 184 lines.
- **b's files touched by c:** `POOR_FIT_*` moved to `thresholds.py`, and `signed_units`/`forward_of` extracted. b's
  tests still pass, and the values are pinned by the card test.
- **Readings I checked against the card:**
  - cause 11 held to expiry;
  - cause 12 before costs;
  - cause 8 on an expiry alive over the window, with clock time between captures;
  - cause 13 not testable in v1.

  Each is stated in `INSTRUCTOR_V1.md` and matches the code.

## Addendum 1: round 2 at ffd76737

**Verdict: PASS.** Lane 1, one judge. Scope: the single commit f78b9e55..ffd76737, which adds tests and Claims
only; no code changed.

| Round-1 finding | Result | My evidence |
|---|---|---|
| SF1 eight untested branches | ACCEPTED | `test_branches.py` has one test per branch. I re-ran my whole round-1 plant set: 38 of 38 caught (none survive) |
| Minor: the boundaries named | ACCEPTED | both are in the round-2 Claims table |

- The directional test uses a share of 0.25 so that the boundary is exact in floating point. That is a fair way to
  pin `>=`. The production share (0.20) is still pinned to the card by `test_card.py`.
- **Gates (my run):** pytest -n auto 11,948 passed, 16 xfailed. ruff check and format, check_imports and
  check_records are clean.
