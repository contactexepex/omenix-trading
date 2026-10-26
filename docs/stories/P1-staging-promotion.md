# P1: staging / record split (Phase 1 of docs/PIPELINE_DESIGN.md)

Lane 1 (outside services: Drive; write-once data; a new workflow). Branch `story/P1-staging-promotion`. The design lives
in `docs/PIPELINE_DESIGN.md` ("Phase 1 as built"); this file holds only the criteria and the builder's claims.

## Criteria and claims (code; test; broken-code proof)

| # | Requirement | Code | Test | Break it and it fails |
|---|---|---|---|---|
| 1 | Fetchers write only Staging, never the Record | `promotion/wiring.py` `build_staging_area` (AreaStore `staging`); `runs.Stager` has no Record reference | `test_wiring_cli::test_the_wired_staging_area_can_only_write_under_staging`; `test_runs::test_the_stager_stages_each_session_and_writes_only_staging` | wire the stager with the Record store: the spy sees a non-`staging/` path |
| 2 | Staging keeps source + fetch time; newer fetch beside older; same bytes not staged twice | `staging.py` `StagingArea` | `test_staging.py` (5 tests) | drop the equal-bytes check: `test_same_bytes_again...` fails |
| 3 | Garbage never reaches the Record, stays in Staging with reasons | `gate.py` `PromotionGate.promote`, `checks.SchemaCheck` | `test_gate::test_garbage_never_reaches...` | `if problems:` -> `if False:` makes 4 tests fail (run by builder) |
| 4 | Freshness: not before the fetch day (IST); lag limit; back-fill switch | `checks.FreshnessCheck` | `test_checks.py` (boundary 2 days, IST/UTC day, None, negative) | change `>` to `>=`: boundary test fails |
| 5 | Idempotent; never overwrites a record; differing good file = revision, reported | `gate.py` | `test_gate::test_promoting_twice...`, `test_a_different_good_file_never_overwrites...` | delete the `held is not None` branch: the overwrite test fails (builder ran it: 1 failed) |
| 6 | Older good copy used when the newest is bad | `gate.py` loop | `test_gate::test_a_bad_newest_copy_falls_back...` | `break` at the first copy: fails |
| 7 | Only the authoritative source's copies are promoted | `PromotionGate.source` | `test_gate::test_only_the_authoritative_sources_copies...` | read `copies` for any source: fails |
| 8 | Failures are reported, not silent: exit code 1, #fno-desk alert, manifest rows still committed | `promotion/cli.py` | `test_wiring_cli.py` promote/stage tests | drop the alert call: alert test fails |
| 9 | Live workflows unchanged; no schedule on the new one | `.github/workflows/pipeline-staging.yml` (`workflow_dispatch` only); no other workflow touched | `git diff main --stat` | n/a |

Out of scope, listed with reasons: snapshot (reference list) datasets (a later switch, needs the owner's go-ahead);
cross-source agreement and dedup (no second source until Phases 2-4); Staging retention (no rule yet); reading the
Record through a Staging-aware reader (consumers unchanged).

## Real output sample (committed code, offline test fixtures)

`test_runs::test_end_to_end_stage_then_promote_leaves_bad_days_out_of_the_record` produces, for three sessions where
one staged file is an HTML error page: 2 promoted, 1 rejected (`rejected 2026-10-22: f.csv: bad`), the rejected day
absent from the Record, `result: INCOMPLETE`. No real-data run is possible from the build container (no Drive
credentials, by design); the first real run is `pipeline-staging.yml` by hand after merge (dry-run first).

## Known limits (honest)

- `StagingArea.copies` lists the source folder on every call: one Drive listing per file; fine for a daily run, slow
  for a long back-fill (not optimised: KISS until measured).
- The default 7-day lag is a placeholder for the owner's tolerance (open decision 1).
