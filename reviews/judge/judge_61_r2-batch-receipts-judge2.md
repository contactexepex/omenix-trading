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

## Addendum 1: round 2 on `498151a` (supersedes `e9b98b2`)

Reviewed `git diff c37a381 498151a`, read `batch_receipts.py`, `receipts.py`, `drive_cache.py`, `cache_cli.py`,
`repair_cli.py`, `receipt_repair.py` and the R2 story section on unreceipted files.

**Gates (cleared `__pycache__`):** full suite 1151 passed; `ruff check fno tests tools ops` clean;
`tools/check_imports.py` clean (485 files); `tools/contract_plants.py` C1, C2, K1, K2, K3 ok.

**Mutations planted (12 of 12 killed, full suite each, file restored):** `covers` always True (1 failed); the
PER_FILE_CONFLICT report removed (1); the not-at-line-end `BatchBroken` check removed (2); a CONFLICT marked settled (1);
the write loop cut to one `os.write` (1); `unreceipted` finding nothing (3); pathless problems sent to `problems` (2);
the torn line's UNPROVED dropped (4); settlement ignored (1); `_attributed` naming any area (1); batch read before
per-file (1); the writer not adding to the index (2).

**Round-1 findings, re-run with my own script:**
- F1(a) fixed: a torn news batch leaves `sync("data/vix")` clean (no problem, no warning); `sync("raw/news")` reports
  UNPROVED for the named path and TORN as a warning. A damaged line naming a `data/` path, or an undecodable batch
  file, reaches only syncs around `raw/news` (as a warning), never `data`.
- F1(b) not done: `ops/commit_news_record.sh` still commits `receipts/_batches` unchecked. I accept that now. A
  torn file on `main` is a permanent warning, plus one UNPROVED problem until the path is proved. It is never read as
  a receipt and never silent. The same run's next append raises `BatchBroken`, so the run ends red. It is still
  worth a guard (see R1 below), but it is not blocking.
- F2 fixed: a per-file receipt with a different digest from the batch is now reported (`PER_FILE_CONFLICT`), and the
  sync is incomplete.

**The implementer's four questions:**
1. A Record file with no or a wrong receipt: a wrong later digest is caught. A torn line settled by a later batch
   receipt whose digest does not match Drive gives `DAMAGED`, so settlement hides nothing that the Drive check would
   catch. A file with no receipt is caught only by the opt-in `--unreceipted`, which no workflow runs. The story says
   so plainly (opt-in).
2. Damaged lines reaching an unrelated prefix, or crashing: neither reproduced (cases: CRLF, non-news path, bytes that
   are not UTF-8, a 2-field line).
3. "Settled" hiding a real problem: not by a batch receipt, as in point 1. **But see F3: a per-file receipt never
   settles it.**
4. Append: a half line refuses the next append (`BatchBroken`), and a short write loops. Two writers in one process
   with separate `ReceiptFolder`s have stale indexes, so the second writer appended a different digest for the same
   path. It was reported as CONFLICT, and the sync was incomplete. Through `DataStore.put` this cannot happen, because
   Drive's write-once `put` refuses the different bytes first. Not a finding.

### F3 (must fix): a repaired torn line keeps the news sync red forever

`BatchIndex.problems()` (`fno/ingestion/storage/batch_receipts.py:124`) settles a torn or malformed line only when
the path has a receipt *in a batch* (`p.path in known`, where `known` is the batch index). The module docstring
(lines 11-12) promises "until the file has a valid receipt". Reproduced (strong evidence, my script):
- Drive holds `raw/news/b.json`, and its batch line is torn.
- A per-file receipt with the correct digest is written through `ReceiptFolder.write`. That is exactly what the
  documented repair does: `data-repair receipt <path> --apply` goes through `receipt_repair.py:47` to
  `self.receipts.write`, and the repair allows it because `read()` is None for a torn line.
- `sync("raw/news")` still reports `raw/news/b.json: ... not proved`, and the sync stays incomplete.

It can never clear later either. `BatchReceiptWriter.write` (`batch_receipts.py:170-174`) finds the per-file
receipt, returns it, and appends no batch line. So the only way out would be to edit a committed batch file, which
write-once forbids.

The path to it is realistic: a promote killed mid-append, then the commit guard committing the torn file (F1(b)),
then the owner running the repair tool the story points to. The cost is fail-closed (a red check, no silent loss),
but it is permanent and has no legal fix.

Fix: settle against any receipt, for example in `ReceiptFolder.batch_problems`: drop a settled problem when
`self.read(p.path)` is not None. Then the per-file conflict check still covers a wrong digest. Add a test: a torn
line, then a per-file repair receipt, gives a clean `sync`.

### Recommendations (not blocking)

- R1: give the commit guard one shared check that refuses a batch file not ending in a new line (F1(b)). It would
  stop the permanent TORN warning from reaching `main` at all.
- R2: the story's line "the news writers' reconcile-before-write on the next run also re-saves a missing line" is
  the implementer's claim. I did not trace it end to end (reasoning only). `DataStore.put` with the same bytes would
  re-append the line, so it holds if the writer re-puts the file.

**Verdict: FAIL** (round 2, `498151a`). F3 is a one-line read-side fix plus a test. This was the second round, so
per the round rule the orchestrator or the owner decides next. I am glad to re-check a fix commit if asked.
