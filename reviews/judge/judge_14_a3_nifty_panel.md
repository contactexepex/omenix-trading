# Judge 14: story A3, NIFTY option-chain panel

**Verdict: FAIL.** There is 1 should-fix finding: the scope's NIFTY futures were neither built nor rescoped. There are
6 minor findings and no blocking ones.

All 10 acceptance criteria are MET on my own evidence. That includes an independent rebuild of 2019 and 2024 from
Drive, which reproduced the committed files byte for byte. The data itself is sound and ready for B1/B2. The only thing
open is the futures scope decision, which is cheap to settle (finding 1).

**What I judged.** Trading `main` after 2ecc593 and its merges. The claims are in
`reviews/claude/response_38_2026-10-13-a3-nifty-panel.md`. I read in full `fno/research_data/nifty_panel.py` (200
lines), `fno/research_data/panel_store.py` (121 lines), the panel parts of `fno/storage/wiring.py` and `fno/cli.py`,
`research/data/nifty-panel/README.md`, and the manifest.

## Checks run by the judge

```
$ python -m pytest -q                                    518 passed
$ python -m pytest -q tests/research_data/test_nifty_panel.py   19 passed
$ ruff check fno tests tools; python tools/check_imports.py   clean (114 files)
$ sha256sum options_2019.csv.gz options_2024.csv.gz ; zcat | sha256sum
153d79b7…dc02 / f602c877…7053 (gz) and 99bb26a8…18c0 / efa91850…1904 (csv): equal to the manifest
$ python research/2026-10-13-nifty-panel/compare_extract.py    249958/249958 found, 0 value differences, 689 = 689 days
  (compare_extract.json rewritten with identical content: git status clean)
manifest sessions: 1,916 regular, 6 special, 7 muhurat; 1,928 ok, 1 "no file" (2021-03-30, sourced exception)
```

### Independent rebuild from Drive (the story's "judge verifies")

I wrote my own script in the scratch area; it writes nothing to the repository. It ran in two steps:

1. Copy every needed raw file of the year from Drive, read-only, with retries. 490 files for 2019, 626 for 2024; 0
   were missing on Drive.
2. Build the year through the app's own `build_nifty_panel`, the app's calendar and the app's exceptions, into a
   scratch sink.

```
2019: options_2019.csv.gz 773,364 rows, sha256 153d79b7…dc02, csv_sha256 99bb26a8…18c0   (= committed)  245 sessions ok
2024: options_2024.csv.gz 398,739 rows, sha256 f602c877…7053, csv_sha256 efa91850…1904   (= committed)  249 sessions ok
per-day manifest entries 2019 and 2024: identical to the committed manifest (245 and 249 days)
```

Even the gzip bytes match on this machine. The two years cover both source formats and the format switch in 2024.

My first attempt read straight from Drive. It died partway through on a transient Drive `HTTP 500 Internal Server
Error`, because the store does not retry (finding 3). The copy-with-retries approach above is the builder's own method.

### Spot checks of 5 days against the raw files, by hand

I parsed the raw zips myself with plain `csv`, not the app's parser. For each day I checked:

- the at-the-money contract;
- the highest and lowest strike;
- 2 random contracts.

Each was checked for close, settle, volume and open interest, plus the row count and the NIFTY 50 and India VIX closes
from the raw index file.

| Day | Format | Rows panel = raw | NIFTY 50 / VIX | 5 contracts |
|---|---|---|---|---|
| 2019-07-15 | legacy | 3,244 = 3,244 | 11588.35 / 12.02 = raw | all equal |
| 2021-11-04 (muhurat) | legacy | 2,063 = 2,063 | 17916.80 / 15.75 = raw | all equal |
| 2022-06-20 | legacy | 2,231 = 2,231 | 15350.15 / 22.41 = raw | all equal |
| 2024-05-10 | udiff | 1,505 = 1,505 | 22055.20 / 18.47 = raw | all equal |
| 2026-09-01 | udiff | 1,594 = 1,594 | 24055.80 / 11.49 = raw | all equal |

**Volume units.** On 2024-01-02, which exists in both formats, the old format's `CONTRACTS` equals UDiFF's
`TtlTradgVol` for the same contracts. For example, the 4 Jan 21700 CE shows 4,287,267 in both. So `volume` means the
same in both formats, as the README says ("contracts traded"). `open_interest` is in units.

## Criteria

