# Judge 18: story A1, raw NSE archive complete and checked

**Verdict: PASS.** No blocking or should-fix findings; 3 minor findings.

The builder is the orchestrator session, judged like any other builder. I ran the story's "judge verifies" steps
myself:
- the real `data-coverage` run against the owner's Drive;
- an independent listing of the Drive folder with my own code;
- SHA-256 checks of 10 random files.

**What I judged:** trading `main` after e39ee96. The builder's claims are in
`reviews/claude/response_35_2026-10-13-a1-calendar-coverage.md`.

## Checks run by the judge

### `python -m fno data-coverage --from 2019-01-01 --to 2026-10-12` against the owner's Drive (read-only)

```
dataset                                    from         to expected present missing damaged
nse/derivatives/fo-bhavcopy-legacy   2019-01-01 2024-07-05     1367    1366       0       0
nse/derivatives/fo-bhavcopy          2024-01-01 2026-10-12      690     690       0       0
nse/indices/index-close              2019-01-01 2026-10-12     1929    1929       0       0
nse/derivatives/participant-oi       2019-01-01 2026-10-12     1929     478    1451       0
excepted nse/derivatives/fo-bhavcopy-legacy 2021-03-30: ... 404 from both archive hosts, checked 12 Oct 2026
calendar sha256 6101c8746fe17926498fbfcac895b7aad5218c4653982bba82337b6b5dea3961
exit=1
```

- **A1's three datasets** match the builder's claimed run exactly: 0 missing, 0 damaged, one sourced exception, and no
  "unexpected file" line.
- **The exit code of 1 comes only from A8's participant-OI rows.** The owner's upload of those files was evidently in
  progress: 478 were present at my run, against 0 in the builder's run and 0 in my own listing about 20 minutes
  earlier.

### Independent Drive listing

This was my own script, using the Drive API to walk `raw/` recursively; only the sign-in token came from the app.

| Dataset | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | Total |
|---|---|---|---|---|---|---|---|---|---|
| fo-bhavcopy-legacy | 245 | 252 | 247 | 248 | 246 | 128 | – | – | **1,366** |
| fo-bhavcopy | – | – | – | – | – | 249 | 249 | 192 | **690** |
| index-close | 245 | 252 | 248 | 248 | 246 | 249 | 249 | 192 | **1,929** |

Total: 3,985 files, equal to the sum of the three datasets, so there are no stray files.

I parsed every file name's date and compared it with the calendar:
- **Files on a closed day:** 0.
- **Index closes:** every session from 2019 to 12 Oct 2026 has one.
- **Old-format 2021:** 247 files out of 248 sessions; the gap is the excepted 30 Mar 2021.

These counts equal the command's counts.

### 10 random files (seed 1013): SHA-256 of the Drive bytes

- **1 file with a laptop-tool manifest entry** (`BhavCopy_NSE_FO_..._20260812`): hash matches the manifest.
- **9 files without a manifest entry:** the manifest covers only current-format F&O (1,013 rows, 2024-01-01 to
  2026-10-09). I downloaded 4 of these 9 straight from NSE (`ind_close_all_01092025`, `fo17MAR2023bhav.csv.zip`,
  `ind_close_all_27012022`, `ind_close_all_30122024`), and their SHA-256 equals the Drive copies.
- **The other 5:** zip and CSV schema checks only, through the coverage run.

### Calendar spot check

The 2025 rows match NSE's 2025 holiday list as I know it:
- holidays: 26 Feb, 14 Mar, 31 Mar, 10 Apr, 14 Apr, 18 Apr, 1 May, 15 Aug, 27 Aug, 2 Oct, 22 Oct, 5 Nov, 25 Dec;
- the Budget Saturday on 1 Feb (special session);
- the muhurat session on 21 Oct.

Every row carries an NSE circular link.

## Criteria

| # | Criterion | Judge's own evidence | Result |
|---|---|---|---|
| 1 | Laptop tool saves old-format and index files with original names and bytes, asking only for the folder | Tests named in the claims pass. Real Drive files have NSE's names, and 4 match NSE's bytes exactly. | MET |
| 2 | A second run changes nothing; known no-file days are not asked again | Tests pass (second run asks nothing) | MET |
| 3 | One missing day and one flipped-byte zip: lists exactly those and exits 1 | `test_lists_exactly_the_missing_day_and_the_damaged_file` passes; the real run shows the missing-day lines and exit 1 for the participant-OI gaps | MET |
| 4 | The owner's complete upload: every expected session present and valid, or a sourced exception | Real run: 0 missing and 0 damaged in A1's three datasets; my independent listing gives the same counts; one sourced exception | MET |
| 5 | A file on a closed day is reported as "unexpected file" | Test passes. Real run: none; my listing: 0 files on closed days. | MET |
| 6 | Calendar rows sourced; the calendar commit precedes the coverage result | `test_invalid_calendar_files_are_refused` and `test_committed_calendar_is_valid_and_sourced` pass. Calendar commit 88e1671 is before both runs, and the runs print the calendar's SHA-256. | MET |
| 7 | Only read requests to Drive | Every coverage test uses a fake Drive whose `put` raises; the real `GoogleDriveStore.put` raises `ReadOnlyStoreError` | MET |
| 8 | `SessionCalendar` answers a weekday holiday, a special Saturday and a muhurat session; a day outside the file raises | Tests pass; A7's tests use the same calendar (judge 12) | MET |

## Claims vs reality

- **"0 missing, 0 damaged, one sourced exception, no unexpected file":** true, reproduced.
- **"Exit 1 only because of A8's participant-OI rows":** true, both in the builder's run and in mine.
- **"About 25 minutes with 8 parallel readers":** consistent with my run.
- **Root causes fixed on the way (token renewal on a 401; retries on 429, 5xx and dropped connections):**
  consistent. Unlike my earlier A3 rebuild, this run hit no Drive error.

## Engineering standards

- `coverage.py` is 143 lines and `calendar.py` 111, both under the 150 and 350 limits.
- `CoverageCheck` depends on the store and source interfaces.
- `FingerprintCheck` is reused by A8.
- No breach found.

## Findings (all minor)

1. **No fingerprints for old-format F&O and index closes.** The manifest covers only current-format F&O (and
   participant OI). For 3,295 of the 3,985 files, coverage checks the zip checksums and the schema but not the bytes:
   an altered index CSV with a valid schema would pass. Expected: the laptop tool records SHA-256 for every file it
   saves, in all datasets, and coverage checks them through `FingerprintCheck`.
2. **No way to check one story's datasets.** The command always checks every dataset, so A1's datasets cannot get an
   exit code of 0 while A8's upload is incomplete. Expected: a `--dataset` option, or one exit status per dataset in
   the output, so routines can tell which dataset failed.
3. **Calendar rows after 12 Oct 2026 are unverified** (builder's doubt 3), and the calendar ends on 2026-12-31 (doubt
   2). A December routine to add 2027 is planned. Expected: keep it, and re-run coverage after 8 Nov 2026 (muhurat).
