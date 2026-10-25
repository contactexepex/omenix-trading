# Judge 250: E2d per-trade daily marks, story text (story/e2d-trade-marks at ec2827ea)

Judge B, 16 Oct 2026. Lane 1 (a new story, touching the paper accounts and the record scan). The claims are in the
builder's message (session 0134MoC6; no response number yet). The diff is a new E2d section at the end of
`docs/stories/E-paper-desk.md` plus a register row.

**Verdict: FAIL.** One should-fix: the story builds a second copy of a marking rule that already exists in scoreboard B.

## Claims checked on main

| Claim | Result | Evidence |
|---|---|---|
| `record_equity` has no caller outside tests | TRUE | `git grep record_equity`: `fno/books/account.py:203` and `tests/books/test_paper_account.py` only |
| Marks live only in memory during the exit review; `daily_totals.csv` holds closed equity only | TRUE | no writer of an open trade's value in `fno/desk/` |
| E1's `Mark(stale=True)` exists | TRUE | `fno/books/equity.py:27` (`price`, `stale`); `MissingMark` also exists |
| Only `.gitignore` keeps account files out; the record scan refuses Groww quotes by path only | TRUE | `.gitignore` lines 11-12; `fno/record_scan/forbidden_files.py` has `RAW_GROWW_QUOTES` only |
| Marking after the exit review sees the day's new entries | TRUE | `fno/desk/daily_run.py`: snapshot, fill (78-82), then exits (89) |
| Scoreboard B re-marks at score time and is not affected | TRUE, but see the should-fix | `fno/scoreboard/daily_values.py` |
| No other register row covers account marks or the record scan's account paths | TRUE | register rows E2c (done), LM1 (alerts only), P2c (reader) |

## Should-fix: one marking rule, not two (one builder per function, DRY)

`fno/scoreboard/daily_values.py` (story S2) already computes exactly what E2d specifies:
- each open trade's value per session, as its cash flow so far plus the held legs at the mid of that day's execution
  snapshot (`DayMarks`, `key_of`);
- a leg without a valid mid keeps its last valid mark, flagged stale;
- a leg never marked leaves the day unvalued.

E2d's "unrealised = mark value plus the trade's cash flow so far" is that same `TradeDay.value`. As written, E2d will
build a second implementation of that rule. The two can disagree on a normal path: E2d's design 2 takes the stale
fallback "from the account's own mark record" (`trade_marks.csv`), while S2 takes it from the snapshot history.
Concrete case:
1. A run's marking step is lost one day (Drive refused, alerted, that day's rows not written).
2. On a later day the contract has no valid quote.
3. E2d then uses an older mark than S2 does, so the paper-books page and scoreboard B show different values for the
   same trade and day.

`daily_values.py` is hashed by the S1 protocol (`research/evaluation/PROTOCOL.md:427`), so E2d must reuse it without
editing it. The story text needs:
1. E2d's marks and trade values come from the same rule S2 uses: import `trade_days` / `DayMarks` / `key_of`, or one
   shared function both call, without editing the hashed file. The stale fallback comes from the execution snapshots,
   not from the account's own earlier rows.
2. An acceptance criterion: for a fixture with an open trade over several sessions, including a missing quote, E2d's
   mark value and unrealised equal S2's `trade_days` value for every session.

## Notes only (no should-fix)

- `ForbiddenFiles.matches` takes one fixed folder prefix. `journal/<book>/account/` and
  `journal/shadow/<account>/account/` need a matcher with a wildcard segment: a new class beside it, not a change to the
  Groww one. That is for the code judge.
- `top_up` also writes an equity row on its day. A same-day `record_equity` replaces it (by date), which is right
  because the later row has the later state. Worth one test in the code phase.
- An entry fills at one side of the quote, so a leg can fill while its mid is invalid (one side missing): the entry day
  is then "unmarked" and alerted. That is correct, and rare.

## Rest of the text

The other design points (snapshot only, never invented, Drive only, public totals unchanged, shadows in their own
files, rerun idempotent) are sound and testable. The acceptance criteria are concrete, nothing posts while building,
and the scope is clear.

## Gates

Story text only: no code to run. The claims above were checked by me on main and ec2827ea.

## Addendum 1: story/e2d-trade-marks at 6b92cd11 (response 246)

**Verdict: FAIL.** The should-fix is half done, and one new gap comes from the fix itself.

