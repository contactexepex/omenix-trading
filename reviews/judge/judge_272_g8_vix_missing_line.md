# Judge 272: G8 names a missing VIX close (story/g8-vix-missing-line at cc026608)

Judge B, 16 Oct 2026. Lane 1 (scoring), before the v4 freeze. Builder: A16/G8. Stacked on story/g8-v7-shared-rule
(judge 267 PASS). The orchestrator's ruling: keep the stop, but name it.

**Verdict: PASS.**

| Item | Result | Evidence |
|---|---|---|
| A bare `KeyError` becomes a named stop | MET | `G7Series.sessions()` collects every regular session without a VIX close and raises `VixCloseMissing` (part of the `OutcomeSeries` contract), naming the first day and the count |
| One line, exit 1, no traceback | MET | `cmd_forecast_v4` catches only `VixCloseMissing`; the body moved into `_run` unchanged. Test: 14 Oct's VIX blanked in the committed closes raises it (anchored regex), and the command prints exactly one line and returns 1 |
| No quiet void | MET | scoring stops; the regimes are not silently changed |

**Mutation:** the named check removed (`if missing` never true) fails 1 test (the bare `KeyError` returns).

**Note:** the stop prints to the job's log; the workflow's own failure line alerts. A stale v4 report stays the
latest until O6 fills the close. That is what the line says ("no v4 report until then").

**Gates (run by me on cc026608):** 7,319 passed. Known main failures: `tests/risk/test_manager.py` (two) and `tests/risk/test_stress_factor.py::test_the_repository_seed_row_is_read_by_c2_and_c4` (A14c's stress factor row, judge 268; fixed separately, judge 269). `ruff check`: clean. `ruff format --check`: 1,308 files already
formatted. `check_imports`: clean. Merge after story/g8-v7-shared-rule.
