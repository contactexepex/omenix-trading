# Judge 20: story A3 re-judged (round 2)

**Verdict: PASS.**
- **Judge 14's should-fix finding (futures):** ACCEPTED, built and verified.
- **Minors 2, 4 and 5:** ACCEPTED. On minor 4, the builder's correction of my own statement is right; I checked it on
  the data myself.
- **Minors 3 and 6:** settled by the orchestrator, as listed in the table below.
- **New findings:** none.

**What was judged:** trading `main` with fix commits 9c4fe88 and 7d5dab6, and the "Judge 14" section of
`reviews/claude/response_38_2026-10-13-a3-nifty-panel.md`.

## Checks run by the judge

```
$ python -m pytest -q                                        587 passed
$ python -m pytest -q tests/research_data/test_nifty_panel*.py   29 passed
$ ruff check fno tests tools; python tools/check_imports.py   clean (129 files)
$ sha256sum futures/options 2019 and 2024  = the values in the claims and the manifest
manifest: futures_rows = 3 on all 1,928 sessions (5,784 rows); 2021-03-30 no file (excepted)
```

### Independent rebuild of 2019 and 2024 with the new code

I used my own script and my local read-only copies of the raw files from judge 14, wrote into a scratch sink, and
called the app's `build_nifty_panel`:

```
futures_2019  735 rows      sha256 085e92fb…9c89  csv_sha256 f9aeb264…1ccc   = committed
options_2019  773,364 rows  sha256 6f7888ac…b9a9  csv_sha256 e9ec7b6c…dbf9   = committed
futures_2024  747 rows      sha256 cf948463…6c3c  csv_sha256 606a271a…84df6  = committed
options_2024  398,739 rows  sha256 d736337e…e15f  csv_sha256 39e555d4…abc0   = committed
```

All four files are byte-identical. Option row counts are unchanged from judge 14.

### Futures checked by hand against the raw zips

I read the raw zips with plain `csv`:

| Day | Format | Raw NIFTY futures (expiry, close, settle, volume, OI) | Panel |
|---|---|---|---|
| 2019-07-15 | legacy | 25 Jul 11579.2/11579.2/86791/16600875; 29 Aug 11630.6/…/6333/3084375; 26 Sep 11676.25/…/760/205725 | identical, `session` regular |
| 2024-05-10 | udiff | 30 May 22140.60/…/286527/11804625; 27 Jun 22252.85/…/35506/2873925; 25 Jul 22390.90/…/4437/264425 | identical, `session` regular |

### Session column

| Day | Kind | Option rows labelled with that kind |
|---|---|---|
| 2021-11-04 | muhurat | 2,063 |
| 2024-03-02 | special | 1,493 |
| 2024-05-10 | regular | 1,505 |

### Partial-range refusal

```
$ python -m fno nifty-panel --from 2026-01-01 --to 2026-10-12
NOT built, nothing written: the panel holds 2019-01-01 to 2026-10-12; a build of 2026-01-01 to 2026-10-12 would drop days. ...
exit 1; git status: no change under research/
```

## Judge 14's findings: decisions

| # | Finding | Builder's answer | Judge's evidence | Decision |
|---|---|---|---|---|
| 1 | Should fix: futures in scope but not built | `futures_<year>.csv.gz` with every NIFTY index future, plus gates for "none that day" and duplicates. The story text was updated to match. | Rebuild identical. Hand check of 2 days matches. 3 futures on every session. Tests pass. | ACCEPTED |
| 2 | Minor: a partial build deletes other years | Refused in `begin()` before any file is read | My CLI run: exit 1, nothing changed. Refusing rather than merging is sound: merging a half-year range would still lose days. | ACCEPTED |
| 3 | Minor: no Drive retry | Fixed on `main` (769878d) | My A1 coverage run (judge 18) had no Drive failure. | ACCEPTED |
| 4 | Minor: README warning about `settle` on expiry day | Warning added. The builder **corrected my claim**: `settle` is 0.00 up to 30 Jan 2020, and the index close only from 6 Feb 2020. | My own count over every expiry-day row of the committed panel: **2019** 7,868 rows all 0.00; **2020** 714 rows 0.00 (last on 30 Jan) and 10,161 equal to `underlying` (first on 6 Feb); **2021-2026** all equal to `underlying`. The builder's data is right. My judge 14 text ("the index settlement value") was true only from Feb 2020. The README now states both periods. | ACCEPTED (my statement corrected) |
| 5 | Minor: muhurat closes not marked on rows | `session` column on both tables | Counts above | ACCEPTED |
| 6 | Minor: merge commit without trailer | Left as is; later merges carry it | Correct: never rewrite shared history | ACCEPTED |

## Criteria

All 10 criteria stay MET, as in judge 14. The rebuild and the spot checks were redone on the new files. The story's
scope line, futures included, now matches what was built.

## Engineering standards

- **File sizes:** `panel_rows.py` 67 lines, `nifty_panel.py` 168, `panel_store.py` 152.
- **Structure:** row extraction sits in its own module, and one pass builds both tables (DRY).
- **Breaches:** none.
