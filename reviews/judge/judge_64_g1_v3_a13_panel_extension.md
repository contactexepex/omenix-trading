# Judge 64: G1 protocol v3 and story A13 (the NIFTY panel extends daily)

Date: 13 Oct 2026 (UTC). Code: trading `main` at 217fa7c, merged as b5e5e9b. Claims: `reviews/claude/response_68_g1-v3-panel-extension.md`
addendum 2; ChatGPT review 30; Claude response 69. Holdout rule kept: I opened no 2019-2023 row of the golden file or
the back-fill (I ran their tests; I read no rows).

## Verdict: NOT YET: one must-fix (replay reads the wrong commit) and two should-fix items before v3 is frozen

The A13 append itself is sound. Two real days rebuilt from Drive match the panel row for row. The first archived
version is used even when a revision has a different close. Crashes are refused. v1 and v2 hold. **Do not freeze v3
yet:** its text and the byte-frozen `replay.py` anchor the replay on the wrong commit. Once that is fixed (small) and
re-checked, v3 can be frozen and A13's schedule switched on.

## Gates

- CI `checks` at b5e5e9b: **success** (run 38469554175). Runs at 20ea237, c8b03c9 and 6d21d6d failed while `main`
  was broken (the ISOLATION import), as the orchestrator said.
- My local run at b5e5e9b: 1,777 passed; ruff and imports clean.
- v2's `require_version_frozen` at HEAD passes (protocol ab2e811, every byte-checked file equal). The v1 and v2 freeze
  tests and the new experiment 1 freeze-hash test pass (13). The diff 6d21d6d..b5e5e9b touches nothing under
  `fno/forecast/` and no panel data file.

## The orchestrator's checks

| # | Question | Finding | Result |
|---|---|---|---|
| a | v1/v2 still hold; re-scoped tests not weaker | `test_golden.py` keeps the golden file's own days; `differences` still names every golden day missing from the recomputation, and every value must match. `test_backfill.py` recomputes the back-fill's own days and takes the pack hash from `manifest.json` at the commit that last wrote the back-fill (CI uses `fetch-depth: 0`). A rewritten old panel row would still fail both | MET |
| b | First archived version for both inputs | My planted revision with a **different NIFTY close** (+111.11) in the revisions area: the day records the first file's SHA-256 and A11's later version. Code plant "prefer the revision when it exists": caught (3 tests fail). The builder's own test changes only a trailing newline, so mine is the stronger case | MET |
| c | Crash test; commit only on exit 0 | The crash test passes. The workflow adds `research/data/nifty-panel` only when `steps.append.outcome == success` (true exit status, even with continue-on-error). **But** `PanelAppender.verify()`, the start-of-run check response 69 promised, has **no test**: I disabled it and all 132 `tests/research_data` tests passed. The crash test passes only because `_require_unchanged` re-checks the files being appended to. An untouched older year file that is corrupt would not be caught by any test | PARTLY (should fix: one test corrupting an untouched year file) |
| d | Replay uses the panel at the forecast's parent commit | **Wrong under the real workflow.** Since F1/G5, `forecast-capture.yml` commits the pack alone at about 15:12, then pulls `main` (steps at lines 81, 88 and 90), then commits the records at about 15:16-15:30. The records commit's first parent is therefore `main` after those pulls, not the checkout the capture computed from. I built that commit order in a temporary repo (panel, pack commit, another commit pulled in, records commit): `inputs_commit` is the pulled-in commit, and the replay **reports a mismatch** on `pack.json`. The builder's test commits pack and records together, so it cannot see this. Fix: anchor on the commit that added `<d>_pack.json` (committed before any pull, so its first parent is what the capture read), in `replay.py` and in v3 section 3's text, plus a test with the real commit order | **NOT MET (must fix)** |
| e | Live Q5 against the 15:00 pack IV30 | `score_sources.pack_iv30` reads the receipt-verified pack; flagged or missing IV30 voids primary Q5. G4's planted-disagreement test passes. **But** the rule sits in `fno/forecast_scoring/wiring.py` (`LIVE: ... live.pack_iv30.get(day)`), and my plant swapping it for the panel IV30 passed all 39 `tests/forecast_scoring` tests. That file is also not in v3's freeze list | PARTLY (should fix: a wiring test, or freeze the file) |
| f | Archive time = run read time: enough for point in time? | See below | Enough, with one condition |

**(f), statistician and data engineer:** for a live forecast, point in time means the capture at day *t* reads no
data from day *t* or later. That is guaranteed by **git order**, not by the archive time. The capture reads the panel
committed before its run. NSE publishes day *t*'s F&O file in the evening, so the panel cannot hold day *t* at 15:10.
`LiveForecastHistory` also reads only `d < day` (v3 section 3). `inputs_read_at` is then an audit field (an upper bound
for when the file existed in Drive), and the append commit time in git is a second bound. **Condition:** the morning
retry must never run on the same day as a session's own F&O file. It cannot, since the file comes out after 15:30.
Reasoning only; no counter-case found.

