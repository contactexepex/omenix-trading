# R1b: the NSE downloads onto the shared resilience layer

Lane 1, two judges (NSE, the schedules that call it, and the code the 13 live workflows run). Branch
`story/R1b-nse-source`. **Story text only; no code until it is judged.** The design and the rules are in
[R1-resilience.md](R1-resilience.md) (one functionality, one owning document); this file says only how R1b applies them.
R1a (the library, `fno/shared/resilience/`) is the dependency.

## Scope

Three live pieces move onto the library; nothing else changes.

| Piece | Today | After R1b |
|---|---|---|
| `NseArchiveSource._response` (`storage/raw_source.py`) with `retry_policy.py` | its own loop: waits (5, 15, 45), `Retry-After` up to 120 s, second 429 in a row ends the call | a `GuardedCall` for source `nse`; the classifier is today's `verdict()` (same statuses, same Retry-After rule) |
| `RequestPacer` + `PacedSession` (`shared/http_pacing.py`) | 1 s spacing per host; pause 15 min after two 403/429 in a row; in-process | `RateLimit` (spacing, thread-safe) and `CircuitBreaker` for `nse`; `PacedSession` stays as the one place a request is paced |
| `PublicData.nse_json` (`providers/public.py`) | 3 tries, `time.sleep(1.5 * n)`, 0.4 s pause after a success | one `RetryPolicy` with floors (1.5, 3.0); the 0.4 s pause becomes the source's spacing |

Not in R1b: Drive (R1c), Groww and the rest (R1d), the promotion gate, any workflow YAML.

## Two steps, so each is small and reversible

**R1b1, same behaviour in the same process (no workflow change, nothing persisted).** The breaker has no log, so the
pause lives in the process exactly as today. Differences from today, all deliberate and listed here:

1. Waits gain upward jitter: a wait is its table value plus up to the same again (5 s becomes 5 to 10 s). Never shorter.
2. The 15-minute pause ends with one probe request, not an open door: the first call after the cool-down is a single
   request with no retries; if it is refused the pause doubles (cap 24 h). Today the whole retry loop is let loose.
3. `PublicData.nse_json` no longer waits after its last failed try (today it sleeps 4.5 s and then raises). Reasoning
   only: that wait protects nothing. If a judge prefers it kept, it stays; the characterization test then stays as is.

**R1b2, memory across runs and alerts (lane 1, touches workflows).** The breaker gets its transition log
(`research/data/resilience/nse.csv`, `merge=union`, already in `.gitattributes`), each NSE workflow commits that one path
with its other outputs, and breaker open/close alerts go to #fno-desk. This is a workflow change on all NSE workflows,
so it is its own judged step and its own dry-run check. Until it merges, R1b1 behaves as today across runs.

## What must not change (the contract the characterization tests pin)

`tests/characterization/` (merged, `b8492fe`) pins today's behaviour: 38 tests, 10 hand mutations caught. The refactor keeps
them green with exactly two kinds of adaptation, both stated here and nowhere else:

- The source and pacer take their `RetryPolicy`, clock and sleep by injection, as they do today. Tests pass a zero-jitter
  policy so the waits read 5/15/45 exactly; a separate new test proves the live policy's waits lie in `[t, 2t]`.
- The one behaviour change in R1b1 item 3 changes one assertion (`sleeps == [1.5, 3.0]`), with its reason on that test.

Any other change to a characterization assertion fails the story.

## Claims and how each is shown

1. Same classification: every status the old `verdict()` maps stays mapped (parametrised over 2xx, 404, 429, 5xx, 403,
   418, 451), plus the unbuildable-request class.
2. Same stop rules: second consecutive 429 ends the call as cooling-off; 403 and the other refusals never retry;
   `Retry-After` above 120 s ends the call; `RawSourceUnavailable.tries` and message text are byte-identical.
3. Never weaker: the live waits are always at least 5/15/45 and at most twice that; the pause is 15 minutes at two
   403/429 in a row (any other answered status resets the count); a 404 between two 403s resets it.
4. One probe after the pause, one request, no retries; a probe answered 404 closes it; refused re-opens for twice as long.
5. One request in flight past the pause per breaker, even with 8 threads (the library test, reused through the source).
6. Callers unchanged: the exceptions (`RawFileRefused`, `RawSourceCoolingOff`, `RawSourceUnavailable`) and their
   fields are the same, so `coverage`, the librarian and the stager need no edit.
7. One builder, no second rule: after R1b1 the old `RETRY_WAITS` in `retry_policy.py` and the loop in `_response`
   are gone; `retry_policy.py` keeps only `verdict` and `retry_after_seconds`. A static test lists `sleep(` sites.
8. Deferred writes nothing: when the breaker defers a fetch, the stager/library leave Staging, Record, manifests and
   receipts untouched (spy store, zero writes).

## Risks (stated, not hidden)

- A refactor of code the 13 live workflows run reaches production on the next cron after merge. Protection:
  the characterization tests, mutation plants on the new code, and a dry-run dispatch after the merge (below).
- Jitter makes a worst-case file up to twice as slow (65 s of waits can become 130 s). A12's `--max-minutes` already
  checks its deadline per file; the story's judge checks that no workflow's timeout is within that margin.
- The probe rule is stricter than today: after a 15-minute pause today's loop would retry 4 times at once; the new one
  sends one. That is the point, and is never weaker.
- Thread safety: today's `RequestPacer` has a lock. The library's classes have one (mutation-proven in R1a).

## Post-merge check

After R1b1 merges, dispatch with `dry_run` one NSE workflow that has it (for example `index-closes.yml`) and read its
log: the refactored code ran on the real runner and wrote nothing. NSE is not Groww, so the market-hours rule does not
apply. If the dry run shows a refusal pattern, stop and report before the next cron.

## Judges

Two judges. Freeze rule as always: one SHA, no push after sending it.
