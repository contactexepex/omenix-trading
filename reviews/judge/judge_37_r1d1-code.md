# Judge 37: R1d1 code (Groww reads on the shared primitives), judge #1

**SHA:** `4dcc88652cb1f8a20be5e42d4cd485e1278b1092` (`story/R1d1-groww`, base 290fc9b). Lane 1 (Groww).
**Verdict: FAIL, round 1 of 2.** The code is behaviour-preserving as built. The tests that should prove it per caller
do not.

## Gates

- Suite: 550 passed, 2 runs out of 2.
- ruff and imports (393 files): clean.
- `test_code_size`: 3 passed.
- No existing test file is edited: the only test change is the new `test_groww_consolidation.py`.

## The code: behaviour preserved (strong evidence: old and new read side by side)

- **`RatePacer` on `RateLimit`: identical.**
  - Old: `start = max(now, _next)`, `_next = start + interval`, reserved under a lock, sleeping outside it.
  - New `_next_start`: `max(now, _last + spacing)`, `_last = start`, same lock pattern (`rate_limit.py:89-104`).
  - The first start is free in both.
  - `per_minute` and `per_day` are unset; `max_wait=inf`, so the pacer never defers.
- **Candle gap: equivalent up to oversleep.**
  - Old: the gap is measured from the monotonic reading after the sleep.
  - New: the gap is measured from the reserved start.
  - Only a sleep that overruns by δ could make the next start 0.5 − δ s after the previous one. That is milliseconds,
    and `RatePacer` already worked this way (reasoning only; not blocking).
- **`RateLimitPause` on `FixedPause`: identical.** It is a fixed 60 s pause, a restart extends it from now, and it keeps
  the same exception and text. `groww.py:142` is unchanged: one pause per provider.
- **The deviation from the plan ("shared breaker") is right.**
  - (a) `CircuitBreaker.check` raises `Deferred("circuit half-open: a probe is already out")` for every other caller
    while a probe is out (`breaker.py:76-77`). That is exactly the probe deferral condition 1 forbids.
  - (b) `FixedPause` reproduces today's behaviour (above).
  - (c) It is today's 10-line no-probe pause moved to `fno/shared`, not a new mechanism. Its one user is honest. Leaving
    `RateLimitPause` where it was would have been equally fine (reasoning; not blocking).
- **The carried conditions from judge_34:**
  - The scan test parses every `.py` under `fno/` with `ast` and compares the set of sites. It catches a new site:
    planting a second `get_provider` in `window_wiring.py` is caught.
  - The 429 table row is not re-checked here; it is a story-text item.

## Plants

| Plant | Result |
|---|---|
| Pacer interval halved | caught |
| First start not free | caught |
| Candle gap 0.4 s | caught |
| Pause half as long | caught |
| Pause never ends | caught |
| Pause not started on a 429 | caught |
| Pause shared per process (a real module-level shared instance) | caught |
| Pacer wait capped at 1 s (deferral) | caught |
| Index rate constant 5.0 | caught |
| Second provider in a root | caught |
| **The quote recorder builds no pacer** (`recorder.py:127` → `None`, so the index slots are unpaced) | **survives: 550 passed** |
| **The intraday source paces at 400 a second** (`groww_source.py:56`, `RatePacer(PER_SECOND * 100)`) | **survives: 550 passed** |

## Required to PASS

**Condition 5 of the passed plan is not met at the callers (strong evidence: two plants survive).** The plan's condition
5 says "each caller's request starts stay spaced exactly as today". The new tests check constants and a bare
`RatePacer`: `RatePacer(PER_SECOND).interval == 0.25`, and 11 `wait()` calls on a pacer built in the test. They never
check that the callers build and use that pacer. So:
- an intraday source at 400 a second would pass;
- an index recorder with no pacer at all would pass.

Those are the two live-window callers, and the second is the A16 reason the 2.5 exists ("under the about 10 where Groww
began failing").

This also answers the orchestrator's question: "541 pre-existing tests pass with zero edits" is weaker evidence than it
looks. The existing tests do not pin the callers' spacing either; the same two plants pass them.

Fix, tests only:
1. `GrowwIntradaySource` built without a `pacer` uses one with `interval == 0.25`, and its fetch path calls `wait()`
   once per request.
2. A `QuoteSnapshotRecorder` with `index_slot(...)` has a pacer with `interval == 0.4`. Its `BookFetcher` with 3 workers
   shares that one pacer: N books mean N starts 0.4 s apart on a fake clock. The R1c `record_one_attempt` harness over
   `SampleProvider` shows this is cheap.
3. The NIFTY recorder (`slot.per_second is None`) has `pacer is None`.

Each test must fail under the matching surviving plant above.

## Not blocking

- With `per_minute` unset, `RateLimit` appends each start to `_slots` and never pops it. Intraday at 4 a second for 2 h
  45 min is about 40,000 floats, a few hundred kB. This predates R1d1 (library code), but R1d1 is its first long-running
  user. A follow-up should pop or skip the deque when `per_minute` is `None`.
- The story's "per process" table row is to be reworded in the story (judge_34 condition 2). Story text is not in this
  diff.

## Hard lines

No orders. No secrets. No Groww call: every plant and test uses fakes. No write-once path is touched.

## Addendum 1: round 2, b1bebc4: PASS

Reviewed `b1bebc4139a512a0697dd18ad2f6e576666e8172` (`story/R1d1-groww-r2`).

**Gates:** 555 passed in 2 runs out of 2. ruff, imports (393 files) and size are clean.

**The production delta from 4dcc886 is one line** (`rate_limit.py:101`): starts go into `_slots` only when
`per_minute` is set. It is behaviour-neutral for every source: `_slots` is read only under `if s.per_minute is not None`.
NSE, which sets no `per_minute`, now also stops growing it.

**Plants, all caught:**

| Plant | Result |
|---|---|
| The quote recorder builds no pacer (round-1 survivor) | caught |
| Intraday paces at 400 a second (round-1 survivor) | caught |
| The NIFTY slot paced at 4 a second | caught |
| `BookFetcher` workers skip `pacer.wait()` | caught |
| The intraday fetch skips `pacer.wait()` | caught |
| `_slots` never appended even when `per_minute` is set | caught by the per-minute tests |

The round-1 plants against the unchanged code carry over.

**Story:**
- The "Groww 429" row now says "one pause per provider" (judge_34 condition 2, met).
- The scan test is described honestly as a tripwire per file, not a per-process proof.
- Nit, not blocking: the candle note says "never weaker". Strictly, an overslept sleep of δ can make the next start
  0.5 − δ s after the previous actual start, so it is "milliseconds, as the intraday pacer always was". It is not
  literally never.

**Verdict: PASS (strong evidence: gates run, every round-1 survivor now caught, the code read side by side with
today's).**
