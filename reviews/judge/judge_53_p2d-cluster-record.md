# Judge 53: P2d (the news cluster record), judge #1 of two

**SHA:** `e1febbd20b2536fae2c25364cec24cfa42b3454b` (`story/P2d-cluster-record`, base aa8e355). It contains d5ed23b (the
guard refactor) and e1febbd (the cluster record). Lane 1.
**Verdict: FAIL, round 1 of 2, on one untested fail-safe branch.** Everything else holds under attack.

## Gates

- Suite: 836 passed, 2 runs out of 2.
- ruff and imports (469 files): clean.
- Size: 3 passed.

## 1. The guard refactor is never weaker (strong evidence: the diff read, plants)

`ops/commit_news_record.sh` is the merged P2b3 step, parameterised by `MANIFEST`, `RECEIPTS` and `COMMIT_MESSAGE`. It
keeps the same branches, the discard, the always-committed receipts and `exit "$broken"`. `news-promote.yml` now calls
it with the same manifest, receipts and message text.

One difference, in the safe direction: a receipts folder that does not exist is skipped. The old `git add "$RECEIPTS"`
would have failed the step.

The P2b3 real-git tests assert the same outcomes, and only the way they find the script changed. The broken-branch
test now pins that the receipts are added after the branch, for both outcomes.

| Plant | Result |
|---|---|
| Guard bypassed | caught |
| Discard removed | caught |
| Exit swallowed | caught |
| Receipts never added | caught |
| Wrong broken flag | caught |
| The guard checks `articles.csv` instead of `$MANIFEST` | caught |

**The concurrency group.** Both workflows use `concurrency: news-record` with `cancel-in-progress: false`, so a cluster
run queues behind a running promote and never reads a half-promoted window. Neither run is cancelled. This is correct.

## 2-8. The cluster record (plants and code read)

**2. The writer's own write-once refusal.** `test_the_writer_itself_refuses_to_overwrite_even_if_the_store_would` uses
an overwriting store. The plant that turns the writer's held-bytes check off is caught.

**3. Reconciliation**, each part pinned on its own:

| Plant | Result |
|---|---|
| Duplicate-member check off | caught |
| Made-up-member check off | caught |
| Sum check off | caught |
| Write despite a rejection | caught (3) |

Reconciliation runs before `_write`.

**4. Fail-safe.**

| Plant | Result |
|---|---|
| `article_unreadable` silenced | caught |
| A *damaged* earlier file ignored | caught |
| A listed-but-missing earlier file ignored | **survives**; see R1 |

**5. Privacy across the whole chain is not vacuous.** The test stages a real poll, promotes it through the real P2b2 gate
and runs the real P2c and `ClusterRun`, with DEBUG captured. It scans the report line, the alert, the logs,
`clusters.csv`, every receipt and the cluster file itself for the headline, host, path, query, "Outlet", "nifty" and
"rally": none appear. The headline is present in private Drive only. Cluster paths carry the version and stamp only.

**6. Conflict and repair.** Other bytes at a name give `cluster_conflict` plus the "investigate" alert, and the first
file stays. Same bytes give a no-op. A missing row is repaired from the held bytes: a plant that always re-puts is
caught.

**7. File first.** A plant that writes the row before the put is caught. A Drive failure leaves no receipt and no row.

**8. Determinism.** A closed window run again is a no-op (tested).

## 9. The edited tests and the wiring

- 17 installs: the new `news-cluster.yml` uses `requirements.lock`. There is no new dependency.
- `NOT_PACED += news-cluster.yml` is right: the run reaches Drive (DriveSession) and Slack only.
- `NewsManifest(folder, file_name)` and `recorded_since` are additive.
- An AST test pins `writer.py` as the only caller of `put` in the package.

## 10. The documented flags: both acceptable

- **(a)** An article first seen before the candidate net but future-dated by its feed is missed. This is rare and
  documented; the remedy is a wider `MARGIN`.
