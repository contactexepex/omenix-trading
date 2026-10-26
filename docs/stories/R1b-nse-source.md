# R1b: the NSE downloads onto the shared resilience layer

Lane 1, two judges (NSE, the schedules that call it, and code the live workflows run). Branch `story/R1b-nse-source`.
**Story text only; no code until it is judged.** Round 2 (round 1: both judges FAIL on `b9ef26a`, every finding checked
against the code and accepted, see "Round 1 findings"). The rules are in [R1-resilience.md](R1-resilience.md) (one
functionality, one owning document); this file says only how R1b applies them. R1a, the library
(`fno/shared/resilience/`), is merged (`cde3b2f`); R1b adds one small method to it, flagged for the judges below.

## Where the layer sits (revised: it stays where the pacer is today)

Today the pause lives in the **session**: `PacedSession` asks `SHARED_PACER.wait_turn(host)` before every request and
tells it `observe(host, status)` after, for every NSE caller (archive files, `nse_json`, circulars, the Stager). Callers
then decide what to retry. R1b keeps exactly that split, so no caller's classification changes:

| Piece | Today | After R1b |
|---|---|---|
| Spacing, refusal count, pause | `RequestPacer`, one `SHARED_PACER` per process, **per host** | `NsePacer`, same two methods, one shared instance per process, per host: a `RateLimit` (1 s) and a `CircuitBreaker` (2 refusals, 15 min) for **each** of `www.nseindia.com` and `nsearchives.nseindia.com`, never one "nse" |
| What counts | `observe`: 403/429 count, any other answered status resets | the same, through `record_refusal` / `record_other` |
| A paused host | `wait_turn` raises `SourceCoolingOff` | the breaker's `Deferred` is converted to `SourceCoolingOff` at this one point, so `NseArchiveSource`, the librarian, the stager and `nse_json` see the exception they see today |
| After the 15 minutes | the door opens for everyone at once | **one probe**, then open (below) |
| Archive-file retry loop (`NseArchiveSource._response`, `retry_policy.py`) | own loop, waits 5/15/45 | `RetryPolicy.run` with today's `verdict()` as the classifier (403 and other refusals: stop, never retry; 404 not published; 429 and 5xx retry); the second 429 in a row still ends the call at once |
| `PublicData.nse_json` | 3 tries, `1.5 * n` s, cookie warm-up after a failure | its **own** classifier: every non-200 or empty answer, a 403 included, is RETRY after the warm-up (NSE refuses a cookie-less first call by design); waits 1.5/3.0/4.5 as floors **including the last** (kept; see below) |

Not in R1b: Drive (R1c), Groww and the rest (R1d), the promotion gate, `circulars` (it uses `PacedSession` directly and
gets the session-level changes only).

## The probe (revised: never stricter than today for data)

After the cool-down the first `wait_turn` is admitted as the probe and everything else on that host is refused
(`SourceCoolingOff`, "probe in flight") until its answer: one request instead of a flood. Its answer is treated as the
pacer treats answers today, with one addition:
- 403 or 429: re-open, cool-down doubled (cap 24 h);
- **any other answered status, 5xx included: close.** Today the pacer ignores 5xx, and one morning 503 must not push
  `index-closes` past its 07:41 retry (judge 2, S2);
- no answer (timeout, connection error): re-open with the **same** cool-down (not doubled).

**Library addition (flagged, touches merged R1a):** `CircuitBreaker.record_unanswered()`: from half-open back to open
for the same cool-down, logging a `reopened` row; a no-op in any other state. Tests and a mutation plant come with it.
**Stated difference from today:** during the one request in flight the other threads of the process are refused where
today all would have proceeded; the window is one request, never longer.

## Dropped: the "differences" of round 1

Withdrawn: dropping `nse_json`'s last wait (a 5xx storm would otherwise get about ten times the rate: the gap
between failing calls would fall from 4.5 s to 0.4 s). It stays. Differences that remain, all deliberate: upward jitter
on the archive waits (never shorter); the one-probe rule above; jitter is capped at 25% for NSE (below).

