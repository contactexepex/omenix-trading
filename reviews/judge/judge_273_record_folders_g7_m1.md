# Judge 273: record_folders() for G7 (story/g7-record-folders at 23c610a7) and M1 (story/m1-record-folders at 7cc22a68)

Judge B, 16 Oct 2026. Lane 1 (forecast records' commits). One function each for O1's per-step commits, so the weather
step and the forecasts_v4 step never commit each other's half-written files. Builders: R2/G7 (23c610a7) and P2/M1
(7cc22a68; claims: response 251).

**Verdict: PASS for both.**

| Item | Result | Evidence |
|---|---|---|
| G7: the 10 folders `forecast-v4 capture` writes | MET | derived from `FORECASTERS`, sorted, repository-relative with a trailing "/"; test: equals the forecaster ids, none is a weather folder, and every committed G7 record file is under one |
| M1: its records and its two forecasters' v4 folders | MET | `fno/weather/folders.py`, outside `wiring.py` and outside `METHOD_FILES` (the files are listed by name), so `method_sha256` is unchanged. Test: a real capture laid out as in the repository writes only under `record_folders()` |
| Disjoint | MET | G7's set excludes `weather*`; M1's are `v4/weather/`, `v4/weather_vix_v1/`, `v4/weather_checklist_v0/`. The trailing "/" keeps `weather/` from matching `weather_vix_v1/` as a pathspec |
| G7's method hash | unchanged | the "every committed G7 record row carries this tree's method hash" test passes, with no back-fill regenerated |

**Mutations (real cases, both caught):**
- G7's list missing its last forecaster: 1 test fails.
- M1's list with the records folder only: 1 test fails.

**Gates (run by me):** 23c610a7 gives 7,349 passed; 7cc22a68 gives 7,351 passed. Known main failures: `tests/risk/test_manager.py` (two) and `tests/risk/test_stress_factor.py::test_the_repository_seed_row_is_read_by_c2_and_c4` (A14c's stress factor row, judge 268; fixed separately, judge 269). `ruff check`, `ruff format
--check` and `check_imports`: clean on both.
