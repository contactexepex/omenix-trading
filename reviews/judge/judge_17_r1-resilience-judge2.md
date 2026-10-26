# Judge 17: R1 resilience layer, story text (judge #2)

Branch `story/R1-resilience`, SHA `2d6ea2a4a49ffb4e8166799edb92d9216aa70492`, design only. **FAIL** (round 1),
lane 1, on 5 should-fix and no blocking finding. The direction is right: one policy, a breaker with cross-run memory,
no partial data, numbers left to the owner. Three of the five findings would make the build *weaker* than today's code.

## Criteria

| Item | Verdict | Evidence |
|---|---|---|
| (1) "What exists" table | PARTLY | NSE `(5, 15, 45)`, 4 tries, `Retry-After` up to 120 s (`retry_policy.py:22-23`); Drive 401 re-sign-in once, `{429, 5xx}`, `(2, 8, 30, 60)` (`drive_session.py:12-14`); Groww 60 s pause (`groww_rate_guard.py:17`); global cues 3 a day (`attempt_log.py:18`): all correct. **Missing:** Drive also retries **403 with `rateLimitExceeded`/`userRateLimitExceeded`** (`drive_session.py:16,81`). See S1 |
| (2) Classification, jitter, bounds | PARTLY | full jitter, `Retry-After` as a floor with a ceiling, attempt and time bounds: right. "Never 403": S1 |
| (3) Breaker and cross-run state | PARTLY | S2, S3, S4 |
| (4) Deferred leaves everything untouched | PARTLY | S5 |
| (5) Groww hand-run market-hours rule untouched | MET | gap list, last line |
| (6) Claims 1-8, gap list | PARTLY | Claim 8 (a static test of the allowed `sleep` sites) is a good guard |

## Findings

1. **S1: "never retry 403" breaks Drive.** Google sends its rate limit as **403** with reason `rateLimitExceeded`,
   and today's `DriveSession` correctly retries it. A single global rule, tested as claim 1, would turn every Drive
   rate-limit answer into a permanent failure. Fix: make the classification part of each source's configuration (NSE:
   403 means blocked, never retry; Drive: 403 with a rate-limit reason is transient), and add the Drive row to the
   table and to the claim-1 test.
2. **S2: the breaker must not loosen today's NSE protection.** Today two refusals in a row (403/429) pause an NSE host
   (`http_pacing.py`, `REFUSALS_BEFORE_PAUSE = 2`). The proposal "N = 5 consecutive failures" lets NSE be hit 2.5 times
   as often once it starts refusing. Fix: the threshold depends on the outcome kind and the source (for NSE, 403/429
   open after 2, as today). State that **404 / not published never counts** as a breaker failure, or every holiday or
   unpublished day trips it. "Configure with today's numbers first" must include this one.
3. **S3: the half-open probe needs two rules, or it is the hammering it should prevent.**
   (a) A probe is **one request with no retries**. If it goes through `RetryPolicy`, a "single probe" is up to 4
   requests to a blocking host.
   (b) **Grow the cool-down on each re-open** (for example doubling, up to a cap such as 24 h). With a fixed 30 minutes
   and 13 workflows on cron, an IP block lasting days gets a probe from almost every scheduled run.
   Also say that runs at the same time may each probe once: at most one per run per source, which is acceptable.
4. **S4: cross-run state, three holes.**
   (a) Several workflows call the same hosts (about 10 for NSE), and each appends to the transition CSV and pushes with
   `git pull --no-rebase`. Two appends at the end of one file conflict, the push fails, and the state is lost. The repo
   already solves this: `.gitattributes` `merge=union` for append-only logs. Name it for the new CSV.
   (b) If the log commit fails, the open state never reaches the next run. Say what then happens, and alert on it.
   (c) Per-day budgets (Groww's 150 sign-ins a day; "at most 3 attempts a day" today) are counted in memory if
   `RateLimit` holds them, which means per run, not per day. Persist them like the breaker state (an append-only ledger,
   as `attempt_log.py` does) or label them per-run only.
5. **S5: "no partial data" needs two precise statements.**
   (a) It holds **per file**: in a multi-day run, days written before a `Deferred` stay written (correct, because each
   is complete and write-once). Say so, so nobody reads it as rollback.
   (b) A retry around a Drive upload must keep today's idempotency. `GoogleDriveUploadStore` pre-reserves the file ID
   and treats `409 ID in use` as "our earlier attempt got through", then verifies the bytes
   (`google_drive_upload.py:60-67`). That is what stops a retried POST from making a **duplicate** file. The shared
   policy must wrap the call without dropping it; add a claim and a test (a timeout after a successful create, retried,
   gives one file).

## Notes

- Labelling the numbers as owner placeholders (reasoning only) is right.
- The rejected Drive-state alternative is correctly reasoned: Drive stores cannot overwrite raw files, and a Drive write
  on a failure path is a poor fit.