## Worst case against every workflow timeout (computed; code references from a read of the code)

One archive fetch, every try failing with 5xx or a timeout: today 3 waits (65 s) + 4 × 60 s request timeouts = **305 s**.
Jitter 0.25 (waits `[t, 1.25 t]`): 81 + 240 = **321 s** (+5%). With jitter 1.0 (the library default) it would be 370 s
(+21%), which is why NSE gets 0.25: the library's `RetrySettings` gains a `jitter` fraction (default 1.0, validation
`cap >= (1 + jitter) * max wait`), NSE sets 0.25. A `Retry-After` is bounded by 120 s either way (600 s per fetch, same as today).

| Workflow (timeout) | Max NSE fetches per run (code) | All-fail worst case today / after | Verdict |
|---|---|---|---|
| flows-download (15 min) | 1 fetch (`snapshot_source.py:104`) | 305 s / 321 s | fits |
| fo-masters (20) | 2 fetches (`fo_masters/wiring.py:38-41`) | 610 s / 642 s | fits |
| vix-history (30) | 2 fetches (`vix_history/cli.py:91-98`) | 610 s / 642 s | fits |
| participant-oi-watch (15) | 6 fetches (`release_times.py:45,184-191`) | 1830 s / 1926 s | **does not fit today (900 s) and does not after**; a pre-existing exposure |
| circulars (15) | 1 list GET, no retry, plus one download per new circular, **unbounded in code** | list 60 s; downloads data-dependent | **pre-existing, unbounded** |
| index-closes (60) | the librarian pass ends at its first `RawSourceUnavailable` (`librarian.py:58-86`: the fetch raises out of `fill`): 1 fetch; the sweep records an unavailable file and goes on, stopping only on cooling-off (`revision_source.py:59-67`): up to 6 sessions = 6 fetches; 7 in all | 2135 s / 2247 s | fits |
| flow-history (60) | 2 librarian passes (1 fetch each) + 2 sweeps (6 each) = 14 fetches | 4270 s / 4494 s | **does not fit today (3600 s) and does not after**, if every file fails every try with 5xx or timeouts; a pre-existing exposure |
| pipeline-staging (60) | 4 × sessions in the range; `DAYS` has **no cap in code** | data-dependent | unchanged in kind |
| quote-recorder-nse (90) | window-limited (14:55 to 15:10, one attempt a minute); about 242 `nse_json` GETs and about 190 archive requests at most | bounded by the window | unchanged in kind |

Honest reading: the workflows that cannot fit today cannot fit after (participant-oi-watch, circulars, flow-history). R1b widens the
worst case by about 5% and fixes none of that. A timeout skips the workflow's commit step. R1b does not add a
run-level retry budget (that would be new code and a new rule); it is recorded as a gap for the owner (`go-live list`)
and R1b proposes, as a separate small story if wanted, a per-process retry budget. The judges decide whether this is
acceptable for R1b; the numbers are here so they need not recompute them.

## Characterization contract

`tests/characterization/` (on `main`: `b8492fe` and `b3253e6`) pins today's behaviour: 42 tests. The refactor keeps
them green with exactly one adaptation: the source and pacer take their `RetryPolicy` by injection, as they take sleep
and clock today, and the tests pass a zero-jitter policy so waits read 5/15/45 and 1.5/3.0/4.5. A separate new test proves
the live policy's waits lie in `[t, 1.25 t]`. Any other change to an assertion fails the story.

## Claims and how each is shown

1. Same classification: every status the old `verdict()` maps stays mapped; unbuildable requests; `nse_json` retries
   every non-200 including a 403 after one warm-up (the pinned test).
