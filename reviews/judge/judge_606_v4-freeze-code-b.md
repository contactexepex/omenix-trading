# Judge 606: v4 freeze code (story/v4-freeze @ 10dc1c1c3), judge B, round 1 of 2

**FAIL (1 blocking; 1 note). Lane 1** (frozen files, forecast and score records). Criteria 1-4, 9, 11 and 12 of
`docs/stories/G6-v4-freeze.md` (text passed as 597.2), judged against main with G11 merged, as the orchestrator asked.

## Criteria

| # | Criterion | Result | My evidence |
|---|---|---|---|
| 1 | the three classes | PARTLY | `freeze_classes.py`: on the merged tree, 139 byte-checked, 60 recorded, 44 not deciding (the claim says 45). Every "named in FREEZE.md/_v2/_v3" lock is true: my scan of the three records finds every such path. A4's lock file `tests/quotes/test_recorder_baseline.py` exists. `recorder.py` and its capture modules are recorded (597.2 m3). Incomplete against G11: B1 |
| 2 | protocol commit | MET | `protocol_problems`: exactly one line, the commit exists and is an ancestor, and it is the last commit touching the protocol (`Git.commits_touching` is oldest-first, `ledger.py:104-106`, so `[-1]` is right), with the text hash checked. Plants "protocol check dropped" and "not-last accepted" caught |
| 3 | the rate | MET | `fno/forecast_v4/pricing.py` is byte-identical to G7b's (same SHA-256 on `story/g7b-completion`). The pack's rule is `build_iv30_rule` at the constant, and `pricing.py` is in `IV30_METHOD_FILES`. The tool refuses today on purpose: on my merged tree it prints exactly the two G7b readers (`forecast_v4_rules/wiring.py`, `forecast/wiring.py`), exit 1. Plants: pack rate 0.07, pricing dropped from the method, scan blind to `cfg[...]`: all caught |
| 4 | look refuses a broken freeze | MET | `cli._look` refuses unless `holds()`; the report's first lines are the check's. `freeze` is a keyword-only argument with no default. A shallow clone gives "NOT CHECKED". Plants "look ignores", "shallow read as checked" caught |
| 9 | disclosure | MET (read) | `freeze_disclosure.py` with its tests passes on both trees; the tool refuses a dirty tree (`refusals`) |
| 11 | the import walk | NOT MET on the merge | passes on the branch head (4 passed); fails on the trial merge: B1 |
| 12 | recorded drift printed | MET | `drift` from the recorded rows only (a 3-column pattern, apart from the byte-checked 2-column rows); plants "drift not printed", "drift ignores changes" caught |
| Gates | trial merge into origin/main 9d14a9332 (clean, 532b46ac9) | NOT MET | ruff, format (2,572), imports (2,701), record scan (9,176), check_numbers clean; **3 failed**, 16,145 passed, 1 skipped, 14 xfailed (token kept): the three walk tests |

## Findings

1. **Blocking B1: the classes miss G11 as merged on main.** On the trial merge `test_freeze_walk.py` fails 3 tests. My
   run of its `walk` lists 7 unclassed modules, each with its importer: `fno/ai/run_terms.py` (13 importers, among them
   `versions.py`, `outcome.py`, `scoring_gate.py`, `stop_rule.py`, `v4_fire.py`; the passed text classes it as recorded),
   `fno/ai/budget_stop.py` (from `v4_fire.py`), `fno/ai/record_writer.py` (`v4_collect.py`),
   `fno/budget/usage_ledger.py` and `fno/research_engine/statistics.py` (`v4_cost.py`), and `fno/alerts/sender.py` and
   `fno/pipeline/trigger.py` (`v4_fire.py`). It also finds one stale entry, `fno/ai/timing.py`, which is recorded but
   reached by nothing. The table was built before G11 merged. Fix: merge main, class each of the 7 with its reason
   (`run_terms.py`, `budget_stop.py`, `record_writer.py` decide AI rows, stops or misses, so recorded in the AI
   registration table; `usage_ledger.py`, `statistics.py`, `sender.py` and `trigger.py` each on its own reading), drop
   or justify `timing.py`, and rerun the full gates on the merged tree.

## Plants

