# Judge 556: the DRY1 school fixes

**Scope:** story/ms-sim-dryrun-fixes at 2b90a22ad (code 9d778e84a; builder session_01W2JE3W9xYftEDWTysHkdVC). I judged
the diff from main at c9c3dba49; 9d778e84a adds only one lot test, and 2b90a22ad only Claims text. It covers:
- `school/cli.py`, `constants.py`, `fleet/quote_share.py`, `quality/{command,options}.py` and `roads/{catalogue,lots,ports}.py`;
- `simulator/practice/{render,report,runner}.py` and `simulator/source/catalogue.py`;
- the tests.

"SIM dry-run fixes" Claims. Lane 1. The orchestrator ruled one judge for all of it, the pilot files included. Round 1
of 2. Judge H (session_01KNkZVoWvXMkoihKrrXk5Xa).

**Verdict: FAIL**, with 1 should-fix. Findings 2-4 of DRY1 are fixed and tested. The new line for finding 1 can state
a falsehood.

## Checked
| DRY1 finding | Result | Evidence |
|---|---|---|
| P-e2 `capture-gate --through D` | MET | One `add_through` serves the gate and the school subcommand. Plant (`--through` ignored) caught. Nothing in `.github`, `tools`, `docs` or `CLAUDE.md` uses the old `-- --through` form (my grep) |
| P-e1 quote-share line | MET | The suffix shows only when N > 0, and a law refusal is not counted twice. Plants caught: double count, suffix always on. The 22 Oct replay is byte-identical apart from the FINNIFTY line (MS-P1j's owner, in the Claims) |
| P-e3 `lot_unavailable` against `lot_mismatch` | MET | `LotSource.lot` returns `DatedLot \| LotProblem`, and the only real implementer and the two test fakes follow it. Plants caught: mismatch reported as unavailable; the zero-lot check dropped; a fixed reason in the catalogue; the simulator's reason put back. 9d778e84a pins the order of the two checks; `tests/school/roads` 120 passed there |
| P-e4 "not enough sessions" line | **NOT MET** | Finding 1 |
| Gates | MET | At c9c3dba49, pytest -n 6 gave 14,790 passed, 1 skipped, 16 xfailed. ruff check/format and check_imports are clean |

## Finding
1. **Should-fix: the line prints "not enough sessions yet" with a count above the need.**
   - It is printed whenever any leg is insufficient, and N is the *best* bucket's count. A leg is insufficient when
     *its own* bucket has fewer than 30 sessions.
   - My render: a report with `best_bucket_sessions=35` and 3 of 10 legs insufficient prints:

     `not enough sessions yet: the best-quoted spread bucket has 35 of the 30 recorded sessions a bucket needs, so 3 of 10 legs read 'insufficient spread data'`

   - Today the best bucket has 7 sessions. Once it reaches 30, in about 23 sessions, the wing buckets will still be
     short and the line becomes false every run.
   - The tests can't see it: `thin_model` cuts every bucket to the same count. My plant changing `max` to `min` in the
     runner survived.
   - Expected, per the orchestrator: name the buckets still short (with their counts) and never show a count above
     the need. Add a test with unequal buckets, one at 30 or more and one below.

**Accepted from the Claims:** of the 2,350 legs in the real window, 716 are untraded and 549 impossible. That means 30
sessions would still not price most legs. It is a useful finding for the practice results, and a reason the line must
say only what waits on sessions.

## Plants
9 planted, 8 caught, 1 survived (finding 1).

## Addendum 1

**Round 2 of 2:** story/ms-sim-dryrun-fixes at 4364179cc. Since 2b90a22ad it changes only the sessions line:
`practice/{render,report,runner}.py`, `source/{coverage,snapshots}.py` and `test_runner.py`. **Verdict: PASS.** Lane 1.

**Gates (my run):** pytest -n 6: 14,792 passed, 1 skipped, 16 xfailed. ruff check/format and check_imports are clean.

**Should-fix 1: ACCEPTED.**
- A leg found insufficient now records its own bucket's sessions (`InsufficientSpreadData.sessions`, always under 30).
- The line names only those buckets: "K spread buckets are short ... (shortest A, longest B)". Each bucket line
  carries "S of 30 sessions".
- A bucket with 30 or more sessions is never named, so the "35 of the 30" line can't occur.
- The tests use unequal buckets (8, 12, 35).
- Plants caught: the runner's collection dropped, the source's record dropped, min and max swapped.

**Minor (new): the case of a leg with no bucket is untested.** `bucket_of` gives None for an expired contract or a
spot of zero or less. Two plants survived:
- `if not short` replaced by `if False`: with only such legs, `min(())` would raise and lose the report;
- the bucket count taken from all insufficient buckets.

In that mixed case the "so X of Y legs" count also includes the unbucketed legs, which aren't waiting on sessions.
This is rare, so add one test when this code is next touched.

**Plants:** 5 this round, 3 caught, 2 survived (the minor).

## Note after Addendum 1 (b56e2fdd7, tests only, not a round)

The builder added two tests on top of 4364179cc and moved the sessions tests to `test_not_enough_sessions.py`
(97 lines; `test_runner.py` is now 279). Both of my surviving plants (`if not short` replaced by `if False`, the bucket
count taken from all insufficient buckets) are now caught.
**The minor in Addendum 1 is closed.** Gates: 14,795 passed, 1 skipped, 16 xfailed. ruff check/format and
check_imports are clean. The PASS stands at b56e2fdd7.
