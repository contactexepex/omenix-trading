# Judge 610: REH1j code, a step not live in real runs is exercised, never a problem of the day (story/reh1j-not-live @ 2b902569d), judge E

**PASS (round 1 of 2). Lane 1** (what a rehearsal posts and records). Judge E, judge 1 of 2, own session; judge B's
verdict not read. Labels: strong, some, reasoning only.

## Criteria

| # | Criterion | Result | My evidence |
|---|---|---|---|
| J1 not counted | MET | `NotLiveInRealRuns` returns `not_live` with `exercised` (`live_wiring.py:57-80`). J1 plant (outcome unchanged) 5 failed; J12 (code unregistered) caught |
| J2 files kept | MET | Inputs and paths pass through; J2 (paths dropped) caught |
| J3 not built | MET | `is_built` walks fno's own parser (`built_commands.py`). J3 (check removed), J5 (prefix accepted) and J14 (not-built branch removed) caught; J13 (a lookup raise not caught) caught |
| J4 quote parts | MET | `ExercisedPartsApart` decides by `parts_result` on the live parts only. J6 (parts back in) and J11 (parts set apart in a real run) caught |
| J5 the line | MET | J7 (no post), J8 (one post per item) and J9 (parts left out) caught. Real run below: printed after "day done", posted once, labelled |
| J6 real runs unchanged | MET | Outside the mode `rehearsed_live` returns no notes (`live_wiring.py:35-38`), so `rehearsed_not_live` and `rehearsed_quotes_done` wrap nothing. J4 (every step wrapped) caught. `build_parser()` is a pure extraction |
| Gates | MET | Trial merge 76104cea3 with origin/main e06ec20fc (A22e, MS-P1j2 and G7b now on main): ruff clean, format clean (2,576 files), imports clean (2,705 files), record scan clean (9,184 files). Full suite with the token kept: **16,170 passed, 1 skipped (`growwapi`), 14 xfailed, 0 failed** |

## Real rehearsal at the trial merge (`daily run --rehearse --day 2026-10-23`, run 20261024T172343Z-e73f54)

Run after `sh tools/routine_setup.sh --groww` ("routine setup ok"); about 38 real minutes. Its last lines:
- `day done`
- `not live in real runs (exercised): margin_check not built; v4_release ok; quotes_done's v4 part failed: window closed ... no recorded in-window attempt of nifty on 2026-10-23; card ok; premium_range_scores ok; v4_deadline ok`
- `... ended: day done; branch refs/heads/rehearsal/2026-10-23-20261024T172343Z-e73f54; Drive dryrun/20261024T172343Z-e73f54/`

The full log, read by me:
- `v4_release`'s exercised result is G10's real exercise ("system_late (rehearsal: no v4 capture recorded for this
  day)"), not a NOT_LIVE exit 0.
- `card` is ok (T1f), `margin_check` is `not_built`, and `quotes_done` is ok, with the v4 part kept apart.

The clone's `origin` is the rehearsal's local bare repository.

**#fno-desk, read back:** this run's posts all carry the bold "DRY RUN, 2026-10-23 replay" label and, where not live,
the note: the v4 part alert, the card and one exercised-line post. `margin_check` posted nothing (not built). A
"margin_check failed: exit code 2" post at 19:47 CEST came from another session's rehearsal on code without REH1j: it
was started about 19:46, and margin_check runs at a run's start, about 20 minutes before that in this run.

## Plants

13 planted, 13 caught (J1-J9, J11-J14), each alone on `tests/rehearsal` and `tests/daily` (322 tests), restored after
each.

## Findings

None blocking, none should-fix, none minor.

## Notes

- An exercised failure reaches Slack twice: the step's own labelled alert, and the line. This is stated in the Claims
  and is acceptable.
- The rehearsal needs the Groww SDK installed even though it never calls Groww (the builder's REH1b point, reported
  to the orchestrator). Confirmed: it ran only after `routine_setup.sh --groww`.
