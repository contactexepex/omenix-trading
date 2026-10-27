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
| `Retry-After` | ignored | honoured as a **floor, capped at 120 s**, on a retried answer; the call keeps all its tries (it never stops early, unlike NSE), see "Stated differences" |
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

## The invariant: no manifest row, receipt or index entry without its Drive file

The thing never to break. **Every Drive write path was enumerated** (by a read of the code, and independently traced by
judge 2; the two agree). Two facts make the order structural: the only creator of a Drive file is
`GoogleDriveUploadStore.put`, which returns only after the bytes are verified by Drive's MD5 or a read-back
(`google_drive_upload.py:33-70`); and the only other content write is `replace_contents` (index files, MD5 checked,
`google_drive_upload.py:77-85`). A row written after a `put` that raised is never reached. **No ROW-FIRST path exists.**

| Mechanism | The record it keeps | Where the file-before-record order is (file:line) | Writers |
|---|---|---|---|
| Archive put: `FingerprintingStore.put` | manifest row (a local CSV, committed later) | `manifest_folder.py:108` put, `:109` record | the librarian (`librarian.py:78,93`), snapshot and session-filed takers (`snapshot_taker.py:29,35`, `session_filed_taker.py:51,53`; `fo_masters` and flows through them), `raw_library.py:59`, `vix_history/librarian.py:85,100`, the promotion gate's Record put (`promotion/gate.py:66`), filings day lists |
| Data put: `DataStore.put` | SHA-256 receipt (a local file, committed later) | `data_store.py:43` put, `:46` receipt | the close read (`close_read/store.py:35`, all of `reader.py` and `confirm.py`), `receipted_rows.py:36`, `part_table.py:40` (circulars, NSDL back-fill), preopen (`record.py:80,93,100`, `open_check.py:117`) |
| Receipt repair | a receipt for a file already in Drive | `receipt_repair.py:40` reads the file back, `:47` writes the receipt | the repair job (`repair_wiring`) |
| Revision archive | revision index row | `revisions.py:142` put ("bytes first"), `:143` append | `RevisionArchive.capture`, `revision_source.py:39`, `promotion/revision_sink.py` |
| Own log or ledger after a put | a row in that writer's own log | `global_cues/collector.py:112` put, `:113` log append (the attempt log's `STARTED` row claims no file; the outcome row comes after the archive returns); `global_cues/preopen.py:182-183`; `global_cues/archived_copies.py:54` (adopting a copy already in Drive: the row is written only when `_read` returned the bytes, `data is not None`); `intraday/candle_archive.py:54` put, `_append` after; `intraday/snapshot_files.py:27` put, then the ledger append in `settle.py:48`; `filings/archive.py:43` put, `:53` manifest record; `quotes/recorder.py:284-286` sidecar then marker; `pipeline/dry_run.py:36-37` derived file put, then the `processed` marker (`pipeline/records.py:31`); the `fired` marker (`pipeline/dispatcher.py:58`) claims a job started, not a file | the global cues, the intraday candles and snapshots, the filings archive, the quote recorder (below) |
| Index files | none (an in-place file) | `index_store.py:37-39`: put, then `replace_contents` | filings progress and the symbol map (`filings/progress.py:93`, `filings/wiring.py:144`), written after the run's filings |
| No record kept | none | n/a | staging (`promotion/staging.py:53`, `runs.py:75`), `pipeline/run_summary.py:71`, `row_log.py:99,113`, `quotes/recorder.py:185` (a "none" marker claims nothing), folder creation, `DriveItems.move/rename` |

**Reconciliation of the three enumerations.** Judge 1 counted by wiring module, judge 2 traced by mechanism, and mine
went site by site (about 45); they differ in granularity, not in a classification. Every module that builds a Drive store
maps to a row above: `storage/wiring.py`, `fo_masters/wiring.py`, `vix_history/wiring.py`, `promotion/wiring.py`,
`filings/wiring.py` and `flow_history/wiring.py` (archive put, plus data put and index files where they use them);
`storage/data_wiring.py` and `close_read/wiring.py` (data put); `storage/repair_wiring.py` (receipt repair);
`storage/quote_wiring.py` (the quote sidecar); `global_cues/wiring.py`, `intraday/wiring.py`,
`intraday/backfill_wiring.py` and `pipeline/wiring.py` (own logs and ledgers, written after the put). No module is
unmapped, and no site disagreed on file-first.

