# Judge 515: MS-SIM-d1, the practice run's inputs

**Scope:** story/ms-sim-d1 at 6b6d18c6 (code 01bf888d; builder session_01W2JE3W9xYftEDWTysHkdVC), diff
origin/main...6b6d18c6. SIM-d1 Claims in MS-market-school.md. Lane 1 (practice). Round 1 of 2. Judge H
(session_01KNkZVoWvXMkoihKrrXk5Xa).

**Verdict: PASS**, with 1 minor (the isolation question, answered below).

## Checked
| Item | Result | Evidence |
|---|---|---|
| Index close by (underlying, session) | MET | `bhavcopy_chain.py:55-63`; test with NIFTY and BANKNIFTY on one day. Plant (NIFTY's close for every underlying) caught. **My miss:** I passed SIM-a (judge 500.1) with the date-only lookup. Its index close was only a callable then, wired here for the first time, but I should have caught the signature |
| Real data, stores only | MET | My run: legacy 24 Jun 2021 gives NIFTY 15,790.45 and BANKNIFTY 34,827.0; legacy 31 Mar 2023 gives 17,359.75 and 40,608.65; UDiFF 2 Jun 2025 gives 24,716.6 and 55,903.4. Requests went only to Google hosts (1 OAuth, 202 Drive), none to NSE |
| No NSE fallback | MET | `StoredFilesOnly` behind the stores. Plant (an NSE source swapped in) caught |
| Spot history strictly before the session | MET | `spots.py`: 42 points before 24 Jun 2021 for BANKNIFTY, the last 23 Jun. Plant (the session included) caught |
| Index-close file outside its cover, or damaged | MET | Plant (cover check removed) caught. The damaged-file test passes |
| Cached chain | MET | `lru_cache` of the port's `day`; the file reads only |
| Gates | MET | pytest -n auto: 13,841 passed, 16 xfailed. ruff check/format, check_imports and check_records are clean |

## The isolation question
**Yes, keep the one-file exception, but narrow it to the names that file uses.**
- `test_isolation.DATASET_NAMES` allows the whole of `fno.storage.wiring` and `fno.storage.raw_source` for
  `practice/stores.py`. So a later `from ....storage.wiring import build_nse_fo_library` in that file would pass the
  import test. Only the runtime test would stop it, and only if it ran the path.
- Expected (minor): allow exactly `fno.storage.wiring.daily_files` and the three source classes
  (`NseDailyFoSource`, `NseLegacyFoSource`, `NseIndexCloseSource`).
- `banned()` already sees fully qualified names, so this is a set of names, not a design change.
- Moving the dataset names to a constants module would touch storage's own wiring (another owner) for no gain.

## Plants
5 planted, 4 caught. The survivor widens `except BadFile` to `except ValueError`. That is nearly equivalent, since
`BadFile` is a `ValueError`; the damaged-file case still gives None.

## Addendum 1

**Follow-up:** story/ms-sim-d1 at 6afa4848 (only `tests/school/simulator/test_isolation.py` and the Claims changed).
**Verdict: PASS**, unchanged. The minor is partly closed.

- A planted `from ....storage.wiring import build_nse_fo_library` in the real `practice/stores.py` is now caught (my
  plant, reproduced).
- **Still open (minor):** the allow-list keeps the bare module names `fno.storage.wiring` and `fno.storage.raw_source`.
  So `import fno.storage.wiring` or `from ....storage import wiring`, then `wiring.build_nse_fo_library(...)`, both
  pass the import test (my plants, both survived). Only the runtime no-NSE test stands behind them.
- Fix: accept a bare module name only as the parent of an allowed `from X import name`. For example, refuse a plain
  `import X` or `from pkg import X` in that file.

## Addendum 2

**Follow-up:** story/ms-sim-d1 at 91bb8c23 (only `test_isolation.py` changed). **Verdict: PASS. The minor is closed.**
- My plants caught: `import fno.storage.wiring`, `from ....storage import wiring`, and an allowed-plus-builder
  `from ....storage.wiring import daily_files, build_nse_fo_library`.
- `tests/school/simulator` passes (140) and ruff is clean.
- Three deliberate evasions still pass. No static import check can close them, and they are not findings:
  - `import fno.storage`, then attribute access;
  - `from .... import storage`;
  - `__import__("fno.storage.wiring")`.
  The runtime no-NSE test is the guard there.
