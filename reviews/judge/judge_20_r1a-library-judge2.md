# Judge 20: R1a resilience library (judge #2)

Branch `story/R1a-resilience-library`, SHA `ee441a9cc4880320b7011088f492825b1575fb50`; `fno/shared/resilience/`
(521 lines, 7 modules), unused by any module yet. **FAIL** (round 1), lane 1: 1 blocking, 3 should-fix. The retry
floor, the NSE two-refusal rule, the one-request probe and the doubling cool-down are correct and well pinned. The
library is not thread-safe, unlike the two pacers it is to replace.

Gates: 312 passed; `ruff check`, `check_imports`, `test_code_size` clean; new files formatted.

## Criteria

| Claim (story) | Verdict | Evidence |
|---|---|---|
| 1 classification vocabulary | MET (library side) | `Outcome`/`Verdict`; the classifiers come in R1b/R1c |
| 2 waits in `[t_n, 2 t_n]`, Retry-After, ceiling, bounds | MET | `retry.py:57-62`; plants on the floor, equal jitter, Retry-After, ceiling, total and attempts all caught |
| 3 breaker: NSE 2, half-open single probe, doubling | MET single-threaded, NOT MET concurrently | plants on the threshold, doubling, probe retries, stop-on-open and half-open defer caught; see B1 |
| 4 state survives a new process; union merge | MET | restore plant caught; sort plant caught; `.gitattributes` row; `test_union_merge` |
| 5 a persisted day ledger across processes | **NOT MET** | S1 |
| 7 one alert per transition / exhaustion | MET (library side) | |
| Settings are today's numbers | MET | plants: NSE waits 5/10/20 caught; NSE threshold 3 caught; Groww 30 s caught |

## Findings

1. **B1 (blocking): `RateLimit` and `CircuitBreaker` are not thread-safe; the pacers they replace are.** Today's
   `RequestPacer` (`http_pacing.py:40`) and intraday `RatePacer` (`intraday/pacing.py:14`) hold a `threading.Lock`,
   and their callers run in thread pools (`quotes/book_fetch.py:39`, `storage/coverage.py:111`, intraday). I ran 8
   threads calling `acquire()` with 0.3 s spacing: the new `RateLimit` lets calls through **0.0 s** apart, while
   today's `RequestPacer` keeps them 0.3 s apart. Wired in as written (R1b/R1d), NSE would get bursts above 1 a
   second, and Groww above 10 a second. `CircuitBreaker.check()` has the same race: two threads can both see the
   cool-down as over and both become the probe, so the "exactly one probe" claim fails. Fix: one lock per instance
   around the read-modify-write (`acquire`/`_wait_needed`, `check`, `record_*`), sleeping outside the lock as
   `RequestPacer` does. Add concurrency tests: N threads keep the spacing; exactly one of N concurrent `check()` calls
   returns `PROBE`.
2. **S1 (should fix): claim 5 is claimed as covered, but no persisted ledger exists.** The test
   `test_a_ledger_shared_between_processes_carries_the_day_across` shares one in-memory `MemoryLedger` object between
   two `RateLimit` instances. That is not two processes. Either build the persisted ledger now (the `attempt_log`
   pattern: a row per use, counted by IST day, with a test across two instances reading the same file) or move claim
   5 to R1d in the evidence and say so.
3. **S2 (should fix): two behaviours are unpinned (surviving plants).**
   - **A13:** for NSE, a plain answer such as 404 between two 403s must reset the run of refusals, as today's pacer
     does (`observe` resets on any non-refusal status). With the reset limited to OK only, every test still passes, so
     "403, 404, 403" could open NSE where today it would not.
   - **A18:** a probe answered 404 must close the breaker (the source answered). With 404 treated as probe failure,
     every test still passes.

   Add a test for each.
4. **S3 (should fix): the owning document contradicts itself.** `R1-resilience.md:8` ("after ... V1 has passed") and
   `:49` ("Design (build, after acceptance and V1)") still gate on V1; `:146` says the gate is lifted. Fix the two
   lines in place.

## Notes

1. For R1d, not now: a Groww breaker with half-open defers every concurrent read while the probe is out. Today, after
   the 60 s pause, all reads resume. For the time-critical intraday snapshots that turns a pause into lost captures.
   R1d must show its Groww configuration keeps today's behaviour, perhaps with no half-open for Groww.
2. `tests/ingestion/test_paths.py` gets a one-line formatting change, outside R1a's scope. Harmless (it was the
   `ruff format` drift on `main`).

## Plants

20 planted, 18 caught. Survivors: A13 and A18 (S2).

## Addendum 1: re-freeze `0929993f5b81aebc339bf1967b9bc60a26c33216` (supersedes `ee441a9`)

The diff from `ee441a9` is `docs/stories/R1-resilience.md` only; the code and tests are identical. **S3: FIXED**
(`:8`, `:10` and `:51` now state the lifted gate and the replacement checks). Verdict unchanged: **FAIL**, round 1,
on B1 (not thread-safe), S1 (no persisted day ledger behind claim 5) and S2 (two unpinned behaviours). All of them
apply to `0929993` as is.
