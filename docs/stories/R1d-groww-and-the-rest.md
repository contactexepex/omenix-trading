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
| Quote recorders' pacer | `RatePacer(slot.per_second)`, one per recorder across its attempts; the index slots use one recorder with 3 workers at 2.5 a second in total (`INDEX_WORKERS, INDEX_PER_SECOND`); slots without `per_second` are unpaced | `quotes/recorder.py:127`, `quotes/indices.py:25`, `quotes/book_fetch.py` |
| Candle source gap | `MIN_GAP_SECONDS = 0.5`, one at a time, **not thread-safe** (by design: one call at a time) | `intraday/candle_source.py:_pace` |
| Groww 429 | the process pauses all Groww reads for 60 s (`RateLimitPause`), per process, no probe | `providers/groww_rate_guard.py` |
| Groww sign-in | one sign-in per process and token day; a failure backs off 5 then 10 minutes; at most 3 tries per process per token day; **no cross-process count**: the 150 a day is an estimate (about 38 processes, 114 tries in the worst case, `groww_sign_in.py` docstring) | `providers/groww_sign_in.py` |
| Close read | 3 tries, 60 s apart, no wait after the last; failure reported by class name only | `close_read/reader.py:_read` |
| Index recording loop | a 60 s retry gap inside the 15:01-15:13 window (a **window wait**, stays) | `quotes/indices.py`, `recorder.py` |
| Filings probe | 2 tries, 30 s pause after each failure | `filings/cli.py:_probe` |
| NSDL back-fill | 2 tries per month, form forgotten between tries, calls at least 10 s apart | `flow_history/nsdl_backfill.py` |
| Global cues | at most 3 attempts per source per IST day, kept in a committed log (already the day-ledger pattern) | `global_cues/attempt_log.py` |

## Proposed split (each step small, judged, behaviour-preserving first)

- **R1d1, Groww reads: a pure consolidation (design ruled by the orchestrator and both judges, 27 Oct 2026).** The per-caller
  `RatePacer`s and the per-provider `RateLimitPause` move onto the shared `RateLimit` and breaker with **identical spacing and
  identical pause topology**. Nothing new is added.
  1. **Spacing, pinned exactly as today:** intraday 4 a second (`PER_SECOND = 4`); the index recorders **2.5 a second in total**
     (one recorder with 3 workers, `quotes/indices.py:25`; the slots run one at a time, so the combined rate is 2.5, not 7.5);
     the main NIFTY recorder **unpaced** (`per_second=None`, `quotes/slot.py:18,30`; no limiter, as today); candle source 0.5 s.
  2. **No host-wide ceiling.** Today has none, so a ceiling is a new component, not a refactor, and its "never bites" cannot be
     proven: the unpaced NIFTY recorder's peak rate is unmeasured. A real ceiling needs the true aggregate measured, a number
     chosen and throttling accepted: an owner decision with the Groww health feature (R1d2). The host numbers in
     `settings_for("groww")` stay unused here.
  3. **Pause topology, exactly as today:** one 60 s `RateLimitPause` per `GrowwProvider` instance (`groww.py:142`), in process only,
     no half-open, no log, no alert. The index recorders share one provider (`quotes/index_wiring.py:20`) and so share its pause;
     intraday (`intraday/feed_wiring.py:51`) and the quote window (`quotes/window_wiring.py:28`) each have their own. Not
     "independent per caller" (that would un-share the indices) and not "shared per process" (that over-shares). A pause shared
     across providers would be a data-versus-blacklist call for the owner, deferred with R1d2.
  4. **Every Groww composition root builds exactly one provider** (each provider signs in on its own, `groww.py:139`): a named
     test covers `intraday/wiring.py:63`, `intraday/feed_wiring.py:51`, `intraday/backfill_wiring.py:46`,
     `quotes/index_wiring.py:20`, `quotes/window_wiring.py:28`, `composition.py:53` and `preopen/wiring.py:80`.
  5. `RateGuardedGroww` keeps its class and translation (`GrowwRateLimited`, `GrowwRateLimitPaused`, no Groww text carried); the
     quiet-window check stays first, then the pause (pinned).
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
4. Pause topology tests: two index recorders on one provider share its pause; a 429 in one provider does not pause a caller of
   a different provider.
5. Never-weaker tests: each caller's request starts stay spaced exactly as today (intraday 4/s, index recorders 2.5/s combined,
   candle 0.5 s, the NIFTY recorder unpaced), and the composition-root test of R1d1 point 4.

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
