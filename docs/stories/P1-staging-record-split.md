# P1: staging / record split (Phase 1 of docs/PIPELINE_DESIGN.md)

Lane 1, two judges (outside services: Drive; write-once data). Branch `story/P1-staging-record-split`. Round 2: this
text and the code answer both judges' round-1 findings together. The design stays in `docs/PIPELINE_DESIGN.md`; this
file holds the claims, the default rules, the gap list and the evidence.

## Principle: Phase 1 changes where files land, not which files are good

Today (`storage/librarian.py`) a dated file is archived when (1) its day is a calendar session inside the source's
archive range (`archive_range`, `is_session`, line 61), (2) it has no sourced exception (`build_file_exceptions`, line
81), (3) the dataset's content check passes, and (4) the first copy wins: it is never replaced, and later NSE versions
go to the revisions area (A11). The gate applies the same four rules to staged files, plus the identity rule below for
the datasets whose content check reads no date. It promotes nothing today's pipeline would refuse and refuses nothing
it would archive. No numeric freshness window is a default (owner decision 1 stays open).

## Default rule per dataset (fail-closed identity: the file's own date must equal the session its path claims)

| Dataset | Own date read from | Phase 1 |
|---|---|---|
| participant-oi, participant-volume | title ("as on <date>") | promotable; the existing content check already rejects a wrong or missing date |
| fii-stats | title "FII DERIVATIVES STATISTICS FOR <date>" | promotable; same |
| fo-bhavcopy | `TradDt` of every row (legacy: its `TIMESTAMP`, converted by the reader) | promotable; `ContentDayCheck`: all rows == claimed day; no rows or an unreadable date = rejected |
| cm-bhavcopy | `TradDt` of ALL rows of the raw CSV (not the EQ/BE rows the equity reader keeps) | promotable; same check |
| index-close, security-delivery | not read by today's readers; the repo's index fixture has an `Index Date` column (dd-mm-yyyy), not confirmed against a real archived file | **not promotable in Phase 1** (a wrong format guess would reject every real file); they stay on the direct path |

## Where a numeric tolerance goes later (owner decision 1)

`FreshnessCheck(max_lag_days)` is a `PromotionCheck` (an interface, `promotion/checks.py`), wired only when
`config.yaml` sets `promotion.max_lag_days` (an allowed key, tested); it ships `null`, so it is off.

## Which staged copy is promoted, and what happens to the others

Staging holds every fetch as its own write-once copy at `<source>/<fetch time>/<archive path>`; the fetch time is
UTC, `YYYYMMDDTHHMMSSZ` (sorts as time, no zone ambiguity). For one archive path the gate:
1. runs every check on every staged copy (earliest fetch first);
2. if the Record has no file: the **earliest-fetched passing copy** is written (first-copy-wins, as the librarian);
3. every other passing copy with different bytes (staged later) is offered to the **existing A11 `RevisionArchive`**
   through a `RevisionSink`: bytes go to the revisions area, one index row, deduplicated against the record and every
   indexed version; its `found_at` is the copy's fetch time. The gate therefore writes the Record (`gate.py`) and the
   revisions area (only through the sink); the AST test counts `.put` references, the sink uses `.capture`;
4. a Record already holding the path (written by a live workflow or an earlier run) is never touched; staged passing
   copies that differ from it are revisions as in 3;
5. failing copies stay in Staging.

## What a run examines and when a failure stops being reported

`stage` and `promote` need `--from` (no default, so no run scans all history) and take `--to` (default yesterday). A run
examines the sessions in that range. A day with no record after the run (nothing staged, or every copy failing) is a
**problem**: listed, exit 1, one #fno-desk line, and it repeats every run that includes the day until the Record
holds it or a sourced exception is filed. A copy that fails while the Record already holds the day (an older passing
copy was promoted, or the live path wrote it) is a **note**: printed in the log, counted nowhere as failure, no alert.
The failure is therefore still reported, once per run, without failing it.

## Claims (what will be true when done)

1. **The new `stage` command writes only Staging; only the gate writes the Record**, enforced in code: the `Stager` is
   built from a `StagingArea` only (a `TypeError` otherwise, tested); the Record store is passed to `PromotionGate`
   only; an AST test asserts only `staging.py` and `gate.py` reference `.put`; a spy test asserts every Drive path the
   staging wiring writes starts with `staging/`. **Not claimed:** credential separation (see gaps).
2. **Staging** keeps source and UTC fetch time in the path; a newer fetch is a new copy; identical bytes are not
   staged twice (against the newest copy).
3. **The gate** applies the librarian's rules: calendar session and archive range, sourced exceptions, the dataset's
   content check, plus identity; first-copy-wins; later passing versions go to the revisions area; idempotent.
