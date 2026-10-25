# Judge 478: O9b step 1b, the global cues to Drive (story/o9b-cues @ 44ef74ad)

Judge F. Round 1 of 2. Lane 1 (outside-service data, a workflow, FL1's report input). Labels: **strong**, **some**,
**reasoning only**.

## Verdict: FAIL (1 should fix, 1 minor). The data move itself is sound.

Gates on 44ef74ad: **9860 passed**, 16 xfailed; ruff, ruff format (1866) and `check_imports.py` are clean.

What is right:
- The public tables, the shared revisions log, `us_trading_dates` and the public checks are receipt-backed series,
  through A17's `RowLog` and the `Report` port.
- `global-cues.yml` commits the receipts, manifests and `behind_alerted.txt` only.
- `catch_up` adds only the rows after a whole-line start held in Drive; anything else is refused.
- `PartOutOfOrder` stops a part that would sort before a held one.
- The merge-day race step (no global-cues run queued; `move` before and after the merge) is in the plan.

## Should fix

**SF1. A Drive network failure ends FL1's whole report instead of giving the promised failed "Reasons' facts" view
[strong: a probe].**
- `CueRows` (`fno/forecast_lab/page/facts.py`) catches only `RuntimeError`. That covers missing settings,
  `DriveDataUnavailable` and `DriveSignInRefused`.
- A Drive read that fails at the network level raises `requests` errors (`ConnectionError`, `HTTPError`;
  `fno/storage/drive_session.py` re-raises them after its retries). These are `OSError`, not `RuntimeError`.
- My probe: `CueRows` over a table whose `rows()` raises `requests.ConnectionError` → the error **escapes**.
- The page builder calls `self.facts.facts(day)` unguarded (`builder.py` line 59), so the 08:50 or 20:05 edition
  is lost for a Drive outage, where the story says "a failed view, shown and alerted once".
- Before O9b these tables were repository files and could not fail this way, so this is new behaviour.

Fix expected:
- catch `(RuntimeError, OSError)`, or `requests.RequestException` too, in `CueRows`, naming the class only;
- a test: a table raising `requests.ConnectionError` gives the failed view, the rest of the page, and one alert.

## Minor

**The private cues stay on `DrivePartsRowLog`.** The step text states this and the A17 owner agreed, but the umbrella
text (line 84) still says the global cues move to the receipt-backed classes "one way, not two". Update that line,
and add the private cues' move as a named later step in section 3, so it is tracked.

Plants: the probe above. Mutations: the builder's 12 of 12 (read, not rerun, given SF1).

## Addendum 1: round 2 at a2f96e5f

**Verdict: PASS. Step 1b may merge** from Mon 26 Oct, outside 14:00-16:15 IST, only while `global-cues.yml` has no
queued or running run, with `global-cues move` run before and after the merge.

The delta from 44ef74ad is one code line, a parametrized test and the story text.

| Finding | Fix | Check | Result |
|---|---|---|---|
| SF1: a Drive network error ends FL1's report | `CueRows` catches `(RuntimeError, OSError)` and names the class only. The test covers `RuntimeError`, `requests.ConnectionError` and `requests.HTTPError`: one failed facts view, its system line, one alert, the other facts kept, no path in the line | Plant: back to `RuntimeError` alone: 2 of 3 cases fail. forecast_lab, global_cues and o9b: 345 passed. Ruff clean; the record scan clean (8018 files, the scan I skipped in round 1) | **Accepted** |
| Minor: "one way, not two" | Section 2 says step 1b moves the public cues only; step 1c (the private cues, with the A17 owner) is a named row in section 3 | read | **Accepted** |

Round 1's full suite (9,860 passed) stands for the unchanged code. The builder reports 9,862 on a2f96e5f.

## Addendum 2: the DRY1 delta (story/o9b-cues @ 61a0eee5; delta da66ae90..61a0eee5)

**Verdict: the PASS stands at 61a0eee5. It may merge under the stated steps** (no `global-cues` run queued, `move`
before and after, full gates).

- **g1, the merge of `main`:** `receipted_rows.py` holds both sides intact: judge 536's empty-series guard (`files()`
  returns `[]` before syncing an empty series) beside this step's `catch_up` and `PartOutOfOrder`. The other
  conflicts were additions on both sides.
- **g7, the new `data` test:** while a moved file is still in the repository, its bytes must be a whole-line start of
  the Drive table (`rebuilt().startswith(copy)`). That is the right direction: Drive may be ahead, never behind. The
  builder reports that it failed on 24 Oct, a real `move` caught up us10y, usdinr_rbi and us_trading_dates, and it
  then passed; the receipts are in the delta [as reported]. data-checks runs it daily and alerts.
- **Checks:** tests/o9b, global_cues, o9_store and forecast_lab: 409 passed. The builder reports the full suite at
  61a0eee5 as 14,784 passed.
