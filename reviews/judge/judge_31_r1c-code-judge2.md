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

## Addendum 1: the orchestrator's checks on 1381a8e (still FAIL, round 1; findings S2 and S3 added)

The orchestrator asked for more planted checks and a view on the one stated behaviour delta. These are all on
`1381a8e`; every file was restored and `__pycache__` cleared after each plant.

| Check | Result |
|---|---|
| Library `retry_after_ceiling` 600 -> 120 (X1) | caught (1 failed) |
| `RetryPolicy` and the NSE settings unchanged vs `main` | MET: `git diff origin/main 1381a8e -- fno/shared/` shows only the `drive` entry of `settings.py`; `retry.py` and `nse_pacer.py` are unchanged |
| Drive cap as ruled | MET: the classifier clamps to `DRIVE_RETRY_AFTER_CAP_SECONDS = 120.0`; the `drive` ceiling is 600 s; no `RetryPolicy` edit |
| 401 counted as a retry (X2) | caught (5 failed) |
| 401 re-signed on every attempt (X3) | caught (1 failed) |
| 409 not accepted (D4) | caught |
| Row before file, per writer | W1 manifest row first, W2 revision index row first, W3 global-cue log row first, W4 candle manifest row first, W5 filing manifest row first (put moved after `record`), W6 quote save error swallowed: **all caught**; the data store (R3) and snapshot (R5) as before |
| Reader-side sidecar tests | present: not saved -> `None` (`test_drive_resilience.py:306`), missing -> `RawQuoteMissing` (`:311`), hash mismatch -> `RawQuoteHashMismatch` (`:319`) |
| Drive characterization | MET: unchanged except the one zero-jitter policy injection (no assertion changed) |

