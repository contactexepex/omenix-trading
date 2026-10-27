# Judge 31: R1c the Drive session onto the shared layer, code (judge #2)

Branch `story/R1c-code`, SHA `1381a8eea6661a5c797df64e1e7fa8ee373c9b45`, lane 1. **FAIL** (round 1) on 1 should-fix,
tests only. The code matches the approved story: today's Drive loop is kept call for call, `Retry-After` is honoured as
a floor capped at 120 s, all five tries stay, and there is no Drive breaker. One required invariant test is missing: a
mutation to receipt repair's "no file in Drive" refusal survives the full suite.

## Gates (on the branch, `__pycache__` cleared)

| Gate | Result |
|---|---|
| `python -m pytest -q -n auto` | 511 passed |
| `ruff check fno tests tools ops` | clean |
| `python tools/check_imports.py` | clean |
| `python -m pytest -q tests/test_code_size.py` | passed |
| `python tools/check_numbers.py` (on `main`) | passed |

## Criteria

| Item | Verdict | Evidence (branch) |
|---|---|---|
| Same as today's Drive loop | MET (traced) | `drive_session.py` `request()`: one 401 re-sign inside the attempt, not counted; `accept` statuses returned; `ConnectionError`/`Timeout` and `TRANSIENT {429, 500, 502, 503, 504}` plus the rate-limited 403 retried; everything else raised with its reason, as before |
| Waits never shorter (jitter upward) | MET | `settings.py` `drive`: waits `(2, 8, 30, 60)`, jitter 0.25; `test_live_waits_lie_between_the_old_table_and_a_quarter_more` |
| `Retry-After` capped, five tries kept (my judge 29 S1) | MET | `_classify`: `retry_after=min(asked, DRIVE_RETRY_AFTER_CAP_SECONDS)` (120 s); tests at `test_drive_resilience.py:58,65,70,77` |
| No Drive breaker | MET | `settings.py` `drive` has none; `test_drive_settings_have_no_breaker_and_nothing_in_drive_code_builds_one` |
| No other Drive retry loop left | MET | `test_the_old_wait_table_is_gone_and_every_drive_call_goes_through_the_session` |
| Invariant tests: no row, receipt or index row without its file | MET except receipt repair | `test_drive_resilience.py:138-252,306-319`; see S1 |
| Shared library and NSE untouched in behaviour | MET | the only library code change is the `drive` entry in `settings.py`; `google_drive.py` only passes an optional policy through; no NSE file changed |

## Mutations planted (each restored, `__pycache__` cleared)

- **Drive session D1-D10, all caught:** D1 library `retry_after_ceiling` 600 -> 120 (a `Retry-After` of 300 would
  stop the call); D2 the 120 s cap removed (wait the full `Retry-After`); D3 the 401 re-sign without its resend; D4
  `accept` statuses not returned; D5 the rate-limited 403 made permanent; D6 jitter 0.25 -> 1.0; D7 a connection error
  made permanent; D8 a Drive breaker put back; D9 the last failed answer returned, not raised; D10 waits
  `(2, 8, 30, 60)` -> `(2, 8, 30, 30)`.
- **No record without its file, R1-R3 and R5 caught:** R1 the quotes sidecar's "not saved" check removed
  (`drive_only_store.py`); R2 a saved-but-missing raw quote returns `None` instead of raising; R3 `DataStore.put`
  writes the receipt before the Drive put; R5 the snapshot save skipped before its path is returned
  (`snapshot_files.py`).
- **R4 survives:** in `receipt_repair.py:37-38`, replacing `raise ReceiptRefused(NO_FILE...)` with returning a made-up
  `Receipt` (zero hash, size 0) leaves all 511 tests green.
- **Characterization tests:** the only change in `test_drive_behaviour.py` injects a zero-jitter policy (lower bound
  of the jitter); no assertion changed, so today's waits, tries and accept rules are still pinned.

## Findings

1. **S1 (should fix, tests only): receipt repair's "no file in Drive" refusal has no test.** `receipt_repair.py:36-40`
   is the one place that builds a receipt for a file it did not just write, so it is where "no receipt without its
   file" is most at risk. Only the read-back failure is tested (`test_drive_resilience.py:154`). Add a test that, for a
   path with no Drive file, `receipt_for` raises `ReceiptRefused` and no receipt is written; and the same for a path
   with two files (`SEVERAL`), which is also untested by my grep. Proof wanted: plant R4 above is caught.

No other finding. Round 2 needs only these tests; I will re-run the gates and plant R4 again.
