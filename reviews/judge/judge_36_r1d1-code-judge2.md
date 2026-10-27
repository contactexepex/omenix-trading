# Judge 36: R1d1 Groww consolidation, code (judge #2)

Branch `story/R1d1-groww`, SHA `4dcc88652cb1f8a20be5e42d4cd485e1278b1092`, lane 1. **FAIL** (round 1) on 1 should-fix,
tests only. The code reproduces today's spacing and pause exactly, but nothing pins the plan's "no ceiling, no new
limit": adding a per-minute or per-day cap to the Groww pacers leaves every test green.

## Gates (`__pycache__` cleared)

550 passed; ruff check and format clean; imports clean; code size passed. The diff changes no existing test (only
`tests/ingestion/test_groww_consolidation.py` is added), so the pre-existing tests pass unedited.

## Equivalence, traced

| Piece | Today | Now | Verdict |
|---|---|---|---|
| `RatePacer` | under a lock, `start = max(now, _next)`, `_next = start + interval`, sleep outside the lock; first start free (`_next = 0.0`) | `RateLimit.acquire`: under a lock, `start = now` if first, else `max(now, _last + spacing)`; sleep outside; `per_minute`/`per_day` None; `max_wait = inf` | same |
| Candle gap | sleeps `0.5 - (now - last)`; `last = monotonic()` **after** the sleep (the actual start) | `RateLimit` with spacing 0.5; `_last` is the **scheduled** start | same to within the sleep's overshoot (note 1) |
| `RateLimitPause` | `_until = clock() + seconds`; `check` raises `GrowwRateLimitPaused(PAUSED)` while `_until - clock() > 0` | the same arithmetic in `FixedPause`; `check`, the text and the exception unchanged | same |
| Topology | one `RateLimitPause()` per `GrowwProvider` (`groww.py:142`) | `groww.py` unchanged | same |

**`FixedPause` instead of the breaker: justified.** `CircuitBreaker`'s half-open state lets one probe through and
holds the rest, which is the deferral the plan forbids (condition 1). A "no probe" mode would add a branch to the
breaker that NSE does not need. `FixedPause` is the old 3-line logic moved to `fno/shared/resilience/`. It has one
user today (CLAUDE.md: "never add a pattern without a second use"), but it is a plain class, not a pattern, and R1's
purpose is to put the primitives in the shared layer; I accept it.

## Plants (mine; each restored, `__pycache__` cleared)

| Plant | Failed |
|---|---|
| G1 `RateLimit` spacing removed | 12 |
| G2 intraday interval halved | 4 |
| G3 the pause halved / G4 never active / G9 `PAUSE_SECONDS` 60 -> 59 | 4 / 5 / 2 |
| G5b intraday pacer `max_wait` 0.3 s (a deferral) | 3 |
| G6 a second `GrowwProvider(...)` in `intraday/wiring.py` | 1 |
| G7 quiet-window check after the pause / G8 the pause text changed | 1 / 1 |
| G5 candle `max_wait` back to the default 120 s | 0: an equivalent mutant (a 0.5 s gap, one call at a time, never waits 120 s) |
| **G10 intraday pacer `per_minute=100`** | **0: survives** |
| **G10b candle `per_minute=10`** | **0: survives** |
| **G10c intraday pacer `per_day=50`** | **0: survives** |

## Finding

1. **S1 (should fix, tests only): "no ceiling, no new limit" is not pinned.** The plan's R1d1 point 2 and condition 5
   say no caller is slowed and there is no host ceiling. `RatePacer` and the candle source now build a `RateSettings`,
   which has `per_minute` and `per_day` fields; setting either (G10, G10b, G10c) would throttle a live capture (100 a
   minute against the intraday 240) with all 550 tests green.
   - `test_each_callers_spacing_is_what_it_was` checks only `.interval`.
   - The 11-start index test stays under any realistic cap.

   Fix, either:
   - assert the built settings for each caller: `per_minute is None`, `per_day is None`, `max_wait_seconds == inf`;
   - or run past a minute on the fake clock: e.g. 241 intraday starts in 60 s, and 121 candle calls in 60 s.

   The second is behavioural and preferred: it would also catch a cap added inside `RateLimit` itself.

## Notes (not blocking)

1. **The candle gap is now measured from the scheduled start, not the actual one.** Today `_last_start` is read
   after the sleep, so a sleep that overshoots by a few milliseconds pushed the next start later. Now the next start
   is `scheduled + 0.5`, so the gap between actual starts can be 0.5 s minus that overshoot. This is milliseconds, and
   it is how the intraday `RatePacer` already worked today. Reasoning only: I did not measure the overshoot. Name it
   in the story as the one micro-delta, or accept it explicitly.
2. **The one-provider test checks each file, not each process.** It catches a second call site in a file (G6) and any
   new file (set equality). It would not catch:
   - one call site run twice, such as a builder called in a loop;
   - two files' builders run in one command.

   Fine as a tripwire; the story should say these limits.
3. **`RateLimit._slots` grows without bound when `per_minute` is None:** every `acquire` appends, and only the
   per-minute branch pops. For a day of Groww starts that is thousands of floats, negligible, but it is a leak in a
   shared primitive (it also affects NSE's pacer users). A one-line fix: append only when `per_minute` is set. It is a
   lane-2 follow-up, not R1d1.

**Verdict: FAIL** (round 1). S1 is tests only; everything else holds.

## Addendum 1: decisive round 2, b1bebc4 (PASS)

Branch `story/R1d1-groww-r2`, SHA `b1bebc4139a512a0697dd18ad2f6e576666e8172`. Compared with `4dcc886`, the only code
change is in `rate_limit.py`; the rest is tests, the two story texts and judge files.

**Gates** (`__pycache__` cleared): 555 passed; ruff check and format clean; imports clean; code size passed.

**The `_slots` change in shared code is behaviour-neutral.** `_slots` is read only inside `if s.per_minute is not None`
(`rate_limit.py:110-113`), and the append is now under the same condition. With a per-minute budget, nothing
changes. Without one, the deque was never read. The production `RateLimit` instances are NSE's per-host pacer
(`nse_pacer.py:141`), the intraday pacer and the candle source, and all three have `per_minute` None.
`settings_for("groww")` does carry `per_minute=300` (`settings.py:64`), but no `RateLimit` is built from it, so
"every source has None" is true of every limiter in use, not of every settings entry.

**Plants on b1bebc4** (each restored):

| Plant | Failed |
|---|---|
| G10 intraday `per_minute=100` / G10b candle `per_minute=10` / G10c intraday `per_day=50` / G10d candle `per_day=20` | 1 / 1 / 1 / 1 (S1 fixed) |
| G11 `_slots` appended always / G12 never appended | 1 / 2 |
| G1 spacing removed / G2 interval halved / G4 pause never active / G9 pause 59 s | 15 / 7 / 5 / 2 |
| G6 a second provider in `intraday/wiring.py` / G7 quiet check after the pause | 1 / 1 |

(I also tried a hidden cap inside `RateLimit`, plant G10e. It was a broken mutant that crashed instead of capping, so
it proves nothing and I discard it.)

My three notes are in the story: the candle micro-delta, the scan described as a tripwire, and the `_slots` fix.
Only nit: the story calls the candle delta "never weaker". Strictly, the gap between actual starts can be a few
milliseconds under 0.5 s; "a millisecond difference, as the intraday pacer always had" is the exact wording. Not
blocking.

**Verdict: PASS** (lane 1, code round 2, judge #2).
