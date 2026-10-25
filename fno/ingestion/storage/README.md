# Raw data archive (fno/storage)

All project files live under **one project folder** (`fno-research`), so nothing spreads across the rest of the
owner's Drive. Inside it, each kind of file has its own area; the tree is identical on disk and in Google Drive:

```
fno-research/                        local: the --keep-raw folder; Drive: the shared folder (FNO_GDRIVE_FOLDER_ID)
  raw/                               area: original downloads, never changed (wiring.RAW_AREA)
    <publisher>/<market>/<dataset>/  what the files are, readable from the path
      <YYYY>/<MM>/                   one folder per month of the file's date
        <original file name>         the publisher's own name, unchanged
  revisions/                         area: later NSE versions of raw files (story A11; wiring.REVISIONS_AREA)
    <raw file's path>/               a folder named like the raw file's full path
      <YYYYMMDDTHHMMSS+0530>_<sha256><ext>   one file per version: when it became available, its SHA-256
  pipeline/                          area: the fetch-then-trigger bookkeeping (story O6; constants.PIPELINE_AREA)
    runs/<job>/<YYYY>/<MM>/<run id>.json                  one run's summary and every batch's outcome
    fired/<routine>/<dataset>/<batch>/<version>.json      a download job fired the routine for this version
    processed/<routine>/<dataset>/<batch>/<version>.json  the routine finished this version
  derived/                           area: what routines produce, one result per version (O6; constants.DERIVED_AREA)
    <routine>/<dataset>/<batch>/<version>.json
  cards/                             area: the daily trade card records, Drive only (story T1; constants.CARDS_AREA)
    <YYYY>/<MM>/<d>_<Slack ts>.json  one posting attempt: card text, sections, record hashes, Slack receipt
  <other area>/                      future kinds of files (exports, backups...), each in its own area
```

Example: `fno-research/raw/nse/derivatives/fo-bhavcopy/2024/01/BhavCopy_NSE_FO_0_0_0_20240102_F_0000.csv.zip`.

Datasets so far (all from NSE's public archive, `raw_source.py`):

| Folder | Source class | Files | Dates |
|---|---|---|---|
| `nse/derivatives/fo-bhavcopy` | `NseDailyFoSource` | F&O, current UDiFF format | 1 Jan 2024 onwards |
| `nse/derivatives/fo-bhavcopy-legacy` | `NseLegacyFoSource` | F&O, old format (`fo02JAN2019bhav.csv.zip`) | up to 5 Jul 2024 |
| `nse/indices/index-close` | `NseIndexCloseSource` | daily index closes (NIFTY 50, NIFTY Bank, India VIX...) | 2017 onwards (2017-18: warm-up, A10) |
| `nse/derivatives/participant-oi` | `ParticipantOiSource` | participant-wise open interest (client, DII, FII, pro; story A8) | 2019 onwards |
| `nse/derivatives/span-bod` | `NseSpanBodSource` | NSE Clearing's beginning-of-day SPAN risk parameters (`nsccl.<YYYYMMDD>.i1.zip`, written the evening before, by 03:05 IST in 131 sampled files; story A14's margins) | 1 Oct 2026 onwards (NSE keeps them back to 2020) |
| `nse/equities/cm-bhavcopy` | `NseEquityBhavcopySource` | capital-market file, UDiFF (every security's prices and volume; P6) | 1 Oct 2025 onwards |
| `nse/equities/security-delivery` | `NseDeliverySource` | security-wise file with delivery % (`sec_bhavdata_full_DDMMYYYY.csv`; P6) | 1 Oct 2025 onwards |
| `nse/equities/equity-list` | `EquityListSource` | the list of listed companies (`EQUITY_L.csv`), one copy per day fetched (P6) | 13 Oct 2026 onwards |
| `nse/indices/nifty500-list` | `Nifty500ListSource` | the Nifty 500's members and industries (`ind_nifty500list.csv`), per day fetched (P6) | 13 Oct 2026 onwards |
| `nse/equities/corporate-actions-by-symbol` | `CorporateActionsBySymbolSource` | one symbol's own corporate-action list, for symbols the range list leaves out (ETFs such as BANKNIFTY1), filed as `<YYYY>/<MM>/<DD>/<SYMBOL>.json` (P6) | 12 Oct 2026 onwards |
| `nse/equities/symbol-change` | `SymbolChangeSource` | NSE's symbol changes with their effective dates (`symbolchange.csv`, replaced in place, so archived per day fetched; P6, judge 49) | 13 Oct 2026 onwards |
| `nse/equities/corporate-actions` | `CorporateActionsSource` | NSE's equity corporate actions over the 400 days to the day fetched (website JSON, filed as `corporate-actions-equities.json`; P6) | 13 Oct 2026 onwards |
| `nse/equities/filings/results-xbrl/<SYMBOL>/<YYYY>` | `NseFilingFileSource` | a company's results XBRL files by the year of the period reported, NSE's names kept (story A12) | NSE has XBRL from 2018 |
| `nse/equities/filings/shareholding-xbrl/<SYMBOL>/<YYYY>` | `NseFilingFileSource` | a company's shareholding-pattern XBRL files (A12) | NSE lists the latest 20 quarters |
| `nse/equities/filings/announcements` | `NseAnnouncementsSource` | every company's announcements made public on one day (website JSON, `announcements_YYYYMMDD.json`; A12) | 2005 onwards |
| `nse/equities/filings/board-meetings` | `NseBoardMeetingsSource` | every company's board-meeting notices of one day (`board-meetings_YYYYMMDD.json`; A12) | 2005 onwards |
| `nse/indices/india-vix-history` | `NseVixHistorySource` (`fno/vix_history/`) | India VIX daily open, high, low, close, one NSE website JSON answer per ended calendar month (`india-vix_<YYYYMM>.json`; story A15); manifest rows at save time, revisions by `vix-history sweep`; derived table in Drive's `data/vix/` with receipts (O9b) | 19 Jul 2010 (NSE's first served day) onwards |
| `cboe/indices/spx-history`, `nasdaq/indices/ndx-history` (private: values in Drive only, owner decision a927390), `us-treasury/rates/par-yield-curve`, `eia/petroleum/brent-spot-daily`, `rbi/currency/reference-rate`, `fbil/currency/reference-rate` (private since story A17d) | `fno/global_cues/` sources (story A17) | the publishers' files, one copy per fetch filed as `<dataset>/<YYYY>/<MM>/<DD>/<HHMMSS>_<name>` (IST fetch time; the publishers rewrite them in place); logged in `research/data/manifests/global-cues/<cue>.csv`; tables in `research/data/global-cues/`, or for the private cues in Drive's `derived/global-cues/<cue>/` | 15 Oct 2026 onwards (values from 2007) |

