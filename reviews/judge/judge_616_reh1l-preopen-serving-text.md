# Judge 616: REH1l, a pre-open read never shifted past its window; the replay clock reported apart, story text (story/reh1l-preopen-serving @ c06ac3b24)

**PASS (text; 4 minor, two of them conditions for the code round). Lane 1** (what a rehearsal records and posts).
Judge F, own session (session_01A8XfbTUVgeeEpqatHaWbtP). Labels: strong, some, reasoning only.

## Facts and rules checked

| Item | Result | My evidence |
|---|---|---|
| The forward wait never serves bytes before their seen time | TRUE | `recorded_preopen.py:39-40` sleeps until `seen` before reading the file |
| 23 Oct's copies | TRUE | `receipts/data/preopen/raw/2026/10/23/`: `gift_084000`, `fo_list_090830`, `nifty_091059`, `banknifty_091101` (the only BANKNIFTY copy) |
| Windows and the read plan | TRUE | `parts.py:22-23` INDEX 09:10-09:11, FO 09:08:30-09:11, GIFT 08:40-08:45; `INDEX_LAST_READ_MARGIN` 15 s; `run.py:18` every 30 s |
| The cue copies 08:50:17-08:51:00 (6 indexes) | TRUE | the `*_preopen.csv` manifests for 23 Oct: nikkei 08:50:17, kospi :34, asx :39, hang seng :46, sse :51, sti 08:51:00; taiex absent (the typhoon) |
| The measured flips | TRUE by the rule | at-or-before-now: NIFTY (09:10:59 after every A22e read), BANKNIFTY and all 6 cues flip; the window rule: only BANKNIFTY (09:11:01 is at or after its 09:11:00 close) |
| The serving-path table | COMPLETE | `serving.py`'s two rules (`is_near`, `ServedOnce`) and the six recorded sources REH1 wires; quotes are republished at `finished_at` (`recorded_quotes.py:1-5`) |
| No real-run path changes | TRUE by design | `RecordedPreopenPart` exists only under the mode (`preopen_wiring.py:18-27` returns the live parts with no mode); `RehearsalClockCheck` only via `rehearsed_clock_check` |
| The clock warning is a pre-open problem today | TRUE | `record.py:57` turns any `clock_warning()` into `Problem("clock", "warning")`; `RehearsalReading.warning()` returns `NOT_CHECKED` (`preopen_wiring.py:32-33`) |
| Doc-reading tests (trial merge with main) | PASS | 920 passed, 14 xfailed; record scan clean (9,252 files) |

## Minor

1. **Code-round condition: filter before the pick.** `ServedOnce.pick` (`serving.py`) chooses the nearest copy and
   moves `_last` to it. If the window bound is applied after the pick, a read with an eligible in-window copy and a
   nearer post-close copy gets NOT_RECORDED, and `_last` moves past the eligible copy. The code must drop copies seen
   at or after the close before `pick`. L1 needs that case: a read at 09:10:45 with copies at 09:10:30 (not yet served)
   and 09:11:01 gets 09:10:30.
