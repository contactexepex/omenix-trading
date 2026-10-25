# Judge 589: A22d story text, the flat 09:15 pre-open candle (story/a22d-flat-candle @ 5e2dfff03), judge E

**FAIL (round 1 of 2, text; 1 should-fix, 2 minor). Lane 1** (Groww, the A22 routine's record). Judge E, own session.
Text only: one file, `docs/stories/A22-preopen-data.md`, +118. Judged by reading. Doc-reading tests with the token
kept: 853 passed, 15 xfailed.

## Evidence (my own read of the record; differences and shapes only, no value)

| Claim, 23 Oct | Result | My evidence |
|---|---|---|
| Live answers: one candle of the day each, stamped 09:15, flat, `null` volume | **Reproduced** | `nifty_091059.json` and `banknifty_091101.json`, each read from Drive and hashed against its receipt: 1 candle, 09:15, open = high = low = close, volume field None |
| Its close minus NSE's Open Index Value | **Reproduced: 0.00 and 0.00** | `ind_close_all_23102026.csv` from Drive, SHA-256 equal to its manifest row |
| Minus Groww's 09:09 history close; the real 09:15 candle not flat | **Not reproduced** | Needs live Groww (`growwapi` is not installed here; no 23 Oct 1-minute archive in `groww-candles/`). Accepted as the builder's claim, marked one session |
| Today's outcome: "candles only from 09:15" | True | `answers.py:82-83`; O10 rows 12-13 |

## Rulings asked for

| Choice | Ruling |
|---|---|
| Flat candle only alone, read 09:10:00 to before 09:15:00 | **Accepted.** From 09:15 a 09:15 candle can be a traded minute. The lower bound is after step 0b's final 09:08-09:09 value. The answer's `received_at` is `seen_at` (`parts.py:86-91`). A stale placeholder (yesterday's close) would pass every shape test, so the next-morning check is the real guard |
| `flat_0915_unverified`, kept not blocked, usable from Monday on n=1 | **Accepted, with reasons.** No reader uses the value today: my grep for `nifty_preopen` and the day folder outside `fno/preopen/` finds none, and the forecast lab's GIFT section reads only `early_file`. The label leaves the choice to a future reader. Five matches is a label, not proof [reasoning only] |
| Open check before 08:40 never delays the 09:12 commit | **Not accepted as written** (finding 1) |
| One tick (0.05), A16b's `beyond` | **Accepted.** `minute_check.py:18-20` rounds before comparing; 0.00 seen on both indices |
| Mismatch alert and O10 row carry no value | **Accepted.** The difference stays in the Drive check file |
| NSE `key=NIFTY` out of scope | **Accepted.** The reason is true: no morning answer is archived, so its layout is unread |

## Findings

1. **Should fix: nothing bounds the open check's time, so a slow Drive can push GIFT's read out of its window.**
   - The check runs "at the start of `preopen record` ... before the GIFT window". The routine starts at 08:36 and
     setup takes part of that, so there are about 2-4 minutes before 08:40:00.
   - It syncs Drive folders for up to 10 sessions. D7 covers Drive down or an unreadable file, but not Drive slow (each
     call waiting for its timeout).
   - A check still running at 08:40 delays GIFT's first read. A run that reads only after the window has closed is
     `late` (`run.py:1-4`), and the 08:50 morning edition needs GIFT's receipt at about 08:41.
   - Fix: give the check a hard stop before 08:40:00 (sessions not reached are left for the next morning, never counted
     as a match), or run it after the 09:12 commit. Test it with a slow fake store and an injected clock: GIFT's read
     still starts at 08:40:00. Plant 14 then needs restating to match.

## Minor

1. Day rows written before A22d (23 Oct) have no basis columns. Name that header in D4 and D5's cases: the open check
   and any reader accept it, and a row with no value is skipped.
2. The Evidence heading says "[strong, one session]", but two of its five rows rest on a Groww read that the
   repository cannot replay. Mark those two rows "the builder's read".

## Plants

None (text round). The 14 planned plants cover the rule's bounds, the label count and the check's source.

## Addendum 1

**A22d story text, round 2 of 2 (story/a22d-flat-candle @ 6e52b51a9): PASS. Lane 1.** Judge E. Since 5e2dfff03 the
branch changes only `docs/stories/A22-preopen-data.md` (+29/-16) and its `docs/WORK_REGISTER.md` row. Judged by
reading. Doc-reading tests with the token kept: 853 passed, 15 xfailed.

| Round-1 item | Outcome | My evidence |
|---|---|---|
| SF1: the open check had no time bound before GIFT's 08:40 read | **Accepted, fixed** | The check is now the last step of `preopen record`, after the capture's own commits. Nothing waits on it: no reader of the label until the next morning's row. I accept the reason given against a hard stop: a stop checked between calls cannot bound a single slow Drive call. D7 now tests a slow fake store (10 min per read on the injected clock): GIFT's first read is still at 08:40:00, the capture's commit comes before the check, and a check failure changes nothing of the capture. Plant 14 is restated to match |
| m1: old-header day rows | Fixed | 23 Oct's row has no value, so it is skipped. A pre-A22d row with a value is checked with a blank basis and never counted. Both cases are in D4 and D5 |
| m2: the Groww-history rows | Fixed | Marked * as the builder's read, which the repository cannot replay; the others are noted as reproduced by me |

**Dates checked.** Today's label is written at 09:11, from check files that exist by then: the check for yesterday
runs after today's row. So the label counts sessions up to the day before yesterday. NSE's calendar has no holiday or
special day from 26 Oct to 4 Nov (`nse_sessions.csv`). Five live values (26-30 Oct), the fifth checked on Mon 2 Nov,
make Tue 3 Nov's row the earliest `verified`, as written.

## Findings

None blocking, none should-fix.

## Note (not a finding)

The run's last line changes. After this, `preopen record`'s lines end with "open check: ..." and it can exit 1 for a
check problem. CLAUDE.md's pre-open section says the command "ends on 'pre-open recorded' or 'pre-open recorded with
problems: ...'". No code parses that line (my grep outside `fno/preopen/`). The section should still be updated with
the code: it is a rule document, lane 2, unless the orchestrator folds it into this change.

## Addendum 2

**A22d code, round 1 of 2 (story/a22d-flat-candle @ 3555eda2f): PASS. Lane 1.** Judge E. Judged against the text
passed in 589.1.

| Criterion | Result | My evidence |
|---|---|---|
| D1 flat candle accepted | MET | **Real 23 Oct answers**, from Drive and checked against their receipts, through the branch's `read_index_preopen`: NIFTY at 09:10:59 and BANKNIFTY at 09:11:01 are complete, basis `flat_0915`, `source_time` None |
| D2 refusals | MET | The same real answers at 09:15:00 and at 09:09:59 give "no pre-open value: candles only from 09:15". Plants A2 (no upper bound), A3 (no lower bound), A4 (any volume), A5 (any stamp), A6 (other candles allowed) and A15 (another day's read) each caught |
| D3 precedence | MET | A7 (flat wins over the 09:09 candle) caught |
| D4 day row | MET | `day_row` writes `flat_0915_<label>`, with `unverified` as the default (A14 caught) |
| D5 open check | MET | Uses `beyond` (A9: 0.10 tolerance caught). A missing official file is never a match (A21 caught). One index's missing row never hides the other's (A19 caught). No value in any line (A12 caught). The last morning in the look-back is named (A17 caught) |
| D6 label | MET | A10 (4 matches) and A11 (one mismatch ignored) caught. A16 (any basis counted) caught: old-header rows never count |
| D7 timing | MET | `record.py:56-69`: the check runs after `_finish` has committed the capture. A13 (check before the capture) caught |
| D8 sample | MET | My real-answer run above |
| Gates | MET | Trial merge 29cca45c0 with origin/main afaf3061b: ruff clean, format clean (2,528 files), imports clean (2,657 files), record scan clean (9,115 files). Full suite with the token kept: **15,763 passed, 1 skipped (`growwapi`), 15 xfailed, 0 failed**, the builder's 15,764 with the skip counted. Largest file in `fno/preopen/`: 136 lines |

**Plants:** 19 planted, 19 caught (`tests/preopen`, `tests/rehearsal`, `tests/intraday`: 551 tests), each restored
after its run.

**The six choices beyond the text, ruled (all accepted):**
1. **Labels read in a background thread from the run's start, with a 10-minute join before the check.** It reads only
   check files that earlier runs wrote. No window waits on it, and a late or failed read labels every value
   `unverified` (A20 caught). Minor 1 below.
2. **One index's missing official row is its own problem**, and it is written `no official value`, which never counts
   as a match.
3. **A waiting session is named once,** on its 10th and last morning in the look-back, never dropped silently.
4. **`PreopenPart.read` made abstract, with REH1c's `RecordedPreopenPart` calling the live part's reader.** This
   removes the `isinstance` branch, so the rehearsal and the live run share one reader. 23 Oct replays as complete.
5. **`parse_candles` refuses a dict row** (KeyError becomes `CandleParse`). Its other callers: `backfill.py:183`
   already catches `CandleParse`; in `session_deriver` the error that propagates is now named, never a bare KeyError.
6. **`read_nse_day(index_row=NIFTY_ROW)`**: the default keeps every existing caller unchanged.

**CLAUDE.md.** Only the end-line sentence of step 3 changes. It matches the code: the capture's line, then after its
commit the check's "open check: <n> checked, <m> waiting for NSE's file" or "open check with problems: ...", each
exit 1 with its own alert (`record.py:66-70`, `max` of the two codes). As before, the alert's send result follows a
problem line. The same step still says "NIFTY's and BANKNIFTY's 09:09 one-minute candle"; left as the orchestrator
asked, though it is now one of two sources.

## Findings

None blocking, none should-fix.

## Minor

1. If the label read hangs past `FINISH_WITHIN_SECONDS` (600 s), the open check starts while that thread still uses
   the same Drive cache: the overlap `finish()` exists to prevent. This needs one Drive call stuck for over 10
   minutes. It cannot change a recorded value, because the labels were already taken.