2. Same stop rules and exceptions: the second 429 in a row ends the call; 403 and other refusals never retry;
   `Retry-After` above 120 s ends the call; **`Deferred` reaches callers only as `SourceCoolingOff`, which
   `NseArchiveSource` turns into `RawSourceCoolingOff` with the same `tries`, so `RawFileRefused`, `RawSourceUnavailable`,
   `RawSourceCoolingOff` and "not published" are unchanged** (a test per exception, message text included).
3. Never weaker: pause at two 403/429 in a row for 15 minutes **per host**; any other answered status resets; a 404
   between two 403s resets; the warm-up's 200 resets (pinned).
4. One process-wide pacer: two `PacedSession`s share one `NsePacer`; a refusal seen by one pauses the other (a test, as
   `SHARED_PACER` today).
5. Per host: a pause on `www.nseindia.com` does not stop `nsearchives.nseindia.com` and the reverse; spacing is per host.
6. The probe: one request after the pause, with the three answers above; eight threads get exactly one probe
   (a concurrency test); 5xx closes it; a timeout keeps the same cool-down.
7. One builder: after R1b the loop in `_response`, `RETRY_WAITS` in `retry_policy.py` and `RequestPacer` are gone;
   `retry_policy.py` keeps `verdict` and `retry_after_seconds`. A static test lists the `sleep(` sites.
8. Deferred writes nothing: when the pause defers a fetch, the stager and library leave Staging, Record, manifests and
   receipts untouched (spy store, zero writes).

## Two steps

**R1b1, same behaviour in the same process:** everything above; the breaker has no log, so the pause lives in the
process exactly as today. **R1b2, memory across runs:** the breaker's transition log
(`research/data/resilience/nse.csv`, `merge=union`, already in `.gitattributes`) committed by each NSE workflow with its
other outputs, and breaker alerts to #fno-desk. That edits all NSE workflows, so it is its own judged step.

## Verification (honest; no claim that `--help` proves anything)

The `dry_run` of `index-closes.yml` and the other workflows runs only `--help` (e.g. `index-closes.yml:52-57`): it sends
no NSE request and **does not exercise this code**. It proves nothing here and is not used.
1. **Build-time (primary safety):** all characterization tests green, the new tests, and mutation plants on the new code.
2. **Strongest real proof, owner-gated:** a stage-only `pipeline-staging` dispatch (participant-oi) at the owner's
   validation step. It runs the refactored NSE fetch layer on the real runner and writes only to reversible Staging.
   It is on the go-live list and is not run before the owner's go.
3. **Interim, after each of R1b1 and R1b2 merges (both change live code):** the next scheduled run of every affected
   workflow is the real test, and an **active** check is made, not "no alert came" (alerts fire only on breaker
   transitions and exhausted retries, so a silent regression would raise none): the session that merged the step reads
   that run's log and compares it with the previous run's: exit code, per-day counts and statuses (saved, not
   published, refused), the wait pattern. **Stop rule:** any divergence that is not explained by NSE's data (a file
   reported "not published" that the previous run saved, a changed exception, a breaker that opened without two
   refusals, a run longer than its predecessor by more than the jitter allows) means the step is reverted at once and
   reported. The data stays consistent meanwhile: a deferred fetch writes nothing.

## Round 1 findings (each checked and accepted; evidence in the sections above)

Judge 1: B1 verification plan (accepted: `--help` only, `index-closes.yml:52-57`); per-host keys (accepted:
`http_pacing.py:38-39`); worst-case table (accepted, above); keep `nse_json`'s last wait (accepted). Judge 2: B1
`nse_json` retries a 403 after warm-up (accepted: `public.py:46-55`, now pinned); S1 last wait (accepted); S2 probe
treatment of 5xx and timeouts (accepted); S3 one instance per process (accepted); S4 timeouts (table above); S5 exceptions
(claim 2). Orchestrator's refinement: an active log comparison (accepted, step 3).

## Judges

Two judges. Freeze rule: one SHA, no push after sending it.
