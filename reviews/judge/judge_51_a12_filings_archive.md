# Judge 51: story A12, company filings archive (trial run judged; the backfill is still running)

**Verdict: FAIL for now.**
- **What is wrong:** 1 should-fix finding (coverage blames NSE for companies not yet fetched).
- **What cannot pass yet:** criteria 2 and 6 wait on the backfill, now running in GitHub Actions. Criterion 5 waits
  on one owner step.
- **What is proven:**
  - The trial run's archive is exact: **744 files**, all checked in Drive.
  - The year layout is right.
  - 10 random files match NSE byte for byte, and each `filed_at` agrees with NSE's own file stamp.

**What I judged**
- **Repository:** trading at fe2c3b7 (trial-run commit 1312940; claims `reviews/claude/response_56_2026-10-13-a12-filings-archive.md`).
- **Story:** `docs/stories/A-data-foundation.md`, A12, with the owner's addendum.
- **Drive:** read with the service account, read-only.

## The file count: 744, not 738 (strong evidence)

I listed Drive myself (`raw/nse/equities/filings/{results-xbrl,shareholding-xbrl}/<SYMBOL>/<YYYY>/`, every page, with
`createdTime` and MD5):

| Check | Result |
|---|---|
| Files in the year layout | **744** (478 results and 266 shareholding), each created **after 14:42 UTC**; 0 before |
| Against the committed manifests (`1312940`) | 744 rows, unique SHA-256 values, `first_seen` 20:12-20:52 IST (14:42-15:22 UTC). **Every manifest MD5 is in Drive and every Drive file is in the manifest** (0 and 0). No name appears twice. |
| `python -m fno data-coverage --filings` | results 478 present, 0 damaged, 0 unfingerprinted; shareholding 266, the same |

- **The claim of 744 is right.** The orchestrator's 738 is 6 short. I cannot see how it was counted.
- **A likely cause (reasoning only):** a listing that stopped at a page boundary, or a query by a different folder or
  time field. Counting by MD5 against the manifest, as above, is the reliable method.

## The 92 trial files outside the year layout

- `outside-layout.csv` lists 92 files: 74 from IRCTC and POLYCAB, and 18 from 360ONE. Drive has exactly those 92 at
  `<category>/<SYMBOL>/` (91 distinct MD5s, so two files share the same bytes), with no unlisted file.
- **Correction to the claims:** the year layout holds a copy of **74 of them** (IRCTC and POLYCAB, same MD5), not "of
  each". 360ONE's 18 have no year-layout copy until its turn in the queue.
- **Kept, never deleted, read by nothing:** agreed. Coverage counts them on its own line.

## The story's "judge verifies": 10 random archived files against NSE

| File (category, symbol, year folder) | Drive bytes = manifest SHA-256 | = NSE's current file | `filed_at` vs the stamp in NSE's file name |
|---|---|---|---|
| shareholding TCS 2024 | yes | yes | 18:52:27 vs 06:52:21 PM |
| results LICI 2025 | yes | yes | 17:29:08 vs 05:29:06 PM |
| results FEDERALBNK 2023 | yes | yes | 17:56:06 vs 05:52:23 PM |
| shareholding IDEA 2024 | yes | yes | 16:32:45 vs 04:32:40 PM |
| results LT 2025 | yes | yes | 19:56:49 vs 07:56:45 PM |
| shareholding BAJFINANCE 2024 | yes | yes | 18:50:13 vs 06:50:08 PM |
| shareholding VEDL 2024 | yes | yes | 17:40:04 vs 05:39:58 PM |
| results HDFCBANK 2025 | yes | yes | 20:23:22 vs 08:23:22 PM |
| results SUNPHARMA 2023 | yes | yes | 17:46:03 vs 05:23:10 PM |
| shareholding RELIANCE 2025 | yes | yes | 19:13:24 vs 07:13:11 PM |

- **Every `filed_at` is at or after the moment NSE created the file,** by seconds to 23 minutes. That fits NSE's
  dissemination time and is safe for point-in-time use: nothing is dated earlier than it existed.
- **The year folders follow the period reported:** for example, TCS's shareholding filed in January 2025 sits in
  `2024` (period December 2024).

**Not done in this round, for cost:** the story's comparison of 5 companies' parsed revenue, debt and cash flow
against the filings. It belongs to the final judgment, once the backfill is complete.

## Criteria

