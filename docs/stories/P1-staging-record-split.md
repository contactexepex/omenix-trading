# P1: staging / record split (Phase 1 of docs/PIPELINE_DESIGN.md)

Lane 1, two judges (outside services: Drive; write-once data). Branch `story/P1-staging-record-split`. This is the
story text, pushed alone for review before any code (JUDGE.md quality rule 1). The design stays in
`docs/PIPELINE_DESIGN.md`; this file holds the claims, the default rules and the gap list only.

## Principle: Phase 1 changes where files land, not which files are good

Today a dated file is archived when the dataset's content check passes (`coverage_datasets()` validators, used by the
librarian). Phase 1 puts Staging and a gate in front of the same Record with the same content check. It promotes
nothing today's pipeline would not archive and rejects nothing it would archive, **except** that it adds the identity
rule below, which today's code already enforces for 3 of the 7 datasets and which Phase 1 adds for 2 more. No numeric
freshness window ships as default (owner decision 1 stays open).

## Default rule per dataset (fail-closed identity: the file's own date must equal the session its path claims)

| Dataset | Own date read from | Today | Phase 1 |
|---|---|---|---|
| participant-oi, participant-volume | title line ("as on <date>") | content check already rejects a wrong or missing date | promotable; rule = the existing content check, tested through the gate |
| fii-stats | title "FII DERIVATIVES STATISTICS FOR <date>" | same | promotable; same |
| fo-bhavcopy | `TradDt` of every row (legacy format: its `TIMESTAMP`, already converted by the reader) | not checked | promotable; new `ContentDayCheck`: every row's date == claimed day; no rows or unparseable date = rejected |
| cm-bhavcopy | `TradDt` of every row | not checked | promotable; same new check |
| index-close, security-delivery | no date read by today's reader; column formats unverified here (no NSE access in the build container) | not checked | **not promotable in Phase 1**: stay on the direct fetch-to-Record path; listed in the gap list |

A stale, wrong-session or undated file is rejected; a correct one is promoted (tests below). No numeric window is a
default.

## Where a numeric tolerance goes later (owner decision 1)

`FreshnessCheck(max_lag_days)` is a `PromotionCheck` strategy (an interface, `promotion/checks.py`). The wiring adds it
only when `config.yaml` sets `promotion.max_lag_days` (new allowed key in `fno/shared/config.py`, with a test); the
shipped value is unset (`null`), so it is off. Per-dataset windows would be a mapping under the same key later.

## Claims (what will be true when done)

1. **Fetchers write only Staging; only the gate writes the Record, enforced by design.** A `StagingArea` is the only
   thing a `Stager` can hold; the wiring gives it a Drive `AreaStore` on `staging`. The Record store is passed to
   `PromotionGate` only. A static test (AST) asserts that, inside `fno/ingestion/promotion/`, only `staging.py` and
   `gate.py` call `.put(`. A spy test asserts every Drive path the staging wiring writes starts with `staging/`.
2. **Staging records source and fetch time in the path** (`<source>/<fetch time>/<archive path>`); a newer fetch is a
   new write-once copy; identical bytes are not staged twice.
3. **The gate**: copy equal to the Record = skip (same SHA); passing copy not in the Record = written through the
   existing write-once, manifest-fingerprinting store; passing copy differing from the Record = reported as a revision
   (existing revision path), never written; failing copies stay in Staging with reasons; older passing copy used when
   the newest fails.
4. **Checks** = the dataset's content check (same function the librarian uses) + the identity rule above; freshness
   window only when configured.
5. **Reporting**: non-promoted files make exit code 1, post one #fno-desk line (first five named), and the manifest
   rows written are still committed.
6. **Live collection unchanged**: no existing workflow, schedule or fetch path is edited. Phase 1 adds the `stage` and
   `promote` commands and one new workflow `pipeline-staging.yml`, `workflow_dispatch` only, no schedule.
7. **Tests** (good, bad, boundary, empty) each with a broken-code proof, listed in the Claims table once code is
   pushed: stale / wrong-session / undated file rejected and correct file promoted, per dataset in the table above.
8. **Doc fixes**: `docs/PIPELINE_DESIGN.md` dated 26 Oct 2026 (was 27); no claim about how many workflows are enabled.

## Gap list: not covered by Phase 1, with the reason

- **index-close, security-delivery** through the gate: no verified own-date column (see table); a later phase adds
  `ContentDayCheck` for them once the column format is confirmed against a real file.
- **Snapshot / reference-list datasets, filings, circulars, quotes, flows, global cues**: other fetch paths; not moved.
- **Switching a live workflow to stage-then-promote**: separate deliberate change per workflow, owner's go-ahead.
- **Numeric freshness windows, cross-source agreement, authority ranking, news dedup**: owner decision 1 / Phases 2-4.
- **Staging retention** (copies are never deleted) and **receipts for Staging** (not a record): no rule yet.
- **Speed**: one Drive folder listing per staged file; acceptable for a daily run, unmeasured for a long back-fill.
- **No real-data run is possible in the build container** (no Drive credentials): the first real run is
  `pipeline-staging.yml` by hand after the merge, dry-run first.
