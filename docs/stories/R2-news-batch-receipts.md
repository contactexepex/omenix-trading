# R2: news receipts, one batch file per run (option B)

**Lane 1, two judges (the writer of the write-once Record and the proof of it).** Owner decision, 27 Oct 2026 (relayed by the
orchestrator): "we don't want to lose any data anymore"; receipts for news go from one file per Drive file to one file per run.
**Status: built, awaiting two judges.** Scope: the news article and cluster writers only. vix, flows and every other source keep one receipt per file.

## What is true today (read from the code, 27 Oct 2026)
- `DataStore.put` (fno/ingestion/storage/data_store.py) writes the Drive file, then calls `ReceiptFolder.write(receipt)`: one
  `receipts/<drive path>.sha256` file per Drive file. The news writers (`news/record/writer.py`, `news/cluster_record/writer.py`) use
  that `DataStore`. **There is no receipt-strategy interface yet**; it has to be added (the earlier note that B was "anticipated
  behind the interface" does not hold).
- Every reader that checks a file against its receipt asks `ReceiptFolder.read(path)` or `.under(prefix)`: `DriveCache.sync`,
  `receipted_rows`, the reconcile paths, `receipt_repair`, `folder_merge`. They never open a `.sha256` file themselves.

## Design (one new reader, one new writer, one interface)
1. **Interface `ReceiptWriter`** (a small Protocol next to `ReceiptFolder`): `write(receipt) -> Receipt` (returns the receipt kept for
   the path). `ReceiptFolder` already has that method, so strategy A (one file per Drive file) is unchanged and stays in the tree.
   `DataStore` is typed against the Protocol instead of `ReceiptFolder`.
2. **Strategy B, `BatchReceiptWriter(folder, run_id)`** (the run id is checked when it is made, before the run writes anything to Drive): appends one line per Drive file to ONE file for the run,
   `receipts/_batches/<YYYY>/<MM>/<run_id>.tsv` (run ids are unique and time-sortable, so two runs never touch one file: no merge conflicts, the
   property the per-file layout was chosen for). A line has the same five fields a per-file receipt has plus the path
   (`path, sha256, size, written_at, writer, run_id`), written as ONE `O_APPEND` write of the whole line, after Drive accepted
   the file (rule W3 unchanged). The articles run and the clusters run are two workflow runs, so two batch files; each covers
   every Record file that run wrote.
3. **The reader finds a file inside a batch**: `ReceiptFolder.read(path)` and `.under(prefix)` look at the per-file receipt first and
   then at the batch files (an index of all `_batches/**/*.tsv`, built once per `ReceiptFolder` and kept current by the writer). So
   `DriveCache.sync`, `receipted_rows` and the other readers verify a batch-receipted file **without any change**: "a batch that
   cannot prove an individual file is unacceptable" is met because the proof of one file is one line, found by its path.
4. **Write-once, as today (W4)**: the same path with the same digest keeps the first line; a different digest for a path that
   already has a receipt (in any batch or per-file) is refused. A batch line is never edited or removed by the code.
5. **Torn or damaged batch**: a last line without its newline is ignored by the reader and reported as a problem, never read as a
   receipt; a line with the wrong field count is a problem. A Record file with no receipt anywhere is found by the existing
   reconcile (the writer's "missing receipt, same held bytes saved again" path) exactly as today.
6. **Wiring (the one line)**: `news/record/wiring.py` and `news/cluster_record/wiring.py` build `DataStore(drive, RAW_AREA,
   BatchReceiptWriter(receipt_folder(), run_id), ...)`. The commit step (`ops/commit_news_record.sh`, which `git add`s the receipt
   folders) is given `receipts/_batches` as well; nothing else in it changes.
7. **Existing news receipts** (written by the per-file strategy before this) stay as they are; the reader accepts both shapes.

## What does NOT change in the guarantee
Every Record file has its SHA-256, size, time, writer and run id recorded in GitHub; a changed Drive file is detected by the same
comparison (`DriveCache.sync`), and a missing or different receipt for a path is refused by the same rule. Only the packaging changes
(about 300 files a day become about one file per run). It is NOT stronger: a batch file can be edited in git like a per-file receipt
can; the protection against that is git history, same as before.

## Tests and plants (all offline)
- Every `put` of a run is findable by path through `ReceiptFolder.read` and `.under`, with the right digest, from the batch alone.
  Plant: the writer drops the line for one file -> that test fails ("a batch receipt missing one file's hash").
- `DriveCache.sync` over a news prefix receipted only by a batch: a Drive file whose bytes changed is reported DAMAGED, a missing
  one MISSING. Plant: the reader ignores batch files -> the sync finds no receipts and reports the problem (tampered file detectable).
- Same path, different digest in a second batch -> refused; same digest -> first line kept; a torn last line is ignored and reported.
- The news writers end to end with the batch strategy (article and cluster): every Drive file has a line, no per-file receipt files are made.
- `RECORD_CONTRACT.md`: row W4 names both strategies; a new row for the batch guarantee with its plants; the "Not guaranteed" list
  keeps the verified-cache coverage bullet. `EXPECT_SURVIVE == stated_only_rows` stays true.

## Built (27 Oct 2026)
`fno/ingestion/storage/batch_receipts.py` (`BatchIndex`, `BatchReceiptWriter`), `receipt.py` (the `Receipt` dataclass moved out so the two modules do not import each other; `receipts.py` still exports it), `ReceiptWriter` Protocol and the combined reader in `receipts.py`, `DataStore` typed to the Protocol, `DriveCache.sync` reports batch problems, `batch_receipt_writer()` in `data_wiring.py` used by the two news wiring roots, `receipts/_batches` added to the two news workflows' commit paths. Contract rows N6 to N8 (plants run). Existing news tests changed only where they patched the old `receipt_folder` or asserted the old `RECEIPTS` path.

## Round 1 of the code judges (judge_62) and what changed
- **B1, a damaged news line broke unrelated readers (true, reproduced).** Now a damaged line is never a crash and never a receipt
  (a digest that is not 64 hex characters, a non-numeric size, an unusable path, a carriage return, the wrong field count, a file that
  is not text are all `BatchProblem`s). A problem is shown only to a sync of a prefix that covers the file it names, or, if it names none,
  to a sync inside or around the batched area (`raw/news`); `data/flows`, circulars and pre-open never hear of it. **Way out for a
  torn tail:** a torn or malformed line that names a file stops mattering once that path has a valid receipt (the next run saves the
  file again and writes a valid line); a line that names no file proves nothing about any file and is a warning, not a failure.
- **B2, a short write could glue the next line on (true).** The writer loops until the whole line is written and raises if it cannot;
  before appending it refuses a batch file that does not end in a line break (`BatchBroken`), so a half line is never extended and the
  run ends red (the file is then re-saved and receipted by the next run).
- **M1:** a per-file receipt is read before a batch line, and a different digest between a batch line and a per-file receipt for the
  same path is reported. **M2:** this document now matches the code. **M3:** a line is read from its exact bytes (no newline translation).

## Fail closed (orchestrator, 27 Oct)
A Record file with no valid receipt line is never passed silently. Verifiers that walk receipts (`DriveCache.sync`, `receipted_rows`) cannot see a file that has none, in the per-file layout either; so `DriveCache.unreceipted(prefix)` walks the Drive folder and lists every file with no receipt (per-file or batch), and `data-cache sync <prefix> --unreceipted` reports them and exits 1. It is opt-in so the existing `data/vix` check is unchanged. A torn last batch line names its file (`path: its receipt line is cut short, so the file is not proved`) and the file is listed as unreceipted too. The news writers' own reconcile-before-write on the next run also re-saves a missing line.

**Where the guarantee lives (stated plainly):** tamper-evidence is the committed hash compared with the Drive file, plus git history; it is not a self-protecting receipt, in the per-file layout or the batch. A batch file edited in git can hide nothing that git history does not show.

## Questions for the orchestrator (settled)
1. One batch file per workflow run (so articles and clusters get separate files); the brief says "one receipt file per run
   covering both": they are two different workflow runs, so I read it that way. Say if you want something else.
2. SHARDED by the month of the run id (`receipts/_batches/YYYY/MM/`), not flat (orchestrator's call, 27 Oct: about 17,000 batch files a year would otherwise sit in ONE folder). The month comes from the run id, which starts with its UTC date; a run id without one is refused when the writer is made, before the run writes anything to Drive.
