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