4. **Default checks have no number**; the owner's window is the optional config key.
5. **Reporting** as defined above: problems alert and exit 1; notes are log only; manifest rows written are committed.
6. **Live collection unchanged**: no existing workflow, schedule or fetch path is edited (`git diff main --stat`
   touches no existing workflow). One new workflow `pipeline-staging.yml`, `workflow_dispatch` only. One existing
   storage file gains an optional argument (`RevisionArchive.capture(found_at=None)`, default behaviour unchanged).
7. **Doc fixes**: `docs/PIPELINE_DESIGN.md` dated 26 Oct 2026; build-plan item 1 updated to the deferral.

## Gap list: not covered by Phase 1, with the reason

- **No credential separation.** `stage` and the live workflows use the same owner Drive credential, so any job holding
  it can still write `raw/`. The design's Security property ("an abused workflow can at worst drop garbage in
  Staging") is **not met** by Phase 1. Missing: a separate Drive credential or folder permission for Record writes,
  held only by the gate's workflow. Needs the owner's Drive setup; a later phase.
- **Moving the live fetchers to write Staging** (design build-plan item 1, first half): deferred per workflow, with the
  owner's go-ahead, after the gate has promoted real files.
- **index-close, security-delivery** through the gate (see table). **Snapshot datasets, filings, circulars, quotes,
  flows, global cues**: other fetch paths; not moved.
- **Numeric freshness windows, cross-source agreement, authority ranking, news dedup**: owner decision 1 / Phases 2-4.
- **Staging retention** (copies are never deleted) and **receipts for Staging** (not a record): no rule yet.
- **Speed**: one Drive folder listing per file; fine for a daily range, unmeasured for a long back-fill.
- **No real-data run is possible in the build container**; the fo/cm tests use small synthetic files. The first real
  run is `pipeline-staging.yml` by hand after merge, dry-run first.

## Evidence (builder's runs; the judges re-run their own)

Gates on the branch: 219 tests pass; `ruff check fno tests tools ops`, `tools/check_imports.py`, `tools/check_numbers.py`,
`tests/test_code_size.py` pass; the commit's record scan is clean.

| Claim | Code | Tests | Mutation run by the builder -> result |
|---|---|---|---|
| 1 | `wiring.py`, `runs.Stager`, `gate.py` | `test_design_rules.py` (AST on `.put` references; Stager signature), `test_runs::test_a_stager_cannot_be_given_a_record_store`, `test_wiring_cli::test_the_wired_staging_area...` | Stager guard off -> 1 failed |
| 2 | `staging.py` | `test_staging.py` | (judge to plant) |
| 3 first copy, revisions | `gate.py`, `revision_sink.py`, `revisions.capture(found_at)` | `test_gate.py` (earliest wins, later to sink with fetch time, idempotent, record written elsewhere untouched), `test_revision_sink.py` (real `RevisionArchive`, one index row, no duplicate on re-run) | newest copy wins -> 3 failed; capture removed -> 4 failed |
| 3 librarian rules | `checks.SessionCheck`, `ExceptionCheck`, `wiring.checks_for` | `test_gate` (non-session day, day before archive start, sourced exception), `test_runs` (excepted day), `test_datasets::test_every_promotable_dataset_carries_the_librarians_rules` | session check off -> 1 failed; exception check off -> 2 failed; archive range off -> 1 failed; session check dropped from wiring -> 1 failed |
| 3 identity | `checks.ContentDayCheck`, `datasets.py` | `test_datasets.py`: per dataset good promoted, other-session rejected, undated rejected, garbage and empty rejected for all 5, mixed-date and other-series-row files rejected, fii title via `parse_fii_rows` | `ContentDayCheck` dropped -> 3 failed; filtered equity rows -> 1 failed; gate skips checks -> 24 failed (earlier build) |
| 4 | `wiring.checks_for` (no lag by default), `config.yaml` | `test_datasets` (60-day-late right session promoted by default; window None/3 promote, 1 rejects), `test_config` | default lag 7 -> 1 failed (earlier build) |
| 5 | `runs.PromotionReport`, `cli.py` | `test_runs` (note vs problem, repeat while unrecorded, only the range examined), `test_wiring_cli` (alert only for problems, `--from` required) | failures always problems -> 3 failed |
| 6 | no existing workflow edited | `git diff main --stat` | n/a |

Real output sample (committed code, synthetic files, local folders as Drive): three sessions staged, the 22 Oct file
contains the 21 Oct data:

```
nse/derivatives/participant-oi: staged 3, unchanged 0, 0 with a sourced exception
result: complete
nse/derivatives/participant-oi: 2 promoted, 0 already recorded, 0 not staged, 1 rejected, 0 later versions kept as revisions, 0 excepted
rejected 2026-10-22: fao_participant_oi_22102026.csv: the title says 'as on Oct 21 2026', the file is for 2026-10-22
result: INCOMPLETE: see the lines above
record holds: ['2026-10-21', '2026-10-23']
```