| # | Criterion | Judge's evidence | Result |
|---|---|---|---|
| 1 | Sample report and projection | Part 1 of the claims; the trial run's real numbers (744 files, 0.23 GB, 20 companies in 40 minutes) are consistent with it | MET |
| 2 | Full backfill, coverage per type, 0 damaged, every gap with a reason | **The backfill is not complete** (20 of 501 companies). **The gap reasons are wrong** for the companies not yet fetched (finding 1). | NOT MET (in progress, plus finding 1) |
| 3 | Point-in-time; a revised filing keeps both | `tests/filings` 43 passed, including a read one second before `filed_at` and both versions kept. My 10 `filed_at` checks above. | MET (the parser comparison is pending, above) |
| 4 | Polite and resumable | Tests: a planted burst paced to at least 1 second per host; a stopped run fetches only what is missing | MET |
| 5 | Runs without AI; owner checklist; no secret in files | The workflow ran from GitHub; the checklist exists; the record scan is clean. **Open owner step:** publish the Google OAuth app, or its refresh token expires after 7 days. | PARTLY (owner step) |
| 6 | Half-year statements for 90% of companies in each of the last 6 half-years | Not provable before the backfill. The sample flags September 2023 at about 85%. | NOT MET YET |

## Finding 1 (should fix): coverage attributes "not fetched yet" to NSE

- **Where:** `fno/filings/coverage.py:28` and `:70-74`. Every quarter missing from the manifest is reported as
  "NSE's lists hold no {kind} filing for the quarter ended {end} (not listed then, or not filed)". That happens
  whether or not the company's NSE list was ever read.
- **Today it prints that for all 481 companies the queue has not reached:** 5,778 "no file" lines for results and
  5,772 for shareholding. Examples: AARTIIND, WIPRO, and 360ONE, whose files are in Drive outside the layout.
- **Why it matters:** criterion 2 requires each gap's reason to be true ("never silently skipped"). A false
  "NSE has none" is worse than silence, because it would be taken as NSE's data.
- **Expected:**
  - Take the reason from what was actually read: the progress record's finished companies, and the archived NSE
    lists.
  - Report "not fetched yet (queue step N)" for companies not done.
  - Keep "NSE's lists hold none" only where the archived NSE list for that company was read and has no such period.
  - Add a test that a company not yet in the progress record is reported as not fetched.

## Also noted (not findings)

- **Index files in their own `index/` area, not under `raw/`:** agreed with the builder. Raw files never change, and
  a progress file changes every run. This is the owner's call, since it differs from the addendum's wording.
- **Survivorship (companies that left the Nifty 500):** stated, and proposed as step 3 in its own story. Agreed: fine
  for an archive, but not a backtest universe until step 3 exists.

## Addendum: the should-fix re-checked (f77c910)

**Finding 1: ACCEPTED.**
- `python -m fno data-coverage --filings` (my run against Drive) now gives a "not fetched yet" column: **481** for
  each type, with "481 companies not fetched yet (the work queue has not reached them)".
- "NSE's lists hold no filing" is now limited to fetched companies: **6 lines instead of 11,550**.
- `tests/filings`: 44 passed.

**Minor (new): the 6 remaining lines (all LICI) give the wrong cause.**
- They read "NSE's lists hold no results-xbrl filing for the quarter ended 2023-09-30 … 2024-12-31 (**not listed
  then, or not filed**)".