12 planted on the branch head, 12 caught: drop the `fno/v4_pack` glob; drop `recorder.py` from recorded; shallow read
as checked; protocol check dropped; a not-last protocol commit accepted; drift not printed; drift ignoring changes; a
file added after the freeze ignored; the look ignoring a broken freeze; the pack's rate not the constant; `pricing.py`
out of `iv30_method`; the rate scan blind to `cfg["risk_free_rate"]`. The walk itself is shown working: it is what
fails on the merge.

## Notes

1. `fno/forecast/wiring.py` (v1, frozen) reads the configured rate and can never change. The tool stops naming it only
   once G7b's `forecast_v4_rules/wiring.py` no longer imports it (its only v4 importer: `forecast_scoring/wiring.py`
   is v3's). Then the walk flags it as stale and it leaves `RECORDED`. That is the intended path (blocker 3); say it
   in the reason string.

## Addendum 1: head 8c30d0b17 (main with G11 merged, G11's files classed), still round 1

**FAIL (1 should-fix; B1 fixed). Lane 1.** Trial merge into origin/main ddb0c0510 (clean, 18103c85d): ruff, format
(2,572), imports (2,701), record scan (9,179) and check_numbers all clean; **16,148 passed, 1 skipped, 14 xfailed**
(token kept). The walk passes.

- **B1: FIXED.** `freeze_classes.py` adds `run_terms.py` and `record_writer.py` to recorded; `budget_stop.py`,
  `alerts/sender.py`, `pipeline/trigger.py`, `budget/usage_ledger.py` and `research_engine/statistics.py` to not
  deciding; and drops `timing.py`, which is no longer reached. `usage_ledger.py` and `statistics.py` serve
  `v4_cost.py`'s cost line only; the sender and the trigger decide nothing (read).
