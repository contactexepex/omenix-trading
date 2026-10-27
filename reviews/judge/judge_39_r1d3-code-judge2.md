# Judge 39: R1d3 close read and NSDL waits, code (judge #2)

Branch `story/R1d3-waits`, SHA `b4f1fc6d40d356c536b4bf9d9677ce449bd9a6cf`, lane 1. **PASS** (round 1). Two nits.

## Gates (`__pycache__` cleared)

559 passed; ruff check and format clean; imports clean; code size passed. No characterization file is changed
(`git diff --stat origin/main...b4f1fc6 -- tests/characterization` is empty).

## Equivalence, traced

| Piece | Today (`main`) | Now | Verdict |
|---|---|---|---|
| Close-read tries | `for attempt in range(TRIES)` (3); `except Refused` keeps its text, `except Exception` keeps the class name; `sleep(TRY_GAP_SECONDS)` (60) only between tries | `RetryPolicy`: `waits = (60,) * 2`, so `max_attempts = 3`; jitter 0 (`wait = 60 + uniform(0, 0)`); `max_total = inf`; Retry-After never set; `_retry_every_failure` gives RETRY for any error; the policy catches `Exception`, as before; no wait after the last try; the reason is taken from the last error, with the same two rules | same |
| What is inside a try | `source.answer()` and `read_answer(payload, day)` | `_answer` does both inside the attempt | same (plant C8 caught) |
| NSDL gap | sleeps `10 - (now - last)`; `last` read after the sleep | `RateLimit`, spacing 10, no budget, `max_wait = inf` | same to within the sleep's overshoot (nit 1) |
| NSDL tries | 2 per month, the form forgotten between them | unchanged | same |

## Plants (mine; each restored)

| Plant | Failed |
|---|---|
| C1c jitter 0.25 (with the cap raised so it builds) | 6 |
| C1 jitter 0.25 alone | 8 errors (the settings check refuses it at import) |
| C2 tries 3 -> 2 / C3 gap 60 -> 30 / C4 `max_total` 100 | 5 / 6 / 1 |
| C5 a refusal treated as PERMANENT | 4 |
| C6 a refusal's text withheld / C7 an error's message leaked into the public reason | 2 / 1 |
| C8 parsing moved out of the retried attempt | 1 |
| N1 NSDL gap halved / N2 gap removed / N3 `per_day=3` / N4 `max_wait` back to 120 s | 2 / 1 / 1 / 1 |
| C1b cap doubled with jitter 0 | 0: equivalent mutant (with no jitter the cap is never reached) |

C7 matters: the run log is public, and an error's message can carry a URL. The test keeps it withheld.

## The filings probe: I agree it stays as it is

`filings/cli.py:68-78` prints a line for each failed try and pauses 30 s after **every** failure, the last one too.
`RetryPolicy` never waits after the last try, so moving the probe would either change that pinned pause or add a
single-use "wait after the last try" mode to a shared primitive. For a diagnostic with no live window, leaving it is
right (reasoning only). Separately, the trailing 30 s after the final failure buys nothing; removing it would be a
small change for the owner to decide, not part of R1d3.

## Nits (not blocking)

1. **NSDL now has the candle's millisecond difference too:** the 10 s gap counts from the scheduled start, not the
   actual one after the sleep. The story names this for the candle only; add one clause for NSDL.
2. **One sentence in the R1d story repeats itself:** "the intraday pacer always worked that way, so it is a difference
   of milliseconds, as the intraday pacer always was".

**Verdict: PASS** (lane 1, code round 1, judge #2).
