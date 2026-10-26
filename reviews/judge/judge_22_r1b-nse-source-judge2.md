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

## Addendum 1: round 2, `7a1ee0e` (story text; my last round on the R1b story)

**FAIL** on 1 should-fix, which the owner decides (via the orchestrator). All six round-1 findings are fixed:

| Round-1 finding | Verdict | Evidence (round-2 text) |
|---|---|---|
| B1 `nse_json` 403 after the cookie warm-up | FIXED | its own classifier: every non-200 or empty answer is RETRY after the warm-up; the archive `verdict()` is unchanged; claim 1 pins it |
| S1 the last wait | FIXED | 1.5/3.0/4.5 kept as floors, the last included |
| S2 the probe on 5xx/timeouts | FIXED | 403/429 reopen doubled; any other answer, 5xx included, closes; no answer gives the same cool-down (`record_unanswered`, flagged as a library addition) |
| S3 one per process | FIXED | `NsePacer`, one per process and **per host** (www and nsearchives), as `SHARED_PACER` (`http_pacing.py:38-39`); claims 4 and 5 |
| S4 timeouts | FIXED | the table is computed with code references; jitter 25% for NSE (+5% worst case). The three workflows that cannot fit under total failure are shown to be a pre-existing condition, not introduced by R1b, and are recorded for the owner |
| S5 `Deferred` to today's exceptions | FIXED | one conversion point to `SourceCoolingOff`; claim 2 tests each exception and its message |

The honest verification section is right: `dry_run` runs only `--help`. So the active comparison of the next run's
log, with a stop rule, is the real check.

### Finding

- **R2-1 (should fix): during the probe, the other threads should wait for its answer, not be refused.** The story
  states this difference ("other threads ... are refused") as bounded by one request. But a refusal is not a short
  wait: `SourceCoolingOff` makes callers **stop**. `NseArchiveSource` turns it into `RawSourceCoolingOff`, and
  `revision_source.py:60` and `filings/librarian.py:82,96` end their passes on it. One live caller is concurrent on
  NSE today: `quotes record --source nse` (`quote-recorder-nse.yml:65`). It runs index slots with `INDEX_WORKERS = 3`
  (`quotes/indices.py:25,42`) through `BookFetcher`'s thread pool (`book_fetch.py:39`), each calling `nse_json`. A
  probe inside the 14:55-15:10 window would cost two of the three threads that minute's quotes. Today, after the
  pause, all three go ahead. That contradicts the section's own title, "never stricter than today for data". Fix:
  while a probe is in flight, other `wait_turn` calls on that host **block until the probe answers** (bounded by the
  request timeout, 20 s for `nse_json`, 60 s for the archive). Then they proceed if it closed, or get `SourceCoolingOff`
  if it reopened. That is still one request in flight, with the same data outcome as today when the source has
  recovered. Test: 3 threads during a probe, the probe gives 200, all 3 complete; the probe gives 403, all 3 get
  `SourceCoolingOff`, and only 1 request was sent.

Recommendation to the owner (reasoning only): a small, local change; allow the fix and a check of just this point.
