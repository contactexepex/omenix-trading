# Judge 549: DR1-d2, the commit hook's record scan imports only the standard library (second judge)

**Scope:** story/dr1-d2-stdlib-record-scan at 29d3c9d8 (code 8f04d4c2), DR1 builder. The story is
docs/stories/DR1-d2-stdlib-record-scan.md. Lane 1, a hard line: the secrets record scan. Judge I is first (548). I
judged independently and did not read 548 first. Judge K (session_019ZApRwkUiNMKDsf1k4W44z).

**Verdict: PASS.** No blocking or should-fix findings. 1 minor.

## Checks (all mine)
| Check | Result | Evidence |
|---|---|---|
| The same refusal set | MET | I made 38 planted files: each of the 19 `PLANTED` kinds as `.md` and as `.py`, plus a clean file. `check_records.py` from main 2b267aa0 and from the branch gave byte-identical output (42 findings, exit 1). On whole trees, both versions gave the same answer on the branch's tree (clean, 8843 files) and on main's tree (clean, 8863 files) |
| No value printed | MET | None of the 19 planted values appears in the output, including the alert line |
| Exit codes | MET | Clean: 0. Refused: 1. Refused with `--alert` and no sender: 1 |
| `python -S` (no site-packages) as the hook runs it | MET | `--staged --alert` in a temp repo with a staged private key prints the finding, then "REFUSED", then "alert NOT sent: the #fno-desk sender could not be loaded (ModuleNotFoundError: numpy) \| <text, no value>", and exits 1. A clean staged file gives "clean (1 files)" and exit 0 |
| A half-installed package (a fake `numpy` raising RuntimeError on import) | Refusal holds | The finding and "REFUSED" print, then a traceback, then exit 1, so the commit is still refused. See minor 1 |
| The re-export keeps callers working | MET | `fno.composition` re-exports `build_record_scanner`. Its 4 test importers pass. No caller imported the removed `ALLOWED_VALUES`, `credential_patterns`, `RecordScanner` and the rest from `fno.composition`. Monkeypatches of `fno.composition.build_alert_sender` still reach `send_alert`, which imports it at call time |
| The stdlib-only claim | MET | The branch's test runs under `-S` and loads none of numpy, requests, yaml, pandas or google |

## Plants (mine, `tests/record_scan`): 4 of 4 caught
- `send_alert` no longer catches ImportError: 1 test fails.
- `wiring.py` imports `fno.composition` again: 21 tests fail.
- A forbidden path (MOVED_VIX_FILES) dropped: 1 test fails.
- `send` skipped (always "sent"): 4 tests fail.

## Minor
1. `send_alert` catches only `ImportError`. A package that fails at import with another error (a half-installed
   wheel, or a config error at import) leaves a traceback instead of the "alert NOT sent ... | <text>" line. The
   commit is still refused (exit 1) and no value is shown, but the routine then has no line to post. Catching
   `Exception` there, with its type named, would keep the routine's alert in every case. The old code was worse: it
   failed before scanning, even for clean commits.

## Gates (my run, a trial merge of 29d3c9d8 with main 2b267aa0)
- `pytest -n auto`: 14725 passed, 1 skipped, 16 xfailed.
- ruff check, ruff format, check_imports, check_records (8866 files) and check_numbers: clean.

## Addendum 1: DR1-d2b at 3225c5a22 (the minor)

**Verdict: PASS.** The minor is closed.
- **The change:** `send_alert` catches every `Exception` from loading and building the sender. The line names the error's class and, for an error with a `.name` (an ImportError), that name. Otherwise it says "load failed", because the message may hold a path.
- **My probes on the branch:**
  - A fake `numpy` raising RuntimeError at import: "alert NOT sent ... (RuntimeError: load failed) | <text>", exit 1. In 549 the same probe gave a traceback.
  - `python -S`: "(ModuleNotFoundError: numpy)", exit 1.
  - A nested missing module: "(ModuleNotFoundError: numpy.missing_thing_xyz)".
  - No value printed in any of them.
- **Plant:** putting back `except ImportError` fails the new test.
- **The stated limit is accepted:** a BaseException such as pyo3's PanicException is not caught. The hook then exits non-zero, so the commit is still refused, only without the text.
- **Gates (a trial merge with main 511edf2a5):**
  - `pytest -n auto`: 14770 passed, 1 skipped, 16 xfailed.
  - ruff check, ruff format, check_imports, check_records (8879 files) and check_numbers: clean.
