# R1b: the NSE downloads onto the shared resilience layer

Lane 1, two judges (NSE, the schedules that call it, and code the live workflows run). Branch `story/R1b-nse-source`.
**Story text only; no code until it is judged.** Round 2 (round 1: both judges FAIL on `b9ef26a`, every finding checked
against the code and accepted, see "Round 1 findings"). The rules are in [R1-resilience.md](R1-resilience.md) (one
functionality, one owning document); this file says only how R1b applies them. R1a, the library
(`fno/shared/resilience/`), is merged (`cde3b2f`); R1b adds one setting to it (`jitter`), flagged for the judges below.

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

After the cool-down the first `wait_turn` is admitted as the probe. Every other `wait_turn` on that host **blocks until the
probe's answer** (bounded by that request's timeout: 20 s for `nse_json`, 60 s for a file) and then proceeds if the probe
closed the breaker, or gets `SourceCoolingOff` if it re-opened it. One request is in flight, nobody is turned away
for the probe's sake, and no thread loses its quote or its file to a probe that succeeds (judge 2, R2-1: the 14:55 to
15:10 quote window runs three index threads through `nse_json`). The probe's answer is treated as the pacer treats
answers today, with one addition:
- 403 or 429: re-open, cool-down doubled (cap 24 h); the waiting callers get `SourceCoolingOff`;
- **any other answered status, 5xx included: close.** Today the pacer ignores 5xx, and one morning 503 must not push
  `index-closes` past its 07:41 retry (judge 2, S2);
- **no answer (timeout, connection error): close, too.** Today a transport failure never reaches `observe()`, so after
  the 15 minutes the door is open whatever the next request does; a timeout is no evidence of a block, and a probe that
  re-paused the host on one would defer data today's code reads (judge 1, round 2, item 1; this replaces my earlier
  "same cool-down" rule, taken from judge 2's S2, and withdraws `record_unanswered`).

**Waiters.** The waiters released by a closing probe still pass through the per-host `RateLimit`, so they start one second
apart as every NSE request does (the test asserts the gaps). **If a waiter's bounded wait expires** (the probe thread is
stuck past the request timeout), the waiter treats the probe as unanswered: the host is closed and it proceeds as a normal
call. **If the probe thread raises** (any exception, not only a request error), the release of the waiters is in a
`finally`, so none is left blocked.

