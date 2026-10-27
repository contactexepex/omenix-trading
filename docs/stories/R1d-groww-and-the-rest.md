# R1d: Groww, the close read and the remaining waits on the shared layer (PLAN; not a frozen story)

Lane 1 (outside services: Groww, NSE, NSDL; live capture windows). Plan, with the orchestrator's rulings below. Rules and design: [R1-resilience.md](R1-resilience.md); precedent: R1b ([R1b-nse-source.md](R1b-nse-source.md),
[R1b2-persisted-pause.md](R1b2-persisted-pause.md)) and R1c ([R1c-drive.md](R1c-drive.md)). The floor is the characterization
already on `main` (`tests/characterization/test_groww_and_close_read_behaviour.py`, `test_probe_backfill_and_index_loop_behaviour.py`,
27 tests, `296f76e` and `49788eb`).

## Hard rule that shapes the verification

No hand-run Groww command from 09:15 to 15:35 IST (CLAUDE.md, owner 25 Oct 2026). So **nothing in R1d is proved by a live Groww call
by hand**: the proof is offline tests (pytest never calls Groww), mutation plants, and the first scheduled run read the next
evening, exactly as R1b. The post-merge comparison reads logs only. A Groww dry-run before the merge does not exist and is not claimed.

## What exists today (checked in the code, not assumed)

| Piece | Today | Where |
|---|---|---|
| Intraday request spacing | `RatePacer(per_second)`: starts spaced `1/rate` apart, thread-safe, no persistence | `intraday/pacing.py` |
| Quote recorders' pacer | `RatePacer(slot.per_second)`, one per recorder across its attempts; the index slots use 3 workers at 2.5 a second (`INDEX_WORKERS, INDEX_PER_SECOND`); slots without `per_second` are unpaced | `quotes/recorder.py:127`, `quotes/indices.py:25`, `quotes/book_fetch.py` |
| Candle source gap | `MIN_GAP_SECONDS = 0.5`, one at a time, **not thread-safe** (by design: one call at a time) | `intraday/candle_source.py:_pace` |
| Groww 429 | the process pauses all Groww reads for 60 s (`RateLimitPause`), per process, no probe | `providers/groww_rate_guard.py` |
| Groww sign-in | one sign-in per process and token day; a failure backs off 5 then 10 minutes; at most 3 tries per process per token day; **no cross-process count**: the 150 a day is an estimate (about 38 processes, 114 tries in the worst case, `groww_sign_in.py` docstring) | `providers/groww_sign_in.py` |
| Close read | 3 tries, 60 s apart, no wait after the last; failure reported by class name only | `close_read/reader.py:_read` |
| Index recording loop | a 60 s retry gap inside the 15:01-15:13 window (a **window wait**, stays) | `quotes/indices.py`, `recorder.py` |
| Filings probe | 2 tries, 30 s pause after each failure | `filings/cli.py:_probe` |
| NSDL back-fill | 2 tries per month, form forgotten between tries, calls at least 10 s apart | `flow_history/nsdl_backfill.py` |
| Global cues | at most 3 attempts per source per IST day, kept in a committed log (already the day-ledger pattern) | `global_cues/attempt_log.py` |

## Proposed split (each step small, judged, behaviour-preserving first)

- **R1d1, Groww reads:** each caller keeps **today's spacing as its own limiter**: the intraday source 4 a second
  (`PER_SECOND = 4`), the index recorders 2.5 a second (`quotes/indices.py:25`, 3 workers), any other recorder slot its own
  `per_second` or none, the candle source 0.5 s. `RatePacer` becomes the shared `RateLimit` configured with that caller's
  spacing; no caller is slowed or sped up. **No new host-wide ceiling is added in this step:** the 10 a second and 300 a
  minute of `settings_for("groww")` stay unused here, because two callers in one process would sum to 6.5 a second (390 a
  minute) and a 300 a minute ceiling would slow them, which is new behaviour. (A real host ceiling, if wanted, is a
  separate decision with the owner.) What **is** shared, one instance per process like `SHARED_PACER`: the 429 pause as the
  breaker for host `groww` (threshold 1, 60 s, no doubling: exactly today's pause), **in process only** (no log, no alert in
  this step). Today each provider builds its own `RateLimitPause()` (`groww.py:142`), so a pause in one provider does not
  stop another in the same process; sharing it is the one deliberate change and only makes the process stop sooner after a
  429, never later. `RateGuardedGroww` keeps its class and translation (`GrowwRateLimited`, `GrowwRateLimitPaused`, no Groww
  text carried). The quiet-window check stays first, then the pause (pinned).
- **R1d2, the day budgets (PARKED, see Rulings; shown only so the split is whole):** the 150 sign-ins a day gets a real cross-process count (`FileDayLedger` on `groww_sign_in`, 150 a day),
  **committed and union-merged** (judge 1 and 2: otherwise overlapping runs each miss the others' rows and the count understates, which is
  unsafe). This needs a commit path for the callers (see "Unknowns"). Malformed ledger line: **fail closed** (count it), because
  an undercount could exceed a limit that locks the next morning out.
- **R1d3, the non-Groww waits:** close read tries onto `RetryPolicy` (3 tries, 60 s floor, no jitter: a live window, so **jitter 0**,
  the wait must stay exactly what the 15:40 read budgets), filings probe and NSDL gap onto `RetryPolicy` / `RateLimit` with
  today's numbers; window waits stay as they are.
- **R1d4, global cues and preopen:** characterization is **missing** (the attempt log and the preopen waits are not pinned): pin them first
  (the orchestrator's rule), then decide whether the attempt log needs any change at all (it already is a committed day ledger).

## Conditions carried from the judges

1. The Groww half-open probe would defer concurrent snapshot reads during the probe, where today all reads resume after 60 s
   (judge 2). R1d1 therefore uses **no probe and no half-open for Groww**: the pause just ends at 60 s, as today, which is not a
   behaviour change and needs no wait/probe machinery. This must be stated and tested.
2. The market-hours rule above.
3. Nothing may make fewer attempts at a live capture than today (R1c's lesson): the same never-weaker test for each moved wait.
4. One shared Groww **pause** per process, like `SHARED_PACER` (a test: two providers share it). The limiters are per caller.
5. Never-weaker tests: each caller's request starts stay spaced exactly as today (intraday 4/s, index recorders 2.5/s across
   3 workers, candle 0.5 s), and two callers in one process are not slowed by each other (their combined rate equals the sum
   of their own rates, with no host ceiling).

## Rulings (orchestrator, 27 Oct 2026) and what stays parked

- **R1d1 is in process only.** Groww's pause has no log and no committed file: today keeps none (no workflow calls Groww and no
  step could commit one), so in-process is never-weaker. No new persistence.
- **No Groww alert in R1d1** (a 60 s pause is routine backpressure). All Groww health alerting (sustained failure and the
  sign-in budget approaching its limit) is one feature, designed once in R1d2.
- **R1d2 is PARKED for the owner:** whether this repository owns Groww sign-in budgeting, whether the routine containers can persist
  a committed ledger, and how many of the 150 daily sign-ins are reserved for hand-run reads after 15:35 IST (the refuse-at
  number: not derivable here; it must clear the normal worst case of about 114 and the in-flight sign-ins before a ledger
  reflects them). Nothing about R1d2 is designed or built in this story.
- R1d1, R1d3 and R1d4 go ahead, behaviour-preserving, one story in judge-flight at a time.

## Gates

Characterization green with injection-only adaptations; the worst-case and never-weaker tables per moved wait; mutation plants; for
each step a post-merge comparison of the first scheduled run (log reads, no hand-run Groww); full gates; two judges per step.
