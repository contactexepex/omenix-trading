# R1c: the Drive session on the shared resilience layer (PLAN; not yet a frozen story)

Lane 1, two judges (Google Drive is the system of record and the write-once data). Branch `story/R1c-drive-plan`. This
is the plan the orchestrator asked for before a story is written: what moves, what stays, the gates. The rules and the
design are in [R1-resilience.md](R1-resilience.md); the NSE precedent is [R1b-nse-source.md](R1b-nse-source.md) (R1b1)
and [R1b2-persisted-pause.md](R1b2-persisted-pause.md). The floor is `tests/characterization/test_drive_behaviour.py`
(on `main`, `cc5114e`, 27 tests, 12 of 12 mutations caught): the refactor keeps it green.

## What moves behind the shared layer

`DriveSession.request` (`fno/ingestion/storage/drive_session.py`) is the one place every Drive call goes through
(`GoogleDriveStore`, the upload store, the cache, the index files). Today it holds its own retry loop and its own wait
table `RETRY_WAITS = (2, 8, 30, 60)`.

| Piece | Today | After R1c |
|---|---|---|
| The retry loop | own `for wait in (*RETRY_WAITS, None)` | `RetryPolicy.run` with the `drive` settings (waits 2/8/30/60 as floors) and a classifier |
| Which answers retry | 429, 500, 502, 503, 504; Google's 403 with `rateLimitExceeded` / `userRateLimitExceeded`; `ConnectionError`, `Timeout` | the same, as a `Verdict` (RETRY); a plain 403 and every other error: PERMANENT, raised with Google's reason as today |
| Accepted statuses (`accept`, e.g. 409 `fileIdInUse`) | returned as answers | OK verdicts, unchanged |
| The 401 re-sign | once per call, inside the loop, no wait | stays **inside the attempt** (a sign-in is not a retry and not counted); the second 401 is raised as now |
| Jitter | none | upward only, **0.25** as for NSE (the worst case per call grows 5%, not 21%; to be tabulated per Drive-using workflow against its timeout, as R1b did) |
| Pace | none (spacing 0) | none: `RateSettings(min_spacing_seconds=0.0)` stays |
| Breaker | none | one per process on the Drive host, **new behaviour on the Record store**, see below |

What stays exactly as it is: `google_drive_upload.py` (the reserved IDs, `fileIdInUse` 409 idempotency, the read-back
`_holds`, `_fresh_child`), `owner_token.py`, the `accept` contract, `_raise_with_reason`, and every exception callers
catch (`requests.HTTPError` with Google's reason, `ConnectionError`, `Timeout`). `retry_policy.py`'s NSE verdict code is
not touched.

## The decision that needs the judges: a Drive breaker

The R1 story gives Drive a breaker (5 exhausted calls in a row, 15 minutes, doubling to 24 h). Today there is none: a
Drive outage makes each call retry and fail, run after run. A breaker defers calls while Drive is failing, which is the
point (do not hammer a quota-limited API), but Drive is the **system of record**. Three questions the plan puts to the
judges before any code:

1. **What a deferred write leaves behind (judge 1's R1c requirement).** The breaker opens only after 5 exhausted calls
   in a row, and it defers the *next* call at its start. A deferral can therefore land between two calls of one write: the
   create succeeded, the read-back did not run. The claim to show with a test: a deferred call raises a
   `requests.RequestException` subclass (`DriveCoolingOff`, so every existing `except requests.RequestException` treats it
   as a failed Drive call, as the callers already do); it writes nothing itself; at worst it leaves **a Drive file with no
   manifest row, never a row without a file**; and the next run repairs that by the existing paths (the librarian's "saved
   by a run stopped before its manifest commit" re-put, the gate's repair of a proven-good held file, and the 409 on a
   repeated create). Spy-store tests over each writer: staging, the Record put, the revision sink, the manifest recorder.
2. **Whether to ship the breaker in R1c at all.** The safe alternative is the retry policy and the jitter first, with the
   Drive breaker defined but **not wired** (a `drive.breaker: off` setting, default off) until the owner has seen a real
   Drive outage in the logs. Reasoning only: Drive's 403 rate limit is the real hazard, a breaker for it is cheap, but a
   breaker that wrongly stays open on the system of record costs more than a few extra retries. The plan recommends
   **retry and jitter now, breaker off by default, wired and tested so one setting turns it on**; the judges decide.
3. **Persistence across runs.** If the breaker is on, it is in-process only in R1c. Persisting it (R1b2's run-local log
   and last step) is a separate decision, since a persisted Drive pause defers every workflow's writes, not one host's reads.

## Gates (the same as R1b)

1. The Drive characterization stays green with only injection adaptations (a zero-jitter policy; `DriveSession` takes
   its policy like `NseArchiveSource` does).
2. Worst-case table per Drive-using workflow against `timeout-minutes` (one call: 4 waits plus 5 request timeouts of 60 s
   today; the table is made from the code, with references).
3. Mutation plants on the new code (waits, the 403 reasons, the 401 rule, the 409 accept, the exception mapping, a
   deferral that writes, a breaker counted twice).
4. A static check that `RETRY_WAITS` is gone from `drive_session.py` and that `tools/` or other loops are listed.
5. Two judges, freeze rule; then the post-merge active comparison: the first scheduled run of each Drive-using workflow
   against its predecessor (tries, waits, statuses, manifest rows, receipts), revert only for a clear regression.

## Not in R1c

The Groww reads and the rest (R1d), NSE (R1b), the promotion gate, and any workflow YAML.

## Open questions for the orchestrator

- Breaker on or off by default (the plan recommends off, wired).
- Whether jitter 0.25 is also right for Drive (the plan says yes, for the same reason as NSE).