**Where the waiting lives:** in `NsePacer` (a condition per host, under the pacer's lock), not in the library: the library's
`check()` still refuses while a probe is out, and `NsePacer` turns that into a wait. The **only** library edit is the
`jitter` fraction in `RetrySettings` (flagged: it touches merged R1a), with tests and a mutation plant.

**Data cost, stated:** the probe never defers data that today's code reads, except after a 403 or 429, where the pause
exists to defer it: a timeout, a 5xx or any other answer closes the host. Threads waiting on a probe that is then refused
(403 or 429) are refused too; that is more cautious than today (each would have met the refusal in turn and the pause
would have come back after two). On a successful probe nothing is lost.

**Stated difference from today:** after a pause, the first request goes alone and the others wait for its answer (at
most one request timeout) before they start; today all would have gone at once.

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
6. The probe: one request after the pause, with the answers above. Three threads, a 200 probe: all three complete
   and exactly one request went before them; a 403 probe: all three get `SourceCoolingOff` and only one request was sent
   (concurrency tests, asserting the 1 s gaps between the released threads); 5xx and a timeout both close it; a waiter
   whose wait expires proceeds; a probe thread that raises releases the waiters.
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
   published, refused), and the tries and waits per fetch (not the run's duration, which varies with NSE). **Stop rule:** any divergence that is not explained by NSE's data (a file
   reported "not published" that the previous run saved, a changed exception, a breaker that opened without two
   refusals, tries or waits outside the table values and the 25% jitter) means the step is reverted at once and
   reported. The data stays consistent meanwhile: a deferred fetch writes nothing.

## Round 1 findings (each checked and accepted; evidence in the sections above)

Judge 1: B1 verification plan (accepted: `--help` only, `index-closes.yml:52-57`); per-host keys (accepted:
`http_pacing.py:38-39`); worst-case table (accepted, above); keep `nse_json`'s last wait (accepted). Judge 2: B1
`nse_json` retries a 403 after warm-up (accepted: `public.py:46-55`, now pinned); S1 last wait (accepted); S2 probe
treatment of 5xx and timeouts (accepted); S3 one instance per process (accepted); S4 timeouts (table above); S5 exceptions
(claim 2). Orchestrator's refinement: an active log comparison (accepted, step 3).

## Judges

Two judges. Freeze rule: one SHA, no push after sending it.

## R1b1 build evidence

Branch `story/R1b1-nse-layer`. In-process only; no workflow change; no breaker log (R1b2).

- **Code:** `fno/shared/nse_pacer.py` (`NsePacer`: per host a `RateLimit` and a `CircuitBreaker`; the waiters; the probe),
  `fno/shared/http_pacing.py` (`PacedSession` tells the pacer of an unanswered or raising request in a `BaseException`
  handler; one `SHARED_PACER`), `NseArchiveSource` over `RetryPolicy` (`_Answers` classifies; `_raised` maps to today's
  exceptions), `PublicData.nse_json` on `RetryPolicy.wait_before` (loop kept: warm-up, every non-200 retried, the last
  wait kept), the `nse_json` settings, and the one library edit: `RetrySettings.jitter` (NSE 0.25). `record_unanswered`
  was withdrawn with the design change; nothing else in the library changed. `RequestPacer`, `RETRY_WAITS` and
  `MAX_RETRY_AFTER_SECONDS` are gone from `fno/` (a test checks); `tools/nse_raw_download/` keeps its own copy (a
  standalone tool outside `fno/`, not on any workflow path; listed for R1e).
- **Characterization contract:** all 42 NSE tests unchanged except the adaptations the story names: the source and
  `PublicData` take a zero-jitter `RetryPolicy` (`run()` and `client()` helpers), the pacer tests construct `NsePacer`
  with `clock` and `sleep` (the old `RequestPacer` had `clock=` and a `.sleep` attribute), and `COOL_OFF_SECONDS` is the
  literal 900 (the constant is gone; the settings test pins 900, 2, 5/15/45 and 120).
- **New tests** (`tests/ingestion/test_nse_pacer.py`, 13; `test_runs.py` +1; library +3): one probe goes alone and a good
  answer releases three threads one spacing apart and promptly; a 403 and a 429 probe refuse all three with one request
  sent and the doubled cool-down; a 5xx, a 404 and no answer close the host; a waiter whose wait expires goes ahead and
  closes the host; a probe that raises releases the waiters; the loser of the race to be the probe waits (a barrier
  makes the race certain); hosts are kept apart; one pacer per process; the cooling-off message text; the live archive
  policy's waits lie in `[t, 1.25 t]`; a paused host defers a whole stage pass and writes nothing (claim 8).
- **Mutation plants** (each caught, a hang counting as caught): no waiting, an unbounded wait, a waiter expiry that does
  not close, an unanswered probe that re-opens, one key for both hosts, a pacer per session, no release when the probe
  raises, no wake-up after an answer, the race, `nse_json`'s last wait dropped, its 403 not warmed. Two survived at first
  (the race, and the wake-up, which waiters covered by timing out) and were closed with a barrier test and a
  promptness assertion.
- **Data cost, as the story states:** a probe never defers data today's code reads except after a 403 or 429.
- **Gates:** ruff, `check_imports`, `check_numbers`, size test clean; 431 tests pass.
- **Not in this step:** claim 7's static `sleep(` allowlist (the old loops are gone from the NSE path; the allowlist
  test arrives with R1c/R1d when the last loops move), the transition log and alerts (R1b2).

### R1b1 round 2 (judge 2, round 1 on 9034093: one should-fix, two minors; each checked and accepted)

- **S1 hang -> fail:** the threaded tests are now bounded: threads are daemons, every join has a timeout and asserts
  `not is_alive()`, and calls that could block run through `run_bounded` (fails after 10 s instead of hanging pytest).
  Shown on the plants judge 2 named: an unbounded wait (P2) and an expired wait that leaves the host half-open (P12) now
  each **fail one test in about 13 s** (before: the suite hung); "waiters do not wait" fails in under a second.
- **Minor 1:** `observe()` set the cooling-off message after the breaker had opened, so a thread refused in that window
  raised `SourceCoolingOff("")`. The status is now recorded before the breaker can open and the message is built when it
  is raised, from the breaker's current cool-down. A test forces the window; with the order reversed it fails.
- **Minor 2:** `COOL_OFF_SECONDS == 900` is listed as an adaptation above (the constant is gone; the 899/901 behaviour
  tests still pin the 15 minutes, and the settings test pins 900).
- Carried to R1b2: the breaker clock is `EPOCH + monotonic`, wrong for a log shared across processes; R1b2 uses real UTC
  (a restored breaker also has no refusal status, so its message is built from the log's cool-down alone).
- Gates: ruff, imports, numbers, size clean; 432 tests pass.
