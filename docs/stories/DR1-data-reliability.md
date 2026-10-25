# DR1. Data reliability: availability and consistency (audit 14-23 Oct 2026, and design)

**Builder:** session_01SPR8hz6AY8S99wE6ypFRik. **Orchestrator:** session_01VG1RqxLFUVdvvPuMRYZtDH. **Lane:** 1 for
every build part (outside services, records). This file is step 1 (the audit) and the design for the owner's review;
nothing is built before the orchestrator's go.

Owner, 23 Oct 2026: "If we have problem reading the data or fetching the data, then we need to fix it. We cannot just
simply say we could not read the data. That is also unacceptable." And, on the store fix: "Our reliability is not just
the data, but our reliability is also the quality of the data as well ... One, the data must be available all the time
... The second is data consistency. We do not accept corrupted, stale, or incomplete data."

Evidence labels: **strong** (data or code proves it), **some**, **reasoning only**. Sources: journal/runs/*.json,
research/ops/capture_errors.csv, receipts/, git history of main, the Drive folder (searched by name, read-only),
GitHub job logs, #fno-desk and #fno-forecast (215 + 4 messages, 14-23 Oct).

## 1. The audit: what failed, why, who owns it

One line per failure; "state" is on 23 Oct about 21:30 IST.

### A. Drive reads and writes (the core of the owner's complaint)

| # | What failed, when | Root cause (label) | Owner | State | Fix |
|---|---|---|---|---|---|
| 1 | FL1 evening edition "today's close was not read" 22 and 23 Oct; morning GIFT section never shown | `ReceiptFolder.under` (fno/storage/receipts.py:64-70) treats its prefix as a folder; a file path returns `[]`, and `DriveCache.sync` (drive_cache.py:40-57) reports an empty success. Callers with a file path: forecast_lab/a4h_closes.py:27, forecast_lab/sections/gift.py:34; `data-cache sync <file>` prints "0 files", exit 0 (strong, code) | O9 013u1Ac2 (store), FL1 01FWkBH4 (callers) | O9 fix on story/o9-sync-file 494d97df3, with judge F; no FL1 branch needed once it merges | O9's fix (a sync that matches nothing is a problem) plus DR1-c contract tests through the real cache |
| 2 | 23 Oct 15:40 "step close_read failed: exit code 1, nothing printed"; two Drive files `2026-10-23.first.raw.json` (114,130 and 114,129 bytes, 0.8 s apart) | Two `daily run` processes in one checkout: the routine took run A's NotBefore-15:40 wait for a hang and started a rerun; both read NSE at 15:40. `GoogleDriveUploadStore.put` checks then creates (google_drive_upload.py:32-42, "meant for one writer at a time", :7); Drive has no unique names. The loser's `ReceiptFolder.write` raised RawFileConflict (receipts.py:52-55), uncaught in close_read/reader.py:76; the traceback went to the private log only. The journal shows "ok" because RunLog keeps the last writer per step (commits dfbd8c0fb failed, ed4caf499 ok) (strong) | O1 014zYLf1 (lock), A4h 01MKtUHB, O9 (store) | stray copy trashed by the A4h builder (owner approved); day-run lock sent to O1; not built | DR1-e (section 3) |
| 3 | 23 Oct 16:00 "full run log NOT saved to Drive (RawFileConflict)" | Not a mutable log: the name is unique per run (daily/full_log_archive.py:15,35). Two folders named `daily_runs/full` exist, created 22 Oct 10:03:30.564Z and .679Z by two runs ending in the same second (`_create_folder`, google_drive_upload.py:49-57, check then create). Every later walk into `full` raises (google_drive.py:78-79), so this fails **every day** until merged. Run 20261022T100328Z-39767f's log has no receipt (strong, Drive) | O1, O9 | owner: "DR1 merges, judged" | DR1-0 (section 4) |
| 2b | Lasting harm of any duplicate | `_child` raises on two matches and `_listing` raises "two items named" (google_drive.py:78-79, 121-122): one stray copy makes a whole folder unreadable (reasoning from code) | O9 | not started | DR1-e reader rule |
| 5 | 22 Oct: 15:15 execution capture null, retry "outside its window", "the pack holds no spot for chain 2026-11-23", no desk trade possible | Two desk runs (the scheduled session's branch rerun and the orchestrator's main rerun) recorded the same snapshot ID (the start second, quotes/recorder.py:202) at 14:55 and 15:15: RawFileConflict, quote file not in Drive, so the capture is None (desk/execution_capture.py:48-50). The retry takes 2m45s-3m15s and cannot fit the 15:15-15:20 window (config.yaml:166-167); the 14:58:58 A4 retry delivered chain 2's spot at 15:00:15, after the pack cutoff (journal/packs/2026-10-22/common.json) (mechanism strong, second writer some) | O1, A4 01MKtUHB | not started | DR1-e (writer-unique names, cross-host claim), retry sized to its window |
| 15 | 22 Oct 23:49 data-checks "sync failure" | Drive token refresh got HTTP 500 from oauth2.googleapis.com, no retry (strong, job log) | O9 | recovered next runs; not fixed | retry 5xx once in the Drive auth adapter (one place for every job) |

### B. Routine environment

| # | What failed, when | Root cause (label) | Owner | State | Fix |
|---|---|---|---|---|---|
| 4 | 22 Oct 14:06 and 14:37: quote parts NOT committed, desk STOPPED; the session's own 15:09 rerun refused weather and v4 (after 14:30) | `git_sync.py` used the checkout's branch (`rev-parse --abbrev-ref HEAD`); the scheduled session sat on its own branch `claude/bold-thompson-2lkkg6`, never on origin. The journal's ok steps are the orchestrator's 14:09 rerun on main (strong) | O1 014zYLf1 | **fixed**: PUBLISH_BRANCH (constants_operations.py:71), judge 474, merged c15ffa4b; no code reads the current branch any more (grep) | routines must still start from main (DR1-d): CLAUDE.md's hand steps say a bare `git pull`, which fails or pushes a session branch on such a checkout |
| 10 | 23 Oct 08:45 morning picture not made (ImportError), while #fno-forecast said "All systems normal" | `from PIL import ...` (forecast_lab/page/camera.py:60) loads Ubuntu's python3-pil 10.2 built for 3.12 under python 3.13; pip calls `Pillow>=10.0` satisfied. `routine_setup.sh` checks only numpy, requests, yaml (+growwapi) (strong, reproduced) | O7b 01W5HZPY (setup), FL1 (camera, status line) | fixed **by accident** (O7b's `--ignore-installed` retry runs only while `cryptography>=42` forces the plain install to fail) | DR1-d import check from requirements; the edition's status line must not say normal while a part failed |
| 11 | 23 Oct A16 marks 14:15, 14:30, 14:45 lost; the day's RV void | `cryptography>=42` (cdd8e9501, 13:39) broke setup on Debian's 41.0.7; the fire stopped before the recorder and before any alert (some: the 14:52 fire's success is unexplained) | O7b | setup fix fa270dae, A16i double cover merged 2ae8a5cce; the marks cannot be back-filled (live quotes, by design) | DR1-d (setup alerts on failure; heartbeat per routine) |
| 6 | AI books: both no_submission 14 Oct; both late 15 Oct; book2 late (34 s), book3 no commit 22 Oct; book2 late (28 s) 23 Oct; on time 16, 19, 21 Oct | Classification is right (receipts 2-3 s after the commit). The seal's commit runs the record scan hook, which imports `fno.composition` (the whole app); the prompt installs requirements in the background, so on days the install is slow or fails the seal is retried by hand after 15:15. Fired 15:10:19-15:10:29, leaving 4 min 40 s (forecast-capture.yml:86-88). 14 Oct: GitHub started the job at 19:26 (strong for 15, 22, 23 Oct; book3 22 Oct reasoning only, transcript not visible) | G11/F1 013xqaNT, O7b, O5 (record scan) | not started | record scan stdlib-only (its imports lazy), one setup through routine_setup.sh, earlier pack release (NF step 4, needs the freeze route) |
| 16 | 16 Oct A8 setup "denied by the permission classifier" | the routine's permission mode blocked tools/routine_setup.sh (strong, alert text) | A8 owner | recovered by the Actions path that day | owner's routine settings (one line in section 5) |
| 17 | Today's conversation log cut from 365 lines to 21 by the A8 routine's commit bbd2fb6a9 (19:39 IST) | the routine rewrote the file instead of appending (strong, git) | A8 routine | **restored** by DR1, 418634a34 | a test that refuses deleted lines in `conversations/` (lane 2) |
| 18 | origin/main force-updated around 23 Oct (A8 log "unrelated histories", 92 local-only commits; 74eb7e993 "a force push in the window") | not traced to a person or job (some) | orchestrator | open | branch protection on main: no force push (owner setting) |

### C. Sources and dataset gaps

| # | What failed, when | Root cause (label) | Owner | State | Fix |
|---|---|---|---|---|---|
| 7 | A22 pre-open, 23 Oct (first live day; will fail every day): "no pre-open value: candles only from 09:15" | Live, before 09:15, Groww returns one flat candle stamped 09:15 (O=H=L=C, no volume) holding the pre-open price; the 09:00-09:14 candles appear only later in history, which is what step 0b tested. preopen/answers.py:82-83 rejects the candle that holds the value (strong, raw answers in Drive) | A22 013u1Ac2 | not started | accept the flat 09:15 candle read before 09:15, checked against `ind_close_all`'s open for 5+ sessions; NSE's pre-open `key=NIFTY` as a second source (layout unverified) |
| 8 | 23 Oct 08:51 "taiex failed" (first live morning) | Yahoo's ^TWII answered 200 with empty quote arrays (no 23 Oct bars); preopen.py:63 indexes `["close"]`: KeyError counted as a failure, the reason printed to stdout only (mechanism strong; closed market or Yahoo gap: some) | A17 01MBnbVU | not started | empty answer = "no session data" with its reason; raw answer archived before parsing; TWSE holiday list |
| 9 | 21 Oct ban list not archived | the workflow's first run was 19:46 IST, after NSE had replaced fo_secban.csv with 22 Oct's (~18:12); the stale check refused correctly (strong, job log). GitHub starts these schedules hours late (22 Oct: 13:03 and 23:29) | A20 013u1Ac2 | not back-filled | back-fill 21 Oct from NSE's dated archive file (path unverified); dated fallback in the job (DR1-a) |
| 12 | 22 Oct price_distribution exit 1 (FINNIFTY 23 Nov: no parity forward) | the far expiry was illiquid (4 of 50 quotes usable), not a capture gap; all four index records were written (strong) | G13 01UkTaDe | **fixed**: thin-expiry note, 9cc3169c | none |
| 13 | G13b: no N1 on 21 Oct, so 22 Oct has no live score | by design: price_ranges live from 22 Oct (config.yaml:212) (strong) | G13 | back-filled for research (fe7c40993); a live gap for good | coverage reports say "before live", not "missed" |
| 14 | Health check "unknown" push times for every dataset, every day | the receipt search read only ~32 h of pushes (strong, earlier work) | 013xqaNT | fixed on main (da2739357, bd9f86bc0); **not yet verifiable**: no 23 Oct health run yet (GitHub starts the 17:51 cron ~22:40; the 22 Oct run took 1h28m against a 15-minute timeout) | check tonight's row; health-check timing is a separate risk |
| 19 | NSE 3 pm recorder (Actions) 0 contracts 14 and 15 Oct | the Actions runner path before story O6 moved NSE into the routine (some) | A4/O6 | superseded | none |
| 20 | forecast-capture "cancelled before any step" 19, 21, 22, 23 Oct; data-checks cancelled 23 times 23 Oct | concurrency groups replace queued runs; the capture itself ran each day (strong) | O10 013YJ5gj, O9b | data-checks fixed (5a4234979, ccfc340a6); forecast-capture still alerts falsely | add forecast-capture to REPLACEABLE (health/run_failures.py:29) |
| 21 | filings archive 14, 17, 19, 20 Oct (NSE read timeouts from GitHub's runners, 636-646 failures) | NSE throttling Azure IPs (strong) | A12 01MBnbVU | recovered by later runs each time (501 of 501) | per-company retry with backoff; this is already a working catch-up |
| 22 | forecasts v2 never complete: 10-15 of 20 probabilities every day | not investigated in depth: inputs "no India VIX / futures / spot observed by 15:00" on 15 Oct (some) | v2 owner | open | DR1-b ledger line per input; investigate in build |
| 23 | 16 Oct A16 marks incomplete (quotes_failed up to 82) | two runs on one Groww key hit 429 (strong, claims.py docstring) | A16 | fixed (claims, one taker per mark) | none |
| 24 | 14 Oct: 84 identical PlaybookError alerts in 77 minutes | no repeat suppression on that alert (strong, Slack) | E3 desk | open | one alert per episode (the A20 pattern) |

**What the audit shows (strong evidence):** of 24 problems, only 6 are source problems (7, 8, 9, 15, 21, 22). The
rest are our own system: concurrent writers with no lock (2, 3, 5), a reader that hides an empty answer (1), setup
that checks 3 of about 10 needed packages (6, 10, 11), and routines that do not start from main (4). Every one of
them was found by a person reading Slack, not by the system: nothing compares "expected" with "present and readable".

## 2. Design: two pillars

**Superseded (23 Oct): sections 2, 3 and 6 are replaced by `DR1-design-staging.md`, the owner's staging and
certification model.** Kept below as the record of the first proposal.

**Availability:** every expected dataset is present and readable through its real reader every session, or the system
repairs it itself, or proves it gone (the source no longer serves it) and says so once. **Consistency:** no reader ever
uses a corrupted, incomplete or stale copy; a better copy can always supersede a worse one, with its reason.

### The orchestrator's proposal, checked

- **(a) Prevent: one writer per dataset and day. Agree.** A `flock` only covers one container; 22 Oct had two
  containers (strong). So: a day-run lock in `DayRunner` (same container) plus a git claim per dataset and day on
  main (A16's `MarkClaims`, first push wins, fno/intraday/claims.py) for different containers. A second run prints
  "run already active (pid, started)" and runs no step.
- **(b) Never publish incomplete data: agree on the aim, change the mechanism.** "Write under a temporary name, then
  rename" does not stop the race on Drive: Drive has no atomic rename-if-absent, so two writers that both verify then
  both rename make the same duplicate (reasoning from Drive's API; it is how 3 happened with create). The one atomic
  step we have is a git push to main (first push wins). So: each writer saves under its **own** name (the dataset
  name plus its run id), verifies it (SHA-256 and size read back, then the dataset's checks), and only then pushes the
  receipt. **The receipt is the publish step; a Drive file without a receipt is never data.** Two writers can no longer
  collide on a name at all, and nothing is ever renamed.
- **(c) Choose by quality, never by time: agree, with one correction from the data.** The two 23 Oct close files
  differ by one byte: they are two real NSE reads 0.8 s apart, both very likely valid (some evidence). Blocking the
  dataset there would have stopped the evening edition: an availability loss for no consistency gain. So each dataset
  declares one of two kinds:
  - *observation* (live quotes, close reads, pre-open, A16 marks): two copies are two observations. The record is the
    copy that passes the checks and was taken inside the dataset's window; the other is kept, labelled, never a
    conflict. If both pass, the declared rule decides (e.g. the more complete, then inside the window);
  - *publication* (NSE files, bhavcopy, ban list, circulars): the publisher's file. A different verified copy is a
    **revision** (d). Only two copies that both pass, differ, and claim the same publication (same Last-Modified or
    publisher stamp) are a conflict: alert, the dataset is blocked for readers, a person decides.
  This answers the owner's case directly: an incomplete earlier copy fails its checks, so it never becomes the record,
  and a later correct copy always can.
- **(d) Corrections are revisions: agree.** A11's revisions (fno/storage/revisions.py, `VersionedRawStore`) do this
  for NSE archive files today; DR1 makes it the rule for every `DataStore` dataset: a receipt can be superseded by a
  newer receipt naming the better copy and its reason; point-in-time readers keep what was known when.
- **(e) Freshness: agree.** Each dataset declares its expected as-of (e.g. A4h: an NSE stamp of today after 15:30);
  readers refuse older data with a named reason. Pieces exist: `SnapshotInWindow`, the pack cutoff, A4h's stamp check,
  FL1's "newest scored close is stale".

### What already does part of it

Content checks per raw dataset (`fno/storage/content_checks.py` VALIDATORS); expected-versus-present for NSE archive
files (`fno/storage/coverage.py`, A1/A10); revisions (A11); SHA-256 receipts (O9); the 3 pm part flocks
(`fno/daily/part_locks.py`); git first-push-wins claims (A16); NSE retry rules (`retry_policy.py`, A9b); A4h's check
against the official close within 0.01; O8's evening health check and O10's capture-error rows; the librarian's
`--from <7 days ago>` re-runs (a catch-up in practice). DR1 joins these behind one registry, not a second version of any.

## 3. The structural fixes (each lane 1, its own judge; owners build their own parts)

- **DR1-a Catch-up.** A `CatchUp` strategy per dataset in one registry: the source, how far back it still serves the
  data (NSE archives: years; ban list: dated archive; live quotes and A16 marks: never), and its command. A daily
  `data catch-up` step re-fetches every missing or failed session within that horizon until present; past it, the
  session is recorded "gone: <reason>" once, with one alert. Owners keep their fetchers; DR1 builds the registry and
  the runner.
- **DR1-b Completeness ledger.** For each dataset and session: expected (NSE calendar plus the dataset's live date),
  present (receipt), readable (read back through its **real** reader via `DriveCache`, checks passed), fresh (as-of).
  One daily row file under `research/ops/completeness/` and one #fno-desk line naming each gap; a gap starts DR1-a.
  A reader bug like 1 shows up the same day as "present, not readable".
- **DR1-c Real-adapter contract tests.** Every reader of Drive data gets one test through the real `DriveCache` and
  `ReceiptFolder` over a fake remote (`LocalFolderStore`), never a fake cache; a test lists every `DriveCache.sync` and
  `ReceiptFolder.under` caller and fails on a new one without a contract test.
- **DR1-d Routine start.** Every routine's first step puts the checkout on latest main (section 5);
  `routine_setup.sh` imports every module the requirements files provide (the list built from them, a test keeps it in
  step) in every Python, never lets a system package built for another Python satisfy a requirement (a venv or
  `--ignore-installed`), and on failure posts one #fno-desk line before any step; each routine writes a heartbeat O8
  checks. The record scan becomes stdlib-only (lazy imports) so a seal never waits on pip (item 6; O5's code).
- **DR1-e Write-once races.** As in section 2: one writer (lock plus claim), writer-unique Drive names, verify then
  receipt, receipts as the only publish step; readers read through receipts only and pick the copy whose SHA-256
  matches, so a stray file can never make a folder unreadable; folders: after a create, list again and treat
  same-named folders as one (union of children; a folder holds no data, so which ID survives does not matter);
  `RawFileConflict` from a second writer of an observation becomes "already recorded by run <id>", never an empty exit 1.

## 4. DR1-0: merge the two `daily_runs/full` folders (owner: "DR1 merges, judged")

**What Drive holds (read-only look, 23 Oct):** `data/daily_runs/full` created 10:03:30.564Z holds
`2026-10-22/20261022T100328Z-39767f.json` (13,149 bytes, no receipt); `full` created 10:03:30.679Z holds
`2026-10-22/20261022T100329Z-f224c7.json` (13,475 bytes, receipt in `receipts/data/daily_runs/full/2026-10-22/`).

**Build (branch story/dr1-0-merge-folders):** `python -m fno data-repair merge-folders <path>` and `python -m fno
data-repair receipt <path> --writer W --run-id R`, each printing only, until `--apply`.
- `fno/storage/drive_items.py`: Drive items with IDs and creation times (every copy of a name, which the path-based
  store refuses to see), move and rename; never a delete.
- `fno/storage/folder_merge.py`: the copy kept is the one holding the most files whose bytes match their receipts
  (by content, never by time: the owner's rule); a tie, or two files with one name, is refused before anything moves;
  same-named subfolders merge the same way; each emptied copy is renamed `<name>.merged-<day>` in place (no delete, no
  trash: the earlier trash attempt was refused as a mass delete, and a rename needs none); afterwards every receipt
  under the path is read back through the path-based store.
- `fno/storage/receipt_repair.py`: a receipt for a saved but unreceipted file from its own bytes and Drive's creation
  time; refused when the path already has a receipt, has no file or two, or runs through a doubled folder.
- `fno/storage/repair_cli.py`, `fno/storage/repair_wiring.py` (composition root), one line in `fno/cli.py`.

**Dry run on the real Drive (23 Oct, read-only):** `data/daily_runs/full: keep the copy created
2026-10-22T10:03:30.679Z (holds the most files matching their receipts); 1 other copy(ies) emptied and renamed` /
`move data/daily_runs/full/2026-10-22/20261022T100328Z-39767f.json`. The kept copy is the newer one: the older holds
only the unreceipted log (the orchestrator's text said "into folder 1"; by the owner's content rule it is folder 2).

**Steps after the PASS and merge (on main, in this order):** (1) `data-repair merge-folders data/daily_runs/full
--apply` (ends "merged; every receipt under it reads back"); (2) `data-repair receipt
data/daily_runs/full/2026-10-22/20261022T100328Z-39767f.json --writer daily-run --run-id 20261022T100328Z-39767f
--apply` (commits the receipt to main); (3) the owner may move `full.merged-<day>` (empty) to the bin by hand.

### Claims (DR1-0)

1. Through the real `GoogleDriveUploadStore`, `DriveItems` and `ReceiptFolder` over an in-memory Drive HTTP fake
   (tests/dr1/fake_drive.py), 22 Oct's state is reproduced: a path through the doubled folder raises RawFileConflict.
2. The copy holding the receipt-verified file is kept whichever copy is older (both orders tested); after `--apply`
   one `full` remains, both logs read back by path, the other copy is renamed, nothing is deleted.
3. A plan changes nothing; a tie or a same-name file clash is refused and `apply` then changes nothing.
6. (Round 2, judge 540 SF1.) After `--apply`, a receipted file under the path that is missing or holds other bytes
   is returned by `apply` and named by `merge-folders --apply`, which exits 1; a clean merge returns nothing and
   exits 0 (the plant "apply returns [] instead of check()" now fails 2 tests).
4. The receipt repair writes the file's own SHA-256, size and Drive creation time; never replaces a receipt; refuses
   none or two files or a doubled folder in one line; a refused commit fails the command.
5. Gates: ruff, `tools/check_imports.py`, full suite (14,595 passed; the 10 history tests need an unshallowed clone).

## 5. Routines: the first line each needs (for the owner to paste)

Every routine that works in this repository, with its time: daily desk 14:05; morning lab 08:38; evening lab 19:53;
pre-open 08:36; A16 recorder at :52 from 08:52 to 14:52 and 08:22; A8 participant-OI recorder (evening); Book 2 and
Book 3 forecast routines (fired by forecast-capture about 15:10). Proposed first line, the same for all, placed before
setup (A16's prompt runs setup before its pull today, so a stale checkout runs a stale setup):

> 0. First, before anything else: `git fetch -q origin main && git checkout -q --detach origin/main`. If it fails,
> post its error line to #fno-desk (`C0C89E8QCCD`) and stop. Every push in this run is `git pull --no-rebase origin
> main` then `git push origin HEAD:main`.

Why detached and not `git checkout -B main origin/main`: it never moves or discards a local branch (A8's checkout held
92 local-only commits on 23 Oct), it refuses rather than overwrites uncommitted changes, and every committer already
pushes `HEAD:main` (O1's PUBLISH_BRANCH, A16's committer). The Book 2/3 prompts' step 2 (`git checkout -q main && git
pull`) fails when a local main has diverged; this line replaces it. CLAUDE.md's hand steps that say a bare `git pull
--no-rebase` (lines 70, 140, 164) need `origin main` and `HEAD:main` (a rule-document change: lane 1, it touches the
routines).

## 6. Proposed build order (reliability first, owner 23 Oct)

1. DR1-0 (folders) and the day-run lock (O1) together: the full run log fails daily until then.
2. DR1-d routine start and setup check, with the routine lines above (items 4, 6, 10, 11).
3. DR1-e store and reader rules (O9's code, with DR1), then the A4h and desk callers.
4. DR1-b ledger, then DR1-a catch-up on its gaps; DR1-c contract tests alongside each reader touched.
5. Source fixes by their owners: A22 flat candle (7), TAIEX empty answer (8), ban list back-fill (9), Drive token
   retry (15), forecast-capture REPLACEABLE (20).

## 7. Open questions for the owner

1. Observation versus publication (section 2, c): accept that two valid live reads are two observations, not a
   conflict that blocks the dataset? (DR1's recommendation: yes; reasoning plus the 23 Oct close copies.)
2. Turn on branch protection against force pushes to main (item 18)? It is the owner's GitHub setting.
3. Book 3's 22 Oct miss: only the routine's transcript (claude.ai/code/cse_01AxqTAtzzptFqJwknS7141C) can prove why.
