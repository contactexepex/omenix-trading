# R1c: the Drive session on the shared resilience layer

Lane 1, two judges (Google Drive is the system of record and the write-once data). Branch `story/R1c-drive-plan`.
**Story text only; no code until it is judged.** Rules and design: [R1-resilience.md](R1-resilience.md) (amended in
place by this story, below); precedent: [R1b-nse-source.md](R1b-nse-source.md) and
[R1b2-persisted-pause.md](R1b2-persisted-pause.md). The floor is `tests/characterization/test_drive_behaviour.py` (on
`main`, `cc5114e`, 27 tests, 12 of 12 mutations caught): the refactor keeps it green with only injection adaptations.
Orchestrator's rulings on the plan (breaker, persistence, jitter, Retry-After) are applied; where this story differs
from the plan it says so.

## What moves

`DriveSession.request` (`fno/ingestion/storage/drive_session.py`) is the one place every Drive call goes through (the
store, the upload store, the cache, the index files). It holds its own loop and its own table
`RETRY_WAITS = (2, 8, 30, 60)`.

| Piece | Today | After R1c |
|---|---|---|
| Retry loop | own `for wait in (*RETRY_WAITS, None)` | `RetryPolicy.run` with the `drive` settings; 2/8/30/60 stay the per-attempt floors |
| What retries | 429, 500, 502, 503, 504; Google's 403 with `rateLimitExceeded` or `userRateLimitExceeded`; `ConnectionError`, `Timeout` | the same, as RETRY verdicts; a plain 403 and every other error: PERMANENT, raised with Google's reason as now; statuses in `accept` (409 `fileIdInUse`) are OK |
| The 401 re-sign | once per call, inside the loop, no wait | stays **inside the attempt** (not a retry, not counted); a second 401 is raised as now |
| Jitter | none | upward only, **0.25** (as NSE) |
| `Retry-After` | ignored | honoured as a **floor**, on a retried answer; above the 120 s ceiling the call stops (as NSE), see "Stated differences" |
| Breaker | none | **none** (below) |
| Spacing | none | none |

