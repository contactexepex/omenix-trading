# Judge 34: story A10, 2017-18 warm-up closes, and a fingerprint for every new file

**Verdict: PASS.** All 6 criteria are MET. There are no blocking or should-fix findings and 1 minor finding. Both of
the builder's deviations from the story text are ACCEPTED on their merits, with my own evidence.

I ran every "judge verifies" step myself:
- `data-coverage` on the real Drive;
- F2 for 2 Jan 2019, recomputed from **raw India VIX closes I downloaded from NSE myself** (not the builder's derived
  file);
- an unfingerprinted file planted, with the result confirmed not complete.

I also recomputed F1 for 2 Jan 2019 and F2 for 14 Jan 2019, and checked the 2017-18 calendar against both NSE's
circular PDFs and NSE's own file archive.

**What I judged**
- **Repository:** trading `main`, which contains A10 code commit deeec72 and claims 64d3e5e.
- **Claims:** `reviews/claude/response_46_2026-10-13-a10-warmup-fingerprints.md`.
- **Story:** `docs/stories/A-data-foundation.md`, A10.

## Checks run by the judge

```
$ python -m pytest -q                       873 passed
$ ruff check fno tests tools                All checks passed!
$ python tools/check_imports.py             clean: 189 files
$ python tools/check_records.py             record scan: clean (458 files)
```

### `python -m fno data-coverage --to 2026-10-12` (real Drive, read-only)

```
dataset                                    from         to expected present missing damaged no sha
nse/derivatives/fo-bhavcopy-legacy   2019-01-01 2024-07-05     1367    1366       0       0      0
nse/derivatives/fo-bhavcopy          2024-01-01 2026-10-12      690     690       0       0      0
nse/indices/index-close              2017-01-01 2026-10-12     2423    2423       0       0      0
nse/derivatives/participant-oi       2019-01-01 2026-10-12     1929    1929       0       0      0
excepted nse/derivatives/fo-bhavcopy-legacy 2021-03-30: ... (A1's sourced exception)
result: complete
calendar sha256 e34fbad752bb244e6116c1e474902208a72a03f5af6037c6d75bf9baa6756b4d          exit=0
```

This is identical to the claims. "no sha" is 0 everywhere, and the current-format F&O file of 12 Oct is now
fingerprinted (judge 23 minor 1).

### Raw NSE files, fetched by me from `nsearchives.nseindia.com`, every weekday from 1 Dec 2017 to 14 Jan 2019

- **Files:** 292 weekdays, 276 files. The 16 weekdays without a file (404) are **exactly** the calendar's holidays.
  The muhurat-only 7 Nov 2018 has a file, as expected.
- **Against the warm-up file:** all 266 overlapping rows of `warmup_closes.csv` equal my raw files. NIFTY 50 and
  India VIX closes have 0 differences, and **all 266 SHA-256 values are equal**.
- **2017, Jan to Nov** (HEAD requests): the weekdays without a file equal the calendar's 2017 holidays exactly. The
  muhurat day, 19 Oct, has a file.
- **The circulars** (PDFs fetched and read):
  - FAOP/33750 lists 13 weekday holidays in 2017, with the muhurat on 19 Oct;
  - FAOP/36476 lists 16 in 2018, with the muhurat on 7 Nov.

  Both equal the calendar rows date for date.

### F2 and F1 by hand from the raw files (story step 2)

F2 is the VIX close on the day against the median of the previous 250 daily closes, with muhurat sessions left out.

| Day | VIX | Previous 250 (first used) | Median | F2 | Builder |
|---|---|---|---|---|---|
| **2 Jan 2019** | 16.39 | from 26 Dec 2017 | **14.25** | True | 16.39 / 14.25 / True |
| 14 Jan 2019 | 16.16 | from 5 Jan 2018 | **14.415** | True | 16.16 / 14.415 / True |

**F1 on 2 Jan 2019** (my own Black-76 and bisection, rate 0.065, T = 29/365):

| Input | Value |
|---|---|
| Spot | 10,792.50, so ATM is 10800 |
| 31 Jan future | 10,830.85 |
| 10800 CE | close 204.50 (volume 56,680): IV 15.6019 |
| 10800 PE | close 172.05 (volume 117,216): IV 15.4561 |
| Realised (21 NSE closes, 4 Dec 2018 to 2 Jan 2019) | 15.5742 |
| **F1** | **−0.0452** |

The builder gives −0.04517.

**F1 on 14 Jan 2019 is `None`:** confirmed from the panel. The ATM 10750 PE (28 Feb expiry) had volume 0 (settle
180.05). The CE traded **2 contracts** (see the note for the desk below).

### Planted unfingerprinted file on the real Drive (story step 3)

