# Judge 189: G10 build part 1: `story/g10-build` 0d0d83f7 (f06da575, 4f881a88, 0d0d83f7; lane 1)

Judge B. A16/G8 builder. Story `docs/stories/G-forecasts.md` G10 (text PASS, judge 161 addendum 3). Part 1 covers
criteria 2, 4 and 5, and the G8 side of 3. Criteria 1 and 1a (protocol text, waiting for the owner's sign-off), 1b
(pack-SHA refusal and the 15:10 GitHub receipt), the capture that writes `v4_days/`, the label on each G7 and M1
record, and 6 (the 14:30 dry run) are part 2, by design and stated.

## Gates
- Trial merge of 0d0d83f7 with `main` 7c154a90 is clean. Ruff, format and imports are clean.
- **6,143 passed, 2 failed.** Both failures are E2c's account tests, red on `main` until `fix/e2c-account-tests`
  (judge 187, PASS) is pushed. Not this branch's.
- v4, rules, scoring and weather tests: 317 passed.

## Criteria in part 1
| # | Result | Evidence |
|---|---|---|
| 2 Clock in `terms.py`; G7 and M1 refuse at 14:30 through one constant | MET | `V4_CAPTURE_START` (14:30), `V4_PACK_WINDOW_END` (14:40), `V4_DEADLINE` (15:10) and `V4_COMMON_SNAPSHOT` (15:15) are in `terms.py`. G7's `CUTOFF = V4_CAPTURE_START`, and M1 imports the same `CUTOFF`. There are boundary tests at 14:29:59 (accepted) and 14:30 (refused) |
| 4 X by a committed tool; just above flagged, just below not; nothing dropped | MET, **reproduced** | I ran `tools/v4_moved_after_cutoff.py` myself against the owner's Drive copies (read-only). The output is identical to the committed JSON except `computed_at`: X = 0.006104597099330481, n = 1,661 (2020-01-02 to 2026-10-14), 1,680 rows read, 83 flagged (4.997%), revision 1d68c447. The arithmetic checks: the nearest rank ceil(0.95 × 1,661) = 1,578 leaves 83 strictly above. My plant `>=` for `>` fails the boundary test. The flag only counts and never drops a day |
| 5 Back-fill unchanged for G7 and M1 | MET (sample, mine) | I rebuilt G7's back-fill records for 10 days (2019-2026, crash days included; 90 records) at the merge base and on the branch. They are identical, `inputs_sha256` included, excluding `method_sha256`. M1's weather for 5 days is identical except `method_sha256`, as the builder said. The builder rebuilt all 2,417 files |
| 3 (G8 side) Day labels, `system_late` out for every family, counts on every report | MET for part 1 | `LateDaysOut` drops `system_late` days from forecasts and outcomes in the one `build_scoring` root (members and reports alike), so such a day is never scored, missed or an input failure. `day_counts` counts only days up to the report's date. A bad day file stops scoring. An A or A2 file with a field observed after 14:40 is refused. **My plants:** `LateDaysOut` keeping every day, the 14:40 check removed, and counting days after `as_of` each fail 1 test |

## Must be in part 2 (recorded here; required before go-live, not blocking part 1)
1. **The scheduled report cannot compute the flag.** The only scheduled v4 report (`postmortem-weekly.yml`) has no
   `FNO_GDRIVE_*` settings, so `_cutoff_moves()` returns `NoCutoffLevels`. After go-live every labelled day would show
   "flag not computable", and `flagged` would always be 0. Either give that job read access to Drive, or record the
   flag where the report can read it (for example in the day file, written after 15:15). Today there are no labelled
   days, so nothing is wrong yet.
2. **A Drive failure should not stop the report.** With Drive settings present, a Drive read error in
   `A16CutoffMoves.level` propagates and stops the whole report. The owner's rule is "flag, never block": a Drive
   failure should give "not computable" (`SnapshotChanged` should still stop the report, as built).
3. **Criterion 3's "live and close-proxy cohorts reported apart"** is still only the `live_forecasts` count. The
   builder proposes per-cohort scores in part 2. Agreed: there are no live rows to score yet.
4. **The `report_json` signature:** whichever of `story/v4-iv-proof` and this branch merges second adds `days=`. The
   builder will do it.

**Verdict: PASS for 0d0d83f7 as part 1.** Merge it after `main` is green. Part 2 comes back with criteria 1, 1a, 1b,
the rest of 3, 6 and items 1-3 above.

## Addendum 1 (15 Oct 2026): 5fd16405, part-2 item 2 fixed early

One commit changes `cutoff_moves.py` and its test. `A16CutoffMoves.level` now returns None, meaning "not computable",
when the Drive read raises. The try covers only `store.get`, so `SnapshotChanged` still stops the report. The new test
(a store whose `get` raises `ConnectionError`) passes, and with the fix reverted it fails, as the builder reports.
`tests/forecast_scoring_v4`: 54 passed.

**Item 1, the builder's proposal (store the flag at A16's 15:30 run in the day's derived files):** sound, and better
than giving the weekly job Drive access. The report would no longer depend on credentials, and re-running it gives the
same number (reasoning only). Two conditions:
- (a) it touches A16's paths, so agree it with the orchestrator first, as the builder says;
- (b) A16's `session_rv.py`, `status.py`, `slots.py` and `realised_vol.py` are byte-checked at the v4 freeze (judge
  177 addendum 1), so the change must land **before** the freeze commit, or it becomes a new version.

**Verdict: 5fd16405 stands under the PASS of judge 189.** Items 1, 3 and 4 stay for part 2.

## Addendum 2 (15 Oct 2026): 638cf54c, after the main merge

- **The delta since the PASS:** 5fd16405 (addendum 1); the merge of `main` (355c6669, no conflicts, which brings in
  the orchestrator's batch: the V1 filter, skill_n, effective_start, the IV proof and the E2c test fixes); and
  638cf54c, one test call. `test_iv_never_used.py` now passes `days=build_day_counts(DAY)` to `report_json`, the
  agreed one-line merge fix (part-2 item 4, done). The IV proof still compares the plain and patched runs, with the
  day counts now part of both.
- **Gates on 638cf54c, run myself:** **6,318 passed, 0 failed**. Ruff and format are clean. v4, scoring, rules and
  weather tests: 324 passed.

**Verdict: PASS for 638cf54c** (part 1). Merge it. Part 2 keeps items 1 and 3 (the stored flag, before the freeze; the
cohort scores) and criteria 1, 1a, 1b and 6.
