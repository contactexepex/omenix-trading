# Judge 30: R1c Drive session (story text), branch `story/R1c-drive-plan`, SHA 441f66c

**FAIL (round 1), lane 1, judge 1; 1 should-fix, nothing blocking.** The story (108 lines) plus an in-place amendment
of `R1-resilience.md`. The Drive move is right. The invariant is the right one, but its list of write paths is
incomplete.

## Judged

| Point | Verdict | Evidence |
|---|---|---|
| No Drive breaker (amends R1) | ACCEPTED | Never weaker: nothing today has one (`drive_session.py` has a loop only). A breaker on the one write target would defer every workflow's writes together. Removing it also removes the deferral question I raised in R1a, honestly settled in the R1 amendment |
| Retry stays the same and moves onto the policy; 401 re-sign inside the attempt | ACCEPTED | Matches `drive_session.py:12-16,41-62`: `{429,500,502,503,504}`, the 403 rate-limit reasons, one re-sign |
| Jitter 0.25, `Retry-After` as a floor up to 120 s | ACCEPTED as stated | Upward only. Stopping above 120 s is reasoning only (today the header is ignored and the four retries would most likely be refused too); stated as a difference |
| Worst case, 400 to 425 s (780 s with `Retry-After`), bounded by 900 s | ACCEPTED | Arithmetic checked; total outages time out today too |
| The order in the three cited wrappers | MET | `FingerprintingStore.put` stores and then records (`manifest_folder.py:106-109`); `DataStore.put` puts to Drive and then writes the receipt (`data_store.py:40-46`); `RevisionArchive.capture` saves the bytes and then the index row (`revisions.py`, "bytes first") |
| Every Drive write path covered by the invariant | NOT MET | Finding 1 |

## Findings

1. **Should fix: enumerate every Drive write path, not five.** `grep` for Drive store construction finds 14 wiring
   modules. Beyond `FingerprintingStore`, `DataStore` and `RevisionArchive`, several write through a raw
   `AreaStore(build_owner_drive(...))` and keep their own records, so the three wrapper tests do not cover them:
   - `intraday/backfill_wiring.py` and `intraday/wiring.py` (Groww candles, plus the deferral log);
   - `global_cues/wiring.py` (4 `AreaStore`s, plus the attempt log);
   - `pipeline/wiring.py` (4);
   - `storage/repair_wiring.py`.

   The 3 pm quote path (`quotes/drive_only_store.py`) also writes a repository sidecar whose `RAW_FILE_SAVED` flag
   says the Drive file exists. That is exactly a "row" for the invariant, and `RawQuoteMissing` exists because it can
   disagree. Also, "the index files" in the story is undefined: name them. Fix: a table of every write path. For each,
   give the record it keeps (manifest, receipt, revision index, sidecar, log), the line that orders file before
   record, and the test. Or state "no record kept". Then one test per path, as the story already says.

Note: the story's own text flags staging and the revision sink as unchecked. Both are fine by the code. `StagingArea`
keeps no record. The revision sink writes bytes before its row.

## Addendum 1: 441f66c retracted; this review does not count as a round

The orchestrator retracted 441f66c as incomplete (the write-path enumeration was unfinished), and the implementer
asked me to hold. My review above crossed both messages. By the orchestrator's ruling it does not count against the
two-round budget; the complete SHA starts round 1.

Correction to my own table above: I accepted "stop when `Retry-After` exceeds 120 s" as a stated difference. Judge #2 is
right that it is **weaker than today on data**. Today the header is ignored and all four retries happen, so one of them
may succeed; stopping early gives up attempts. I weighed it on reasoning about Google's likely refusals instead of on
the "never weaker" rule. The orchestrator's corrected rule (cap the wait at 120 s and keep today's 4 tries) is what I
will check on the new SHA.

## Addendum 2: complete SHA d68df6e (round 1 of 2)

**PASS (story text), lane 1, judge 1.** Story plus the R1 amendment.
- **Finding 1 FIXED.** The write-path table now covers every mechanism and every writer I named. I re-read each cited
  line on `main`; the save comes before the record in every case:

  | Writer | Order |
  |---|---|
  | `global_cues/collector.py` | put at :112, log at :113 |
  | `preopen.py` | :182 then :183 |
  | `archived_copies.py:52` | logs only when `data is not None` |
  | `candle_archive.py` | put at :54, then `_append` |
  | `snapshot_files.py` and `settle.py` | put at :27, ledger at `settle.py:48` |
  | `filings/archive.py` | put at :43, `manifest.record` at :53 |
  | the quote recorder | the raw CSV at :260, and `RAW_FILE_SAVED=False` set at :274 when that save failed, before the sidecar at :284, then the marker at :286 |
  | `receipt_repair.py` | reads the file back from Drive (:41), then writes the receipt |
  | `index_store.py:37-39` | put or `replace_contents` (index files hold no record) |
  | `pipeline/records.py:31` and `row_log.py` | the file is itself the record |

  Each mechanism has its own required test.
- **Retry-After, corrected and now never weaker.** The wait is a floor capped at 120 s, and all five tries are kept, as
  today (`(*RETRY_WAITS, None)` makes five). Worst case: 4 x 120 + 5 x 60 = 780 s, under the 900 s total cap.

Build note: today's `RetryPolicy` **stops** on a `Retry-After` above its ceiling (`retry.py` `_give_up_reason`). To keep
the five tries, either the Drive classifier caps `retry_after` at 120 s before returning its verdict (no library
change), or the library gains a cap-instead-of-stop option. Say which, and plant against it: a `Retry-After` of 300 s
must still give 5 tries.

## Addendum 3: SHA b057f5a (module map; supersedes d68df6e)

**PASS (story text), lane 1, judge 1.** d68df6e..b057f5a changes only the story (+11/-2).
- The pipeline correction is right. `pipeline/records.py:31` is the processed marker, and it follows the derived put
  (`pipeline/dry_run.py:36-37`, put then `mark(PROCESSED)`), which I re-read. The `fired` marker claims a job start,
  not a file.
- The module map is complete by mechanism. Four modules from my grep are not named, but each builds its store through
  a mapped builder:
  - `circulars/wiring.py` and `preopen/wiring.py` through `build_data_store`, so the data put (their writers are
    already in that row);
  - `quotes/index_wiring.py` and `quotes/window_wiring.py` through `build_drive_only_quote_store`, so the quote
    sidecar.

  Optional: name them in the map, so a reader counting modules finds all 18.