- **Should-fix SF1: `fno/ai/budget_stop.py` is classed "not deciding", but it decides v4 rows.** Its own reason reads
  "whether an AI book fires ... a stop is a counted miss", and `v4_fire.py:10-11, 98-111` turns its answer into a
  logged `not_fired` row (a miss under protocol 4) for that book and day. That is the definition of a file whose bytes
  decide a v4 value. As "not deciding", a change after the freeze (its threshold, its fail-open choice, which the
  docstring says awaits the owner's ruling) prints no drift line. The walk also stops there, so its imports
  `fno/budget/report.py` and `fno/budget/constants.py` (BG1's meter and cap) are never classed. Fix: record it in the
  AI registration table (lock: G11 C8's tests) and class what the walk then reaches.

Plants: none new (12 of 12 in round 1, on code unchanged here except the class tables).

## Addendum 2: round 2 (the last), head 4183c46c8

**PASS (1 minor). Lane 1.** I ran the gates on a trial merge into origin/main 5a5d4ddc5 (clean, ac3e2d4d6). ruff,
format (2,578), imports (2,707), record scan (9,187) and check_numbers are all clean; **16,179 passed, 1 skipped, 14
xfailed** (token kept); the walk passes.

- **SF1: FIXED.** `budget_stop.py` is recorded in the AI registration table (`freeze_classes.py:83-84`), its lock
  `tests/ai/test_v4_budget_stop.py`.
- **The orchestrator's doubt: are `fno/budget/constants.py` and `report.py` deciding?** No; "not deciding" holds, by
  trace. `MeterBudgetStop.check` (`budget_stop.py:39-52`) takes from `constants.py` only the name `BUDGET_STOP`
  (`"stop"`), the same constant `cap.py` sets, so changing it changes both sides alike. From `report.py` it takes only
  the `MonthMeter` dataclass shape. The values that decide a stop (`cap.level`, `cap_minutes`, the book minutes) come
  from the injected meter: `fno/ai/wiring.py:92` passes `budget.wiring.build_month_meter`, whose
  `cap_reading(..., CapSettings.from_config(budget), ...)` (`fno/budget/cap.py:92-104`) decides the level. With
  `budget.cap: none` (owner, 24 Oct: "unlimited"), `CapSettings.capped` is False (my run), so the level is
  `BUDGET_NO_CAP` and `budget_stop` can never return a stop: no `not_fired` row can come from it today.
- **live_wiring.py: MET.** "A real run gets `daily.live_from` unchanged" is shown by two plants on the no-rehearsal
  branch of `rehearsed_live` (all dates None: 5 failed; `v4_pack` moved to 22 Oct: 6 failed).
- **The `wiring.py` conflict is resolved with both sides:** `build_iv30_rule()` (line 70) and `run_live_dates(cfg, env)`
  (lines 75, 95) are both present; no `risk_free_rate` read is left.
- **Minor m1:** the decider of a budget stop is `fno/budget/cap.py` plus the setting `budget.cap`, both outside the
  walk (injected by a composition root). Name `budget.cap` (value `none`) in the record's "settings v4 reads" with that
  sentence, so that a later cap (an owner decision) is known to start AI `not_fired` misses. Not a code change.

## Addendum 3: main merged in (G7b, MS-P1j2, A22e), head 56cd033eb

**PASS. Lane 1.** I judged only the merge resolution, m1's text and the class changes. My gates on a trial merge into
origin/main 0cdfdfe97 (clean, 2b14202fb): ruff, format (2,600), imports (2,729), record scan (9,212) and
check_numbers all clean; **16,335 passed, 1 skipped, 14 xfailed** (token kept).

- **`cli.py` (3451f75c0): both sides kept, nothing lost.** Against the freeze side, the merge adds only G7b's
  `build_diagnostic_lines`, `diagnostics` passed to `report_lines` and `report_json`, and `_report(...,
  diagnostics=(), *, freeze)`. Against G7b's side, it adds only the freeze parts: freeze lines first in the report, `|
  {"freeze": ...}` in the JSON, `_look`'s refusal and its `"freeze"` key, and `freeze` keyword-only with no default.
  Both diffs read.
- **m1: FIXED** (cce85cbcf). `budget.cap` (none) is among the settings v4 reads, with the sentence that a later cap
  starts AI `not_fired` misses.
- **Class changes: MET** (my run on the merge). 149 byte-checked, 63 recorded, 54 not deciding. `rate_readers()` is
  empty, `unmatched()` is empty, and no `PENDING_G7B` is left in `fno/` or `tools/`. The walk is clean with no stale
  entries. `fno/forecast/wiring.py` and `golden.py` are gone from the classes (no longer reached). `release_times.py`
  is recorded (V5's `first_seen_at` fallback). `availability.py` is not deciding: `release_times.first_seen_times`,
  the function V5 uses, does not call it (read).

## Addendum 4: the whole freeze, head b6ccadf80 (one round)

**FAIL (1 blocking; everything else MET). Lane 1.** I ran the gates on a trial merge into origin/main a54f1016d (clean,
c8c1c4fc2; a full clone). ruff, format (2,631), imports (2,760), record scan (9,268) and check_numbers are clean;
**1 failed**, 16,553 passed, 1 skipped, 13 xfailed (token kept).

| Check | Result | My evidence |
|---|---|---|
| Owner's answers | MET | DESK_DECISIONS row 342 (25 Oct): S = Mon 26 Oct, `Frozen on: 2026-10-25`, W1, W2, W5, W6, W7 signed, W3 and W8 decided, W4 dropped, the AI instruction files registered and hashed |
| Protocol commit 1712a476b, W1-W8 | MET | each added wording says what the signed plain-words table says (W1 intraday `RV_s`; W2 the future at mid, 5% spread, else void; W3 both yardsticks, never pooled; W5 bid > 0, ask >= bid, a trade that day, legs and the future; W6 V4's start and the pack's SHA-256; W7 the intraday series' rules; W8 the back-fill only as the scale, with the drift alert). The rest is the planned status line, `pricing.py`, section 10 (the three classes, the append-only slot registry) and ChatGPT's review paused. Nothing extra |
| Protocol commit in history | MET | an ancestor of the merge, and the last commit touching `PROTOCOL_v4.md` (`git log`); `check()` on the merge: "v4 freeze: intact" |
| Section split 5e99d5782 | MET | pins only under "## Frozen files", drift only under "## Recorded" (the AI `###` table stays inside); a missing heading reads the whole record (fails closed). Plants: AI table cut off (3 failed), pins from the whole record (4), drift from the wrong section (2), a missing heading read as no pins (11); all caught. Live check: `pricing.py` 0.065 to 0.066 gives "v4 freeze BROKEN: fno/forecast_v4/pricing.py: changed since the freeze"; a recorded `iv30.py` edit gives one drift line, intact |
| Slots, Frozen on | MET | `build_slot_registry().registered()`: 15 members, all effective 2026-10-26 (after `Frozen on: 2026-10-25`, `registered_on` 25 Oct ≤ start; `slot_file`'s refusals pass). AI rows `book2_hybrid_v2`, `book3_ai_v2` = G11's `current_version(..., "v4").forecaster`; both prompts' SHA-256 in the record |
| Ledger 101-108, settings | MET | eight `forecasts-v4` rows naming 1712a476b; `hypothesis` yes for V1, V2, V6a, V6b; `ai_books_v4` and `forecasts_v4_pack` set to "2026-10-26" |
| Forecast lab (ruling (a)) | MET | shows v4 frozen with its commit only from `Frozen on:` (point in time); plant "frozen before its day" caught (3) |

## Finding

1. **Blocking B1: the freeze commit's own test depends on test order, and fails alone.**
   `tests/forecast_scoring_v4/test_slot_file.py::test_since_the_freeze_the_repository_registers_the_15_members_from_its_first_counted_session`
   fails in my full trial-merge run, and alone on the exact head three times out of three (1 failed, 9 passed). It
   passes only when an earlier test in the same worker has filled the process-wide `@cache` on
   `fno/forecast_scoring/v4/wiring.py:132` `_forecasts()` from a fake Drive. Run cleanly, `build_slot_registry()` reaches
   `_first_eligible` → `_forecasts` → `build_drive_records(...).files()` → `build_drive_cache()`. That raises "set
   FNO_GDRIVE_... to use the Drive data store", because G7b's back-fill receipts (6a480457c, `receipts/data/v4/records/
   backfill/...`) are on main, and the test sandbox strips the Drive settings. So CI is red at random, and when the test
   passes it reads another test's fake data. Fix:
   - give this test its no-Drive seam (patch `build_drive_records`, or `_forecasts`, with an empty source);
   - clear `_forecasts.cache_clear()` around every test that patches it (an autouse fixture);
   - rerun the full suite with `-p no:randomly` and also the file alone.

   Production is not affected: a command builds `_forecasts` once, with Drive.

## Addendum 5: B1's fix and the 14:32 capture start, head 631a47c28 (the owner: "B checks it")

**PASS (1 note). Lane 1.** I ran the gates on a trial merge into origin/main 54890d75e (clean, 022ec3a42). ruff,
format (2,631), imports (2,760), record scan (9,275) and check_numbers are clean; **16,554 passed, 0 failed, 1
skipped, 13 xfailed** (token kept).

- **B1: FIXED.** `tests/forecast_scoring_v4/conftest.py` clears `wiring._forecasts` before and after every test in the
  folder (autouse), and the 15-members test takes the `no_v4_drive_records` seam. The test file alone: 10 passed, 3 of
  3 runs. Plant: the seam removed gives 1 failed alone.
- **No frozen constant moved.** `git diff b6ccadf80 631a47c28` touches nothing in `fno/forecast_v4/`, `fno/v4_pack/` or
  `fno/quotes/`. `V4_CAPTURE_START` 14:30:00 and `V4_PACK_WINDOW_END` 14:40:00 are unchanged (my run). The capture's
  own window is now `quotes.windows.v4` 14:32:00-14:40:00. The part starts at 14:29 (`v4_part._shortly_before`), and
  its early floor is 14:05.
- **Protocol and record.** a6da6f2b2 rewords only line 45 and the 1.6 row ("the window opens at 14:30:00; the capture
  starts inside it at 14:32:00, after A16's 14:30 mark"). `FREEZE_v4.md` names a6da6f2b2, which is an ancestor and the
  last commit touching the protocol; `check()` on the merge reads "v4 freeze: intact". Ledger 101-108 now name
  a6da6f2b2; those rows were never on main, so nothing written once is edited.
- **Note (timing, some evidence):** the measured full attempt is 2 min 38 s for 180 quotes (23 Oct), plus about 80 s
  for G10's extras, so about 14:32-14:36. A16's mark ends about 14:31:25 (85 s, 22 Oct). A retry after an incomplete
  first attempt now has about 4 minutes, not 6, and a slow one is cut at 14:40:00 (no request after it). One retry
  usually fits; two do not. The first live day's sidecar (G10 criterion 10) is the evidence to read.