| # | Criterion | Builder's claim | Judge's own evidence | Result |
|---|---|---|---|---|
| 1 | Rows per day = NIFTY option rows of the source; manifest has the source SHA-256 | `_rows`, `fo_sha256`; `check_panel.py` 1,928 days | 5 days hand-counted, equal; the rebuild's per-day entries (with `fo_sha256`) are identical | MET |
| 2 | 2024 before 6 Jul uses udiff; 2019-2023 legacy | precedence `nifty_panel.py:127-133` | Rebuild of 2024 identical with `udiff` on every day; 2019 `legacy`; spot checks show the same | MET |
| 3 | Same raw files give byte-identical outputs | gzip `mtime=0`, no name, sorted JSON | My rebuild on another machine gives identical gz and csv hashes for 2019 and 2024 | MET |
| 4 | Day with no F&O file is absent and listed as "no file" | `_missing` | 2021-03-30 listed as "no file" with its sourced exception; test passes | MET |
| 5 | `underlying` = NIFTY 50 close, `vix` = India VIX close | from the index file for every row | 5 days checked against the raw index file | MET |
| 6 | (date, expiry, strike, type) unique; a duplicate fails | `seen` set raises `BadFile` | Code read (`nifty_panel.py:154-158`); test passes | MET |
| 7 | Manifest has both SHA-256s per day | `fo_sha256`, `index_sha256` | Rebuild entries identical, including both hashes | MET |
| 8 | Research-ready gate, never empty values | gate plus `discard()` | Code read: any problem raises after all days and the sink is discarded (`build_nifty_panel`, `panel_store.discard`); empty `underlying` is impossible, since a missing close is a problem; tests pass | MET |
| 9 | Deterministic precedence on days with both formats, choice recorded | ordered `fo_files`, manifest `source_format` and `fo_file` | 2024-01-02 and 2024-03-02 fixtures; rebuild identical | MET |
| 10 | 2024-2026 reproduces the existing extract | `compare_extract.py` | Re-run: 249,958/249,958, 0 differences, 689 = 689 days | MET |

## Claims vs reality

- **Size (45.6 MB, largest file 7.8 MB):** true.
- **"21 min 50 s from a local copy; over an hour straight from Drive":** consistent with my run: copy plus build took
  about 9-11 minutes per year with two years in parallel.
- **"Building straight from Drive works":** only while Drive answers. One transient 500 kills the build (finding 3).
- **Doubt 6, compare `csv_sha256` across machines:** sound advice. Here even the gzip bytes matched.
- **Doubts 1, 3, 4, 5, 7 and 9:** accurate and honestly stated.

## The orchestrator's questions

**Are futures a gap or only context?** They are a gap in the story as written. The scope line says "In: NIFTY index
options (and NIFTY futures for reference)", while no criterion and no output schema covers them. This is reasoning
only, but futures matter for the research: the near-month future gives the market's forward, which put-call parity and
implied-volatility work need (the spot index ignores carry and dividends), and B1/B2 may need it. Either build a small
`futures_<year>.csv.gz` with a stated schema, or move futures out of A3's scope into a named story. Either way the
story text must match what was built (finding 1).

**Doubt 7: challenge data in the repository before B5's freeze.** Reasoning only. This does not change what could be
read: the 2019-2023 raw files have been on the shared Drive since 12 Oct, so any agent could already read them. The
panel only makes reading easy. The real guard is the ledger: registration before results are read (B4). I recommend
that B5's freeze records the panel's `csv_sha256` for 2019-2023, so that any later change to challenge data is visible.
That is not an A3 defect.

**Merge commit ee29335 has no trailer:** confirmed (minor finding 6).

## Engineering standards

- Files are under the 350-line limit (200 and 121 lines).
- `PanelSink` is an interface with `CsvGzPanelFolder` as its adapter, wired in `wiring.py`.
- `DailyFiles` keeps NSE naming out of the builder.
- `cents` and `whole` refuse to round.
- Constants live in `fno/constants.py`.
- No breach found.

## Findings

1. **Should fix: futures in scope but not built or rescoped.** Expected: the story owner decides, then either a
   futures file is built with its schema and tests, or A3's scope line drops futures and names the story that owns
   them.
2. **Minor: a partial-range build silently deletes the other years.** `CsvGzPanelFolder.finish` unlinks every
   `options_*.csv.gz` not in this build and rewrites the manifest for the given range only (`panel_store.py:109-111`).
   So `nifty-panel --from 2026-01-01 --to …`, a natural "update this year" run under the builder's own rebuild advice,
   removes 2019-2025. Git keeps them, but a routine could commit the loss. Expected: refuse a range narrower than the
   existing panel unless an explicit flag is given, or merge the untouched years, with a test.
3. **Minor (storage layer).** The Google Drive store has no retry on a transient error. One HTTP 500 ended my direct
   rebuild. Expected: a small bounded retry for 5xx and connection errors in the Drive store, with a test.
4. **Minor (README).** On expiry day, NSE's `SttlmPric` for an expiring option is the index settlement value, not an
   option price. For example, on 2026-09-01 the expiring 24050 CE and 24950 CE both have `settle` 24055.80. Research
   that reads `settle` as a price on expiry day would be badly wrong. Expected: one warning line in the panel README.
5. **Minor.** The rows do not carry the session kind, so muhurat-session closes (a one-hour evening session) look like
   normal daily closes unless the manifest is joined. Expected: a README note, or a `session` column in a later
   version.
6. **Minor.** Merge commit ee29335 lacks the required co-author trailer (a process slip, already known).