Two cases need a sentence each. **The quote sidecar** (`quotes/drive_only_store.py`): the one row-equivalent that is designed to be writable without its
file. If the CSV save fails, the sidecar is still written with `RAW_FILE_SAVED=False` (`recorder.py:274`; absent means
saved). The safety rests on the readers, and this repository has **two** (corrected after judge 1 found the second): the guarded
`DriveOnlyQuoteStore.get` (`drive_only_store.py:48-62`), and `quotes/compare.py:40`, which reads the sidecar directly and
the CSV through the guarded store. The comparison is safe because it starts from the canonical marker, which
`recorder.py:285-286` writes only for a `complete` attempt (`recorder.py:261-263`), and `complete` requires no failures, the
raw-save error being one (`recorder.py:258-259`): canonical implies complete implies saved; if they ever disagreed the
guarded read returns `None` and the comparison fails loudly. For the guarded reader: a flag of false returns `None` without touching Drive (the file
is not counted and no receipt or row is derived from it); a flag of true with no file in the private store raises
`RawQuoteMissing`, and a file whose SHA-256 differs from the sidecar's `csv_sha256` raises `RawQuoteHashMismatch`, so the
reader also reconciles the claim with Drive's real state. Readers outside this repository (the dashboard) are not
checked here; that is an open question for the owner. **Required tests (part of the list below):** reader side: flag
false returns `None` and makes no Drive read; flag true and the file missing raises `RawQuoteMissing`; a mismatched hash
raises; the comparison never builds a snapshot from a file that was not saved. Writer side (judge 1): over the offline
sample provider, a CSV save that fails every try is incomplete, writes no canonical marker and marks the sidecar not saved.

**The deferral log**
(`intraday/backfill.py:108`) records sessions put off and claims no file.

A file without a row remains possible after a crash between `put` and the record; the librarian's re-put
(`librarian.py:78`, `vix_history/librarian.py:100`), the gate's repair and the 409 on a repeated create heal it.

**Tests, one per mechanism and per own-record writer** (a Drive that fails every try on the call after the create leaves
the file and no record, and raises the exception callers catch; the repeat run writes the record once): the archive put,
the data put, receipt repair, the revision archive, the global-cue collector, the candle archive, the snapshot files and
ledger, the filings archive, the quote sidecar flag (writer side, and the three reader-side tests above), and the index file. If any path is found writing its record first,
that is a bug to fix in R1c.

## Stated differences from today (all deliberate)

