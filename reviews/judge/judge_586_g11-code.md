# Judge 586: G11 code, story/g11-ai-books-v4 at d8aabba4c (judge J, round 1 of 2)

**FAIL**, lane 1, one judge (C15 agreed): 2 should-fix, 3 minor. Code = merge 562718c5; the two later commits touch only
`G-forecasts.md` (checked). Gates on a trial merge with main 88d94efb8: 15,566 passed, 1 skipped, 14 xfailed; ruff, format, check_imports (2,620), check_records (9,072), check_numbers clean.

## Criteria
| C | Verdict | My evidence |
|---|---|---|
| C1-C4 | MET | 5 questions (`versions.py:21`); caps reproduced from closes (0.0193/0.0287/0.0641); history `d < day` and V2 close-proxy (my P2, P24 caught); envelope recomputed at brief (P7, P14 caught) |
| C5-C7 | MET | 9-min cap and 15:01:10 boundary (P5), v4 reveal 15:10:10 (P20), whole-second 14:55 (P6), not-today refused (P21) |
| C8 | MET | both owner defaults are one line each, `budget_stop.py:47,51` (P4, P16 caught); meter not signal file: no workflow writes `accounting/budget/` |
| C9 | PARTLY | guard at `v4_rows.py` unit-tested; end to end not (F2) |
| C10 | MET | `received > deadline` with V4_DEADLINE; my P1 (`>=`) caught at 15:10:00 (m3) |
| C11, C19 | MET | system_late refused at collect (P11), too-early (P17), lost log (P10), unknown receipt (P22), pending (P15) |
| C12 | PARTLY | unit stop rule tested; the firer's v4 window not (F2) |
| C13 | PARTLY | order, freeze, 09:15 (P12) MET; late go-live branch not built (F1) |
| C14 | MET | replay re-run: 10 rows, Hybrid V1 `invalid` (V1 `not_started` on 22 Oct), fire log 2,539 bytes |
| C15 | MET | 6 packages, AST and text; direct imports only (note) |
| C16 | MET | pre-go-live run on this host: `ai fire --protocol v4` "no go-live date", exit 0; `collect` "not live", exit 0; `reveals-ready --protocol v4` exit 0; commit step skips a missing folder |
| C17, C18 | MET | cost report empty before go-live; largest file 350 lines (`constants.py`) |

## Findings
**F1 (should fix) C13's late go-live branch is not built.** The passed text and `v4_register.py:7` say sessions between `effective_start` and a later `ai_books_v4` become `not_fired` rows, with a daily count from `ai fire`. `V4BookCollector.collect` starts at `live_from` (`v4_collect.py:71-73`), and no count is printed. Probe: start one session early, go-live on DAY; collect wrote no audit for the early session. G8's reconciliation (`reconcile.py:49-50`) then refuses every v4 look. Fix: collect from the earliest AI `effective_start`, writing `not_fired` for days before go-live; print the count; one test.

**F2 (should fix) Three v4 wiring paths are untested (my plants survived, 507 tests green each time):**
- P18: dropping `mark_exposures` from the v4 collect. `exposed` is a C11 outcome.
- P23: taking `released_sha256` from the fire log, not the release record. This defeats the "two sources" guard, which is C9's bad case end to end.
- P25: dropping the v4 session window in the firer's `stop_reason` call (`v4_fire.py`). After go-live, v2's pack days stop, so the v4 stop rule would never fire. The test patches `stop_reason` with `*args`.

Fix: one test each, through the collector and the firer.

**m1** Stale docstrings: `v4_input.py:4-5` ("the collection rebuilds it") and `tests/ai/test_v4_collect.py:1-4` contradict change 6.
**m2** `answer.py:3-5` and change 1 say an annualised figure is refused. For V2 it passes below VIX ~22.4 (0.15^2 = 0.0225 < 0.05). Fix the wording or name the gap.
**m3** C10's reason is wrong: no book-side module imports `outcome.py`. Ruling: the pin is enough (same constant, P1 caught at the boundary); only the reason needs correcting.

## Rulings on the 9 changes
1. Accepted: caps reproduced; see m2.
2. Accepted: no workflow writes the signal file.
3. Accepted: rule rows are `live` only from 22 Oct; the back-fill ends 15 Oct.
4. Accepted.
5. Accepted: P8 caught; the owner text is in the checklist.
6. Accepted: P3 caught.
7. Accepted, but someone must record v4's first 10 transcript audits, or every v4 day waits.
8. Accepted: the start is never after first-eligible.
9. Accepted: P10 caught.
The 4 blocking self-review fixes are present (P3, P11 caught; pipefail and the folder guard read in `v4-fire.yml`).

## Plants
25 planted, 22 caught, 3 survived (F2).

## Notes
- G10 (5bde718c1) conflicts only in `config.yaml` (adjacent keys: keep both) and `forecast_scoring/v4/wiring.py`. There, keep G10's body with G11's `build_slot_registry` name. My resolved three-way tree: ai, v4_pack, e2e, scoring_v4, budget, daily and rehearsal tests, 925 passed. G10 changes no name G11 reads (`ReleasedPacks.release`/`pack`/`pack_bytes` unchanged).
- Before go-live, the daily #fno-desk line gains two "v4 not live" lines.
- Each 18-19 KB pointer is retyped by the model, up to three tries: a time and cost risk for 15:10 (reasoning only).

