# Judge 358: A20a, NSE's daily F&O ban list and market lots kept point in time (story/a20a-fo-masters @ 21e3b69c)

Judge F (independent). Story `docs/stories/A20-rules-and-dates.md` at e50ca714 (text PASS, judge 353 add. 1), claims
`reviews/claude/response_266a_a20a-fo-masters.md`. Lane 1 (NSE, Drive, Slack, a workflow). Labels: **strong**,
**some**, **reasoning only**.

## Verdict: PASS (2 merge conditions, 2 notes)

## Gates and runs (mine)

| Check | Result |
|---|---|
| pytest `-n auto` at 21e3b69c | **7445 passed** |
| ruff, ruff format (1325), `check_imports.py`, record scan (6621) | clean |
| Trial merge with origin/main (16 Oct, about 12:40 UTC) | code merges cleanly; text conflicts only, in `CLAUDE.md` (composition-root list), `docs/WORK_REGISTER.md` and `reviews/claude/README.md`. With main's side of those three: **7897 passed, 15 xfailed** |
| Readers on today's live NSE files (fetched by me) | `fo_mktlots.csv` 200, 47,736 bytes → 219 underlyings; `fo_secban.csv` → `BanList(trade_date=2026-10-16, symbols=AMBUJACEM, KAYNES, SAIL)` |
| File size | `storage/wiring.py` 303 lines after moving the source tuples to `source_lists.py`; new files 13-88 lines |

## Planted mutations (mine, reverted; `tests/fo_masters`, `tests/nse_retry`)

| # | Plant | Caught |
|---|---|---|
| 1 | stale copy (session before the run day) accepted | yes |
| 2 | Drive's `OSError` not caught by the step handler | yes |
| 3 | no "today's ban list archived" check on a trading day | yes |
| 4 | a commit failure ignored | yes |
| 5 | the workflow alert `if:` without `failure()` (implicit `success()`, judge 351's lesson) | yes |
| 6 | a muhurat-only session counted as a trading day | yes (2 failed) |

## Criteria (A20a's: 1-4, 13-16)

| # | Evidence | Status |
|---|---|---|
| 1 Ban list filed by its trade date (today, next trading day across a weekend and the 8 Nov muhurat Sunday), stale and two-ahead refused, nothing written on a refusal, first copy kept, readers | `CurrentSessionTaker._check`, `next_trading_day`; tests; plants 1 and 6; live reader output | MET |
| 2 Stale = no list for today's session on a trading day (also at 18:45); no check on weekends, holidays or muhurat days | `ban_list_step`; plant 3 | MET |
| 3 Lots on trading days only; 404 a failure; damaged layouts refused | `taken`, `read_lot_sizes`; live reader (219 rows) | MET |
| 4 Every step runs; one alert names all; rows still committed; not committed is a failure; Drive network errors named | `FoMastersJob.run/_run`; plants 2 and 4 | MET |
| 13 Workflow: crons 07:45 / 11:15 / 18:45 IST, `contents: write`, alert on `failure() && posted != 'true'`, secrets by reference | YAML read; plant 5; `StepOutputAlerts` writes `posted=true` only when Slack accepted | MET |
| 14 Commits only `research/data/manifests` | `build_manifest_recorder`; test | MET |
| 15 Ports and composition root | `fno/fo_masters/wiring.py`; offline tests | MET |
| 16 Real output, first live run | sample in the claims (16 Oct, local folder); first scheduled run to be cited after merge | MET for the sample; live run pending |

## Merge conditions

1. **capture-watch:** whichever of O10 (judge 350 add. 2) and A20a merges second adds `fo-masters` to
   `capture-watch.yml`'s list. Otherwise O10's `test_every_job_is_watched` fails on the merged tree.
2. **Resolve the text conflicts keeping both sides**, above all the `fno/fo_masters/wiring.py` line in CLAUDE.md's
   composition-root list. Run the full gates on the exact merged tree before pushing (the new rule: builders merge
   their own branches after a PASS).

## Notes

- First-seen time is the day folder plus the manifest row's commit time, not a stored timestamp, as the claims say.
  That is enough for daily rules.
- The empty ban list's layout is unseen. A header-only file is accepted and anything else fails loudly: the right
  default. Fix it from the first real empty file.

## Addendum 1: a duplicate line I missed (found while judging A20b, judge 359)

The PASS stands, with one recommended change before merging. `fo-masters.yml`'s fallback step is
`if: ${{ failure() && steps.masters.outputs.posted != 'true' }}`. When the job posted its own line it is skipped, so
O10's watcher (needs an alert step that ran) posts a second line for the same failed run. That is at most 3 runs a
day, the same "duplicate rather than silence" limit I accepted in judge 350 add. 1, so it is not blocking here.

It is removed by the same change as judge 359 SF1: `if: ${{ failure() }}`, and the step exits 0 without sending when
`posted == 'true'`. I recommend doing it in the same merge.

## Addendum 2: d0fdc34b, the alert-step change recommended in addendum 1

**Verdict: PASS. A20a may merge at d0fdc34b, after a fresh merge of main gated on the exact merged tree.**

The fallback step now runs on every failure (`if: ${{ failure() }}`) and exits 0 without sending when the job's own
`posted` output is `true` (passed as `POSTED` through `env`, never pasted into the script). So O10's watcher, now on
main at 54312c31, sees an "Alert" step that ran and adds no duplicate line. A crash, where `posted` is empty, still
sends the fallback line. `tests/fo_masters/test_workflow.py` pins the `if:`, the `env` and the first script line, and
runs the script with `POSTED=true` (exit 0, "already spoke"). Checked by reading the code.

Merge notes:
- capture-watch's list on main must gain `fo-masters`. O10 part 1 is merged, so A20a adds it in its merge, and O10's
  `test_every_job_is_watched` must pass.
- The branch dates from 16 Oct. Merge main, run the full gates (pytest, ruff, ruff format, `check_imports.py`,
  `check_records.py`, `check_numbers.py`) on the exact tree you push, and keep both sides of any
  CLAUDE.md / WORK_REGISTER / README conflicts.