1. Waits gain upward jitter (never shorter), 25%.
2. `Retry-After` is honoured as a floor and **capped**: the wait before try n is `min(max(t_n + jitter, Retry-After),
   DRIVE_RETRY_AFTER_CAP_SECONDS)`, a named constant of 120 s whose comment ties it to the workflow timeouts (the
   shortest is 900 s). The call keeps **all five tries**: stopping early on a long `Retry-After` would make fewer
   attempts at the Record store than today, which is forbidden (judge 2, S1; the orchestrator's first ruling is
   superseded by it). A header asking for more than 120 s therefore gets 120 s, not a deferral. **How it is built (judge 2's note):** no library
   edit. The Drive classifier clamps the header to `DRIVE_RETRY_AFTER_CAP_SECONDS` before it builds the verdict, and the
   `drive` settings set the library's Retry-After ceiling to 600 s, so the library's stop-above-the-ceiling never fires
   for Drive (a test pins both numbers). Whether 120 s is the right
   cap for a write target is not measured: Drive-write calls per workflow is a **required pre-go-live measurement** on
   the owner's go-live list, and raising the cap is a tuning follow-up, not a redesign.
3. Nothing else: no breaker, no spacing, no new exception, same texts.

## Worst case per call, computed (code references: `drive_session.py:41-62`, `TIMEOUT_SECONDS = 60`)

One failing call today: waits 2+8+30+60 = 100 s plus five requests that each time out at 60 s = **400 s**. With jitter
0.25: 125 + 300 = **425 s** (+6%). With a `Retry-After` of 120 s or more on every retry: four waits of 120 s (the cap), so
**780 s** (new: today the header is ignored, so this case does not exist), under the policy's 900 s total cap.
Honest reading: a Drive outage already exceeds the shortest workflow timeouts (15 minutes, flows-download,
participant-oi-watch, circulars, 900 s) after three failing calls today (3 × 400 s = 1200 s), and the Drive-using workflows make many Drive calls per run (a count per workflow is not made here; reasoning
only), so a total outage most likely ends in a timeout today and after; R1c adds 6% (25 s per call) to
that, and up to 380 s per call only when Google sends `Retry-After`. The commit step of a timed-out run is skipped, as
today. No run-level budget is added (a separate story, as for NSE).

## Claims and how each is shown

1. Same classification (table-driven over statuses and the 403 reasons), the 401 rule, the `accept` contract.
2. Waits: with no jitter 2/8/30/60 exactly (the characterization); live waits lie in `[t, 1.25 t]`; `Retry-After`
   raises a wait, a value above 120 s waits 120 s and the call still makes all five tries; `Retry-After` on the last try
   gives up without a wait.
3. Exceptions and their texts unchanged on exhaustion (`HTTPError` with Google's reason, `ConnectionError` re-raised as it was).
4. The invariant: the per-write-path tests above.
5. No breaker: `settings_for("drive").breaker is None`, nothing in `drive_session.py` or the stores constructs one.
6. One builder: `RETRY_WAITS` is gone from `drive_session.py` (a test); `tools/` keeps no Drive loop (listed otherwise).
7. Reads and writes alike go through the one session (a test that every store method reaches `DriveSession.request`).

## Verification (no claim that a `--help` dry run proves anything)

Primary safety: the Drive characterization and the new tests, mutation plants (the waits, the 403 reasons, the 401 rule,
the 409 accept, the Retry-After floor and its 120 s cap, a row written before the file). Real proof, owner-gated: the
stage-only `pipeline-staging` dispatch exercises the Drive writes on the real runner. Interim, after the merge: the
active comparison of the first scheduled run of each Drive-using workflow against its predecessor (tries, waits,
statuses, manifest rows, receipts), comparing tries and waits rather than duration, reverting only for a clear regression.

## Judges

Two judges. Freeze rule: one SHA, no push after sending it. Not routed until R1b2 is merged (orchestrator's sequencing).

## R1c build evidence

Branch `story/R1c-code` (built to the story as passed, plus its two text additions `ddbcf60`).

- **Code:** `fno/ingestion/storage/drive_session.py` (`DriveSession.request` over `RetryPolicy.run`; `_classify`;
  `DRIVE_RETRY_AFTER_CAP_SECONDS = 120.0` applied in the classifier; the 401 re-sign inside the attempt; exhaustion
  re-raises what today raised), `google_drive.py` (a `policy` argument passed through), `fno/shared/resilience/settings.py`
  (`drive`: waits 2/8/30/60 as floors, jitter 0.25, Retry-After ceiling 600 s so the library's stop never fires, **no
  breaker**). No library edit. `RETRY_WAITS` is gone from `fno/` (a test).
- **Characterization contract:** all 27 Drive tests unchanged except the one named adaptation: `drive()` and `store()` pass a
  zero-jitter `RetryPolicy` (so waits read 2/8/30/60 exactly). The library tests that used the old Drive breaker default
  (`test_guarded`) now build the `count_exhausted` breaker explicitly, keeping that library mechanism under test; the settings
  and jitter tests pin the new Drive numbers (no breaker, 0.25).
- **New tests (21)** in `tests/ingestion/test_drive_resilience.py`: live waits within `[t, 1.25 t]`; **Retry-After 300 gives 5
  tries each waiting 120 s** (judge 1); Retry-After raises a wait but never shortens one; on the last try it gives up with no
  wait; a 403 rate limit honours it; the 401 re-sign adds one send and no wait; no breaker anywhere in the Drive code; the old
  table gone and no direct HTTP call besides the session; and the invariant, one test per mechanism or own-record writer,
  each over a Drive whose create got through and whose every later try failed: the archive put (no manifest row), the data
  put (no receipt), receipt repair (no receipt when the read-back fails), the revision archive (no index row), the
  global-cue collector (no log row), the candle archive (no manifest row), the snapshot files (the ledger is not touched),
  the filings archive (no manifest row), the quote writer (the sidecar is marked not saved), and an index-file replace that
  fails (the old version stays); and the quote sidecar's three reader-side tests (not-saved returns `None` and reads no Drive;
  saved with no file raises `RawQuoteMissing`; a wrong hash raises `RawQuoteHashMismatch`).
- **Mutation plants, each caught (16):** no cap on Retry-After; Retry-After ignored; the cap above the ceiling (which would
  stop the call); the 401 re-sign repeated; the 403 rate limit not retried; a row before the file in the archive put, the data
  put, the revision archive, the global-cue collector, the candle archive and the filings archive; the quote reader ignoring
  the not-saved flag and skipping the hash check; the quote writer not catching a save failure.
- **One behaviour difference found while refactoring, in the safe direction:** today a `ConnectionError` raised by the re-send
  after a 401 propagates at once (the re-send sat outside the retry `try`); inside the attempt it is now retried like any
  other dropped connection. More attempts, never fewer.
- Gates: ruff, imports, numbers, size clean; 511 tests pass.

### R1c code round-2 fold (orchestrator's rulings and the judges' notes; prepared on `story/R1c-code-r2`)

- **THE one intentional behaviour change in R1c (named entry, lane 1):** a `ConnectionError` or `Timeout` raised by the
  **re-send after a 401** is now retried inside the attempt, within the 2/8/30/60 table; today the re-send sat outside the
  retry `try` and the error propagated at once. Justification, spelled out: the governing rule is never *weaker* than
  today, not never *different*; this is strictly stronger for data completeness (it tries harder to land a write on the
  system of record), bounded for politeness (inside the table, against our own quota'd Google account), and preserving
  the old quirk would need a special non-retryable re-send step, against KISS. When every try fails, the same
  `ConnectionError` is raised. Pinned by `test_INTENTIONAL_DELTA_...` in `test_drive_resilience.py`. **The post-merge Drive
  comparison must expect this one difference and not revert on it**; every other Drive behaviour must match today.
- **The 401 control flow (exact):** `drive_session.py:49` sets `signed_in_again = False` once per `request` call (per call,
  not per attempt); inside `attempt` (`:51-58`) a 401 re-signs only `if ... and not signed_in_again` (`:54`), sets the flag
  (`:56`) and re-sends once (`:57`). A second 401 on that re-send is not a retry verdict: `_classify` answers OK, and
  `_raise_with_reason` raises `HTTPError`. A 401 on a *later* try (after a 5xx) finds the flag set, is not re-signed, and is
  raised the same way. So at most one re-sign per call and no loop on a persistent 401. Pinned by
  `test_the_401_re_sign_happens_at_most_once_per_call_and_a_persistent_401_cannot_spin` and the existing characterization.
- **The quote sidecar has two readers in this repository** (the story said one; judge 1 found the second): the guarded
  `DriveOnlyQuoteStore.get` (`drive_only_store.py:48-62`) and `quotes/compare.py:40`, which reads the sidecar directly and then
  the CSV through the guarded store. The comparison is safe because it starts from the canonical marker, which
  `recorder.py:285-286` writes only when the attempt is `complete`, and `complete` (`recorder.py:261-263`) requires no failures,
  the raw-save error being one (`recorder.py:258-259`): canonical implies complete implies saved. If they ever disagreed, the
  guarded read returns `None` for a not-saved flag and the comparison fails loudly (`None.decode()`), never a snapshot of a
  missing file. Pinned by `test_the_comparison_never_builds_a_snapshot_from_a_quote_file_that_was_not_saved` (with the
  reader ignoring the flag, it fails). The writer-side test judge 1 required exists: the recorder's `_attempt` runs offline over the sample provider (a
  small harness: `Slot("NIFTY", cross_check=False)`, an in-memory store whose CSV `put` raises), and a failed save gives
  `complete` false, no `.canonical` marker and a sidecar with `raw_file_saved` false; the control run over a working store is
  complete and writes the marker. With the raw-save error not counted as a failure it fails (below).
- **Added mutation plants, each caught:** the raw-save error not counted as a failure (a failed save then goes complete and
  canonical); the not-saved flag not set on the sidecar; the quote reader ignoring the flag (now also caught by the comparison
  test); the Retry-After cap raised to 300 s; the library ceiling lowered to 120 s (judge 2's plant); the retry of a
  `ConnectionError` removed from the classifier.
- **Retry-After worst case pinned:** a test computes 4 x 120 + 5 x 60 = 780 s and asserts it is under the policy's 900 s
  limit, so a long header never makes the policy give up early.
- Gates: ruff, imports, numbers, size clean; 517 tests pass.