I deleted the 2018-06-15 row from `research/data/manifests/index-close.csv` (a day the builder did not use) and ran
`data-coverage --from 2018-06-01 --to 2018-06-30`:

```
nse/indices/index-close              2018-06-01 2018-06-30       21      21       0       0      1
no fingerprint (content checked only) nse/indices/index-close 2018-06-15
result: INCOMPLETE: missing, damaged or unfingerprinted files above          exit 1
```

Restored; `git status` clean.

### Manifests against the laptop tool's independent copies (requested by the orchestrator)

| Manifest | Rows | Laptop rows | Hashes in both | Different | Drive only |
|---|---|---|---|---|---|
| `fo-bhavcopy.csv` | 690 | 689 | 689 | **0** | 2026-10-12 |
| `participant-oi.csv` | 1,929 | 1,929 | 1,929 | **0** | – |

`grep` finds no read of `tools/nse_raw_download` manifests in `fno/`, so the laptop copies are no longer read.

### No 2017-18 F&O data (criterion 5)

- **My own Drive listing:** `index-close` has year folders 2017 and 2018. `fo-bhavcopy-legacy` and `participant-oi`
  start at 2019, and `fo-bhavcopy` at 2024. No 2017-18 F&O file exists to be read.
- **The repository:** the panel's option and futures files start at `options_2019`. Tests at
  `test_warmup_closes.py:103` and `:110` pass.

### Breaks (reverted; `git status` clean)

| Break | Tests failing |
|---|---|
| Unfingerprinted files no longer block "complete" (`ok`) | 1 |
| `FingerprintingStore.put` writes no manifest row | 2 |

## The builder's deviations: decisions

| # | Deviation | Judge's evidence | Decision |
|---|---|---|---|
| 1 | 2017 is added as well as 2018 | 2018 has 245 daily sessions (16 weekday holidays, one of them the muhurat), so 2018 plus 1 Jan 2019 gives 246 previous closes, under F2's 250. My computation uses closes back to 26 Dec 2017 for 2 Jan 2019. | ACCEPTED (strong evidence) |
| 2 | The first 2019 decision day is 14 Jan, not 2 Jan | B2's cycle rule (30-45 days to the monthly expiry) gives 14 Jan for the 28 Feb 2019 expiry. The story's "2 Jan" was not a decision day. Both days are tested and recomputed above. | ACCEPTED (the story's date was wrong; the builder tested both) |

## Criteria

| # | Criterion | Judge's own evidence | Result |
|---|---|---|---|
| 1 | 2017-18 index-close dataset complete in Drive, 0 missing, 0 damaged, every file fingerprinted | Coverage above; 266 hashes equal NSE's own files | MET |
| 2 | F2 (and F1 where traded) not `None` on the first 2019 decision day; equal to hand values | 2 Jan: F2 and F1 recomputed and equal. 14 Jan: F2 equal; F1 `None` for the documented, verified reason | MET |
| 3 | An unfingerprinted file is reported and the result is not complete; a saved file gets its row in the same operation | Real plant: INCOMPLETE, exit 1. The second break shows the row-write is tested. | MET |
| 4 | The current F&O manifest covers to the latest archived day, produced by the same code; the laptop copy is not read | 690 rows to 12 Oct; 0 differences with the laptop's 689; no read of the laptop files | MET |
| 5 | No 2017-18 F&O data read by experiment code | No such data exists in Drive or the repository; tests pass | MET |
| 6 | Code size, lint, imports, tests; raw files only in Drive | All checks clean; 873 tests; the repository holds only derived manifests and closes | MET |

## Engineering standards

- **One verification path:** `CoverageDataset.check` is used by both coverage and the librarian.
- **One manifest path:** `ManifestFolder` writes every manifest.
- **The decorator `FingerprintingStore`** records the row in the same `put`, wired in the composition root.
- **The warm-up hook** stays in A3's reader; no B1 file is touched.
- **Sizes:** `wiring.py` 235, `coverage.py` 151, `manifest_folder.py` 113.
- **Breaches:** none found.

## Finding (minor)

1. **A saved file's manifest row lands in the working tree, and nothing reminds the session to commit it** (the
   builder's own doubt). A fresh checkout then shows the file as "no sha", so the failure is loud, not silent.
   Expected: the librarian prints how many manifest rows it wrote and that they must be committed. Better, the
   routine that runs the librarian commits `research/data/manifests/` itself, as the 3 pm recorder does with its
   quotes.

## Note for the desk (B1 and B5, not A10)

**F1 rests on very thin trades early in 2019.** On 14 Jan 2019 the second-month ATM call traded 2 contracts and the
put none. B1's rule accepts any volume above 0, so a two-contract print can set F1. B5 should look at the volume
behind F1's legs in 2019 before the freeze (some evidence: one day inspected).
