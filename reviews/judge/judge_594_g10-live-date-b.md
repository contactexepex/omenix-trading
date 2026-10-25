# Judge 594: G10 live date (story/g10-live-date @ b1de50141), judge B, round 1 of 2

**PASS (no findings; 1 note). Lane 1.** This change sets the date that switches on Groww and NSE capture, Drive
write-once records and #fno-desk alerts. It is 4 files: `config.yaml` (`daily.live_from.v4_pack: "2026-10-26"`), two
tests re-pinned, and the story's "Live date" note. The owner's row is `DESK_DECISIONS.md:335` ("v4 pack live Monday -
Option A"). The G10 code it switches on is on main: 5bde718c1 is an ancestor of origin/main, judged in 584.2.

## Criteria

| Check | Result | My evidence |
|---|---|---|
| The date matches the owner | MET | `config.yaml` `v4_pack: "2026-10-26"`; `live_dates(load_config())["v4_pack"] == date(2026, 10, 26)` (my run) |
| Tests not loosened | MET | `test_steps.py` pins 26 Oct instead of None; in `test_v4_steps.py` the release's `live_from is None` becomes `release.step.live_from == deadline.step.live_from == date(2026, 10, 26)`: one assertion replaced by a stricter one covering both steps. Plants: `null`, `"2026-10-23"`, `"2026-10-27"` each fail 2 tests |
| Nothing writes before 26 Oct | MET | my run: the parts on 23 Oct are nifty, nse, indices (no `v4`); on 26 Oct v4 is added; `ReleaseRun.run(23 Oct)` gives "not live", `failed` False; both steps are wrapped in `LiveFrom(..., 26 Oct)` |
| 22 and 23 Oct written as `system_late` (D2) | MET, intended | on Monday the catch-up runs over scored sessions 22 Oct to 25 Oct = [22, 23] on the real calendar, and `missing_label` gives `system_late` for both. Correct under protocol 1.6 (no release record, no pack existed) and D2 (accepted 24 Oct); both days are before the freeze, so nothing counted changes |
| Monday's deadline on real receipts | MET (read-only) | my run of `RecordCommitments` plus the real `build_commitment_times` (GitHub push receipts): 22 Oct 23 live rows, 23 on time, the latest received 14:11:34 IST; 23 Oct 23 rows, 23 on time, the latest 14:08:07 IST. No unknown time, so Monday's catch-up should not fail on them |
| Step order, A4h last | MET | `DAILY_RUN_STEPS[-5:]` = premium_range_scores, v4_deadline, candles, close_read, close_recheck |
| Nothing else goes live | MET | no `v4-fire.yml`, no `forecasts_v4_pack` step, no G11 key on the merge (grep); only the `v4_pack` key changed |
| Gates | MET | trial merge into origin/main c97e5848f (clean, 671e064d2): ruff, format (2,516 files), imports (2,645), record scan (9,101), check_numbers all clean; **15,646 passed, 1 skipped, 15 xfailed**, run with `FNO_SLACK_BOT_TOKEN` kept (`tests/conftest.py:124` strips it from every test in any case, `tests/live_credentials.py:14`) |

## Plants

3 planted (the key set to null, to an earlier date, to a later date), 3 caught.

## Notes

1. The builder's out-of-scope finding is for after Monday, as routed: in a rehearsal REH1c makes the step live, but
   `v4-pack`'s child commands read `live_dates(cfg)` directly. It is not a finding here. Monday itself is the day
   before October's monthly expiry: `e` has 1 day left and IV30 is flagged, as the story says.
