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