## A13 criteria

| # | Criterion | Check | Result |
|---|---|---|---|
| 1 | Appended day equals A3's build | Real data: I rebuilt 9 Oct and 12 Oct 2026 from Drive's first archived files with A3's builder through `first_archived_inputs` and compared with the committed panel: options 1,888 = 1,888 and futures 3 = 3 on each day, equal row for row. A real append (13 Oct) could not run: the F&O file is not archived in Drive yet (the workflow's librarian step does that first) | MET (by the equivalent real rebuild; the first two real appends still to be compared) |
| 2 | A day is never rewritten; a planted rewrite names the day | `_check` refuses a day already present or not after the end, with the day named; tests pass | MET |
| 3 | Old bytes are a prefix | One new gzip member per touched year file; `_require_unchanged` checks the old file's SHA-256 before growing it | MET |
| 4 | A missing file, close or contract fails the day, one line, writes nothing | Delayed-input and official-close tests pass for both inputs; my real run on 13 Oct stopped with `fo_file_missing` and wrote nothing | MET |
| 5 | `iv30_history_stale` does not fire 30 sessions on | Covered by the builder's test (not re-planted by me) | MET (not planted) |
| 6 | No frozen file changes | v1, v2 and experiment 1 freeze hashes hold | MET |

## Review 30 section 8 tests

| Test | Result |
|---|---|
| 1 Crash leaves previous generation readable, recovers | Tested; but the start-of-run check is untested (c) |
| 2 First archived versions, first and revised closes disagree | Builder's test differs only by a newline; my different-close plant passes. Should use a real value difference |
| 3 Replay uses its recorded panel generation | Tested only in a commit order the workflow does not produce (d) |
| 4 Live Q5 uses the 15:00 IV30 | Tested at the resolver; not at the wiring (e) |
| 5 Delayed close fails explicitly, retry without gaps | Tested for both inputs |

## Before the freeze (my advice, reasoning only)

1. Must: fix the replay anchor (pack commit) in `replay.py` and v3 section 3, with a test in the real commit order.
2. Should: a test for `verify()` on an untouched year file; a wiring test for live Q5, or add
   `fno/forecast_scoring/wiring.py` to v3's freeze list.
3. Should, design: v3 freezes `fno/pipeline/wiring.py`, which is O6's shared composition root (triggers, closes,
   dry runs). Byte-freezing it means any later O6 or F1 wiring change stops the panel job. This is the same trap as
   G1 v1's shared-file freeze (judge 47). Move A13's wiring into its own small composition root and freeze that
   instead.

Then: v3 can be frozen and A13's schedule switched on, with the first two real appended days compared by me
against A3's build.

## Project rules

New behaviour in new classes; constants in `fno/constants.py`; file sizes within 350 lines (largest 143); no secret in
files; the workflow has no AI and posts only to #fno-desk. Drive was read with the owner drive connection, read-only;
my scratch append went to a copy outside the repository.

## Addendum 1 (re-judge of 94880cc): PASS; v3 can be frozen, with one scope decision first

| Judge 64 item | My check | Result |
|---|---|---|
| (d) replay anchor | My own scenario, in the capture's real order: panel, then the pack commit, then a commit pulled in that changes the manifest, then the records commit. Against the new `replay.py`: `inputs_commit` is the checkout the pack was computed from, and the replay matches. Before the fix it read the pulled-in commit and reported a mismatch. `PROTOCOL_v3.md` section 2 now says the same | MET |
| (c) `verify()` untested | I made `verify()` return at once: 2 tests fail (the new test with untouched 2020 files). The builder also found and fixed a crash on a damaged gzip | MET |
| (e) live Q5 wiring untested | The rule now lives in `fno/forecast_scoring/q5_thresholds.py`. My plant giving the live resolver the panel IV30 fails `test_scoring_wiring_q5` (1 failed, 39 passed) | MET |
| shared O6 wiring frozen | A13 has its own root, `fno/pipeline/panel_wiring.py` (listed in CLAUDE.md); O6's `wiring.py` only imports `drive_files` from it, never the reverse | MET |

Gates at 76eede9:
- tests: forecast, forecast_scoring, research_data, pipeline and research, 314 passed;
- ruff and imports: clean.