2. **The third clock reader is described wrongly.** `quotes/window_wiring.py:30`'s `CaptureLog` never calls
   `warning()`: it records `reading.status` and `worst` (`capture_log.py:57-67`), so under the mode it still writes
   `clock_unchecked`, with or without REH1l. In a rehearsal that recorder is replaced by `rehearsed_recorder` (the
   day's own sidecars, `window_wiring.py:34-36`), so nothing reaches `v4_pack/builder.py:48`'s `clock_ok` rule. Reword
   "all three say nothing" to: two read `warning()` and say nothing; the third records the status and is not used in
   a rehearsal.
3. **Implementation hint (no change to the rule).** With `checks == ()`, `ClockReading.warning()` already returns "".
   So the `warning()` override can simply go, keeping `NOT_CHECKED` for the exercised line and T1f's card. L3's plant
   ("the old text returned") then means the override is put back.
4. The header says "two judges", but the orchestrator routed one. Align the text with the routing.

## Notes

- Cue reads keep the old rule. A cue read near 09:05 could in principle be shifted past its window the same way, but no
  recorded copy comes near it (the last is 08:51:00). Accepted as written; revisit if a cue window ever closes on a copy.

## Plants

None (a text round). L1-L5's plants and my own are run at the code round.

## Addendum 1

**Code round 1 of 2 at story/reh1l-preopen-serving @ 2d8ccb8d4 (REH1l's diff `34aad0d85...2d8ccb8d4`), judge F,
judge 1 of 2: FAIL on 1 should-fix (a test only; the code is right). Lane 1.** Own session; I did not read judge K.
Trial merge with main 6e332c6f2 (clean): **16,540 passed, 1 skipped, 14 xfailed** (token kept); ruff, format (2,630
files), `check_imports`, `check_records` (9,257 files) clean.

| Item | Result | My evidence |
|---|---|---|
| L1 never past the window | MET in code | `recorded_preopen.py:55-57` drops copies seen at or after `window[1]` before `ServedOnce.pick`; plants (filter off, `<=`, window end moved) caught |
| L2 the 23 Oct record | MET | `test_preopen_window.py` on the real receipts: gift, fo_list, nifty served; banknifty None at 09:10:00/30/45; 22 Oct none |
| L3 the clock apart | MET | `RehearsalReading` removed; `ClockReading(CLOCK_UNCHECKED, ())` warns "" (base rule); real unchecked readings still warn (plant caught) |
| L4 said once | MET | `rehearse.py` passes `(REPLAY_CLOCK,)` to `report_exercised`; plant dropping it caught |
| L5 / real runs unchanged | MET | the day cell for every real two-server outcome (ok, skew or down for each server, 9 cases) equals the old `warning or "ok"`: my enumeration printed 0 differences; the rehearsal writes `clock_unchecked`, never "ok" (`day_cell`, plants caught); nothing reads the day row's `clock` cell (grep) |
| 616 minors 2-4 | MET | text reworded (CaptureLog reads status); override removed; two judges |

## Findings

1. **Should fix: judge 616's condition is not proven by its test.** My plant "filter after the pick" (choose among
   all copies, then refuse one seen at or after the close) passes all 622 tests in `tests/rehearsal`, `tests/preopen`
   and `tests/intraday`. The cause is the case I gave in 616: at 09:10:45 the 09:10:30 copy (15 s away) is already
   nearer than 09:11:01 (16 s), so both orders serve 09:10:30. The test's docstring repeats the mistake ("nearer would
   be 09:11:01"). On the committed code a read at 09:10:50 gets 09:10:30, while under the plant it gets NOT_RECORDED
   (my run). Fix: read at 09:10:50 (09:11:01 is 11 s ahead, 09:10:30 is 20 s back), assert 09:10:30 is served, and fix
   the docstring. The plant must then fail. The wrong case was mine; the builder followed it.

## Plants

10 planted on 2d8ccb8d4, one at a time over `tests/rehearsal`, `tests/preopen` and `tests/intraday`, each restored:
**9 caught, 1 survived** (finding 1). Caught: window filter off; close counted inside; window end pushed out; day cell
old rule; day cell never "ok"; the replay reading warning again; the replay-clock item dropped; a real clock warning
no problem; the recorder ignoring `day_cell`.

## Addendum 2

**Code round 2 of 2 at story/reh1l-preopen-serving @ 7693168c2, judge F, judge 1 of 2: PASS. Lane 1.** Own session;
I did not read judge K.

| Item | Answer | My check | Result |
|---|---|---|---|
| SF1 (616.1) | the read moved to 09:10:50, asserting 09:10:30 at once, then NOT_RECORDED; docstring fixed | my plant "filter after the pick" re-run on 7693168c2: **1 failed**, 624 passed (it passed all 622 at 2d8ccb8d4); clean tree 625 passed | **Accepted** |
| No REH1l code change since 2d8ccb8d4 | test and Claims only | `git diff 2d8ccb8d4..7693168c2 -- fno/rehearsal fno/preopen fno/intraday` is empty; the only `fno/` change is `fno/forecast_v5_v1/` (G14 amendment 2, 7442d761f, already on main), carried in by REH1k's main merge cd7cf403d | **Confirmed** |

Gates on a trial merge with main e07863cc4 (clean): **16,543 passed, 1 skipped, 14 xfailed** (token kept); ruff, format
(2,630 files), `check_imports`, `check_records` (9,258 files) clean.

Plants, both rounds: 10 planted, **10 caught**. REH1k's own part of this head (d4fd149a6) is judged by judges E and B,
not here.
