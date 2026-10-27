# Judge 25: R1b1 NSE onto the resilience layer, code (judge #2)

Branch `story/R1b1-nse-layer`, SHA `9034093`. **FAIL** (round 1), lane 1: 1 should-fix, 2 minor, no blocking. Behaviour
equivalence holds: I traced every exit of today's `_response` to the new `_raised` and found each exception, `tries`
value and message unchanged. The pacer's probe path is correct. The gap is that two concurrency regressions **hang**
the test run instead of failing it.

Gates: 431 passed; characterization 96 passed; `ruff check`, `check_imports`, `test_code_size` clean; changed files
formatted; no workflow changed.

## Equivalence (traced against `main`'s `_response`)

| Today | After | Same? |
|---|---|---|
| `SourceCoolingOff` gives `RawSourceCoolingOff`, `tries - 1` | classify BLOCK, unanswered, then `_raised` | yes |
| unbuildable gives "(not sent)", `tries` | PERMANENT, unanswered, then `_raised` | yes |
| a transport error on the last try gives "after N tries" | RETRY, unanswered, EXHAUSTED by the attempt limit | yes |
| 404 gives `None`; REFUSED gives `RawFileRefused` | PERMANENT gives `None`; BLOCK gives `RawFileRefused` | yes |
| a second 429 in a row gives `RawSourceCoolingOff` at once | `_Answers.observe` stops; `paused` gives `RawSourceCoolingOff` | yes |
| `Retry-After` > 120 s, or the last 5xx, gives `RawSourceUnavailable` | `_give_up_reason` gives EXHAUSTED, then `RawSourceUnavailable` | yes |
| waits `max(5/15/45, Retry-After)` | `max(floor + U(0, 0.25 floor), Retry-After)` | floor equal, upward only |
| no total limit | `max_total_seconds = 900` | never reached inside today's worst case (305 s; 600 s with `Retry-After`) |
| `nse_json`: 3 tries, a 403 retried after the warm-up, 1.5/3/4.5 s including the last | `range(1, 4)`, the same loop, policy waits | yes |

## Plants (16 valid; 14 fail a test, **2 hang**)

Caught by a failing test:
- a waiter refused instead of waiting;
- a timed-out probe reopening;
- one pacer per session;
- one key for both hosts;
- `nse_json` not retrying a 403;
- `nse_json`'s last wait dropped;
- no `unanswered` call on exception (the `finally` path);
- released waiters skipping the rate limit;
- jitter 1.0 instead of 0.25;
- a second 429 not stopping;
- 5xx counted as a refusal;
- `tries` on cooling-off off by one;
- an `nse_json` floor changed.

**Hung (the suite never finishes):**
- **P2:** the probe wait made unbounded (`wait_for(..., None)`).
- **P12:** an expired wait leaving the breaker half-open.

(My first P9 plant was invalid and is not counted; a corrected one was caught.)

## Findings

1. **S1 (should fix): a concurrency regression must fail, not hang.** In `tests/ingestion/test_nse_pacer.py`,
   `thread.join()` at line 139 has no timeout, and the waits under test have no guard. A regression in the probe-wait
   path, the code most likely to regress, blocks pytest until the job's own timeout (`data-checks.yml`: 30 minutes)
   instead of producing a red test. JUDGE.md quality rule 4 needs a test that **fails** when the code is broken. Fix:
   join every thread with a timeout and assert it finished (`assert not t.is_alive()`), and keep each test's waits
   short. Then P2 and P12 must turn into failures, and should be shown as such in the evidence.

## Minor

1. `state.message` is set **after** `record_refusal()` opens the breaker, outside the breaker's lock (`nse_pacer.py`,
   `observe`). Another thread can see the host open and raise `SourceCoolingOff("")` before the message is set. Today
   `RequestPacer` set the pause and its message together under one lock. The window is tiny and only cosmetic (the
   text lands in `RawSourceCoolingOff` and the run log), but claim 2 says the message text is unchanged. Fix: build
   the message before `record_refusal()`.
2. The characterization change also drops `assert COOL_OFF_SECONDS == 900`. The 15 minutes is still pinned by
   behaviour (refused at 899 s, admitted at 901 s), so nothing is lost, but the story's "exactly one adaptation" should
   list it.

## Carried to R1b2 (not a finding now)

The breaker's clock is `EPOCH + monotonic` (`_wall_clock`). That is fine in one process, but a transition log written
with it would hold 2000-01-01-plus-uptime times. A new process (a different monotonic origin) would then misread the
cool-down. R1b2 must give the NSE breaker the real UTC clock before it writes `research/data/resilience/nse.csv`.

## Addendum 1: round 2, `0c0af47`

**PASS**, lane 1, judge #2. Gates: 432 passed; `ruff check`, `check_imports`, `test_code_size` clean; the pacer and
characterization tests passed in 12 of 12 repeated runs.

| Round-1 finding | Verdict | Evidence |
|---|---|---|
| S1 the hanging plants | FIXED | the threads are joined with a bound and `assert not is_alive()` (`test_nse_pacer.py:37-38,88-89,162-163`). P2 (an unbounded probe wait) and P12 (an expired wait left half-open) now **fail** (1 test each, about 13 s) instead of hanging |
| Minor 1 the message race | FIXED | `last_refusal` is set before `record_refusal()` can open the breaker, and the message is built when it is raised; plant "status not recorded" fails 2 tests |
| Minor 2 the dropped constant assertion | noted in the story | |

The behaviour equivalence traced in round 1 is unchanged: the delta touches only the message construction and tests.
