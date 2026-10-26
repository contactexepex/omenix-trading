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

## Addendum 1: round 2, `8ffc937342eb65319b39285dac71e656fa3b013b` (my last round on the R1 story)

**FAIL**, on 2 should-fix, both cases where the text breaks its own rule "R1 is never weaker than today". After two
rounds the owner decides, via the orchestrator. Every round-1 finding is fixed:

| Round-1 finding | Verdict | Evidence (round-2 text) |
|---|---|---|
| S1 403 per source | FIXED | design 1: NSE 403 = BLOCK; Drive 403 with a rate-limit reason = RETRY; the 401 re-sign is outside the policy |
| S2 thresholds | FIXED (except R2-2) | NSE 2; 404 never counts; the global N = 5 withdrawn |
| S3 half-open probe | FIXED | one request outside the retry policy; the cool-down doubles to a cap and resets on a close |
| S4 cross-run state | FIXED | one CSV per source, `merge=union`, failure modes stated (fails open, commit failure reported and alerted); per-day budgets in the `attempt_log` ledger; claims 4 and 5 test them across two processes |
| S5 no partial data | FIXED | per file, not rollback; `_fresh_child`, the pre-reserved ID and 409 kept; claim 6 "exactly one file" |

The sleep-site inventory and the equal-jitter reasoning (full jitter can wait 0 s) are good additions.

### Findings

1. **R2-1 (should fix): equal jitter as written can still wait less than today.** Wait = `d/2 + random(0, d/2)` with
   `d = min(cap, base * 2^n)`. If "today's numbers are the first configuration" means base = 5 s (NSE), the first wait
   falls in **[2.5, 5] s, below today's fixed 5 s**. Doubling also gives d = 5, 10, 20 s, against today's 5, 15, 45 s;
   Drive's are 2, 8, 30, 60 s. Fix: make today's wait table the **floor** and jitter only upward. For example, wait_i
   in `[today_i, 2 * today_i]` (NSE 5-10, 15-30, 45-90 s, capped). Or state a base and growth factor whose lower bound
   is at least each of today's waits, and test that lower bound per attempt.
2. **R2-2 (should fix): NSE 429 counts less strictly than today.** Today **any two consecutive refusals, 403 or 429,
   from one NSE host** pause that host for the whole process (`http_pacing.py:53-61`, `REFUSAL_STATUS_CODES = (403,
   429)`). Under R1, NSE 429 = RETRY, and the breaker counts only "BLOCK or exhausted-retry" outcomes. So a 429 storm
   is retried up to 4 times per file, and the breaker opens only after 2 files exhaust: **up to 8 answers of 429 before
   opening, against 2 today**. Fix: for NSE, every 429 response counts toward the breaker (threshold 2, as today),
   whether or not the retry policy would retry it. A 429 then retries at most once before the host opens. Add a
   claim-3 test: two 429s in a row open the NSE breaker and the second retry is not sent.

## Addendum 2: delta check, `163011b05d0158b5f293a23b188a0cd9f94c8b56` (at the orchestrator's discretion, after round 2)

**PASS** on the R1 story, lane 1, judge #2. The delta from `8ffc937` is story text only, and it fixes both round-2
findings:
- **R2-1: FIXED.** Design 2 keeps each source's own table as a floor and adds jitter only upward: the wait before try
  *n* is `t_n + random(0, t_n)`, so in `[t_n, 2 t_n]` (NSE 5/15/45, Drive 2/8/30/60; tables, not `base * 2^n`). Claim
  2 asserts the lower bound per attempt and per source. A new source starts from its own doubling table.
- **R2-2: FIXED.** For NSE, every 403 and 429 response counts, as `RequestPacer.observe` does today. The second in a
  row opens the breaker and ends the call. The cited current behaviour holds: `raw_source.py:165-167` counts
  consecutive 429s and stops on the second. Claim 3 tests that two consecutive 429s open the breaker and no third
  request is sent.
- **Also:** the stated limit of the sleep-site test (a wait under another name, e.g. `numbering/claim.py`'s `pause`,
  is allowlisted with its reason and checked by hand) is honest.

The build (R1a-R1e) is judged separately, after V1, with plants on the jitter floor and the NSE 429 rule first.
