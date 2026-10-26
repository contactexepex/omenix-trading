# R1: one resilience layer (retry, circuit breaker, pacing, no partial data)

Lane 1, two judges (outside services: NSE, Drive, Groww and new sources; the write-once data they feed). Branch
`story/R1-resilience`. **Design only; story text.** Round 2 of the story (round 1: both judges FAIL on `2d6ea2a`, one
blocking and ten should-fix, all checked against the code and accepted below). Owner directive (26 Oct 2026, via the
orchestrator): failures retry politely and never get us blocked, for every source, existing and new. Build starts only
after this text is judged and the stage-only validation (V1) has passed on real data.

**The rule that governs every line below: R1 is never weaker than today for any source.** It consolidates the existing
rules into one interface and adds jitter, a half-open probe, memory across runs and alerts; it relaxes no protection
that exists now. Where an idea would loosen one (a global threshold, "never retry 403", full jitter), it is changed.

## What exists today (measured in the code)

### The retry, pacing and breaker rules, per source

| Where | Today | Kept / changed by R1 |
|---|---|---|
| `storage/retry_policy.py` + `raw_source.py` (NSE files) | retry no-connection, timeout, cut answer, 429, every 5xx; waits `(5, 15, 45)` s, at most 4 tries; `Retry-After` honoured up to 120 s; **403 and every other status never retried**; 404 = not published | same limits as configuration of the shared policy |
| `shared/http_pacing.py` `RequestPacer` | 1 request/s per NSE host; after **two** consecutive 403/429 the host is paused 15 min (`REFUSALS_BEFORE_PAUSE = 2`), no half-open probe, **in-process only** | becomes the NSE breaker: threshold stays **2**, cool-down starts at 15 min, adds one-request half-open and memory across runs |
| `storage/drive_session.py` (Drive) | one re-sign-in on 401; retries `{429, 500, 502, 503, 504}` **and Google's 403 `rateLimitExceeded` / `userRateLimitExceeded`** (`_rate_limited`), waits `(2, 8, 30, 60)` s | same classification (a 403 with a rate-limit reason **is** retryable on Drive); the 401 re-sign stays and **is not a policy retry** (it does not count toward attempts or the breaker) |
| `storage/google_drive_upload.py` | a create is retried safely: the file ID is reserved first and a repeat answers 409 `fileIdInUse`; `put` re-checks (`_fresh_child`) before creating | kept as is; the policy never retries a create without these |
| `providers/groww_rate_guard.py` | after a 429 the process pauses Groww reads for 60 s | becomes the Groww `RateLimit` values; budgets below |
| `global_cues/attempt_log.py` | at most 3 attempts per source per IST day (a committed log) | **is** the per-day ledger pattern; reused, not duplicated |
| `intraday/deferral_log.py` | records sessions a back-fill put off | generalised to carry `Deferred` rows |
| `promotion/runs.py` `Stager` | a failed fetch writes nothing; a refused file is reported | unchanged; gains the breaker |

### Every `sleep` site in `fno/` (the inventory Judge 1 asked for)

`grep -rl "sleep(" fno` finds 17 modules (Judge 1 counted 22 counting injected `sleep` parameters); the build's static
test works from the grep and an explicit allowlist, so a site missed here fails the test rather than slipping through.

| Module | What the wait is | Fate |
|---|---|---|
| `storage/raw_source.py`, `storage/drive_session.py` | retry waits (NSE, Drive) | **migrate** to the shared policy (R1b, R1c) |
| `shared/http_pacing.py` | per-host spacing and cool-off | **migrate**: becomes the `RateLimit` and breaker (R1b) |
| `providers/public.py` (`pause`) | spacing between NSE public-site calls | **migrate** to `RateLimit` (R1b) |
| `close_read/reader.py` (`TRY_GAP_SECONDS`) | gap between tries of a close read | **migrate** to the policy (R1d) |
| `quotes/recorder.py` (`RETRY_GAP_SECONDS = 60`), `quotes/indices.py` | retry gap between capture attempts inside a window | **migrate** the gap (R1d); the wait *for the window to open* stays (below) |
| `intraday/pacing.py` (`RatePacer`), `intraday/candle_source.py` (`MIN_GAP_SECONDS`) | a second pacer: Groww request spacing | **merge** into the one `RateLimit` strategy (R1d) |
| `flow_history/nsdl_backfill.py` (`GAP_SECONDS = 10`; one retry per month) | NSDL spacing and retry | **migrate** (R1d) |
| `filings/cli.py` (`PROBE_PAUSE_SECONDS = 30`) | pause between probes of a source | **migrate** (R1d) |
| `intraday/recorder.py` (5 sites) | window waits, plus `ALREADY_PAUSE_SECONDS` | window waits **stay**; retry gaps **migrate** (R1d) |
| `preopen/run.py`, `global_cues/preopen_cli.py`, `quotes/*` start waits, `providers/groww_quiet_windows.py`, `intraday/feed_probe.py`, `research_data/release_times.py` | waiting for a clock time, a quiet window or a poll interval; **not retries** | **stay**, listed in the test's allowlist with the reason "window wait" |