**The 401 delta, my view: accept it, but it must be pinned (S2).** Today (`main`'s `drive_session.py`) the re-send
after a 401 sits outside the `try`, so a `ConnectionError` there propagates at once. In `1381a8e` it is inside the
attempt and is retried like every other dropped connection. I would not keep the old behaviour: it is an accident of
where the line sat, not a rule. Retrying a dropped connection is exactly what the loop does for every other send, and a
create is retried under its reserved ID, which the existing comment and the characterization test
`test_a_create_retried_after_a_dropped_connection_yields_exactly_one_file` show is safe. It makes more attempts, never
fewer. Reproduced on `1381a8e` with a scripted session (scratch script, not committed):
- 401, then `ConnectionError`, then 200: returns 200 after 3 sends and one wait of about 2 s (today it raises).
- 401, then 401: raises `HTTPError` after 2 sends with no wait. **It cannot spin:** `signed_in_again` is set once per
  `request()` call, not per attempt, so there is at most one re-sign per call (stricter than "once per attempt"), and a
  second 401 is classified OK and not in `accept`, so it is raised.
- A 401 on a later attempt, after the call's one re-sign, is raised. That is the same as today, which also re-signs
  once per call.

## Findings added

2. **S2 (should fix, tests only): the 401 delta has no test.** `git grep` finds no test that sends a 401 and then a
   `ConnectionError`. Add one: 401, `ConnectionError`, 200 returns 200 with sends = 3 and waits = [2]. Also add a
   test that a persistent 401 is raised after exactly 2 sends with no wait, so the no-spin rule is pinned.
3. **S3 (should fix, tests only): the writer's `RAW_FILE_SAVED = False` flag in the sidecar is untested.** Plant W6b
   (`recorder.py`: `meta[RAW_FILE_SAVED] = False` replaced by `pass`) leaves all 511 tests green.
   `test_quote_writer_marks_the_sidecar_not_saved_when_the_drive_save_fails` checks only `_save_quote_file`'s return
   value, never the sidecar that is written. Without the flag, the reader's "not saved -> `None`" branch can never be
   reached for that snapshot: the reader goes to Drive and raises `RawQuoteMissing`. The test the orchestrator listed
   (failed save -> no canonical marker) does not catch this either. Add a recorder-level test: a failed Drive save
   writes a sidecar with `RAW_FILE_SAVED` false, and reading that snapshot returns `None`.

S1 stands. All three are tests only, so they can go into the one superseding SHA, where my plants R4, W6b and the 401
delta plants carry forward.

## Addendum 2: round 2, 1381a8e code plus the 65a99c0 tests (FAIL, round 2; S2 fixed, S1 and S3 open)

Branch `story/R1c-code-r2`, SHA `65a99c0b421ee8f7caac15f6ef29b1d981114db1`. `git diff 1381a8e 65a99c0 --stat` shows
only `docs/stories/R1c-drive.md` and `tests/ingestion/test_drive_resilience.py`: the code is byte-identical. Gates
(`__pycache__` cleared): 514 passed; ruff, imports and code size clean.

| Plant on 65a99c0 | Result |
|---|---|
| X1 library ceiling 600 -> 120 | caught (1 failed) |
| X3 401 re-signed on every attempt | caught (2 failed: the new no-spin test plus the old one) |
| R4 receipt repair returns a made-up receipt when Drive has no file | **survives (514 passed)** |
| R4b receipt repair's several-files refusal removed | **survives (514 passed)** |
| W6b `meta[RAW_FILE_SAVED] = False` replaced by `pass` | **survives (514 passed)** |

The Addendum 1 results (the `RetryPolicy`/NSE guard, 401 counted, 409, row before file for every writer) apply
unchanged, because the code is identical.

- **S2: fixed.** `test_INTENTIONAL_DELTA_...` pins 401, then a dropped connection, then 200 returning 200 with waits
  `[2]`, and five drops after a 401 giving 6 sends. `test_the_401_re_sign_happens_at_most_once_per_call...` pins
  2 sign-ins and 2 sends for a persistent 401, and plant X3 now fails it. I agree the delta is acceptable: more
  attempts, never fewer, bounded by the same 5 tries, and safe for a create under its reserved ID.
- **S1: still open.** No test was added for receipt repair's no-file or several-files refusal (plants R4 and R4b).
- **S3: still open.** No test checks that a failed save writes `RAW_FILE_SAVED` false into the sidecar (plant W6b).
  The new compare test covers the reader. My view on judge #1's writer-side requirement, which is his call: reader
  tests plus reading the code are **not** enough. W6b shows that the one writer line producing the flag can be deleted
  with every test green. A recorder-level harness is not needed, though: the sidecar dict is built in one method, so a
  test can run that method, or `_save_quote_file` plus the meta build, with a store that raises. If the recorder
  cannot be driven at all, that is itself a testability finding.

S1 and S3 are tests only and small. This is my second round on the R1c code, so under the rules the orchestrator
decides the next step. I would PASS a SHA that adds these two tests and makes R4, R4b and W6b fail.

## Addendum 3: correction, the 900 s total cap is weaker than today (judge #1's finding, which I confirm)

My round-1 criterion "Same as today's Drive loop: MET (traced)" was wrong for long attempts. `retry.py:90`
(`if self.clock() - started + wait > self.settings.max_total_seconds`) counts the time spent inside each attempt, not
only the waits. Today's Drive loop (`main`'s `drive_session.py`) has no total limit and always makes 5 tries. On
`1381a8e`, with `Retry-After` capped at 120 s, four waits of 120 s plus four attempts of 105 s or more reach 900 s, and
the fifth try is never made. The tests use instant attempts, so they cannot show this. I traced the waits only and
missed it. The ruled fix (no total cap for Drive only; NSE untouched) is right.

Checks added for the next SHA: a long-attempt case (each attempt over 105 s on a fake clock) still makes 5 tries;
putting a 900 s total back for Drive makes a test fail; NSE's `max_total_seconds` and `RetryPolicy` are unchanged vs
`main`.

## Addendum 4: decisive round 2, c05a1d7 (PASS)