What changed:
- one shared marking function, `fno/books/marking.py`, which E2d calls and S2's `daily_values` moves onto (R2/G7);
- criterion 1 now compares against `TradeDay.value`;
- `awaiting_settlement` past expiry, with criterion 10;
- the unmarked gap's effect is stated: the brake reads closed equity (`fno/risk/book_view.py`, checked).

| Item | Result | Why |
|---|---|---|
| One marking rule | MET | design 1 and the register row name `fno/books/marking.py` |
| **Same inputs, so the same values** | **NOT MET** | design 2 still says the stale fallback comes "from the account's own mark record" (`trade_marks.csv`), while S2's comes from the snapshot history. One function fed different histories still disagrees: D1 marked at 100; D2's marking step lost (Drive refused, alerted) while D2's snapshot is valid at 110; D3 has no quote. E2d marks D3 at 100 (stale), S2 at 110. Criterion 1's fixture has no lost day, so it cannot catch this |
| **The shared function in S1's hash list** | **NOT MET (new)** | `daily_values.py` is in S1's `frozen_files` (PROTOCOL.md, "Scoring files"). Once it delegates to `fno/books/marking.py`, the scoring rule lives in a file the freeze does not hash, so it could change after the freeze. S1 is still a draft, so this is fixable now: the text must say `fno/books/marking.py` joins S1's scoring files (proposed to the S1 text owner, R2/G7, register row "S1 text"), and that R2/G7's move of `daily_values` lands before the freeze, under a register row |
| `awaiting_settlement` | MET | the value is the same as S2's stale last mark; only the label differs; criterion 10 is testable |
| No note column on the next equity row (push-back) | AGREED | the unmarked rows already name the day and the reason; a new `EQUITY_COLUMNS` column changes every reader for no new information |

What the text needs:
1. Design 2: the stale fallback is the last valid mid from the trade's earlier execution snapshots (S2's source), not
   the account's own rows. For example, E2d calls the shared function over the trade's sessions with the snapshots'
   `DayMarks`.
2. Criterion 1, or a new criterion: the fixture includes a session whose marking step was not run, and E2d still
   equals `TradeDay.value` on the next unquoted day.
3. `fno/books/marking.py` is added to S1's hashed scoring files before the freeze; the register covers R2/G7's
   `daily_values` move.

On the builder's open question (a maximum age for a stale mark): no limit is needed in this story. S2 has none, the
flag is on every row, and a limit would make the page and scoreboard B differ again. If the owner wants one, it
belongs in the shared function, for both. Reasoning only.

## Addendum 2: story/e2d-trade-marks at d26ee014 (response 246 addendum 2)

**PASS.** Both open points are closed at the root: one rule and one history.

| Item | Result | Evidence |
|---|---|---|
| Same inputs, so the same values | MET | E2d imports S2's `trade_days`, `key_of` and `DayMarks` and `SnapshotMarks` unchanged. The fallback comes from the trade's earlier execution snapshots (`SnapshotMarks` reads each day's valid snapshot id from the run logs, `CommittedRuns.snapshot_ids`), and `trade_marks.csv` is output only. Criterion 1 now has a lost marking day: day 3 is valued at day 2's snapshot mid, as S2 does |
| No S1-hashed file changes | MET | no `marking.py`; criterion 12 checks `daily_values.py`, `sources.py` and every S1-hashed file byte for byte |
| Today is valued today | MET (checked) | the run order is snapshot, fill, exits, and the run log is rewritten after each step (`fno/desk/run_log.py`), so today's valid snapshot id is in the log when the marking step runs after exits |
| The equity identity | MET (checked) | `fno/books/equity.py:89-107`: marked = closed + open cash flow + open legs' value, which is closed + the sum of the trades' `TradeDay.value` |
| One valuation path in the account writer | MET | `record_marked_equity` from the same values; the unused `record_equity(day, marks)` removed with its tests (it had no other caller: grep) |
| `awaiting_settlement` | MET | a label on S2's stale value, the same number |
| Notes from judge 250 (wildcard matcher, same-day top-up row) | MET | design 6; criterion 5 |
| Register row | MET | names the new files and the removal |

**Note for the code judge (no should-fix):** `record_marked_equity(day, open_value, stale)` takes the sum of trade
*values* (which include each trade's cash flow), while `equity.py`'s own `open_value` means the legs only. Name the
parameter so the two are not confused: added to `closed_equity + open_cash_flow`, it would count the cash flow twice.
Criterion 2's test pins it.

Story text only; I checked the claims myself on d26ee014 and main.