R1 migrates the retry and pacing sites; it does not touch window waits, and the Groww hand-run rule is untouched.

## Design (build, after acceptance and V1)

One package, `fno/shared/resilience/`, behind interfaces; **existing modules are refactored onto it, not paralleled**: a
module in the table above keeps its public interface and delegates, and its own copy of the rule is deleted or becomes a
configuration value. Time, sleep and randomness are injected, so every test is deterministic.

1. **`RetryPolicy` (strategy), classification per source.** Outcomes are `OK`, `RETRY`, `PERMANENT`, `BLOCK`. Each source
   supplies its classifier: NSE: 404 not published, 403 = **BLOCK** (no retry, counts toward the breaker), 429 and 5xx
   and network errors = RETRY; **Drive: 403 with a rate-limit reason = RETRY**, other 403 = PERMANENT, 401 = the single
   re-sign (outside the policy). Never retried anywhere: other 4xx, parse and auth failures, a bad URL.
2. **Backoff with jitter that is never shorter than today's floor.** Wait = `d/2 + random(0, d/2)` with `d =
   min(cap, base * 2^n)` ("equal jitter"). *Deviation from the brief's "full jitter":* full jitter can wait 0 s, which is
   weaker than today's fixed 5 s (NSE) and 2 s (Drive) first wait; equal jitter keeps the lower half. `Retry-After` is a
   floor and honoured up to a ceiling (120 s as today); above it the call stops. Bounded by max attempts **and** max total
   time. Today's numbers are the first configuration; nothing changes until a number is changed in config.
3. **`CircuitBreaker`, per source and per outcome, never looser than today.** Counts consecutive **BLOCK or exhausted-
   retry** outcomes; **404 / not-published never counts**; a success resets. Thresholds are per source: **NSE = 2** (today),
   Drive = its existing give-up behaviour (no new breaker threshold looser than the code now), Groww = a 429 pauses 60 s as
   today; new sources start at NSE-strict (2) until measured. Closed -> open -> half-open -> closed. **The half-open probe
   is exactly one request, outside the retry policy** (a retried probe would be up to four hits on a blocking host).
   **The cool-down grows on each re-open** (doubles from the starting cool-down, 15 min for NSE as today, up to a cap), and
   resets on a close, so a days-long block is not probed by almost every scheduled run.
4. **Memory across runs.** Every run is a fresh process, so an in-process breaker would forget. Transitions only
   (opened, half-open probe result, closed) are appended to **one CSV per source** under `research/data/resilience/`,
   committed with the run's other logs (the `release_checks.csv` pattern), and registered in `.gitattributes` with
   `merge=union` (as the existing append-only logs are) so concurrent runs that append at once keep both sides' rows
   instead of conflicting. Stated failure modes: a lost or uncommitted transition **fails open** (the next run calls the
   source and re-opens on its own failures, bounded by the threshold); a checkout taken before another run's push is
   stale for that run; the "one probe" is per process, so two overlapping runs may probe twice (accepted, bounded); if the
   log commit fails the run says so in its output and alerts, and still honours its own in-memory state.
5. **Per-day budgets** (Groww: 150 sign-ins/day, 10/s, 300/min; global cues: 3 attempts/day) are **persisted** the same way:
   the existing `attempt_log` pattern (a row per attempt, counted by IST day) is the ledger, generalised; a per-second or
   per-minute limit stays in-process (it cannot outlive a minute). Anything not persisted is labelled per-run in the code.
6. **`RateLimit` strategy behind `fno/shared/http_pacing`**: minimum spacing, per-minute and per-day budgets per host;
   `RequestPacer`'s 1 s, Groww's budgets and polite defaults for new sources (news, BSE, Yahoo) are values of it. A spent
   budget makes the call wait, or defer if the wait would pass its window; it never spills over.
7. **Groww**: a sign-in is **never retried blindly** (it counts against the 150/day and is a single deliberate attempt);
   every retry of a read counts against the 10/s and 300/min budgets; **no retry fires between 09:15 and 15:35 IST except
   the scheduled command's own** (`CLAUDE.md`'s hand-run rule is unchanged and not relaxed by this layer).
8. **Writes and consistency.** A retry **re-fetches the full bytes; it never resumes** a partial download. A fetch that
   fails after retries or meets an open breaker raises `Deferred(source, reason)`: the caller writes nothing for that
   file (Staging, Record, manifests, receipts) and reports it; the next run retries. **"No partial data" means per file,
   not a rollback**: a range that completed earlier days keeps them. A response whose length differs from
   `Content-Length`, or that fails its content check, is a failed fetch. **Retried writes are idempotent:** a Drive create
   that times out after succeeding is re-checked before any retry (`put`'s `_fresh_child`; the pre-reserved ID and the
   409 answer are kept); a retry after a successful put but a failed manifest commit takes the gate's re-put path.
9. **Alerts**: #fno-desk only (`FNO_SLACK_BOT_TOKEN`, `AlertSender`), **one line per breaker transition** and one when a
   call exhausts its retries, never one per failed call and never to the market-brief channels.

## Defaults and owner numbers

Shipped defaults are **per source and no weaker than today's code** (NSE threshold 2, cool-down start 15 min, waits and
limits as now). New knobs are the cool-down growth cap (proposal, *reasoning only*: doubling up to 24 h) and the new
sources' starting values (NSE-strict). All live in one `resilience:` block in `config.yaml` (an allowed key, with a
test), so a change is a config change. The global `N = 5` proposed in round 1 is **withdrawn**: it would have loosened NSE.

## Claims (what a judge can check once built)

1. Classification per source (table-driven tests per status): NSE 403 = BLOCK, **Drive 403 `rateLimitExceeded` = RETRY**,
   other Drive 403 = PERMANENT, 404 never counted; the Drive 401 re-sign happens once and is not counted as a retry.
2. Equal-jitter waits stay within `[d/2, d]`, `Retry-After` is a floor, the ceiling stops the call, and attempts and
   total time are bounded (injected clock, sleep and random).
3. The breaker passes closed -> open -> half-open -> closed and half-open -> open; the NSE threshold is 2; a 404 never
   counts; while open a call raises `Deferred` and **sends no request** (spy session); half-open sends **exactly one
   request and does not use the retry policy**; the cool-down grows on a re-open and resets on a close.
4. State survives a new process through the per-source transition CSV (write, new instance, read); two writers that
   append at once merge without loss under `merge=union` (a git test on two clones); a failed log commit is reported.
5. Per-day budgets: the persisted ledger refuses the 151st Groww sign-in of an IST day across two processes; per-second
   and per-minute limits are asserted in-process.
6. A fetch ending in `Deferred` leaves Staging, the Record, manifests and receipts byte-identical (spy stores, zero
   writes); a retried Drive create after a timeout that had succeeded yields **exactly one** file; a retry after a failed
   manifest commit takes the re-put path.
7. One alert per transition and one per exhaustion (spy sender), only through the #fno-desk sender.
8. **One builder, no second rule:** a static test lists the allowed `sleep` call sites (the window waits in the inventory,
   each with its reason); a new retry or pacing loop outside the shared package fails it; the old constants
   (`RETRY_WAITS` in two places, `RETRY_GAP_SECONDS`, `MIN_GAP_SECONDS`, `RatePacer`) are gone or are configuration.
9. No Groww behaviour changes in market hours: the existing hand-run rule tests still pass unchanged.

## Build in steps, each judged (so none is too large)

R1a the library and its tests (no module uses it yet); R1b NSE source, `RequestPacer`, `providers/public.py` and the Stager;
R1c Drive session; R1d Groww pacers, close read, quotes, NSDL backfill, filings probe, global cues; R1e new-source adapters
when those sources exist. Each step preserves today's behaviour first (today's numbers as the configuration).

## Gap list

- **Gated:** no build before V1 (the real stage-only run) passes and both judges PASS this text.
- The failure-rate breaker (over a window) is specified but ships as consecutive-only first; the build story says so.
- A source that blocks by IP for days is outside what a breaker can fix; the alert, the growing cool-down and the
  deferral log make it visible.
- GitHub's runner IPs are shared and not ours to rotate; politeness (spacing, backoff, identity) is the only lever.
- Overlapping runs can probe twice and a stale checkout can miss a transition (stated above, accepted).
- Window waits stay as they are; nothing here makes a hand-run Groww call legal in market hours.
