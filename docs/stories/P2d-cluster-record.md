# P2d: the cluster record — P2c's clusters written to the Record (PLAN)

PLAN for the orchestrator's check before any code. Lane 1, **two judges** (it writes the Record: write-once data, receipts, the
privacy rule). Design and invariants: [P2-news-dedup.md](P2-news-dedup.md); the pure clustering it runs is P2c
([P2c-clustering.md](P2c-clustering.md)); the write discipline it reuses is P2b2/P2b3 ([P2b-article-gate.md](P2b-article-gate.md)).
Built and tested offline only; the first real cluster file is the owner's go-live step, and the workflow is `workflow_dispatch` only.

## What it writes

- **One cluster file per run**, `news/clusters/<ALGORITHM_VERSION>/<window end>.json` in the Record (`raw` area), where the window
  end is the run's as-of time in UTC (`YYYYMMDDTHHMMSSZ`). Deterministic JSON: sorted keys, header `{format, algorithm_version,
  window_end, window_hours, input rule}`, then `clusters` (`cluster_id`, `anchor_key`, `member_keys`, `previous_cluster_ids`) and the
  counts `clustered`, `outside_window`, `repeated_keys`. **Hash ids and counts only**: no title, URL, query, feed id or outlet.
- **Write-once, file first.** `DataStore.put` (Drive, then the SHA-256 receipt), then one row in `research/data/manifests/news/clusters.csv`
  (`date,article_id,status,sha256,size_bytes`; the id column holds the SHA-256 of the file's path, so it stays a 64-hex hash). The same
  bytes again is a no-op; **other bytes at an existing name is a reported conflict** (design N9), never an overwrite. A changed
  algorithm is a new version folder, so an old file is never touched.
- **Reuse, not a second copy.** `NewsManifest` gains a `file_name` argument (default `articles.csv`) and keeps its `CsvRowLog` append,
  per-row checks, torn-line refusal and `problem()`. `check-manifest` checks both files. The workflow's commit step (guard, receipts
  always, manifest only when whole, exit non-zero when broken) is moved out of `news-promote.yml` into one `ops/` script both
  workflows call, so there is one definition of the guard. Reasoning: two YAML copies would drift (the judges' own point on P2b3).

## What it reads (and cannot change)

- **The articles** from the Record, **read only** (a wiring test proves the reader has no `put`). To avoid reading every article ever
  recorded, candidates come from `articles.csv`: the rows dated within the window plus one day, then one Drive read per key. An article
  first seen before that but dated in the future by its feed is missed (reasoning only; rare, and the next version can widen it).
- **The previous cluster file** of the same version (the latest with an earlier window end), to fill `previous_cluster_ids`. A new
  version has no previous file and names none.

## Reconciliation and alerts

Before anything is written: every member key of every cluster is an article that was read; `clustered + outside_window` equals the
distinct keys read; no key is in two clusters. A mismatch writes nothing and exits 1 with a fixed code (`cluster_not_reconciled`).
Other fixed codes: `cluster_conflict` (other bytes at the name), `cluster_record_failed` (Drive or the manifest would not take it),
`article_unreadable` (a candidate key whose file is missing or damaged: counted, never skipped silently). One printed line of
counts, also the alert; the failure alert step and the commit guard are the same as `news-promote.yml`.

## The reader (design N10, "as known at T")

A pure helper over the listing: the latest file with window end at or before T **whose window covers the story's effective time**,
so a story older than the newest file's window is still reachable. Tested against a store with several files.

## Files (`fno/ingestion/news/cluster_record/`, each small)

`cluster_file.py` (bytes, path, parse), `article_source.py` (manifest rows to articles, read only), `writer.py` (file, receipt, row;
conflict), `run.py` (read, cluster, reconcile, write), `reader.py` (N10), `wiring.py` (the composition root); `news cluster --as-of`
in `news/cli.py`; `news-cluster.yml` (dispatch only, same concurrency group as `news-promote.yml` so runs are serial); the `ops/`
commit script.

## Tests and the invariant each plant guards

Deterministic bytes in any article order; same bytes again is a no-op; other bytes at a name is `cluster_conflict` and nothing is
overwritten; a new version writes a new path; file first (a failing Drive leaves no receipt or row); the previous file's ids reach
`previous_cluster_ids`; reconciliation fails when a cluster names an unread key, when an article is dropped and when one is in two
clusters; an unreadable candidate is counted; the reader reaches a story older than the newest window; the reader wiring has no
`put`; the workflow is dispatch only and shares the concurrency group; the commit script behaves as in the P2b3 real-git tests, for
both manifests; **the master privacy test extended** (marker headline, URL, query, outlet and entity through P2b1, P2b2, P2c and
P2d to the cluster file, manifest, receipt, report line, DEBUG logs and the alert, which may contain only hash ids and counts).

## New risks, said plainly

- **Volume (reasoning only).** An hourly run is 24 files a day, 8,760 a year, each a few tens of kilobytes (a window of about 300 to
  1,000 articles at 66 bytes a key): roughly 0.3 to 0.9 GB a year in Drive, plus 8,760 receipts and manifest rows in the public
  repository. Running every six hours cuts that to a quarter. Ask: which cadence, or hourly and revisit? (owner go-live; the code does
  not depend on it).
- **Same window end, other bytes.** The name is the window end, so a second run in the same hour after more articles were promoted
  would conflict. The workflow floors the as-of time to the hour and runs after promote; a conflict is reported, not hidden, and the
  next hour's file carries the new articles. Asked of the judges: is a reported conflict acceptable, or should a rerun in the same hour
  be refused earlier with a clearer code?
- **Untuned clustering.** Any story count or corroboration number from these files is untrustworthy until the threshold is re-tuned on
  real data (P2c). The file header names the algorithm version so a consumer can tell.

## Not in P2d

Corroboration or wire-credit counting (owner decision), tuning the threshold, scheduling (the owner's go-live), the first real file.

## P2d as built

- **Step 1, the guard (own commit):** the commit step is now `ops/commit_news_record.sh` (env `MANIFEST`, `RECEIPTS`, `COMMIT_MESSAGE`),
  called by `news-promote.yml` and `news-cluster.yml`. **Behaviour-preserving:** the merged P2b3 real-git tests (a whole manifest
  commits; a torn one is discarded, not committed, red with the alert and its receipts still committed; a torn one over a good
  committed one leaves main with the good one) run unchanged against the script, plus the same case for `clusters.csv`. The step
  that used to be inline in the workflow is now one `bash` line. `check-manifest` takes `--file` (default `articles.csv`);
  `NewsManifest` takes a `file_name`. Both news workflows now share one concurrency group, `news-record` (the promote one was
  `news-promote`), so a promote and a cluster run are serial. Disclosed test edits: seventeen workflow installs; `news-cluster.yml`
  joins `NOT_PACED` (it reaches Drive only).
- **Code (`fno/ingestion/news/cluster_record/`):** `cluster_file` (path, deterministic bytes, parse), `article_source` (read only),
  `writer` (the one `put`), `run` (read, cluster, reconcile, write), `reader` (design N10), `report`, `wiring`; `news cluster
  [--as-of]` in `news/cli.py`; `news-cluster.yml` (dispatch only). Four new codes in `news/codes.py`, plus `previous_unreadable`.
- **Candidate net:** manifest rows recorded on or after the window start minus two days, then one Drive read per key; P2c applies
  the exact window. **Flag for the judges:** an article first seen before the net but dated in the future by its feed is missed;
  reasoning only, rare, and widening `MARGIN` is the remedy.
- **Order of runs:** cluster only a window whose end has passed, after the promote that covers it (shared concurrency group). The
  default window end is the current hour floored, so every article first seen before it is already in the Record only if that promote
  has run. A `cluster_conflict` means inputs, version or determinism changed for a closed window: investigate, never overwrite.
- **Proof:** 27 cluster-record tests and 12 guard tests; plants fail a test for the conflict check (also with a store that overwrites),
  file-before-row order, the missing-row repair, each reconciliation check on its own (duplicate member, made-up member, counts),
  the version in the path, the strictly earlier previous file, a damaged previous file, an unreadable article, the candidate net,
  the reader's window cover and its `known_at` bound, the member order, and the conflict alert text.

## Order and gates

After P2c merges. Full suite, ruff, imports, numbers, size (350 per file and class), record scan, mutation plants for every line above,
two judges.
