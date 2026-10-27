# Judge 38: R1d3 code (close read and NSDL waits on the shared layer), judge #1

**SHA:** `b4f1fc6d40d356c536b4bf9d9677ce449bd9a6cf` (`story/R1d3-waits`, base 4bc082d). Lane 1 (NSE close list in a
live window; NSDL).
**Verdict: PASS, round 1.**

## Gates

- Suite: 559 passed, 2 runs out of 2.
- ruff, imports (394 files) and size: clean.
- The only test change is the new `test_close_read_and_nsdl_waits.py`. No characterization or existing test is edited.

## Close read: never-weaker (strong evidence: old and new read side by side)

**Settings:** `waits=(60, 60)`, so `max_attempts = 3`. `jitter=0.0`, so `wait_before` is the floor plus `uniform(0, 0)`:
exactly 60 s. Retry-After ceiling and total limit are both `inf`. A 3-failure read therefore waits exactly 120 s, as today.

**Every failure is retried.** `RetryPolicy.run` catches `Exception` (`retry.py:79`), as the old loop did. The classifier
returns `RETRY` for any error, and that includes errors from `read_answer`, which sits inside `_answer` as it sat inside
the old `try`.

**No sleep after the last try.** The policy gives up at `tries >= max_attempts` before computing a wait, matching the
old `if attempt < TRIES - 1`.

**The reason comes from the last failure.** `Attempted.error` is the last attempt's error. A `Refused` keeps its text;
anything else is reported as the class name with "(message withheld)", as today.

**Plants, all caught:**

| Plant | Result |
|---|---|
| A plain exception not retried | caught |
| `Refused` not retried | caught |
| `Refused` text replaced | caught |
| An exception's message leaked into the public log | caught |
| A sleep after the last try | caught |
| A 59 s gap | caught |

These add to the implementer's seven plants (jitter, a third wait, a 100 s total limit, PERMANENT).

## NSDL: identical gap

The new `RateLimit` has a 10 s spacing, no budget and `max_wait=inf`, so it never defers. The first call is free, as
the old `_pace` was. The 2-tries-a-month loop and `form.forget()` are unchanged.

| Plant | Result |
|---|---|
| Spacing 9 s | caught |
| `forget()` removed | caught |

The gap now counts from the reserved start, not the actual start after the sleep. That is the same millisecond
oversleep nuance noted for the candle source in judge_37, and not a concern for a 10 s politeness gap.

## The filings probe left bespoke: agreed (reasoning)

Today's probe sleeps 30 s after every failure, the last included (`filings/cli.py:68-78`). `RetryPolicy` never sleeps
after the last try. Moving the probe onto it would either:
- change behaviour, by dropping the trailing 30 s;
- or add a "sleep after the last try" mode used once.

The probe is a two-try diagnostic outside any live window. Keeping it bespoke is the KISS choice.

Keeping the trailing sleep is right too: it costs 30 s in a diagnostic and harms nothing. Removing it is a behaviour
change for a later story, if anyone wants one.

## Not blocking

`READ_RETRY` is built at import as `waits=(TRY_GAP_SECONDS,) * (TRIES - 1)`. If `TRIES` were ever set to 1, the module
would fail to import (`ValueError: waits must be a non-empty list`). That is loud, not silent, and a 1-try close read is
not planned.

## Hard lines

No orders. No secrets. No live NSE, NSDL or Groww call: every plant and test uses fakes. No write-once path is touched.
