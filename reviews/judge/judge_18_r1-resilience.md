# Judge 18: R1 resilience layer (story text), branch `story/R1-resilience`, SHA 2d6ea2a

**FAIL (round 1), lane 1, judge 1; 1 blocking, 5 should-fix.** Design only (one file, 91 lines). The direction is
right: one policy, a breaker with a half-open probe, jitter, and "deferred writes nothing". The 7 rows of the
"exists today" table match the code. But the inventory is incomplete, and two of its rules would break today's Drive
behaviour.

## Criteria

| Check | Verdict | Evidence |
|---|---|---|
| (1) "What exists" table vs the code | PARTLY | All 7 rows are accurate: `drive_session.py:13-14` `{429,5xx}` and `(2,8,30,60)`; `groww_rate_guard.py:17` 60 s; `attempt_log.py:18` 3. But the table is incomplete: finding 1 |
| (2) Transient-only retries | NOT MET as written | Findings 2 and 3 |
| (3) Transition CSV across runs | PARTLY | Writing transitions only is not noisy, but concurrency is unspecified: finding 4 |
| (4) "Deferred writes nothing" | PARTLY | Right for fetches. Retried **writes** (a Drive create after an ambiguous timeout) are not covered: finding 5 |
| (5) Claims and gap list | PARTLY | Claim 8 cannot be met by the R1a-R1e plan: finding 1 |
| (6) Step sizes | MET | R1a-R1e are sensibly small. Each must also list which sleep sites it migrates (finding 1) |

## Findings

1. **Blocking: the inventory, and therefore the plan, misses whole retry and pacing loops.** `grep` finds `sleep` in 22
   modules under `fno/`. Beyond the table's seven, these hold their own retry or pacing logic:
   - `quotes/recorder.py` (`RETRY_GAP_SECONDS = 60`, in-window retries) and `quotes/indices.py`;
   - `intraday/pacing.py` `RatePacer`, a **second pacer** next to `RequestPacer`, with `intraday/candle_source.py`,
     `feed_probe.py` and `recorder.py`;
   - `close_read/reader.py`, `preopen/run.py`, `providers/public.py`, `flow_history/nsdl_backfill.py`,
     `research_data/release_times.py` and `filings/cli.py`.

   The owner's directive is "for every source, existing and new". Claim 8 ("no other module holds its own copy of a
   retry loop") would fail on day one, and none of R1a-R1e migrates these. Fix: list every site, and for each say
   which step migrates it, or why it stays (some sleeps are window waits, not retries: say so).
2. **Should fix: "never 403" breaks Drive.** Google sends rate limits as **403** with reason `rateLimitExceeded` or
   `userRateLimitExceeded` (`drive_session.py:16`), and Drive retries them today. Classification must be
   per-source (NSE 403 is a refusal; Drive 403 with a rate-limit reason is transient), and the table-driven test must
   include that case.
3. **Should fix: "never auth failures" conflicts with today's Drive 401 handling.** Drive re-signs once on 401
   (`drive_session.py:12`). State that a 401 gets one re-sign, which is not a policy retry, and keep it.
4. **Should fix: the transition CSV under concurrent runs.** Hourly and overlapping workflows that append to one file and
   push with `pull --no-rebase` will conflict, since both append at the end. State the merge rule: one file per source,
   `.gitattributes merge=union`, or the existing keep-remote pattern. Also state:
   - a transition lost when a run dies before its commit (the breaker fails open, so the next run probes again);
   - a run that checked out before another's "opened" push does not see it;
   - two processes in half-open can each send a probe ("exactly one probe" holds per process only).
5. **Should fix: retried writes must be idempotent.** "Deferred writes nothing" covers failed fetches, but R1c puts the
   Drive session (creates, uploads) under the policy. A create that times out after Drive accepted it must be checked
   before it is retried. Today `GoogleDriveUploadStore.put` re-checks the path (`_fresh_child`) and compares bytes.
   State that only idempotent operations, or ones re-checked before retry, are retried, and test a
   timeout-after-success case.
6. **Should fix: per-day budgets need cross-run memory too.** Groww's 150 sign-ins/day spans many processes. An
   in-process `RateLimit` cannot enforce it. Either persist it like the breaker, or state that the per-day limit stays
   process-local and what guards it today.

## Notes

The placeholder numbers (N=5, 30 min, 2 s base, 60 s cap, 5 min total) are fairly labelled as reasoning only, and are
owner decisions. Keeping Groww under the market-hours rule is correct.
