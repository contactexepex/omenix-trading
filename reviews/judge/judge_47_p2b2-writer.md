# Judge 47: P2b2 (the news Record writer), judge #1 of two

**SHA:** `2ad37d21b969874a5ed0dc29bcbc2c83e58d2013` (`story/P2b2-writer`, base 3ef9ed2). Lane 1: it writes the
write-once Record.
**Verdict: FAIL, round 1 of 2.** Write-once, file-first and crash repair all hold under attack. Two gaps remain: a
revision's row and receipt are not pinned, and a retired feed turns every later run red.

## Gates

- Suite: 745 passed, 2 runs out of 2.
- ruff and imports (440 files): clean.
- Size: 3 passed. `fno/ingestion/news/record/` is 261 lines across 5 files, each under 90.

## What holds (strong evidence: code read, plants)

**1. Write-once.** It is enforced in two layers below the writer:
- `GoogleDriveUploadStore.put` (`google_drive_upload.py:37-41`) and `LocalFolderStore.put` raise `RawFileConflict` when
  the bytes at an existing path differ;
- `ReceiptFolder.write` (`receipts.py:50-56`) refuses a different SHA-256;
- `NewsManifest.add` refuses a recorded id with another SHA-256.

| Plant | Result |
|---|---|
| The local store silently overwrites | caught |
| The writer ignores the held file and always records (this hits the conflict) | caught |
| The manifest conflict check removed | caught |

**3. Crash repair uses the held bytes.** `_document` re-saves `held`, not the newly built bytes. A plant that re-saves
the new bytes is caught (`test_a_stopped_run_is_repaired_with_the_held_bytes_not_new_ones` deletes both the receipt and
the manifest row). A later poll with a different `first_seen_at` compares equal on the fixed fields, so it is a NO_OP:
there is no rewrite and no conflict. Different bytes at the same path surface as `record_conflict` through the
`RawFileConflict` catch.

**4. File first.** A plant that writes the manifest row before the Drive put is caught. A failed Drive put gives
`record_failed`, no row, and no message text.

**5. Privacy is not vacuous.** The master test runs the real `ArticleWriter`, `DataStore`, `ReceiptFolder` and
`NewsManifest` on local stores, with a marker headline, host, path and query, a missing-title item and a refused
(DOCTYPE) poll, and DEBUG captured. It scans the manifest, every receipt and the report line, which is also the printed
and alerted text. The headline is present in private Drive only. Receipt and manifest names carry hash keys only.

**6. Reconciliation.** Plants that disable `not_reconciled`, or stop counting `record_failed`, are caught.

**7. Wiring.** A plant that writes revisions under `staging/` is caught.

**8. The edited tests.** Pinned installs 15 → 16 is the new workflow's `requirements.lock` install, and every install is
still asserted to be locked. `NOT_PACED += news-promote.yml` is right: the promote path reaches Drive (DriveSession,
not paced) and Slack only, and nothing in `fno/ingestion/news/record/` touches `PacedSession` or `SHARED_PACER`.
`staging.children()` is additive.

## Required to PASS

### W1. A revision's manifest row and receipt are not pinned (plant survives)

Plant: in `_revision`, replace `self._save(...)` with a bare `self.store.put(path, data)`, so the bytes are written but
there is no manifest row. **745 passed.**

The two key-collision and changed-article tests check the revision *file* and the outcome count, never the revision
row or receipt. This is your item 2 ("bytes exist **and** row appears"), and the rule of one SHA-256 receipt per Drive
file.

Fix: assert one manifest row with status `revision` and the revision's SHA-256, and a receipt for the revision path. The
plant must then fail.

### W2. A retired feed turns every later run red, for ever

Reproduced. Stage a poll for `feed-02`, promote it, then drop `feed-02` from the feed list (as the owner would on
retiring it). Then promote a different day, with only `feed-01` polls in range:

```
news promote: polls 1, items 1, recorded 1, revisions 0, no_ops 0, feed_unknown 1   ok=False
```

`NewsGate.promote` checks *every* feed folder ever staged (`staging.children(SOURCE)`), whatever the date range.
Staging is never pruned, so from then on every run exits 1 and alerts #fno-desk. A permanently red job hides real
failures, which turns the alert into noise.

Fix, either:
- report `feed_unknown` only for feeds that have polls inside `--from`..`--to`;
- or keep retired feeds in the list with a `retired` flag and their kind, and skip them silently.

Add a test: a retired feed's old polls do not fail a run over a later range.

## Notes, not blocking