Branch `story/R1c-code-r2`, SHA `c05a1d7d022d7dd88770ff1287f47b9460367015`. It supersedes `1381a8e` and `65a99c0`
(the orchestrator's round count: this is code round 2). Compared with `1381a8e`, the only code change is the Drive
`max_total_seconds` set to `float("inf")` in `settings.py`; the rest is tests and the story text.

**Gates** (`__pycache__` cleared): 522 passed; ruff check and ruff format clean; imports clean; code size passed.

**The cross-source guard:** in `git diff origin/main c05a1d7 -- fno/shared` only the `drive` entry of `settings.py`
changed. `retry.py`, `nse_pacer.py` and NSE's settings (including its `max_total_seconds`) are unchanged.
`retry.py:90` compares against `inf`, so a Drive call is never cut on total time: always five tries, as today.

**Plants on c05a1d7, all 22 caught** (each restored, `__pycache__` cleared):

| Plant | Failed |
|---|---|
| T1 the 900 s Drive total put back | 3 |
| R4 receipt repair invents a receipt when Drive has no file / R4b several-files refusal removed | 1 / 1 |
| W6b `meta[RAW_FILE_SAVED] = False` removed | 1 |
| X1 library ceiling 600 -> 120 / D2 no 120 s cap | 1 / 2 |
| X2 401 counted as a retry / X3 re-sign on every attempt | 7 / 2 |
| D4 409 not accepted / D5 rate-limited 403 permanent / D7 dropped connection permanent | 3 / 4 / 4 |
| D8 a Drive breaker put back / D10 waits table changed | 2 / 14 |
| Row before file: W1 manifest, W2 revision index, W3 global-cue log, W4 candle row, W5b filings with no put, W6 quote save error swallowed, R3 data store with no put, R5 snapshot with no save | 1, 1, 1, 1, 1, 2, 1, 2 |
| R1 reader ignores the not-saved flag | 2 |

**My findings:** S1 fixed (`test_receipt_repair_refuses_a_path_with_no_file...`, `..._with_two_files...`). S2 fixed
(the delta and no-spin tests). S3 fixed: the recorder-level test runs a real attempt with a store that fails and
checks the sidecar flag and the guarded read. The Addendum 3 correction is fixed too:
`test_long_attempts_never_cut_a_call_below_five_tries` and plant T1. The story names both sidecar readers
(`drive_only_store.py`, `quotes/compare.py:40`) and the one intentional delta.

**Not blocking, recommended:** `tests/ingestion/test_drive_resilience.py` is 576 lines, the only test file over 350.
The 350-line rule is applied to `fno/` (CLAUDE.md "across `fno/shared/` and `fno/ingestion/`"; `tests/test_code_size.py`
scans `fno/` only), so it does not break the rule as written. Splitting it by mechanism (session, writers, readers,
receipt repair) would keep each part readable. If the orchestrator reads `docs/JUDGE.md` item 5 as covering tests, it
becomes a should-fix.

**Verdict: PASS** (lane 1, code round 2, judge #2).

## Addendum 5: the routed round-2 SHA is 60ab2d8 (PASS carries over)

The orchestrator routed `60ab2d8b989763d2c6a86c067299fd2d29de1126` in place of `c05a1d7`. `git diff --stat c05a1d7
60ab2d8` changes only `docs/stories/R1c-drive.md` and `tests/ingestion/test_drive_resilience.py`, so `fno/` is byte-identical.
The message said the change was doc only; it also adds one test assert, that `nse_json` keeps `max_total_seconds == 60.0`,
which matches `main`'s `settings.py:45`.

- Corrected citations checked against the code: `recorder.py:260-262` (save, then the failure appended), `:263`
  (`complete`), `:273-274` (the flag), `:285-286` (the canonical marker), `drive_only_store.py:49-62`,
  `compare.py:40-43`. All correct.
- The new follow-ups are accurate. `compare.py:42` calls `.decode()` on what the guarded store returns, so a not-saved
  file fails with `AttributeError` rather than a named refusal. Safe (no snapshot is built), and fine as a lane-2
  follow-up. The dashboard contract is correctly left to the owner.
- Story is 253 lines (under 500).
- Gates on `60ab2d8` (`__pycache__` cleared): 522 passed; ruff check and format clean; imports clean. Plants re-run:
  T1 (the 900 s Drive total) 3 failed, W6b 1 failed, R4 1 failed. All other Addendum 4 plants carry over unchanged
  on identical code.

**Verdict: PASS** on `60ab2d8` (lane 1, code round 2, judge #2).
