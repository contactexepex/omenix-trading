# R1: one resilience layer (retry, circuit breaker, pacing, no partial data)

Lane 1, two judges (outside services: NSE, Drive, Groww and new sources; the write-once data they feed). Branch
`story/R1-resilience`. **Design only; story text.** Owner directive (26 Oct 2026, via the orchestrator): failures retry
politely and never get us blocked, for every source, existing and new. Build is a separate step after this text is
judged and after V1 (the stage-only validation) has proven the foundation on real data.

## What exists today (measured in the code, not assumed)

| Where | What it does | Gap |
|---|---|---|
| `fno/ingestion/storage/retry_policy.py` + `raw_source.py` (NSE files) | retries no-connection, timeout, cut answer, 429, every 5xx, waits `(5, 15, 45)` s, at most 4 tries; honours `Retry-After` up to 120 s; 403 and other statuses are never retried | fixed waits, **no jitter**; the rule lives in the NSE source only |
| `fno/ingestion/storage/drive_session.py` (Drive) | re-signs in once on 401; retries `{429, 500, 502, 503, 504}` with waits `(2, 8, 30, 60)` s | a **second, different** retry rule; no jitter; no Retry-After |
| `fno/shared/http_pacing.py` `RequestPacer` | one request per second per host (NSE hosts); after **two refusals (403/429) in a row** the host is paused 15 minutes | **in-process only**: every scheduled run is a new process, so the pause is forgotten and the next run calls the host again |
| `fno/ingestion/providers/groww_rate_guard.py` | after a 429, pauses Groww reads for 60 s | Groww-only; the budgets (10/s, 300/min, 150 sign-ins/day) are not modelled as a budget |
| `global_cues/attempt_log.py` | at most 3 attempts per source per IST day | per-feature, not general |
| `intraday/deferral_log.py` | records sessions a back-fill put off | the only "defer" record, used by one feature |
| `promotion/runs.py` `Stager` | a failed fetch writes nothing; a refused file is reported | no breaker: a blocking source is tried again on every run |

So the pieces exist but as **at least four separate retry rules, no jitter, and no memory between runs**. The harm to
avoid is not one slow retry; it is a source that is refusing us being called by every hourly run.

## Design (build, after acceptance and after V1)

One package, `fno/shared/resilience/`, behind interfaces (SOLID; one new class plus one line in a composition root swaps a
policy). Time, sleep and randomness are injected, so every test is deterministic.

1. **`RetryPolicy` (strategy)**: classifies an outcome as `RETRY`, `PERMANENT` or `OK` and gives the wait. Retries only
   transient errors (no connection, timeout, truncated answer, 429, 5xx); **never** 404 (not published), 403 or other
   4xx, parse or auth failures. Wait = **exponential backoff with full jitter**: a random wait in `[0, min(cap, base *
   2^n)]`; `Retry-After` (seconds or HTTP date) is a floor and is honoured, and above a ceiling the call stops (as
   `MAX_RETRY_AFTER_SECONDS` does today). Bounded by **max attempts and max total time**. The NSE rule and the Drive rule
   become two configurations of this one policy (their current limits are the starting point), not two codebases.
2. **`CircuitBreaker` per source**: closed -> open after N consecutive failures (or a failure rate over a window);
   while open, calls **fail fast without touching the source**; after a cool-down it goes half-open and lets **one probe**
   through; success closes it, failure re-opens it. The breaker absorbs `RequestPacer`'s two-refusals pause.
   **Cross-run memory** (the real gap): transitions (opened, closed) are appended to a small CSV committed with the run's
   other logs, the existing pattern (`research/data/participant_oi/release_checks.csv`); a new process reads it, so an
   open breaker stays open across hourly runs until its cool-down passes. Only transitions are written, not every
   failure, so it is not noisy. *Alternative (Drive state file) rejected for now: Drive stores cannot overwrite raw files,
   and it would add a Drive write to a failure path.*
3. **`RateLimit` strategy behind `fno/shared/http_pacing`**: per-host budget (minimum spacing, per-minute, per-day), so
   `RequestPacer`'s 1 s spacing, Groww's 10/s, 300/min and 150 sign-ins/day, and polite defaults for news, BSE and Yahoo
   are values of one strategy, not four modules. A budget that is spent makes the call wait (or defer if the wait would
   pass the window), never spill over.
4. **Consistency, no partial data**: a fetch that fails after retries, or meets an open breaker, raises one
   `Deferred(source, reason)`; the caller writes **nothing** (Staging, Record, manifests, receipts) and reports the day as
   deferred. The next scheduled run retries. The existing `DeferralLog` pattern is generalised to carry these rows, so a
   stuck day stays visible (no automatic void, as today). A response whose length differs from `Content-Length`, or that
   fails the content check, is a failed fetch, not a smaller file.
5. **Alerts**: to #fno-desk only (`FNO_SLACK_BOT_TOKEN`, `AlertSender`), **one line per breaker transition** (open and
   close), never one per failed call and never to the market-brief channels.

## Numbers are the owner's to confirm

N consecutive failures, the failure-rate window, the cool-down, the backoff base and cap, and the max total time are
**placeholders until the owner decides** (as freshness windows were). Proposal, *reasoning only, no data*: N = 5
consecutive failures, cool-down 30 minutes, backoff base 2 s, cap 60 s, max total 5 minutes per call. They live in one
config block (`resilience:` in `config.yaml`, an allowed key with a test) so changing them touches no code.

## Claims (what a judge can check once built)

1. Retries happen only for transient errors, never for 404, 403, other 4xx, or parse and auth failures (table-driven
   test per status and exception type).
2. Waits follow full jitter within the cap; `Retry-After` is honoured as a floor; the call stops at the attempt and total
   time limits (deterministic clock, sleep and random).
3. The breaker passes closed -> open -> half-open -> closed and half-open -> open in tests; while open a call raises
   `Deferred` and **sends no request** (a spy session sees none); exactly one probe goes through in half-open.
4. A breaker state survives a new process through the transition CSV (write, new instance, read).
5. Pacing: with a spent budget a call waits or defers and never exceeds the host's limits (a per-second, per-minute and
   per-day case each).
6. Consistency: a fetch that ends in `Deferred` leaves Staging, the Record, manifests and receipts byte-identical (a test
   with spy stores asserts zero writes), and the Stager reports the day as deferred.
7. One alert per transition (spy sender), only to the #fno-desk sender.
8. The NSE source, the Drive session and the Stager use the shared policy and breaker; no other module holds its own copy
   of a retry loop (a static test lists the allowed `sleep` call sites, as SEC1's scanner does for installs).

## Build in steps, each judged (so no step is too large)

R1a the library and its tests; R1b NSE source, `RequestPacer` and the Stager on it; R1c Drive session; R1d Groww guard and
global cues; R1e the new-source adapters when those sources exist. Existing behaviour is preserved by configuring the
policy with today's numbers first; changing a number is a separate, visible config change.

## Gap list

- **Not built before V1** proves the staging path on real data; **no new sources** here (Phases 2-5 are on hold).
- The failure-rate breaker (vs consecutive failures) is specified but may ship as consecutive-only first; the story says
  which at build time.
- A source that blocks by IP for days is outside what a breaker can fix; the alert and the deferral log make it visible.
- GitHub's runner IPs are shared and not ours to rotate; politeness (spacing, backoff, identity) is the only lever.
- Groww calls stay inside the hand-run market-hours rule (`CLAUDE.md`); this layer does not relax it.