- **(b)** The window end is floored to the hour. A cluster run in the same hour *after* a further promote gives a loud
  `cluster_conflict`, never an overwrite. The concurrency group plus the runbook ("promote first") covers it.

## Required to PASS

### R1. "Listed but unreadable" earlier file: the branch is untested

Plant: in `ClusterRun._previous`, `raise ValueError("listed but unreadable")` becomes `return ()`. **836 passed.**

The damaged-bytes path is tested; the path where the file is listed but its read returns None is not. With the plant,
lineage (`previous_cluster_ids`) is silently lost and the file is written anyway, against fail-safe item 4.

Fix: a test with a listed earlier file whose `get` returns None, asserting `previous_unreadable` and nothing written.

## Not blocking (should-fix)

- **A torn `clusters.csv`.** The cluster run does not call `check_appendable` on `clusters.csv` before its Drive put,
  as the P2b2 gate does for `articles.csv`. A torn `clusters.csv` would make the put succeed and the row fail
  (`cluster_record_failed`). The guard keeps that out of `main`, and a re-run of the same window heals it, so the impact
  is low. A pre-write check would match P2b2.
- **Skipped rows.** `ArticleSource` does not report the articles manifest's skipped rows. The guard keeps such rows off
  `main`, so this is defensive only.

## Addendum 1: round 2, 5aa0af3: PASS

Reviewed `5aa0af341c2d8273828d20792c5d6a83223ecc5b`. The delta is `run.py` (+9), `writer.py` (+8),
`article_source.py` (+5), tests and the story.

**Gates:** 839 passed, 2 runs out of 2. ruff, imports (469 files) and size are clean.

**R1 is closed.** The plant that ignores a listed earlier file whose read returns None is now caught.

**Both should-fixes are done:**
- `writer.check_ready()`, which is `check_appendable` on `clusters.csv`, runs before any read or Drive write. A torn line
  gives `manifest_broken`, and the plant removing it is caught.
- Skipped rows of either manifest give `manifest_row_skipped` and nothing is written. The plants silencing each side are
  caught.

**No regression:** the writer-conflict and guard-bypass plants are still caught.

**Verdict: PASS (strong evidence).** Round 1's holds stand. P2d needs judge #2's PASS as well before it merges.

## Addendum 2: the bounded re-check, 2f2355e: PASS

Reviewed `2f2355ecd89a234d14ba33895924f5ca79da8dc9`, which is 5aa0af3 plus F1 and F2 from judge #2's round 1.

**Gates:** 844 passed, 2 runs out of 2. ruff, imports and size are clean.

**F1 is a real bug, and it is fixed.** Under `set -e`, a failure on the left side of `A && B` does not stop the script.
So a failed `git pull` skipped the push, and `exit "$broken"` (which is 0) still ended the run green with nothing
pushed. The same line is on `main` today in `news-promote.yml`, so merging P2d fixes it there too. Each command is now
checked on its own (`|| exit 1`).

| Plant | Result |
|---|---|
| The push failure ignored | caught |
| The `&&` line restored | caught |
| The pull failure ignored | survives (equivalent; see below) |

**The pull-check equivalence holds (reasoning only).** A pull fails only when:
- origin cannot be reached, in which case the push fails too;
- or the fetch brings new commits that cannot be merged (a conflict, untracked files that would be overwritten, or
  the commit hook refusing the merge commit), in which case `HEAD` does not contain origin's tip and the push is
  rejected as non-fast-forward.

If the merge itself completed and only a later hook failed, `HEAD` is up to date, the push succeeds, and the run really
did push. So "green means pushed" holds without the pull check. The story documents this, and keeping the pull check
as a defence is right.

**F2.** A window end later than the current hour is refused with `window_in_future` (an alert and exit 1) before
anything runs. The plants "bound widened by one hour" and "check off" are caught.

**No regression:**

| Plant | Result |
|---|---|
| R1, listed-but-missing ignored | caught |
| The writer's own conflict check off | caught |
| Guard bypassed | caught |

Everything else in Addendum 1 stands.

**Verdict: PASS.** Both judges have now passed P2d, so P2d can merge.