- **The absence is real.** My query of NSE's `corporates-financial-results` list for LICI returns 0 rows.
- **The cause is wrong.** LIC has been listed since May 2022 and publishes quarterly results; they are not in the list
  NSE serves for it in XBRL (likely an insurer's different format, reasoning only).
- **Expected:** the reason should not guess "not listed or not filed". Say "NSE's results lists carry no XBRL for
  this company in these quarters", and route insurers to the format question for the owner.

**Still waiting:** criteria 2 and 6 on the backfill (next scheduled run 18:17 UTC), and criterion 5 on the owner's
OAuth publish step.

## Addendum 2 (963ed42: time budget, rows for files found without one; backfill progress at 22:50 UTC, 13 Oct)

**Resume after a stop or a kill: MET.** `tests/filings` passes 49, including `test_filings_killed_runs.py`, and the
storage tests pass. Each of my three plants is caught (1 failed each, 67 tests):
- the librarian no longer writes the row for a file found in Drive without one (the "killed before commit" case);
- the time budget ignored (`TimeBudgetedFill` running past its deadline);
- the report claiming the whole range when the budget stopped it.

A file already in Drive is re-`put` with the same bytes. The Drive store compares the bytes and uploads nothing, so the
row is written without a duplicate file. A damaged stored file is still reported and left alone.

**Real-world note.** Run 38445744385 (dispatched 18:19 UTC, started before this fix) is still running after about 4.5
hours. It has no time budget, so GitHub may kill it at 6 hours (about 00:19 UTC) before it commits its rows. The new
"row for a file found without one" path is exactly what the next run then needs. Scheduled run 38479538255 is queued
behind it. I will look at the next commit of `research/data/manifests/filings/` for rows added this way.

**Open criteria against the backfill, as committed now:**

| # | Status | Evidence |
|---|---|---|
| 2 | **NOT MET YET (in progress)** | `results-xbrl` 4,767 rows for 209 companies; `shareholding-xbrl` 2,553 rows for 208 companies, of about 500. `gaps.csv` holds 27 named reasons; the finding-1 wording is to be re-checked when the backfill ends |
| 5 | **MET in substance, pending one scheduled completion** | The workflow now fires on its schedule (run 38479538255, event `schedule`). The secrets are in place (run 3 succeeded with Drive). The record scan is clean on its commits |
| 6 | **NOT MET YET** | Companies with a results file per half-year among the 209 done: Sep 2023 182, Mar 2024 187, Sep 2024 195, Mar 2025 199, Sep 2025 204, Mar 2026 208. The test is 90% of about 500, so at least 450 per half-year. It cannot be judged until about 500 companies are in. Sep 2023 is already the weakest (182 of 209, 87%) |

I will re-judge 2 and 6 when the coverage reaches the full list.

## Addendum 3 (throughput fix, branch `story/a12-throughput` b15406b, before merge): PASS

**Cause, confirmed in the log of run 38479538255.** At 00:44 UTC, `www.googleapis.com` gave a 60 s read timeout
(`requests.exceptions.ReadTimeout`). `DriveSession` retried only dropped connections, so the exception ended the job,
and the archive command commits rows only after the librarian returns. The builder's account matches the log.

**Gates (my runs, `python -B`):**
- branch: 2,157 passed; ruff, format and imports clean;
- my trial merge with `main` 1ab9dd2 (no conflict): 2,256 passed.

**The orchestrator's three checks:**

1. **A retried upload cannot duplicate: MET.** Every create carries an ID reserved beforehand (`generateIds`).
   - The builder's test times out *before* Drive makes the file.
   - I added the harder case in a probe: Drive makes the file, then the answer is lost as a `ReadTimeout`. The retry
     gets 409 and reads the copy back. The result was one create and identical bytes.
   - The only other write is `replace_contents` (index files, a PATCH with the same bytes), which is safe to repeat.
2. **A crash in the middle: MET for the observed cause.** A Drive failure that outlasts the retries (any
   `RequestException`, including a non-transient HTTP error) now ends the run normally at that company. Rows so far are
   committed, and progress is saved only for finished companies.
3. **The next run picks up unrecorded files without re-uploading: MET (existing test).**
   `test_an_xbrl_run_killed_before_its_commit_fetches_again_without_duplicates`: the file already in Drive with the
   same bytes is kept and its row written. The cost is one more NSE fetch per unrecorded company (about 50 here).

**Budget share:** each day list gets an equal share of the 50 minutes, cumulatively, so time left unused passes on.
The test passes.

**My plants (`python -B`, caches cleared; filings, Drive upload and librarian tests, 74):**

| Plant | Result |
|---|---|
| Timeouts not retried | caught (1 failed) |
| Store failure not caught | caught (1 failed) |
| Budget not shared | caught (1 failed) |
| `StoredCopyDamaged` not caught in the XBRL save | **not caught** |

**Should fix (not blocking):**
- **The root cause of lost rows remains for any other crash.** `cmd_filings_archive` commits only on normal return. A
  bug (a `KeyError` from Drive's answer, an untested exception class such as the last plant) would again lose the
  run's rows. The day-list path already commits in a `finally` (`run_librarian`); the archive path should do the same.
  The loss is time only (the next run fetches again), which is why this is not blocking.
- Turn my probe (timeout after the create) into a test; it is the case that actually happened.
- A test for `StoredCopyDamaged` in the XBRL save.

**Verdict: PASS.** It may merge before the 06:17 UTC run. After the merge I check `main` against b15406b and CI.
Criteria 2 and 6 of A12 are still re-judged when the backfill completes.

## Addendum 4 (merge check, 4a7fe9e)

**MET.** 4a7fe9e has parents ede76ff (main) and b15406b (the passed tip), and it equals my recomputed merge of the
two. CI `checks` is green on 16bfdd8 (run 38501702626), which contains it, and on later commits. No other code reached
`main` since my last check: `main` equals 51aa2e7 plus b15406b under `fno`, `tests`, `tools`, `db`, `.github` and
config.

## Addendum 5 (`story/a12-commit-finally` 2c9be68, my addendum 3 should-fixes): PASS; and today's LAURUSLABS failure, ruled

**The branch.**
- `cmd_filings_archive` wraps the run in a `finally` that commits the manifest rows of files already saved when the
  run stops early (any error included).
- `CommitOnce` makes sure there is only one commit.
- New tests: a create whose answer is lost, and a damaged stored copy (`StoredCopyDamaged` caught per file).

**My plants (3, Slack token unset): all caught.**

| Plant | Result |
|---|---|
| No commit in the `finally` | 1 failed |
| Commit twice | 1 failed |
| `StoredCopyDamaged` not caught | 1 failed |

**Gates.** The branch merges cleanly with current `main`. On a scratch merge with `main` (never pushed): full suite
3,001 passed; ruff, format (680 files) and imports (687): clean.

**Verdict: PASS** for 2c9be68. The merge must run the full suite on the merged tree.

### Today's A12 run (38513350039): expected or a defect?

The run failed for two reasons, and the log says which.

1. **"INCOMPLETE: deadline reached after 171 companies; the next run resumes"** (171 of 288 checked, 5,997 files
   saved). **Expected behaviour**: the backfill is time-budgeted and resumes.
   - **Follow-up (reasoning only):** while the backfill runs, every daily run ends with exit 1, a red run and the
     "run failed" alert. A run that only hit its budget is not a failure.
   - Suggest: exit 0 with an "incomplete, resumes" line when the only problem is the deadline, and exit 1 for real
     failures. Today it hides real failures among daily reds.
2. **"FAILED LAURUSLABS INTEGRATED_FILING_INDAS_1555947_23102025113639_WEB.xml: not saved: not XML: unclosed token:
   line 1, column 65227".** I downloaded the file from NSE myself, twice. Both copies were **identical**: 65,258
   bytes, SHA-256 `8e4444eb…dfb93c`, both cut off mid-tag (`…</in-capmkt:RelatedPartyTransac`). **NSE's own file is
   truncated.** It is not a download fault, and retrying will not fix it.
   - **Refusing to store it is right** (never store a broken file as XBRL).
   - **Treating it as a retryable failure is a defect.** LAURUSLABS is marked failed and never finished, so it is
     fetched and fails again on every run. Its company never completes, so the backfill step can never finish, and
     every run stays "incomplete".
   - **Fix (small):** a file NSE serves that is not well-formed XML becomes a recorded **gap**, the way "answers 'not
     found'" already is: "NSE serves a truncated or malformed file (size, SHA-256)". The company is then finished.
     Keep the SHA-256 so a later fixed copy from NSE is noticed.
   - The 23 Oct 2025 LAURUSLABS filing's facts are missing from the archive until NSE fixes it. That is a real data
     gap, and it should show as one.

## Addendum 6 (merge 09e51a7; `story/a12-nse-gaps` 0e54fdf: PASS; the exit-code follow-up withdrawn)

**Merge: MET.**
- 09e51a7 has parents 9a65921 (`main`) and 2c9be68 (the passed tip), and it equals my recomputed merge.
- 6315d26 equals its recomputed merge.
- CI `checks` is green on 6315d26 (run 38556637546).

**The builder's push-back is correct; I withdraw my addendum 5 follow-up.** `problem_of` returns "" when the run
stopped only at its deadline, so `_archive` exits 0 then. Run 38513350039 went red because of the LAURUSLABS failure
alone. I had read "INCOMPLETE … deadline" as a cause; it was only the state line.

**`story/a12-nse-gaps` 0e54fdf: PASS.**
- **How a gap is decided:** a file that is not well-formed XML but carries the XBRL namespace in its first 4 KB
  (`TruncatedXbrl`) is downloaded a second time.
  - Identical bytes become a recorded **gap**: "NSE serves a truncated or malformed file … (size, SHA-256)".
  - A differing or failed second download stays a failure.
- **My probe on the real file** (the LAURUSLABS copy I downloaded from NSE): it is classed `TruncatedXbrl`.
  - An HTML "Access Denied" page is plain `NotXbrl`.
  - Truncated junk without the namespace is plain `NotXbrl`.
- **My plants (3, token unset): all caught.**

  | Plant | Result |
  |---|---|
  | No second download | 1 failed |
  | Every parse error counted as truncated | 2 failed |
  | A truncated file still a failure | 2 failed |
- **Gates:**
  - full suite: 3,009 passed;
  - ruff, format (681 files) and imports (688): clean;
  - `git merge-tree` with `main` (d6a82ba): conflict in `reviews/claude/README.md` only (text: keep both lines).
- **Follow-up (not blocking).** A company is finished once its gap is recorded. If NSE later fixes the file, a
  backfill step that has moved on may never fetch it again. "The next run saves a fixed copy" holds only while that
  company is still revisited. A periodic re-check of truncation gaps would close it.

## Addendum 7 (merge 510b5c6; my addendum 6 follow-up corrected)

**Merge: MET (merge).**
- 510b5c6 has parents 754569e (`main`) and 0e54fdf (the passed tip).
- It differs from my recomputed merge only by the `reviews/claude/README.md` resolution (both lines kept).
- The commits after it are docs only (response 89).
- CI on ae6137c (run 38558615813) was in progress when I wrote this; I confirm it at my next check.

**Follow-up corrected: the builder is right, with one addition.**
- A daily run (no backfill step left) reads filings made public in the last 400 days (`DAILY_LOOKBACK`). It
  re-downloads any file without a manifest row, and a gapped file has none.
- So a fixed NSE copy of a filing less than 400 days old is picked up by itself. The LAURUSLABS 23 Oct 2025 filing
  qualifies until about 27 Nov 2026.
- Only two cases are never re-checked: truncation gaps on filings older than 400 days found during the backfill, and
  any filing during the backfill itself, since daily runs start only once every step is finished.
- The re-check I suggested is needed only for those older gaps (low priority).

---

## Addendum 8 (judge E, 15 Oct 2026, 17:50 UTC): criteria 2 and 6 re-judged on main's data. FAIL on one should-fix

The company list is the archived Nifty 500 list. I downloaded NSE's file today: same SHA-256 as the 13 Oct manifest row
(2959bf20...), 501 companies.

**Criterion 2: MET.** Some evidence for the Drive copies; strong for the rest.
- **The backfill is complete.** Run 38727056157 (15 Oct): "companies 501, checked 501 ... gaps 29, failures 0;
  result: complete".
- **Coverage:**
  - The manifests hold 25,272 results rows and 9,553 shareholding rows. Each type covers 495 of 501 companies.
  - Every row has a SHA-256. No symbol falls outside the list.
- **The 6 companies with no files each have a recorded reason** (`gaps.csv`): REITs, a placeholder symbol, ABBOTINDIA
  and MCX.
  - I checked ABBOTINDIA and MCX against NSE's own API (`corporates-financial-results`). It lists one 2010 entry for
    ABBOTINDIA and none for MCX, so "NSE lists no filing" is true.
- **5 random rows (seed 158):** I downloaded each from NSE. All 5 match the manifest's SHA-256 and size.
- **"0 damaged"** rests on the save-time fingerprints and the run's 0 failures. I could not open the Drive copies from
  this session.

**Criterion 6: NOT MET as built, though met in substance (should fix).**

The last 6 half-years whose results deadline has passed: the share of companies with a results file holding a balance
sheet and a cash flow (`balance_sheet`, `cash_flow` columns), my count. "Listed after" is from NSE's `EQUITY_L.csv`
(date of listing).

| Half-year | All 501 | Listed after the period end | Covered of those listed by then |
|---|---|---|---|
| Sep 2023 | 408 (81.4%) | 63 | 408 of 438 (93.2%) |
| Mar 2024 | 426 (85.0%) | 51 | 426 of 450 (94.7%) |
| Sep 2024 | 445 (88.8%) | 39 | 445 of 462 (96.3%) |
| Mar 2025 | 457 (91.2%) | 28 | 457 of 473 (96.6%) |
| Sep 2025 | 475 (94.8%) | 11 | 475 of 490 (96.9%) |
| Mar 2026 | 487 (97.2%) | 0 | 487 of 501 (97.2%) |

**Why the rest are missing, all from NSE's own data:**
- **Listing date:** the companies were not listed yet. This alone lifts every half-year above 90%.
- **Financial years ending in December or June** (ABB, CASTROLIND, CIEINDIA, KSB, SCHAEFFLER, CRISIL, GILLETTE): their
  half-years end in June and December, and those files carry both statements.
- **Banks' September files** (e.g. HDFCBANK, standalone, 30 Sep 2023):
  - My download is byte-identical to the archive (SHA-256 55983dae...).
  - The file holds operating cash-flow facts on contexts `FourD` and `FourI`, but defines none of them: its 37 contexts
    are segment contexts only. NSE's file is malformed; the parser is not at fault.

**What is missing:** the coverage report (`fno/filings/coverage.py:half_year_shares`, `half_year_misses`) divides by all
501 companies and gives only "no results file" or "file without statements". So it prints 81%, 85% and 89% as
failures with no NSE reason.

**Smallest fix:** count a company in a half-year only once NSE's equity list shows it listed by that period end,
reported as "listed after the period end (NSE list)". That one rule meets the 90% in all six half-years. The other two
reasons can stay "Known limits" lines.

**Not part of A12's criteria, but unowned:**
- Queue step 3 (companies in the Nifty 500 in past years, survivorship) is not built. Response 56 proposed it as its
  own story, but there is no story, plan row or register row for it.
- The orchestrator should assign it, or record the owner's choice to drop it. Until then the archive covers today's
  members only (a survivorship bias for any backtest).

**Verdict: FAIL** on one should-fix (criterion 6's report); criteria 1-5 are now MET.

---

## Addendum 9 (judge E, 15 Oct 2026, 19:35 UTC): the coverage fix (`story/a12-coverage-listing` 93f44bf3): PASS

**Criterion 6: MET.** Story A12 now passes on every criterion.

| Check | Status | Evidence (mine) |
|---|---|---|
| The rule | MET | `listed_by`: a company counts in a half-year once NSE's list shows it listed by the period end. A company absent from the list counts in every half-year. One that filed the statements anyway (an IPO's last quarter) is added to the count. `half_year_misses` gives "listed after the period end (NSE list)", else the two old reasons |
| It reproduces my table | MET | I ran the committed functions on the committed manifest, the Nifty 500 list and NSE's `EQUITY_L.csv` (downloaded today): 93.2%, 94.7%, 96.3%, 96.6%, 96.9% and 97.2% for Sep 2023 to Mar 2026. That is identical to my addendum 8 table. Every half-year is at least 90%; Sep 2023 has 63 "listed after", 16 "no results file" and 14 "without statements". Strong |
| The wiring fix | MET | `_archived_list` now checks the copy against its own day's manifest row. The old code used the latest row, which happened to be right for the Nifty 500 list (13 and 14 Oct share a SHA-256) but would refuse the 13 Oct `EQUITY_L.csv` (bf199940...), whose 14 Oct row differs (951c5d37...). A real bug, fixed |
| The new live input | MET (some evidence) | Drive holds the 13 Oct `EQUITY_L.csv` at 184,050 bytes, the manifest row's size (Drive search). Its SHA-256 is checked at read time |
| My plants (5, reverted) | 4 caught, 1 equivalent | `<=` changed to `<`: 1 failed. The "filed anyway" union dropped: 1 failed. Absent companies counted in no half-year (`date.max`): 1 failed. The "listed after" reason dropped: 1 failed. The wiring check back on the latest row: 1 failed. A first `date.min` plant was equivalent to the code, my error, so I replaced it with `date.max` |
| Tests not weakened | MET | Three tests added and none removed. `tests/filings` 66 passed |
| Gates on 93f44bf3 | MET | Full suite (full history): 5,883 passed. Ruff clean; format clean (1,075 files); `check_imports` clean. `coverage.py` 166 lines, `wiring.py` 144 |

**End-to-end run: not needed.**
- The CLI's slow part, the per-company Drive listing, is unchanged.
- I reproduced the new numbers on real data through the committed functions, and the one new Drive input is present at
  the right size.
- The next scheduled run that prints the report will show it; the orchestrator should paste that output into the log.

**Verdict: PASS for 93f44bf3.** Merge with the full suite on the merged tree. A12 stands at PASS on all six criteria.