## Addendum 1: gates re-run with FNO_SLACK_BOT_TOKEN set (owner rule, DESK_DECISIONS at 69d75ac1c)
- The verdict is unchanged: FAIL (F1, F2).
- The same trial merge (main 88d94efb8 + d8aabba4c), full suite with the token set: 15,566 passed, 1 skipped, 14 xfailed. Run 13:26:37-13:34:35 UTC.
- #fno-forecast and #fno-intraday: no post in that window.
- #fno-desk: 3 posts at 13:33-13:34 UTC, all "DRY RUN, 2026-10-22/23 replay" rehearsal lines (v4 quote part, margin_check, A22 pre-open).
- Re-runs with the token set posted nothing:
  - tests/rehearsal, daily, preopen, e2e and e2e_acceptance: 380 passed;
  - tests/ai, v4_pack, budget, forecast_scoring_v4 and pipeline: 572 passed.
- So I attribute those 3 posts to the orchestrator's dry run running at the same time (some evidence, not proven). No test of this suite is shown to post.

## Addendum 2: round 2 (the last), story/g11-ai-books-v4 at 8fc143ffc
**PASS**, lane 1, with one merge condition (below). Code = 81f4d5460; 8fc143ffc touches only `G-forecasts.md` (checked).
Every check was mine, with `FNO_SLACK_BOT_TOKEN` set.
- **F1 closed.** `v4_go_live.py` makes collect start at the earlier of the go-live date and the AI slots' first
  start. My round-1 probe, re-run (start 3 days early, go-live on DAY): the early session's audits are written as
  `not_fired` ("before the AI books' v4 go-live"), and DAY's are `on_time`. Five plants on the new code all caught:
  collect from the go-live date only, min changed to max, the count line removed, the reason forced to NO_LOG, `<=`
  in the count. The wiring test pins the calendar's sessions (no empty default).
- **F2 closed.** My P18, P23 and P25 re-planted: each caught, by tests through the collector and the firer
  (`test_v4_collect_log.py`, `test_v4_fire.py`).
- **m1-m3 closed.** Docstrings corrected; the m2 wording is true and pinned; C10's reason corrected.
- **The test split:** 106 lines moved to `test_v4_collect_log.py` verbatim; only one docstring line differs.
- **BG1-w:** C8 sums `minutes` only. My plant that adds `wait_minutes` to the stop was caught. `sealed_at` is ISO
  time with zone, or null, which matches BG1-w's reader.
- **Before go-live:** `ai fire` and `ai collect --protocol v4` print not live and exit 0. Consequence (stated in
  Claims): once AI slots are registered, collect writes `not_fired` from their start even while `ai_books_v4` is
  null. That is the protocol's rule; registration and the go-live date should land on the same session.
- **Gates on a trial merge with main 6aea50ad2** (8a5ccf5e7): 15,875 passed, 1 skipped, 14 xfailed. ruff, format,
  check_imports (2,672), check_records (9,131), check_numbers clean; largest file 350 lines.
- **Slack:** #fno-forecast and #fno-intraday got nothing in either run. #fno-desk got two "DRY RUN, 2026-10-23
  replay" card lines during the first run. The second full run posted nothing. So these are rehearsal lines, not
  tests (some evidence; orchestrator asked to confirm).

**Merge condition: BG1-w (story/bg1w-reveal-wait 3d19625a, judge 587.2 PASS).** main + G11 + BG1-w merges cleanly, but
`tests/ai/test_run_timing.py::test_the_ledger_gets_each_books_minutes_once` then fails. G11's timing files now carry
`sealed_at`, so BG1-w's reader records 2.00 working minutes plus a 2.17-minute wait, not 4.17. The Claims' "passes in
either merge order" is wrong for this one test (minor, m4). Whichever of G11 or BG1-w merges second changes its two
expectations:
- `"recorded 4.17 minutes"` becomes `"recorded 2.0 minutes (and a wait of 2.17 minutes apart, not capped)"`;
- the row's `"4.17"` becomes `"2.00"`.

With exactly that change, the full suite on main + G11 + BG1-w: 15,911 passed, 1 skipped, 14 xfailed; no Slack post.
No G11 code changes.

## Addendum 3: pre-merge diff check, story/g11-ai-books-v4 at eb49d77f0 (the 586.2 condition)
**PASS stands; the condition is met.** eb49d77f0 = gated 66db618e5 + one `G-forecasts.md` commit (checked). G11's
own commits since 8fc143ffc:
- 714f7c867 makes exactly my two test changes (`test_run_timing.py:142,145`: "recorded 2.0 minutes (and a wait of
  2.17 minutes apart, not capped)" and "2.00").
- 50a7b1e6c moves `FORECAST_PROTOCOL_V2/V4` into `fno/ai/run_terms.py`, imports only. Ruled acceptable: on the merged
  tree `fno/constants.py` would reach 351 lines, past the hard size limit. `constants.py` is byte-identical to main
  (350 lines), so the freeze's recorded file is unchanged. `run_terms.py` is standard library only (the book side
  reads it), and nothing outside `fno/ai` and its tests used the names.
The merges hold no other change (`git show --cc`). The only conflict, `config.yaml`, keeps main's
`v4_pack: "2026-10-26"` beside `ai_books_v4: null`; only the comment is reworded.
- **Claim confirmed** on the trial merge, with `v4_pack` live: `ai fire --protocol v4 --day 2026-10-24` prints "not
  fired: no v4 go-live date is set", exits 0, and writes no `research/forecasts/ai_v4/`. `v4-fire.yml`'s commit step
  skips a missing folder.
- **Gates on a trial merge with main 35058cba5** (0709ce4ee), token set: 15,986 passed, 1 skipped, 14 xfailed. ruff,
  format, check_imports (2,681), check_records (9,149), check_numbers clean. No post in any of the three channels
  during the run.
