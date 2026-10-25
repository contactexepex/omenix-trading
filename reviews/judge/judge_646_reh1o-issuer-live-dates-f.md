# Judge 646: REH1o, G13's issuers take the rehearsed live date, story and code (story/reh1o-issuer-live-dates @ 07c06957e)

**PASS (1 minor, 1 accepted limit), judge F (judge B the other; not read). Lane 1.** Own session
(session_01A8XfbTUVgeeEpqatHaWbtP). Labels: strong, some, reasoning only.

## Criteria

| Check | Result | My evidence |
|---|---|---|
| The fix | MET | `rehearsed_date(key, real)` = `rehearsed_live({key: real})[0][key]` (`rehearsal/live_wiring.py:46-49`); one line in each of `premium_ranges`, `price_distribution` and `price_ranges` `wiring.py`; plants removing each line caught |
| A real run is unchanged | MET | `rehearsed_live` returns the dates untouched with no mode (`live_wiring.py:38-40`); test "no mode, the real date stands"; plant "always the replayed day" caught (4) |
| On or after its real date, a rehearsal keeps the real date | MET | `rehearsed_live` changes only `real is None or mode.day < real`, and never `KEPT_REAL` (owner-timing fills) |
| Backfills keep the real date | MET | two tests; plant moving the backfill to the rehearsed date caught |
| A live date not true on the replayed day? | BY DESIGN, labelled | only for a step not live that day; REH1j records it `not_live`, keeps its work under `exercised`, and its posts carry the not-live line. It is the same date the daily root already gives that step, now also in the child that checks its own date |
| A write to a live record? | NO | the three `build_store`s use `build_owner_drive` (wrapped by `rehearsed_drive`: Drive writes under `dryrun/<run_id>/`, verified in judge 608) and `build_data_store`; receipts are committed in the rehearsal's clone, whose `origin` is a local bare repository |
| gates | MET | trial merge with main a997cd349 (clean): **16,597 passed, 1 skipped, 13 xfailed** (token kept); ruff, format (2,635 files), `check_imports`, `check_records` (9,297 files) clean |

**The stated limit (accepted).** `price_ranges` on a replay before 21 Oct stops at O1's 10 minutes: no BANKNIFTY close
table existed in the record then, so `CloseTables.update` downloads every index-close file (about 2,414). It is a
rehearsal-only cost of the days before G13b's first table, recorded as exercised (never the day's failure), and later
steps still run. The only harm is replay time and read-only Drive downloads of visible files.

## Minor

1. The step key passed to `rehearsed_date` matters only for `KEPT_REAL`: my plant giving the premium issuer another
   step's key passed (an equivalent plant, no effect today). If a G13 step is ever kept real, a test of the key per
   issuer is needed.

## Plants

6 planted on 07c06957e: **5 caught, 1 equivalent** (minor 1). Caught: each issuer back on its real date (3); the
rehearsed date used even when live; the backfill taking the rehearsed date.
