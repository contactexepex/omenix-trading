# Judge 22: R1b NSE source onto the resilience layer, story text (judge #2)

Branch `story/R1b-nse-source`, SHA `b9ef26a515f9ed49778c6232ed8bb61d28765479`, story only. **FAIL** (round 1), lane 1:
1 blocking, 5 should-fix. The archive-source part is well specified. The `nse_json` part would break live captures, and
two of the "deliberate differences" are not never-weaker as claimed.

## Criteria

| Item | Verdict | Evidence (`main`) |
|---|---|---|
| Scope table matches today | PARTLY | `raw_source`/`retry_policy` and `RequestPacer`: right. `nse_json` (`public.py:46-55`): it retries **every** non-200 or empty answer after `_warm()`, which the table leaves out (B1) |
| Difference 1 (upward jitter) is never weaker | MET for politeness; timeouts unchecked | S4 |
| Difference 2 (one probe after the pause) is never weaker | PARTLY | stricter on 403/429, but stricter than today on 5xx and timeouts too (S2) |
| Difference 3 (drop the trailing wait) is never weaker | NOT MET | S1 |
| R1b2 log concurrency-safe | MET for the file (`merge=union`) | in-process sharing: S3 |
| The two characterization adaptations are justified | MET for zero-jitter injection; the second is the change rejected in S1 | |

## Findings

1. **B1 (blocking): R1's "NSE 403 = BLOCK, never retried" must not reach `nse_json`, or live captures break.** Today
   `nse_json` treats any non-200 (403 included) as "warm the cookies and retry": `_warm()` loads `/option-chain` once,
   then it retries (`public.py:40-53`). NSE refuses a cookie-less first request; `http_pacing.py:21` says "NSE can
   refuse once until its cookies are set". A `RetryPolicy` with the archive classifier would end the call at that
   first 403. That call serves the option chain (`public.py:132,147`), India VIX and futures for the 3 pm quotes
   (`quotes/market_levels.py:81,85`) and the close read (`close_read/source.py:25`), so they would all fail where
   they succeed today. Fix: give `nse_json` its own classifier. A first 403 or empty answer is RETRY with `_warm()`
   before the retry, as today. The breaker still counts each 403/429, so a second in a row pauses the host, as today.
   Add a characterization test: a cookie-less 403, then 200 after the warm, returns the data.
2. **S1 (should fix): dropping `nse_json`'s trailing wait is weaker, not neutral.** Today a call that fails 3 times
   sleeps 1.5, 3 and then 4.5 s before raising, so the caller's next NSE request (callers loop over symbols and
   endpoints) comes at least 4.5 s after the last failure. Without that wait it comes after the 0.4 s spacing. The
   breaker counts only 403/429, so during a 5xx or empty-answer storm the request rate rises about tenfold. Keep the
   trailing 4.5 s (the story allows it), or make the spacing after a failed call at least 4.5 s. Also list as a
   difference that `nse_json` stops retrying 404, which today it retries.
3. **S2 (should fix): the probe rule is stricter than today on non-refusals, and that costs data.** In the library a
   probe answered 5xx, or timed out, counts as a failure and doubles the cool-down. Today the pacer counts only
   403/429; a 5xx resets the count. With R1b2's memory, one NSE 503 on the morning probe after an evening pause keeps
   NSE closed for 30 more minutes: the 07:41 retry run of `index-closes.yml` defers, and the 11:41 run is the last
   before 14:00. Fix, NSE's probe mirroring the pacer:
   - a 403/429 reopens the breaker for twice as long;
   - any other answer (404, 5xx) closes it, and the normal retry rules apply;
   - an unanswered probe keeps it open for the same cool-down, not doubled.
4. **S3 (should fix): name the per-process sharing.** Today one `SHARED_PACER` serves every `PacedSession` in the
   process (`http_pacing.py:63-71`; sessions are made in `storage/wiring.py:154`, `public.py:35`,
   `global_cues/wiring.py:281`, `preopen/wiring.py:63`, `circulars/wiring.py`). The `nse` `RateLimit` and
   `CircuitBreaker` must likewise be **one instance per source per process**, or each session paces only itself.
   That would be weaker than today. Add a claim and a test: two sessions share the spacing and the open breaker.
5. **S4 (should fix): the timeout check is left to the judge; the story must do it.** Jitter doubles the worst-case
   waits per file (65 s becomes 130 s, plus `Retry-After` up to 120 s per try). Four NSE workflows run with
   `timeout-minutes: 15` or `20` (`circulars`, `flows-download`, `participant-oi-watch`, `fo-masters`). A timed-out
   job skips its commit step, leaving uploaded files without receipts until a later repair. Give each workflow's
   worst case (files per run × maximum waits) against its timeout, or cap the total time per run below the timeout.
6. **S5 (should fix): name the mapping from `Deferred` to today's exceptions.** Claim 6 says the callers are
   unchanged. That holds only if an open-breaker `Deferred` becomes `RawSourceCoolingOff` (a `RawSourceUnavailable`)
   in the archive source, and today's exception in `nse_json`. Say so, and test it, so `coverage`, the librarian and
   the Stager stop as today.

## Notes

The R1b1/R1b2 split, the zero-jitter injection for the characterization tests, the `merge=union` log, and the per-merge
dry run of `index-closes.yml` (which has `dry_run`) are right.