- **Revision file names.** A revision file is named by 8 hex characters (32 bits) of its fixed fields. If two
  *different* revisions of one key share those 8 characters, the second is taken as the first (a NO_OP) without
  comparing bytes, so it is dropped. The odds are about 2⁻³² per pair, which is negligible, but comparing the held
  revision's fixed fields before calling it a NO_OP would close it for one line.
- **The `record_conflict` comment.** It says "the manifest holds another SHA-256", but Drive and receipt conflicts land
  there too. Reword.

## Hard lines

No orders, no secrets, no live call. The workflow is dispatch-only, `--from` is required, and it commits only the news
manifest and `receipts/raw/news`. Write-once holds in two layers.

## Addendum 1: the orchestrator's two added items (same round)

**A. Commit on rejection: holds (strong evidence: workflow read).** The promote step is `continue-on-error: true`, so the
job stays successful and the next step's implicit `success()` passes. "Commit the news manifest and receipts" therefore
runs whenever `!dry_run`: whatever the writer saved (receipts and rows of the good articles) is committed. Then the last
step `exit 1`s on `steps.promote.outcome != 'success'`, and the command itself has already sent the alert.

So with 1 rejected and 2 good items, the 2 good receipts and rows are committed, the run goes red, and the alert fires.
I did not run Actions (that is the owner's go-live), but the step logic is unambiguous.

**B. A torn trailing line: required, because the failure is *silent*, not loud.** I reproduced it. Write one good row,
then append a torn row with no newline (`...,reco`), as a crash during the write would leave:
- `NewsManifest` loads it **without error**: the torn row simply does not count as recorded;
- the next `add` **glues** the new row onto the torn line, giving `...,reco2026-10-28,ccc…`;
- after a reload, the new article id is **not** in `recorded`.

The workflow would commit those garbage rows to the public, append-only manifest. They would heal one run later (the
missing-row repair re-adds them), but the corrupt lines stay in history for ever.

`NewsManifest` re-implements CSV appending instead of reusing `CsvRowLog`. The repository already guards exactly this:
`CsvRowLog.check_appendable` raises `TableFileBroken` when the file does not end with a newline (`row_log.py:59-61`).

Fix (DRY, small):
- write the manifest through `CsvRowLog`, calling `check_appendable` before each append, so a torn file stops the run
  loudly before anything is glued;
- make the load skip, and count, a row whose fields are not all valid, rather than mis-reading it;
- add a test with a torn trailing line: nothing is appended, and the run reports it.

I prefer this loud refusal plus a hand-fix over silently adding a newline, because the hand-fix keeps a human looking at
a crashed run.

**The feed kind from the newest list:** confirmed as the documented, accepted limit (story: "Do not change a feed's
kind; add a new feed id"). It is not a finding.

**Verdict unchanged: FAIL.** Required: W1, W2 and B.

## Addendum 2: round 2, 321faad: FAIL, B (the torn manifest line) not addressed

Reviewed `321faad7fed9bb6f7564c29628811a07e9b930a1`, which is 2ad37d2 plus fafff43 and 321faad.

**Gates:** 752 passed, 2 runs out of 2. ruff, imports (441 files) and size are clean.

**Closed (strong evidence: plants and a re-run of my probe):**

| Item | Evidence |
|---|---|
| W1 | The "revision bytes without a row" plant is now caught. |
| W2 | My retired-feed probe now gives `ok=True` for a later range. The "unknown check unscoped" and "never reports unknown" plants are caught. |
| The sha8 compare (should-fix) | A held revision with other fixed fields is now `RawFileConflict` (→ `record_conflict`), never a NO_OP. The plant removing the compare is caught. |
| The `record_conflict` comment | Widened. |
| Judge 2's S2: `kinds_ever_listed` | Feed kinds now come from the union of every valid version. One id with two kinds stops the run with `feed_kind_changed`; an unreadable version is skipped. Plants "a kind change allowed" and "kinds from the newest list only" are caught. This is sound, and it is stricter than the documented limit, because a kind change is now caught rather than only documented. |

**Still open: B, required (Addendum 1).**

`fno/ingestion/news/record/manifest.py` is unchanged from 2ad37d2 (`git diff --quiet`). My reproduction at 321faad:
after a torn trailing line, the next `add` is still glued on (`reco2026-10-28`), and the new id is still not recorded on
reload.

This is a silent corruption of a public, append-only file. The fix is still: write through `CsvRowLog` with
`check_appendable` (a loud `TableFileBroken`), skip and count malformed rows on load, and add a torn-line test.

**Verdict at 321faad: FAIL (round 2 of 2)**, on B alone. Everything else passes. It goes to the orchestrator under the
two-round rule. My recommendation: fold B (a few lines plus one test), then a bounded re-check of B only.
