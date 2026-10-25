# Judge 603: G10 v4-pack children take the rehearsed live dates (story/v4pack-rehearsed-live @ 2871e32d4), judge B, round 1 of 2

**PASS (no findings; 1 note). Lane 1** (forecast records and Drive writes in rehearsals). The code is one composition
root, `fno/v4_pack/wiring.py`: a new `run_live_dates(cfg, env) = rehearsed_live(live_dates(cfg), env)[0]`, used by
`build_release_run` and `build_deadline_run`. Plus one test file, `tests/rehearsal/test_v4_pack_live.py` (RL1-RL3),
the story text and the register row. This is the fix for the note in my judge 594.

## Criteria

| Check | Result | My evidence |
|---|---|---|
| A real run is unchanged | MET | `rehearsed_live` returns `live, {}` when no rehearsal mode is set (`fno/rehearsal/live_wiring.py:24-27`, read); RL1 and RL2 assert the real 26 Oct date; plant "real run altered" fails 3 tests |
| A rehearsal gets the daily root's dates | MET | the same `rehearsed_live` the daily root uses (REH1c), so the steps and their children agree; RL1 (23 Oct replay: `v4_pack` is the replay day, `forecasts_v4` keeps 22 Oct); plant "no rehearsal dates" fails 4 |
| Both children re-pointed | MET | RL2 is parametrised over both builders; plants "deadline back on config dates" and "release ignores env" each fail 1 |
| Writes stay in `dryrun/` | MET | the builders' store is `build_data_store`, behind `build_owner_drive` and REH1's `rehearsed_drive` (unchanged); RL3: the catch-up writes 22 Oct `system_late` and 23 Oct is excused (`NO_CAPTURE`), with no failure; the real-run case writes nothing ("not live") |
| Deadline in a rehearsal | MET | `rehearsed_catch_up(env)` is unchanged, so only the replayed day is checked (G10 criterion 12) |
| Gates | MET | trial merge into origin/main 86eddc67b (clean, 304a7b426): ruff, format (2,563), imports (2,692), record scan (9,164), check_numbers clean; **16,072 passed, 1 skipped, 14 xfailed**, token kept |

## Plants

4 planted (`run_live_dates` returning the config dates; the deadline builder back on `live_dates`; the release
ignoring `env`; a real run altered), 4 caught.

## Notes

1. The freeze builder also edits `fno/v4_pack/wiring.py` (the `pricing.py` import). Whichever merges second must merge
   main and rerun `tests/rehearsal/test_v4_pack_live.py` and `tests/v4_pack`, as the orchestrator said. The builder's
   dry run (20261024T152428Z-b3890a) is not re-run here (no second 23 Oct rehearsal beside the orchestrator's).
