# Judge 19: R1a resilience library, branch `story/R1a-resilience-library`, SHA ee441a9

**FAIL (round 1) on one small should-fix (the story's text), lane 1, judge 1. The code itself is sound.** 20 files:
`fno/shared/resilience/` (7 modules), its tests, the `resilience` config key, a `.gitattributes` union line and a
one-line format fix in `tests/ingestion/test_paths.py`.

## Criteria

| Check | Verdict | Evidence (my own runs) |
|---|---|---|
| Library only; no live module uses it | MET | `grep resilience fno` outside the package: only `config.py`'s allowed key |
| Gates | MET | 312 passed; ruff, check_imports and check_numbers clean; `ruff format --check` now fully clean |
| Waits never below today's | MET | `t_n + uniform(0, t_n)`; the cap is validated as `>= 2 * max(t_n)` (`retry.py:33`); NSE (5, 15, 45) and Drive (2, 8, 30, 60) pinned in `settings.py` and by tests |
| NSE breaker matches today's pacer | MET | It counts each 403/429; any other answered status resets the run, exactly as `RequestPacer.observe` (`http_pacing.py:54-64`); threshold 2, 15 min; the second refusal stops the retries (`guarded._observe`) |
| Half-open: exactly one probe, outside the policy | MET | `guarded._probe`; a second check while half-open raises `Deferred` |
| Cross-run memory | MET | `TransitionLog` is one CSV per path with union merge; `_restore` reopens from the last non-closed row; rows sorted by time after a union merge |
| Budgets | MET | Spacing, per-minute and per-day (ledger protocol), with deferral past `max_wait` |
| Tests catch breakage | MET | 39 plants, 38 caught (jitter below the floor, an extra attempt, Retry-After ignored, ceiling and total time ignored, a 404 retried, threshold off by one, no doubling or no cap, open lets calls through, a second probe, restore ignored, no alert or log, the probe using the retry policy, a timeout resetting the run, every default changed, an unknown config section, ...). The survivor (removing `min(..., cap)`) is an equivalent mutant: the settings validation already guarantees the cap can never bind |
| The story agrees with the build | NOT MET | Finding 1 |

## Findings

1. **Should fix: the story still says the build waits for V1.** `docs/stories/R1-resilience.md:8` ("only after ...
   V1 has passed") and `:49` ("Design (build, after acceptance and V1)") contradict the new gap-list line (`:146`,
   "Gate lifted"). Reword both to match.

Minor (optional, can ride with R1b):
- `cap_seconds` can never bind (see the survivor above). It only matters for `Retry-After`, which bypasses it on
  purpose. Either drop it or say it is a guard against future config overrides.
- `_restore`'s docstring says a probe that died in flight is treated as a failed probe, but the cool-down is not doubled.
  Align the text or the code.
- Drive gets a new breaker (threshold 5). Today Drive has none. That is not weaker, but it is new behaviour on the
  Record's store. R1c must show what a deferred Drive write leaves behind (a put done but no manifest row; the gate's
  re-put path).

## Addendum 1: SHA 0929993 (round 2)

**PASS, lane 1, judge 1.** ee441a9..0929993 changes only `docs/stories/R1-resilience.md` (+11/-7); code and tests are
identical, so my gates and the 38 caught plants from round 1 stand. Finding 1 is FIXED: `:8` and the Design heading
(`:51`) no longer assert the V1 gate. A "Gate change" paragraph (`:10`) records who (the orchestrator, on the owner's
directive), when (27 Oct 2026 IST) and why, plus the safeguards now required for R1b-R1d: characterization tests with
plants, and a post-merge dry run. The `claim.py` wording is corrected. The minor notes from round 1 carry to R1b/R1c.

## Addendum 2: final SHA bea8dc9 (supersedes 0929993)

**PASS, lane 1, judge 1.** 0929993..bea8dc9 changes 2 files and 4 lines, taking two of my round-1 minors:
- `retry.py`: the clip that could never take effect is removed. `cap_seconds` stays as a validated, declared ceiling,
  and its comment says so.
- `breaker.py`: the `_restore` docstring now matches the code (a probe that died leaves the breaker open with the same
  cool-down, not doubled).

My checks on bea8dc9: 312 passed; ruff, check_imports, check_numbers and format clean. A floor plant (jitter from 0)
still makes 8 tests fail. Correction (from the implementer): the Drive-deferral point is NOT written into any file in bea8dc9. It is to be
put in the R1c story, and I will check it there.

## Addendum 3: my PASS withdrawn (a miss on thread safety)

**FAIL, until the round-2 SHA.** Judge #2 found, and I have now confirmed, that `RateLimit` and `CircuitBreaker` hold
no lock (`grep "threading\|Lock()"` in `fno/shared/resilience/`: 0 at bea8dc9). The code they replace does:
`RequestPacer` (`http_pacing.py:40`) and the intraday `RatePacer` (`pacing.py:14`). The codebase calls them from
thread pools (`quotes/book_fetch.py:39`, `storage/coverage.py:111`). Once wired, concurrent callers could burst past
a host's spacing and per-minute limits, which is weaker than today. I did not check concurrency in rounds 1-2. The
round-2 SHA will be judged with my own concurrency plant (remove the lock, and a parallel-callers test must fail).

## Addendum 4: SHA 37bfa45 (thread-safety fix)

**PASS, lane 1, judge 1.** bea8dc9..37bfa45 adds a lock to `CircuitBreaker` (alerts are sent after it is released) and
a lock to `RateLimit` (a slot is reserved under the lock and the sleep happens outside it), plus a persisted
`FileDayLedger` and tests.
- Gates: 319 passed; ruff, check_imports, check_numbers and format clean.
- My plants: the `RateLimit` lock replaced by a no-op makes 1 test fail; the `CircuitBreaker` lock replaced by a no-op
  makes 1 test fail; reserving at "now" instead of the slot's start makes 3 fail.
- My own real-thread check, independent of the suite: 8 threads at 0.1 s spacing span 0.70 s (minimum measured gap
  0.098 s, which is timer noise after `acquire`); 50 trials of 16 threads racing a half-open breaker each gave
  **exactly one** probe.

Note for R1d: `FileDayLedger` persists only within one machine's file. On GitHub runners each job starts from a clean
checkout, so a per-day budget is shared across runs only if the file is committed (and `merge=union`ed) like the
transition logs. Its docstring's "can read one low" understates it: N overlapping runs can each miss the others' rows.