**One scope decision before the freeze (some evidence, from the builder's own note and the freeze list).** v3's list
byte-freezes `resolution.py`, `score_sources.py` and `scoring.py`. Those are G4's general scoring files, not only
question 5. The v3 check runs inside the panel job, so any later G4 change to them stops the daily panel appends. This
is the shared-file trap again, one level down.

Simplest fix (reasoning only): freeze `q5_thresholds.py` and `replay.py` as v3's G4 part, since they now hold the live
Q5 rule and the replay, not the three general files. Alternatively, split the check: the panel job checks the protocol
and the A13 files only, and G4's `score_forecasts` checks the Q5 files whenever live records exist, as it does for v2.
Either is fine. Freezing as listed would also work today, but it will hurt the first time G4 changes. The
judge 62 must-fix touches `ai_sources.py`, which is not on the list.

**On PASS:** v3 can be frozen once that scope is settled, and A13's schedule switched on. After the first two real
appends I will compare them with A3's build, as A13's "judge verifies" asks. Note the builder's point: until
`panel-days.yml` is scheduled, 13 Oct's F&O file reaches Drive only through `market-publish.yml`, which depends on the
database check.

## Addendum 2 (split freeze, e3e2dca / b704c36): PASS, with two small test gaps and an order rule for the freeze step

**1. Each change fails only its own section: MET at the check level.** `tests/test_freeze_sections.py` (5) passes.
My plant made `section_text` return the whole record instead of one section: 3 tests failed, so the isolation is
really tested.

**But the wiring that picks the section is not tested (should fix, small).** I swapped the section name in each
composition root:
- the panel job checking `forecast-scores`;
- scoring checking `panel-days`.

Both plants pass all 214 tests in `tests/test_freeze_sections.py`, `forecast_scoring`, `research_data` and
`pipeline`. `test_scoring_refuses_when_its_own_v3_section_does_not_hold` replaces `require_section_frozen` with a
stub that ignores its section argument. A wrong constant would leave A13's files unguarded, or would tie the panel
to G4's files again: exactly what the split exists to prevent. Fix: each wiring test asserts the section it passes
(`PANEL_DAYS` in `panel_wiring.py`, `FORECAST_SCORES` in G4's wiring).

**2. DRY (the about eight repeated lines): acceptable.** v2's `require_version_frozen` checks every row of its
record, and `freeze_v2.py` is byte-frozen by v2. A shared helper would mean editing a frozen file, so a new v2 for no
behaviour change. The new module reuses v2's building blocks (`read_version_freeze`, `changed_files`, `Git`) and
repeats only the order of checks. The clean path is the one taken: from v3 on, `freeze_sections.require_section_frozen`
is the one shared helper for later versions. Reasoning only.

**3. The freeze step, exactly (and one order rule):**
1. The protocol commit is the commit whose `PROTOCOL_v3.md` is final; today e3e2dca last changed it. The G1 builder
   writes `research/forecasts/FREEZE_v3.md` in a later commit: the preamble names that protocol commit, with one
   section per job, each holding the SHA-256 of the protocol, `fno/freeze_sections.py` and its job's files, taken from
   the files at the freeze commit. The orchestrator confirms, as for v2.
2. **Order rule:** `panel-days.yml` is in the `panel-days` section. Its schedule must therefore be added **before or
   in the same commit as** `FREEZE_v3.md`. If the schedule is added after the record, the workflow's bytes no longer
   match, and the panel job refuses on its own section on its first scheduled run.
3. With that, the schedule is the only remaining change. Then I check the record's hashes against the files, and
   compare the first two real appended days with A3's build.

**One more risk to close at the freeze (should fix, reasoning only).** Before the record exists, the panel job treats
"no `FREEZE_v3.md`" as `NotYetFrozen`, prints "nothing appended" and exits 0 with no alert. Once the job is scheduled,
the same path would let a deleted or renamed record stop the panel silently. Q5's base rate would then go stale
about 21 sessions later with nobody told. Once scheduled, a missing record should fail with an alert, for example
by making `NotYetFrozen` an alerting failure in the scheduled run.

Gates: the affected suites pass (214). The full suite was not re-run for this small change.

## Addendum 3 (the v3 freeze as confirmed: protocol 904c036, record c1bf97f amended in f67065a; look-ahead test fix)

**My own hash check at 8fa1d68:** I hashed every row of `FREEZE_v3.md` from the files themselves, independently of
the code.
- All byte-checked rows of both sections match: `panel-days` 6 files, `forecast-scores` 7 files.
- The "recorded, not byte-checked" rows also match, except `manifest.json`, which the record itself says grows by
  appends.
- `require_section_frozen` passes for both sections at HEAD, with protocol commit 904c036.
- `PROTOCOL_v3.md` is unchanged since 904c036.

**The amendment f67065a changed exactly three things:**
1. the `panel-days.yml` row's hash (`5a7ec8dd…` to `6971c687…`);
2. a dated note saying so;
3. the workflow itself: the archive steps' end day now comes from `last_complete_day(now_ist())` instead of today,
   and the librarian-failure alert's multi-line `python -c` string, a SyntaxError that never sent, now passes the
   message through `sys.argv`.

No other row, no protocol text and no `forecast-scores` row changed. The workflow change keeps "commit the panel only
on a clean append". This is a disclosed record edit before confirmation, approved by the orchestrator. Acceptable,
because no scheduled append ran under the old hash.

**My two should-fixes from addendum 2 are in:**
- Re-planting the section swaps now fails tests: the panel job checking `forecast-scores` gives 3 failed, and
  scoring checking `panel-days` gives 2 failed.
- A missing freeze record is now an alerting failure
  (`test_a_missing_freeze_record_is_an_alerting_failure_never_a_silent_stop`).

**Look-ahead test fix (5c0b366, 716842d): MET, nothing loosened.**
- `perturb_panel` now draws one number per call and gives each day its own stream (`Random(f"{trial}-{table}-{day}")`),
  so appended days never change another day's changes.
- `test_lookahead.py` passes 9 of 9 on HEAD and 9 of 9 on the panel at 3a03b90, just before the first append.
- The test still bites: my plant, replacing the leaking live plant with a feature that does not leak, fails it.

Note (reasoning only): the plant now reads the day's raw VIX close. The harness is still only probabilistic for a
real **threshold** feature declared live by mistake: a scaled VIX may not cross the median. One deterministic trial
that removes every after-cutoff value (all None) would make detection certain for any feature. This is a small
harness improvement, not a defect today.

**Still to do (my side):** compare the first two scheduled appends (from 14 Oct, 21:41 IST) with A3's build. The 13 Oct
day came from the manual dispatch run 38474280810.

## Addendum 4 (look-ahead harness: the deterministic removal trial, 7d5dd17)

**MET, nothing loosened.**
- After its random trials, `assert_no_lookahead` now runs one fixed trial: every panel close after the cutoff is set
  to None, and that day's option and future rows are dropped.
- The new test makes `VixAboveMedian` (a real threshold feature) a live feature by mistake. With `trials=0` the test
  is caught by the removal trial alone, on 5 days.
- My plant, skipping the removal trial's assertion, makes that test fail (1 failed, 9 passed).
- The diff to `test_lookahead.py` only adds a test; no assertion or plant was removed or weakened.
- `tests/research_engine` with the baseline tests: 189 passed. So no correct feature reads data after its cutoff, even
  with everything after it removed.

**Note (information):** a feature that crashes on a missing value would raise a TypeError instead of the look-ahead
assertion. It still fails loudly, so no leak can pass silently.

## Addendum 5 (14 Oct 2026, 17:05 UTC): the first real A13 append (13 Oct session) checked; the 14 Oct run has not started

- **The 13 Oct append is exact.** Commit 9cba740 ("A13 Actions: NIFTY panel sessions 2026-10-14") comes from manual
  run 1 at 21:56 UTC on 13 Oct (03:27 IST on 14 Oct). It appended the 13 Oct session from the first archived files:
  `BhavCopy_NSE_FO_0_0_0_20261013_F_0000.csv.zip` and `ind_close_all_13102026.csv`, with their SHA-256 recorded in the
  manifest, `inputs_version` "first archived (A11 original)", no later versions, and 1,900 option rows plus 3 futures
  rows. I rebuilt 13 Oct from Drive's first archived files with A3's builder (`first_archived_inputs` and
  `NiftyPanelBuilder`). Options 1,900 = 1,900 and futures 3 = 3: **equal row for row**. The commit title carries the
  run date (IST), not the session date. That is confusing but harmless.
- **The freeze gate ran.** The step "Append the new sessions ... only under the v3 freeze" succeeded in run 1 and in
  run 3.
- **Run 1 was red only because of the old alert step.** The append and commit steps succeeded. The red came from the
  "One line to" step at c1bf97f, before its condition fix in f67065a. Scheduled run 3 (12:20 UTC on 14 Oct) skipped
  that step and is green. It appended nothing new.
- **The 14 Oct session is not in yet.** It is due from the 16:11 UTC (21:41 IST) slot. As of 17:00 UTC no panel-days
  or index-closes run for it has started; GitHub's schedule is running hours late on this repository (judge 89). The
  12:11 IST retry tomorrow covers it. My 15 Oct check-in (trig_01DHg1xXtCkmHnLgBfCgjQNs) will compare the 14 Oct rows
  the same way.

**Follow-up (cosmetic, not blocking).** Several workflows have unquoted step names containing ` #`, which YAML cuts at
the `#`. These are `panel-days`, `forecast-capture`, `forecast-scores`, `filings-archive` and `flows-download`. Behaviour
is unchanged, but the names shown in Actions are cut short ("One line to"), and a test that finds a step by its name
breaks, as judge 89 found in A8. Quote them in the next lane-1 change to these files.
