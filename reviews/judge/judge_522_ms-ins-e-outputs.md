# Judge 522: MS-INS part e, the instructor's outputs

**Scope:** story/ms-ins-outputs at c23de177 (builder session_01LH7m9r5TCAKgZbeHVYkiTD), diff 5d9c6672..c23de177. Story
MS-market-school.md INS-e and "INS-e Claims". Lane 1, one judge. Round 1 of 2. Judge K
(session_019ZApRwkUiNMKDsf1k4W44z).

**Verdict: FAIL.** 3 should-fix, 1 minor.

## Criteria
| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Write-once store | MET | other-bytes and damaged-bytes plants caught; store lives under `school/instructor/` |
| 2 | Two runs, identical bytes; a written session returned as written | MET | `for_session` read-back plant caught |
| 3 | Public counts: codes only, record scan, write-once | MET | the corrections-excluded and rewrite plants caught |
| 4 | Why lines: privacy; a ticket has no rupees | MET | template and "(updated)" plants caught |
| 5 | Every denominator, refusals included; tickets never summed | MET | the ticket-sum plant caught |
| 6 | A planted cause in the review and the why line | MET | tests |
| 7 | Off: "school off", nothing written | MET | plant caught |
| 8 | Orphan corrections counted and alerted in the review and the day's output | PARTLY | finding 1 |
| - | Gates | MET | see Notes |

## Findings
1. **Should-fix: criterion 8 is half met, and its count over-reports.**
   - The day's output (`command._session` and `run_instructor_session`) never mentions orphans; only the review
     prints them.
   - In the review, `orphan_corrections(first)` counts a correction sealed inside the window whose original was
     sealed before `first` as "naming no outcome". `test_corrections.py:92` pins that ("its original was sealed
     before the origin: not found"). That is a false alarm on every review whose window starts after an original.
   - Expected: the day's run lists or alerts orphans. An orphan is a correction whose `corrects` matches no outcome
     on file at all (search from the first counted session, or the start of the record), not one outside the window.
     Test both.
2. **Should-fix: a corrected outcome is re-attributed and re-classified only by accident.**
   - `_rechecks` reruns only classifications still `waiting` (cause 11 or the modifier), and attributions are never
     rewritten.
   - My run on the branch's fakes: a trade written with net -140, then a correction sealed later with net -230.
     The later session's run produced a new classification at -230, only because the first one was still waiting.
     The stored attribution stays at -140 while the reader returns -230.
   - Once the controls have closed (modifier set) and cause 11 is testable, a correction is never picked up. The
     review then shows attribution sums and causes from the old net beside rupees from the new one.
   - Expected: a re-check also triggers when a classified position's latest outcome differs from the one it was
     classified on (e.g. by the outcome record's SHA-256 or net). It writes a correction for the attribution as well
     as the classification. Test it with a non-waiting classification.
3. **Should-fix: six branches can be broken with every instructor test green:**
   - `run.py:31`, the modifier half of `waiting`;
   - `run.py:87`, the "unchanged" guard. Without it every waiting record is re-written as a new correction every
     session;
   - `controls.py:20`, RC1 among the controls (the modifier needs both);
   - `comparison.py:69`, h's counting verdict. Removing it pairs uncounted decisions, so the frozen card's gate is
     untested here;
   - `comparison.py:45`, a damaged decisions file listed as unsealed;
   - `review.py:122`, the maximum drawdown formula.
   - Expected: one test each.

**Minor:** `review.driver_summary` sums account rupees itself, filtering tickets. MS-P1f made
`tickets.rupees.account_net` "the only rupee sum; every report sums through here". Use it (DRY).

## Plants
19 planted, 13 caught; the six survivors are finding 3.

## Notes
- **Gates (my run, python3 after routine setup):** ruff check and format, check_imports and check_records are clean.
  pytest -n auto: 14,081 passed, 16 xfailed on the second run. The first run had 1 failure,
  `tests/school/execution/test_settlement.py::test_each_index_settles_at_intrinsic_against_its_own_price[BANKNIFTY]`
  (two settlement files gave different SHA-256s). It passes alone and passed on the rerun. It is part d's test,
  outside this diff, and intermittent under -n auto: worth a look by d's owner.
- The known limits (no unfilled set and no three counts until MS-P1j's sources, cause 13 waiting for the replay) are
  stated and printed ("three counts not supplied").

## Addendum 1: round 2 at 136f5890

**Verdict: PASS.** Lane 1, one judge. Scope: c23de177..136f5890.

| Round-1 finding | Result | My evidence |
|---|---|---|
| SF1 orphans | ACCEPTED | `orphan_corrections()` scans from `RECORD_START` (22 Oct 2026) to today, so a pre-window original is no longer an orphan. Every day run carries `SessionResult.orphans`, and the command prints the alert line. Plants caught: the scan limited to today, the day's alert line removed |
| SF2 corrected outcomes | ACCEPTED | Attributions and classifications carry `outcome_sha256`. The re-check runs on a changed outcome SHA-256 or a waiting record, and writes a new attribution naming the old one. Plants caught: the corrected test off, the attribution correction off, its `corrects` emptied |
| SF3 six branches | ACCEPTED | my six round-1 survivors are all caught now (`test_round2.py`) |
| Minor: rupees | ACCEPTED | `net_rs` from `account_net` |

- **Plants:** 24 planted (my 19 from round 1 plus 5 on the new code), 24 caught.
- **Note:** `PathReader` now caches each file for its own lifetime. That is right for one run, and the wiring builds a
  reader per run (`build_instructor_run`). A reader kept across sessions would not see later seals, so keep it per
  run.
- **Gates (my run):** pytest -n auto 14,090 passed, 16 xfailed. ruff check and format, check_imports and
  check_records are clean.