Groww's 15-minute snapshots (story A16, `fno/intraday/`): `groww/derivatives/intraday-snapshots/<YYYY>/<MM>/<DD>/
nifty_<YYYYMMDD>_<HHMM>_<SHA-256 first 16>.json.gz`, one content-addressed copy per run and mark of a session
(09:15-15:30 IST), raw quotes in Drive only; two runs never write one name, and a mark's copy is the one its ledger
row names. The repository holds only the derived records, one file each: a row per mark
(`research/data/intraday/slots/<YYYY>/<MM>/<DD>/`), the realised variance per session (`rv/<YYYY>/`) and the heartbeat.

Filing files are grouped by category, company and the year of the period reported (owner, 13 Oct 2026); later
categories (annual reports, insider trades, pledges, credit ratings, corporate actions) take the same shape. The
announcement and board-meeting lists stay one all-company file per day (one request a day instead of 500; the raw file
is NSE's exact answer). Their SHA-256 manifests are `research/data/manifests/filings/<category>.csv` (with `filed_at`,
`first_seen`, SHA-256 and Drive's MD5) plus `gaps.csv` (what NSE does not have, with the reason). Files a job rewrites
live in their own Drive area, `index/` (never under `raw/`, whose files never change): the progress record with the
owner's work queue (`index/nse/equities/filings/progress.json`) and the symbol, ISIN and name map
(`index/nse/equities/filings/symbols.csv`). `python -m fno filings archive` fills them; `python -m fno data-coverage
--filings` checks them; `python -m fno filings table <SYMBOL> --as-of ...` reads the point-in-time figures. The
scheduled job is `.github/workflows/filings-archive.yml`; the composition root is `fno/filings/wiring.py`.

NSE's reference lists have no date in their name and are replaced in place, so each copy is filed under the day it was
fetched: `<dataset>/<YYYY>/<MM>/<DD>/<original name>` (`snapshot_source.py`; `python -m fno data-snapshot <name>`).

Both F&O formats are read into one record format by `fno/fo_bhavcopy.py` (originals stay unchanged); the old format's
missing underlying price for index options comes from the index-close file of the same day.

Rules:
- Nothing is written loose in the project folder: every store is wrapped in an `AreaStore` for its area.
- Each source declares its own `dataset` folder and builds paths with `RawFileSource.dated_path` (one place).
- Lower-case folder names, words joined by hyphens; publisher first (`nse`, `bse`, `groww`, ...), then the
  market (`derivatives`, `equities`, `indices`, ...), then the dataset.
- Raw files never change. Saving the same bytes again does nothing; different bytes at an existing path raise
  `RawFileConflict` and nothing is overwritten. Two Drive items with the same name in one folder also raise it.
- Paths are relative, with no empty, `.` or `..` parts.
- Derived files (extracts, results) live with the research that made them, not in the raw archive.

## Reading and writing Google Drive

- **Reads** use the service account (`GoogleDriveStore`, Viewer on the folder; `FNO_GDRIVE_SERVICE_ACCOUNT_JSON`).
- **Uploads** sign in as the owner (`GoogleDriveUploadStore`, story A9), because a service account has no storage
  quota. Settings: `FNO_GDRIVE_FOLDER_ID` plus `FNO_GDRIVE_OAUTH_CLIENT_ID`, `FNO_GDRIVE_OAUTH_CLIENT_SECRET` and
  `FNO_GDRIVE_OAUTH_REFRESH_TOKEN`, made once with `tools/gdrive_oauth_setup.py`. Missing folders are created; every
  new folder and file gets an ID reserved from Drive first, so a retried create cannot make a duplicate; each upload is
  checked against Drive's MD5 of what it received.
- Both share `DriveSession`: one fresh sign-in on a 401, growing waits on 429, 5xx and dropped connections.
- While the owner's Google Cloud app is in "Testing", the refresh token expires after 7 days. The librarian then stops
  with `DriveSignInRefused` and alerts #fno-desk with the fix (rerun the setup tool, or publish the app).

## Groww's 3 pm quote files (story A4b)

Raw Groww quote files (`raw/groww/derivatives/quote-snapshots/<YYYY>/<MM>/<snapshot_id>.csv`) are written by the 3 pm
recorder to Drive only, signed in as the owner (owner decision, 15 Oct 2026, "6 A"). Each attempt's sidecar
(`.meta.json`, with the file's SHA-256) and the day's `.canonical` marker are in the repository
(`research/data/quotes/`). `DriveOnlyQuoteStore` (wired in `quote_wiring.py`) returns a quote file only when its bytes
hash to the committed sidecar's `csv_sha256`; NSE's public chain (`nse/derivatives/quote-snapshots`) stays in the
repository.

## The librarian

`python -m fno data-librarian <participant-oi|index-close> [--from YYYY-MM-DD] [--to YYYY-MM-DD]` fills the dataset's
gaps in Drive from NSE (`librarian.py`): for each session (NSE's calendar) it keeps a verified file already there, else
fetches the file through the paced NSE session, verifies it (schema, and SHA-256 where the manifest has it) and uploads
it. A damaged file in Drive is reported and never replaced. Run it again after a stop: only missing files are fetched.
Each new dataset needs its own story before it is added to `wiring.LIBRARIAN_DATASETS` (A9: participant OI; A10: index
closes).

## Manifests: a SHA-256 for every archived file

`research/data/manifests/<dataset>.csv` (`date,url,status,sha256,size_bytes`, one row per archived file) is the only
manifest the code reads (`manifest_folder.py`), produced by one code path:
- **at save time**: the Drive upload store is wrapped in `FingerprintingStore`, so every file saved (by the librarian
  or by a `RawFileLibrary` archiving what it fetched) gets its row in the same operation, after Drive accepted it; a
  different SHA-256 for a day that already has a row is refused;
- **whole, from Drive**: `python -m fno data-fingerprints <dataset>` reads every file (read-only) and writes the
  manifest when the dataset has none (an existing manifest is never overwritten); `--spot-check N` compares N files
  with NSE's live bytes.

`python -m fno data-coverage` checks every file's SHA-256 against its row; a file without a row is counted under
"no sha" and listed, and the result is not "complete" until it has one. Rows written at save time are only evidence
once committed: every `data-librarian` run, finished or stopped, commits and pushes `research/data/manifests/`
(`manifest_commit.py`: `git pull --no-rebase` first, the record-scan hook on, never `--no-verify`; a refused commit is
printed, not bypassed), and `data-coverage` lists any manifest file still uncommitted and exits 1. The laptop tool's manifests in
`tools/nse_raw_download/` serve that tool only; the code no longer reads them (the regenerated ones agree with them on
every file both have).

`owned_paths_commit.py` (story A16e) is the same committer limited to the paths one writer owns inside a shared folder
(A16's `slots/`, `rv/` and `heartbeat.json`; only those that exist or are tracked), and it names anything else staged
in the checkout so its writer can refuse to pull or commit.

Adding a store (S3, Dropbox) or a source (another exchange) means one new class behind `RawFileStore` or
`RawFileSource`, and one line in `wiring.py`.

## Revisions: later NSE versions of a file (story A11)

NSE sometimes rewrites a file after first publishing it (`ind_close_all_12102026.csv` was rewritten at 23:20 IST on
12 Oct 2026 with 21 more indices; no existing row changed). The raw file is never touched. Every later version found
is saved in the `revisions` area (above) and gets one row in `research/data/manifests/revisions/<dataset>.csv`
(`date,path,sha256,size_bytes,available_from,last_modified,found_at`; append-only, committed like the manifests):
- `available_from`: NSE's Last-Modified for those bytes when it gives one, else the time we fetched them;
- the same version found again changes nothing; bytes for a file the raw archive does not hold are not a revision.

Readers (`versioned_store.VersionedRawStore`, a read-only `RawFileStore`, `wiring.build_versioned_reader`):
- **point in time** (`as_of`): the newest version available at that moment, for research (no look-ahead);
- **latest** (`as_of` None): the newest version we hold, for publishing.

Finding them: `python -m fno data-revisions sweep <dataset> [--from] [--to]` reads each session's file from NSE in
full (a SHA-256 proves a rewrite; the bytes are needed to keep it) and saves new versions; A8's
`python -m fno participant-oi sweep` does the same while it checks write times (`RevisionCapturingSource`).
`python -m fno data-revisions versions <dataset> --day D [--as-of TIME]` shows a day's versions and which one each
reader returns. `data-coverage` counts the days with revisions per dataset ("revised"). Versions NSE published and
replaced between two of our reads are never seen.
