# Judge 245: A14 margins loud (story/a14-margins-loud at 88a725e2)

Judge B, 16 Oct 2026. Lane 1 (a workflow and an outside service's alert line). Asked by the orchestrator (response 239
item 4): the nse-margins job names any unexpected stop (a 2027 `CalendarError`, an `OSError`) in its one line; the
archive-step line no longer blames Drive; the final `failure()` condition is kept, so no line is doubled.

**Verdict: PASS.**

## Criteria

| Criterion | Result | Evidence |
|---|---|---|
| An unexpected stop before the day loop (e.g. 2027 `CalendarError` from `due_session` or `pending_days`) is named in the one line | MET | `run()` catches `Exception` there; `_unexpected` gives "stopped by an unexpected {type}: {message}" and prints the traceback to the log; test `test_a_year_missing_from_the_calendar_is_named_in_the_one_line` (one alert, names the type and "holiday circular") |
| An unexpected stop on one day is named with its day; the run fails | MET | per-day `except Exception`; `run()` returns 1; test with an `OSError` on `log.append` |
| Fails closed, no invented date | MET | the day's rows are not written; `pending_days` keeps the day pending for the next run; no fallback calendar |
| The workflow's "already alerted" now holds for the margins step's own stops | MET | every stop inside `run()` ends in `alerts.send`; the step-name text says so |
| The librarian line no longer blames Drive alone | MET | "the archive step failed (Drive, NSE or the calendar: its log names it)" |
| The final `failure()` alert is unchanged, so no line is doubled for one step | MET | condition still excludes a failed librarian or margins step |
| Register row | MET | one A14 margins-loud row; no other row covers `fno/nse_margins/job.py` or this workflow |

## Claims vs reality

All claims hold. Going on to later days after one day's unexpected stop is safe: `MarginLog.append` takes rows in any
order, and C2 reads the latest row on or before a day (`max`), so a gap filled on a later run gives the same answer.

## Project rules

`job.py` 130 lines; the test file is new. `# noqa: BLE001` is justified on each broad catch (the cause is named and
the run fails; `Exception`, not `BaseException`). The message template is local to the helper, like the module's other
lines.

## Mutations (real cases)

- Remove the per-day `except Exception`: 1 test fails (the `OSError` case).
- Remove the before-the-loop `except Exception`: 1 test fails (the `CalendarError` case).

## Unclaimed-bug hunt (notes only, no should-fix)

1. From 1 Jan 2027 until NSE's 2027 rows are added, one run posts two lines for one cause: the librarian step's
   `--due-day` fails first (its line says "calendar"), then the margins job names the `CalendarError`. These are two
   different lines from two steps that each failed, the same pattern a Drive outage already gives. It is not one line
   sent twice. Note only.
2. A stop while the job is being built, before `run()` (`build_nse_margin_job`: Drive settings missing, a bad
   `risk.margins` block), is still a bare traceback. The final `failure()` alert excludes a failed margins step, so
   such a stop posts nothing. On a normal run the missing-Drive case also fails the librarian step, which alerts. A bad
   config block needs a lane-1 config edit that its own tests would catch. This is older than this diff. Note only.
3. If the disk fills during `_write_at_end`, a half row can stay in `margins.csv`, and the commit step (it has no
   `if:`) would commit it; the next run then fails, named. This is older than this diff, and a disk filling on a runner
   during a few-KB append is far-fetched. Note only.

## Gates (run by me on 88a725e2)

`env -u FNO_SLACK_BOT_TOKEN python -m pytest -q -n auto -p no:cacheprovider`: 6,964 passed. `ruff check fno tests
tools`: clean. `ruff format --check`: 1,236 files already formatted. `python tools/check_imports.py`: clean.
