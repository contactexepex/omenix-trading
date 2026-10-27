# Judge 48: P2b2 the news Record writer, code (judge #2)

Branch `story/P2b2-writer`, SHA `2ad37d21b969874a5ed0dc29bcbc2c83e58d2013`, lane 1. **FAIL** (round 1) on 2
should-fix. Write-once, revisions, repair, file-first, privacy and reconciliation all hold under my plants. The
production wiring is unpinned (the same gap as P2a's S1), and a retired feed's polls are stuck for good.

## Gates (`__pycache__` cleared)

745 passed; ruff check and format clean; imports clean; code size passed (the largest new file is 86 lines).

## The orchestrator's ten checks

| # | Check | Finding |
|---|---|---|
| 1 | Write-once | Enforced at the store: `GoogleDriveUploadStore.put` (`google_drive_upload.py:37-41`) and `LocalFolderStore.put` (`raw_store.py:82-87`) raise `RawFileConflict` on different bytes, and `ReceiptFolder.write` refuses a receipt with another SHA. The writer only ever puts the held bytes or a new path. Plant A2 (a changed article written over the article path) fails 3 tests, as `record_conflict`. Plant A1+A2 together (the writer overwrites **and** the store allows it, so a truly silent overwrite) fails 3 news tests, which assert the first file stays. MET |
| 2 | Two articles, one key | A3 (the revision not written) fails 2 tests; the collision test checks the revision file and its row. MET |
| 3 | Crash repair | (a) file, no receipt: the re-run finds the held file, `_document` saves the **held** bytes, the store no-ops, and the receipt and row are written. (b) receipt, no row: `ReceiptFolder.write` keeps the existing receipt when the digest matches (`receipts.py:53-56`), so the row is written. A4 (repair with the new bytes) fails 2; A5 (no repair) fails 1; A15 (`first_seen_at` compared) fails 3. MET |
| 4 | File-first | A6 (row before file) fails 1; the Drive-failure test checks no row. MET |
| 5 | Privacy | The test drives a marker title, host, path and query through the **real** writer, manifest, `ReceiptFolder`, report line and DEBUG logs, including a refused poll, and checks that the title is in Drive. A14 (an exception's text kept as the code) fails 1. The command path (line, alert, class-only error) is tested with the gate injected. MET |
| 6 | Reconciliation | A8 (the check removed) fails 1; A9 (an item skipped) fails 15. MET |
| 7 | Wiring | **NOT MET: S1** |
| 8 | Two edited tests | `test_pinned_installs` 15 -> 16 counts a new workflow's install and still requires `requirements.lock` for every one. `NOT_PACED += news-promote.yml` is right: the promote code reaches Drive only (`DriveSession`; no `PacedSession` or NSE host in `news/record`, `feeds.py` or the Drive stores); the workflow runs only `news promote`. `children()` is additive. MET |
| 9 | `feed_unknown`, kind limit | A10 (not counted) fails 1. The documented limit (kind from the newest list) is accurate, **but see S2** |
| 10 | Standards | Small single-purpose modules, constants at the top, no dead code found. MET |

## Findings

1. **S1 (should fix, tests only): the production wiring is not pinned.** Every test that reaches
   `build_news_promotion` replaces it with a fake (`test_privacy_cli_workflow.py:44,55,64`). The "writes only the
   Record, reads only Staging" test uses the test's own `Setup` wiring. Two plants in `news/record/wiring.py` leave
   all 745 green:
   - A11, the writer's store on `STAGING_AREA` instead of `RAW_AREA`: the Record is never written, articles land in
     Staging.
   - A12, the gate reading Staging from `RAW_AREA`.

   Fix: a test of `build_news_promotion` itself (on a fake Drive, as P2a's round-2 wiring test does), asserting that
   writes land under `raw/news/articles` or `raw/news/revisions` only and that the reads are under `staging/news`.
2. **S2 (should fix, code plus test): a feed removed from the newest list is stuck for good, and alerts on every
   run.** Kinds come from `latest().feeds` only. Reproduced on `2ad37d2` with the test helpers (scratch script, not
   committed): feed-02 has a poll staged 30 days ago and is then dropped from the list.
   - Promoting today's range: `feed_unknown 1`, ok False.
   - Promoting the old day itself: `polls 0 ... feed_unknown 1`, ok False.

   So the retired feed's polls can never reach the Record (lost from it, though kept in Staging). And the unknown
   check lists every feed folder whatever the range, so every later run exits 1 and alerts. The feed list is
   versioned write-once, so the kind is known from the older versions. Fix:
   - take kinds from the union of every valid version (a feed id never changes kind, which is the documented rule);
   - scope the unknown check to feeds with polls in the requested range;
   - add a test: a retired feed's old poll promotes, and a range without it is clean.
   - Related: `latest()` is called here without `used` or `lowest_version`, so a list edited in place, or rolled
     back, is not detected on the promote side. With union kinds, a changed kind for an existing id should be refused.

**Verdict: FAIL** (round 1). The core write-once machinery is sound and well pinned.

## Addendum 1: the orchestrator's items A and B, and the kind limit (2ad37d2; still FAIL, round 1)

**A. Commit on rejection: correct today, not pinned (S3).** In `news-promote.yml` the promote step is
`continue-on-error: true`, so a refused item (exit 1) does not fail the job. The commit step has only
`if: !inputs.dry_run`, so it still runs (the implicit `success()` stays true) and commits the good articles'
receipts and rows. The last step then turns the run red, and the command has already sent the alert. A
`concurrency` group (`news-promote`, `cancel-in-progress: false`) keeps two runs from appending at once. A job
cancelled at its 60-minute timeout commits nothing, and the next run's missing-row repair heals that from the held
bytes, so it is not a lasting lag. But neither half is tested. Both plants leave all 745 green:
- A16: the commit step limited to `steps.promote.outcome == 'success'`;
- A17: `continue-on-error` removed.

Either would strand the good records on every run that has a single rejection. **S3 (should fix, tests only):** a
workflow test that the promote step has `continue-on-error: true` and that the commit step has no outcome condition.

**B. A torn last manifest line: today it is neither tolerated nor safely loud (S4).** Reproduced on `2ad37d2` with the
test helpers (scratch script, not committed). Two articles recorded, then the last row cut with no trailing newline,
then a new run:
- **Cut inside the article id:** the run reads clean (`no_ops 2`, nothing rejected). The repair appends the row
  **onto** the torn line, leaving `2026-10-27,1aff2f3f02026-10-27,1aff2f3f0963...` in the manifest, which the commit
  step would publish. That is silent corruption.
- **Cut inside the SHA-256:** the manifest now holds a truncated hash for a recorded id, so every later run gives
  `record_conflict` for that article. That is loud, but permanent until fixed by hand.

My ruling: the load must check every row: 5 fields, a 64-hex id and hash, a known status, and an integer size.
- A malformed **last** line with no trailing newline is a torn write: drop it (truncate the file to the last full
  line) before appending, so the missing-row repair re-adds the row from the held bytes.
- A malformed line anywhere else stops the run with a fixed code.
- Add a test for each of the two cases above.

How likely is it? A hard kill during the few-byte append is rare, but `continue-on-error` means an OOM-killed promote
step is followed by the commit step, which would publish the torn file. **S4: should fix, code plus test.**

**The kind limit.** The orchestrator rules that "kind from the newest list" is an accepted, documented limit, and I
agree: the doc says so ("Do not change a feed's kind; add a new feed id"). **My S2 is a different case: a feed
removed from the newest list.** The documented rule never says not to retire a feed, and retiring one leaves its
staged polls unpromotable and makes every later run exit 1 with an alert (reproduced above). S2 stands.

**Verdict: FAIL** (round 1): S1 and S3 are tests only; S2 and S4 are code plus test.

## Addendum 2: 321faad (S1 and S2 fixed; S3 and S4 not yet addressed; FAIL)

Branch `story/P2b2-writer`, SHA `321faad7fed9bb6f7564c29628811a07e9b930a1`. **Gates** (`__pycache__` cleared): 752
passed; ruff, format, imports and size clean.

| Item | Fix | Plant | Failed |
|---|---|---|---|
| S1 the wiring | `test_wiring.py` runs `build_news_promotion` on a recording fake Drive | writer store on `STAGING_AREA` / gate reading `RAW_AREA` / reader on `STAGING_AREA` | 1 / 2 / 1 |
| S2 a retired feed | `kinds_ever_listed`, the union over every valid version; a changed kind gives `feed_kind_changed`; `feed_unknown` only for feeds with polls in the range | back to `latest()` only / the kind-change check removed / the unknown check unscoped | 2 / 1 / 1 |
| Judge #1's revision-name collision | a held revision with other fixed fields is a conflict | the check removed | 1 |

On `used` / `lowest_version` for promote: not needed now that promote does not call `latest()`. One residual
(reasoning only): `kinds_ever_listed` does not check versions against the fetcher's `feed_lists.csv` hashes. So a
feed whose only listing is in a version edited in place takes its edited kind silently; a conflicting kind still
stops the run. This is low risk and not blocking.

**Still open, both raised in Addendum 1. The SHA seems to have been frozen before they reached the implementer:**
- **S3:** plant A16 (commit only when promote succeeded) still leaves all 752 green.
- **S4:** reproduced again on `321faad`. A line torn inside the article id gets the repair row glued onto it
  (`2026-10-27,1aff2f3f02026-10-27,1aff2f3f0963...`) and the run reads clean.

**Verdict: FAIL** on `321faad`, on S3 (tests only) and S4 (code plus test). These are round-1 findings that crossed
the freeze, so whether `321faad` counts as round 2 is the orchestrator's call. A SHA that adds S3 and S4 alone gets a
quick review from me.
