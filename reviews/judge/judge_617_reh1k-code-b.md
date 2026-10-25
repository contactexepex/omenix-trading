# Judge 617: REH1k code, the lab editions in a rehearsal (story/reh1k-lab-editions @ 34aad0d85), judge B (2 of 2), round 1 of 2

**PASS (1 minor). Lane 1** (rehearsal posts to #fno-forecast and #fno-desk). I did not read judge E's verdict. Code:
`fno/forecast_lab/wiring.py` (`lab_live`, `build_edition`, `build_preview`), `fno/rehearsal/live_wiring.py`
(`note_this_process`), `rehearse.py` (not-live routine commands), `routines.py` (`live_key` on `lab open` and `lab
close`), `exercised_line.py`, and the REH1h test fix.

## Criteria (the orchestrator's four checks)

| Check | Result | My evidence |
|---|---|---|
| Real editions unchanged | MET | `lab_live` is `rehearsed_live(live_from(cfg), env)`, which returns `(live, {})` without a rehearsal mode; `note_this_process(None)` changes nothing; `build_composer` gets the same dates `live_from` gave. Plant "real run's dates altered" (6 failed) caught |
| Rehearsal writes only under `dryrun/<run_id>` | MET | the edition's records go through `records(edition, env)`, O9's data store behind `build_owner_drive`'s `rehearsed_drive` (unchanged); `_not_live_editions` only reads the checkout's `config.yaml`; nothing new writes |
| Every post labelled, allowed channels only | MET | #fno-forecast through `rehearsed_report_poster(SlackFilesPoster(token, FNO_FORECAST_CHANNEL_ID))` (`forecast_lab/wiring.py:43-48`), #fno-desk through the alert sender; the not-live line is set for the edition's process (`note_this_process`); the exercised line goes through REH1j's labelled sender. Plants "rehearsal not exercised" (5), "post not noted" (3) caught |
| A not-live command is exercised, never failed | MET | `run_routine` puts it under `exercised` and leaves it out of `failed`; it refuses `not_live` without an `exercised` record (never dropped). Plants "counted failed" (2), "editions never not-live" (1), "morning live key dropped" (1) caught |
| REH1h flake fix hides no bug | MET | the test now patches `fno.storage.wiring.build_manifest_folder`, and every manifest writer the test reaches calls it at run time: `build_owner_drive_store` (`storage/wiring.py:97`), `build_revision_archive` (`:121`), the librarian builders in the same module, and `storage.build_manifest_folder()` in `pipeline`, `filings`, `nse_margins` (grep). The old constant patch leaked into modules first imported during that test (`backfill_daily`), which failed by test order. That was a test-isolation defect, not product code |
| Gates | MET | trial merge into origin/main f2c00af8f (clean, 644ff540f): ruff, format (2,629), imports (2,758), record scan (9,253), check_numbers clean; **16,527 passed, 1 skipped, 14 xfailed** (token kept) |

## Findings

1. **Minor m1:** no test pins `build_preview`'s real dates. My plant (`build_composer(edition, env)` instead of
   `live_from(load_app_config())`) survives the rehearsal and forecast-lab tests. Outside a rehearsal the two are
   equal, and no routine runs the preview, so nothing is wrong today. A test of the preview under a rehearsal mode
   would keep the comment's promise ("the real dates: no rehearsal note").

## Plants

7 planted, 6 caught; the survivor is m1.

## Addendum 1: round 2 (the last), head cd7cf403d (tests and Claims only)

**PASS. Lane 1.** No code changed. The branch's own commits since 34aad0d85 are `d4fd149a6`
(`tests/rehearsal/test_lab_editions.py` only) and `b3c5a1dfe` (the story only). The `fno/` difference against
34aad0d85, `fno/forecast_v5_v1/cli.py` and `freeze.py`, is G14's merge `110cfae03`, already on main. Against main, the
trial merge's `fno/` diff is exactly the five REH1k files judged above.
- **m1: FIXED.** My survivor plant (`build_preview` calling `build_composer(edition, env)`) now fails 2 tests.
- **Gates:** trial merge into origin/main (clean, 9fd602235): ruff, format (2,629), imports (2,758), record scan
  (9,257) and check_numbers clean; **16,532 passed, 1 skipped, 14 xfailed** (token kept).