What stays exactly as it is: `google_drive_upload.py` (reserved IDs, the 409 on a repeated create, the read-back
`_holds`, `_fresh_child`), `owner_token.py`, the `accept` contract, `_raise_with_reason`, and every exception callers catch
(`requests.HTTPError` with Google's reason, `ConnectionError`, `Timeout`). A call that exhausts its retries raises the same
exception as today, with the same text.

## No Drive breaker (orchestrator's ruling; this amends the R1 story)

R1a shipped default settings with a Drive breaker (5 exhausted calls, 15 minutes). **R1c removes it**: the `drive` settings
carry no breaker, and nothing is wired. Reasons (the orchestrator's, checked against the code):
- Drive is the write target, not a source we hammer. Google answers its own throttling with 429, 403 rate-limit reasons
  and `Retry-After`; bounded backoff that honours `Retry-After` already handles that, and the table is bounded: four
  waits, then the call fails and the next run retries.
- A breaker that is wrongly open on the one host all persistence goes through defers every workflow's writes together,
  so it makes Drive less resilient, not more. Nothing today has a Drive breaker, so not adding one is not weaker.
- A breaker that is wired but off is dead configuration. If production ever shows Drive throttling across runs, that is a
  deliberate future story (a write-target breaker must fail closed and never block a write for long), not a dormant switch.
- Without a breaker there is no deferral on Drive, so **no new exception** (`DriveCoolingOff` in the plan is dropped, as
  it would have nothing to carry), and no state to persist: in-process only is correct.

Amended in place in `R1-resilience.md`: the Drive breaker line and judge 1's R1c requirement (the latter becomes the
invariant below). The library's generic `count_exhausted` option stays (a second use may need it); only Drive's shipped
settings change (`drive.breaker` removed, `jitter 0.25`, the change pinned in `test_settings`).

## The invariant: no manifest row or receipt without a Drive file

The thing never to break. By construction (to be shown by tests, with these lines as the reference):
- `FingerprintingStore.put` (`manifest_folder.py:106-109`) calls `self.store.put(path, data)` and only then
  `self.manifests.record(...)`: the row is written after the store accepted the bytes.
- `DataStore.put` (`data_store.py:40-47`) calls `self.drive.put(...)` and only then `self.receipts.write(...)`.
- The Drive store's `put` returns only when the bytes are in Drive: `GoogleDriveUploadStore._create_file` verifies the
  copy by Drive's MD5 or by reading it back (`_holds`) and raises `StoredCopyDamaged` otherwise (`google_drive_upload.py`).

So if any Drive call in `put` fails after its retries, the exception passes through before the row or receipt is written.
**A file without a row is recoverable** (the librarian's re-put "saved by a run stopped before its manifest commit", the
gate's repair of a proven-good held file, the 409 on a repeated create); a row without a file is what the order makes
impossible. Required tests, one per Drive write path: a Drive that fails every try on the call **after** the create (the
read-back, or the next folder lookup) leaves the file, **no manifest row, no receipt**, and raises the exception callers
catch; the repeat run writes the row once. Paths: staging (`StagingArea.stage`), the Record put (`FingerprintingStore`),
the revision sink, `DataStore.put` (receipts), and the index files. If any path is found writing its row before the
file is confirmed, that is a bug to fix in R1c, not to preserve.

## Stated differences from today (all deliberate)

1. Waits gain upward jitter (never shorter), 25%.
2. `Retry-After` is now honoured, up to 120 s; above that the call stops at once instead of retrying at 2/8/30/60 s.
   Reasoning only: Google asking for more than the longest of our waits means retrying sooner would be refused too, and
   the next run is the right retry; judges may veto.
3. Nothing else: no breaker, no spacing, no new exception, same texts.

## Worst case per call, computed (code references: `drive_session.py:41-62`, `TIMEOUT_SECONDS = 60`)

One failing call today: waits 2+8+30+60 = 100 s plus five requests that each time out at 60 s = **400 s**. With jitter
0.25: 125 + 300 = **425 s** (+6%). With a `Retry-After` of up to 120 s on every retry: four waits of up to 120 s, so
**780 s** (new: today the header is ignored, so this case does not exist), bounded by the policy's 900 s total cap.
Honest reading: a Drive outage already exceeds the shortest workflow timeouts (15 minutes, flows-download,
participant-oi-watch, circulars, 900 s) after three failing calls today (3 × 400 s = 1200 s), and the Drive-using workflows make many Drive calls per run (a count per workflow is not made here; reasoning
only), so a total outage most likely ends in a timeout today and after; R1c adds 6% (25 s per call) to
that, and up to 380 s per call only when Google sends `Retry-After`. The commit step of a timed-out run is skipped, as
today. No run-level budget is added (a separate story, as for NSE).

## Claims and how each is shown

1. Same classification (table-driven over statuses and the 403 reasons), the 401 rule, the `accept` contract.
2. Waits: with no jitter 2/8/30/60 exactly (the characterization); live waits lie in `[t, 1.25 t]`; `Retry-After`
   raises a wait and a value above 120 s stops the call; `Retry-After` on the last try gives up without a wait.
3. Exceptions and their texts unchanged on exhaustion (`HTTPError` with Google's reason, `ConnectionError` re-raised as it was).
4. The invariant: the per-write-path tests above.
5. No breaker: `settings_for("drive").breaker is None`, nothing in `drive_session.py` or the stores constructs one.
6. One builder: `RETRY_WAITS` is gone from `drive_session.py` (a test); `tools/` keeps no Drive loop (listed otherwise).
7. Reads and writes alike go through the one session (a test that every store method reaches `DriveSession.request`).

## Verification (no claim that a `--help` dry run proves anything)

Primary safety: the Drive characterization and the new tests, mutation plants (the waits, the 403 reasons, the 401 rule,
the 409 accept, the Retry-After floor and ceiling, a row written before the file). Real proof, owner-gated: the
stage-only `pipeline-staging` dispatch exercises the Drive writes on the real runner. Interim, after the merge: the
active comparison of the first scheduled run of each Drive-using workflow against its predecessor (tries, waits,
statuses, manifest rows, receipts), comparing tries and waits rather than duration, reverting only for a clear regression.

## Judges

Two judges. Freeze rule: one SHA, no push after sending it. Not routed until R1b2 is merged (orchestrator's sequencing).
