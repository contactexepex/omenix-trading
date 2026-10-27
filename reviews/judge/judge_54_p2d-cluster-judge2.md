# Judge 54: P2d the cluster record, and the shared news commit guard, code (judge #2)

Branch `story/P2d-cluster-record`, SHA `e1febbd20b2536fae2c25364cec24cfa42b3454b` (the guard refactor alone is
`d5ed23b`), lane 1. **FAIL** (round 1) on 2 should-fix. The write-once, reconciliation, fail-safe and privacy
machinery all holds under 22 plants. One gap is in the commit script and one in the CLI.

## Gates (`__pycache__` cleared)

836 passed; ruff check and format clean; imports clean; code size passed.

## The orchestrator's checks

| # | Check | Finding |
|---|---|---|
| 1 | Guard refactor, never weaker | `ops/commit_news_record.sh` has the same logic as the merged P2b3 step. The only changes: a receipt folder is added only if it exists (a missing one used to fail `git add`), and `RECEIPTS` may list several folders. The P2b3 guard tests changed only in how they call it, plus an assert that the step is exactly the script call. Plants: guard removed (3 failed), torn manifest staged (4), skip exits 0 (3), receipts not added (4), no restore (2), wrong manifest file (1), and the two halves of `problem()` (1 / 7). MET. The shared `news-record` concurrency group serialises promote and cluster, which both write the news manifests and receipts, so that is correct. **But see F1**, a gap the merged guard already had. |
| 2 | The writer's own refusal | `ClusterWriter.write` raises on other held bytes **before** any put. W1 (the check removed) fails 1, the test with an overwriting store. MET |
| 3 | Reconciliation, each part alone | R1 (duplicate member), R2 (made-up member) and R3 (the sum) fail 1 / 1 / 2. R4 (write even when not reconciled) fails 4. MET |
| 4 | Fail-safe | R5 (a damaged previous file ignored) fails 1; R6 (unreadable articles allowed) fails 1. MET |
| 5 | Privacy, whole chain | The test runs a marker headline, host, path and query, plus "nifty" and "rally", through the real gate, P2c and P2d into the cluster file, manifest, receipt, line, logs and alert, and checks that an unexpected error prints its class only. MET |
| 6 / 7 | Conflict never overwrites; file first | W2 (no repair of a missing row) 1; W3 (row before file) 1. MET |
| 8 | Determinism | covered by the rerun no-op test (no plant of mine; P2c's determinism was judged in P2c) |
| 9 | Two edited tests | 17 installs counts a new workflow with a hash-locked install. `NOT_PACED += news-cluster.yml` is right: the cluster wiring reaches Drive only (`build_owner_drive`, no session to a feed). WI1 (cluster rows in `articles.csv`) fails 1; WI2 (the store on Staging) fails 1. MET |
| 10a | A future-dated article missed by the net | accepted as documented (reasoning only: a feed date more than 2 days ahead is bogus anyway; the remedy is a wider MARGIN) |
| 10b | Window end floored to the hour; promote first | accepted. A late promote then makes a second cluster run for the same hour a `cluster_conflict`, alerted, and the first file stands. That is consistent with "as known at T", since those articles were not yet in the Record at T. The shared concurrency group makes the runs serial but does not order them, so the runbook should say "promote, then cluster". |
| 11 | Standards | small modules (the largest is 91 lines), one guard script, no dead code found. MET |

## Findings

1. **F1 (should fix, script plus test): the commit step reports success when the pull or push fails.** In
   `ops/commit_news_record.sh` (and, before it, the merged P2b3 step):
   - The line `git pull --no-rebase --no-edit origin main && git push origin HEAD:main` sits under `set -e`. A
     failing command on the left of `&&` does not trigger `errexit`.
   - So a failed pull skips the push, and the script reaches `exit "$broken"`, which is 0 for a whole manifest.
   - Reproduced (scratch script, not committed): `set -e; broken=0; false && echo pushed; exit "$broken"` exits 0.

   The run goes green with nothing published, the failure-alert step does not fire, and the runner is then thrown
   away. The repair re-creates the rows, but the receipts carry the new run's time, not the original evidence time.
   No test catches it: plant S7 fails 3 tests only because they then find nothing pushed, not because the step's
   exit is checked. I missed this when I passed P2b3. Fix: `git pull --no-rebase --no-edit origin main || exit 1`,
   then `git push origin HEAD:main || exit 1`, and a real-git test with an unreachable origin that expects a non-zero
   exit. It belongs in this SHA because the script is now the one guard for both workflows.
2. **F2 (should fix, code plus test): `--as-of` accepts a future moment, which writes a permanent cluster file for a
   window that has not closed.** `_utc_moment("2027-10-27T12:00:00+00:00")` is accepted (now is 2026-10-27). Such a
   run writes `news/clusters/v1/20271027T120000Z.json` into the write-once Record with today's articles. When that
   hour really comes, the scheduled run's bytes differ, so every run for that window is a `cluster_conflict`, and the
   "as known at T" reader returns the early file. A typo in the year is enough. Fix: refuse an `--as-of` later than
   now (floored to the hour) with a fixed code, and add a test.

**Verdict: FAIL** (round 1). Both fixes are a line or two plus a test.

## Addendum 1: 5aa0af3 (judge #1's items folded; my F1 and F2 not yet; FAIL)

SHA `5aa0af341c2d8273828d20792c5d6a83223ecc5b`, which replaces `e1febbd`. **Gates** (`__pycache__` cleared): 839
passed; ruff and imports clean. The change touches `run.py`, `article_source.py` and `writer.py` only; `ops/` and
`news/cli.py` are unchanged.

| New item | Plant | Failed |
|---|---|---|
| `clusters.csv` checked appendable before the Drive put | the check removed | 1 |
| Not-whole rows in either manifest reported, nothing written | ignored | 1 |
| Judge #1's R1: an earlier file listed but unreadable (`None`) | treated as no previous file | 1 |
| Carried: the writer's own refusal / write when not reconciled | removed | 1 / 5 |

All of these hold. The rest of the first report carries over: the code it covers is unchanged.

**Still open, crossed in flight. My findings were sent after this SHA was frozen:**
- **F1:** `ops/commit_news_record.sh` is unchanged, so a failed `git pull` still exits 0 (green, nothing pushed).
- **F2:** `--as-of` still accepts a future moment.

**Verdict: FAIL** on `5aa0af3`, on F1 and F2. A SHA that adds those two fixes and their tests gets a quick
re-verify from me.
