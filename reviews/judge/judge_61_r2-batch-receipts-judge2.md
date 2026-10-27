# Judge 61: R2 news receipts packed one batch file per run, code (judge #2)

Branch `story/R2-news-batch-receipts`, SHA `e9b98b2`, compared with base `c37a381`. Lane 1, two judges; this is an
independent read. **FAIL** (round 1) on 2 should-fix. The write path is sound and well pinned. The read side has two
gaps: a news batch problem spills into every dataset's sync, and two disagreeing receipts for one path go unreported.

## Gates (`__pycache__` cleared)

1127 passed; ruff and imports clean.

## The write path: sound

`BatchReceiptWriter.write`:
- checks the path;
- reads any existing receipt (per-file, then batch), and refuses a different digest or keeps the first;
- writes the whole line with one `O_APPEND` call into `_batches/<run_id>.tsv`;
- adds the receipt to the in-process index.

It runs after Drive accepted the file (`DataStore.put`).

| Plant | Failed |
|---|---|
| B1 the different-digest refusal removed | 3 |
| B2 a torn last line read as a receipt | 2 |
| B3 the last line wins instead of the first | 1 |
| B4 the in-process index not updated after a write | 2 |
| B5 sync ignores batch problems | 1 |

**The orchestrator's three questions:**
1. **Can a Record file end with no findable receipt?**
   - A crash between the Drive put and the line leaves the file unreceipted, as before. The news writers' repair
     re-saves the held bytes, Drive no-ops, and the receipt is written into the next run's batch: healed.
   - Index staleness within one process: any second writer for the same path either has the same digest (Drive is
     write-once, so different bytes never get that far) or is refused by B1's check.
   - Two runs never share a batch file (unique run ids).
   - So the answer is no, apart from the torn-line case under F1, which also heals, through the next run's repair.
2. **Is per-file-first precedence safe? Not fully: F2.**
3. **Can the batch reader make a tampered Drive file look verified?** Only through F2's shadowing. Within the batch
   files a second digest is refused on write, reported on read, and the first is kept (B3).

## Findings

1. **F1 (should fix): one news batch problem makes every dataset's sync report a problem.** `DriveCache.sync(prefix)`
   now adds `self.receipts.batch_problems()` whatever the prefix (`drive_cache.py`, the added line). Reproduced
   (scratch script, not committed): a VIX file with a valid per-file receipt, plus one torn line in a news batch file,
   gives `cache.sync("data/vix")` the problem `...tsv: last line has no line break...`. So vix, flows and every other
   sync would report a news problem and go red or alert.

   It is also likely to reach `main` and stay. The commit step (`ops/commit_news_record.sh`) guards the manifest but
   always commits receipts, so a promote killed mid-append publishes the torn batch file. Nothing ever rewrites it, so
   every sync in the repository reports it until someone fixes it by hand.

   Fix, both parts:
   - (a) report a batch problem only to the syncs it concerns: problems on a line whose path is under the prefix,
     torn or malformed files only to syncs whose prefix covers that batch's paths, or only through a news-only check;
   - (b) have the commit guard refuse to commit a batch file without a trailing new line, through one shared Python
     check as for the manifest, so a torn line never reaches `main`.

   Tests: a torn news batch line must leave `sync("data/vix")` clean, and must keep the torn batch file out of the
   commit.
2. **F2 (should fix): a per-file receipt silently shadows a batch receipt with a different digest.** Reproduced: a
   batch receipt for `raw/news/p.json` with digest A, plus a per-file `receipts/raw/news/p.json.sha256` with digest B.
   `read()` returns B and `batch_problems()` returns `[]`. Before R2 a path had one receipt, so two disagreeing proofs
   is new, and the reader picks one without saying so. A tampered Drive file matching B would then verify as OK.
   Changing a per-file receipt by hand fooled the verifier before R2 too. But a shadowing receipt is a new file, not
   an edit, and nothing flags the disagreement. Fix: when a path has both a per-file and a batch receipt and their
   digests differ, report it, in `batch_problems` or in `read`, and treat that path as unverified. Add a test.

## Notes (not blocking)

- `os.write`'s return value is not checked. A short write would leave a partial line. It is next to impossible for one
  small line on a local disk, but `os.write` in a loop until done, or an assert on the count, costs one line.
- Batch files sort by run id, which is the time to the second plus random hex. Two runs in the same second sort by the
  hex, not by time, which only matters with F2-like conflicts, and B3's "first kept" then depends on that order. It is
  harmless while the batch-versus-batch conflicts are only ever same-digest.

**Verdict: FAIL** (round 1). Both fixes are small and local to the read side and the commit guard.
