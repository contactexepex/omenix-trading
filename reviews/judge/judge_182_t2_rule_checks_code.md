# Judge 182: T2 code (card rule checks), `story/t2-t3-advocate` 7477ad4e (lane 1; judge E)

Date: 15 Oct 2026 (UTC). Judged against the passed text (judge 180 addendum 1). New: `fno/cards/rule_checks.py` (156
lines) and `fno/cards/ruled_status.py` (59). Changed: `fno/cards/wiring.py` `build_status`, one constant
(`CARD_HARD_RULE_BREACH`). Tests: `tests/cards/test_rule_checks.py` (7). Claims: response 174, "Code round".

## Verdict: FAIL on 2 should-fix (both small test gaps); the code itself is sound

| Check | Status | Evidence (mine) |
|---|---|---|
| T2 decides and blocks nothing | MET | The status stays T1's (`RuledStatus` keeps `reading.status`, so always `NO TRADE` in v1); only the reason code and the lines change. Nothing writes |
| Reads only committed outcomes; no registry re-read | MET in code | `rule_checks.py` reads only the run log (`journal/runs/<d>.json`) and `journal/<book>/validity_failures.csv` through `CommittedRecords`. Its imports: `constants`, `desk.run_log`, `desk.timetable`, `cards.committed`, `cards.sections`. No `fno.checks`, no registry. T1's `RegistryStatus` is wrapped unchanged |
| Final times from the desk's Timetable | MET | `timetable_from_config(load_app_config())` in the wiring; no time in T2's code. The test gives 15:12, 15:15 and G10's 15:10. The live card shows the run-log path for today |
| Builder's choice: final when the step is in the run log, not when the clock passes | Accepted | Stricter than the text: a late or restarted desk shows "not yet decided", never a premature "no breach". The step is recorded only on success, with its result (`fno/desk/run_log.py:36-40`), so `steps[...]["result"]` cannot be missing. Sound |
| Order: data before C4 before T1 | MET | `SEVERITY`; plant 7 caught |
| T3 and T2b not built | MET | No `fno/cards/advocate.py`; `fno/advocate`, `fno/budget` and `fno/learning` unchanged against `main`; `ObjectionCheck` still holds its module constants |
| Live dry run | MET | `python -m fno card daily --on 2026-10-15` shows "Rule checks: not complete", with "decisions: not yet decided: the desk has not run today" and "execution: ... last session (2026-10-14): no execution record". That is true: there are no `journal/runs/` files on `main`. Nothing posted or written |
| Gates on 7477ad4e | MET | Full suite (full history) 6,103 passed; ruff clean; format clean (1,124 files); `check_imports` clean. `constants.py` 347 lines (O1's split resolves it, as the orchestrator noted) |

**My plants (8, reverted):** 5 caught, 3 survived.
- **Caught:** the day filter removed; the decisions outcome using the execution time; "no breach" while pending; the
  severity order reversed; late books not reported.
- **Survived:**
  - `from fno.checks import gate` added to `rule_checks.py`;
  - `import fno.playbook.registry` added;
  - the `except` around the failures-file parse disabled. A malformed `validity_failures.csv` would then crash
    the card build instead of giving `data_check_failed`.

## Should fix

1. **The AST test does not prove criterion 7.**
   - It checks only `ImportFrom` modules starting with `checks` or `playbook`. That catches the relative
     `from ..checks` form, but misses absolute `from fno.checks ...` and plain `import fno.playbook.registry`
     (both survived).
   - Fix: normalise both import kinds to the full module name and refuse `fno.checks.*` (the rule modules) and
     `fno.playbook.registry`.
2. **No test for an unreadable failures file.**
   - The test plan (item 3, negative) lists it, and criterion 6 requires `data_check_failed` naming the file. Only an
     unreadable run log is tested; disabling the failures-file handling passes every test.
   - Fix: add one case, e.g. a `validity_failures.csv` without a `day` column, that gives `data_check_failed`
     naming that path.

## Note

When C4 refuses, the status line reads "`NO TRADE (hard_rule_breach)`" while the next line keeps T1's "Reason: ...".
That can only happen once a version is at `paper` (no proposal is made otherwise). The rule-check lines below then
explain it, so this is fine for v1. T2b, which builds the trade fields, should make the reason line follow the code.

**Verdict: FAIL for 7477ad4e18c9b4f324a37dd2618e9a4412d2904d** on 2 should-fix (tests only). Re-judge on the fix; the
code needs no change.

---

## Addendum 1 (judge E): re-judge at b0556129: PASS

Diff `7477ad4e..b0556129`: tests only. `fno/` is untouched. A new `tests/import_graph.py`; `test_rule_checks.py`
gains 5 cases; LR1's `test_boundaries.py` now uses the shared reader.

| Finding | Fix | Accepted? (my evidence) |
|---|---|---|
| 1 AST guard | `full_imports` resolves `import` and `from` (relative ones against the package) to full names, including `from fno import checks` as `fno.checks`. `refused` matches a name or a sub-package. A parametrised test plants 4 forms | Accepted. My plants on `rule_checks.py`, each now failing a test: `from fno.checks import gate`, `import fno.playbook.registry`, and `from ..playbook import registry` (a new form). I traced the level-2 resolution by hand: `from ..checks.gate` in `fno.cards` resolves to `fno.checks.gate` |
| 2 Unreadable failures file | A file without a `day` column gives `data_check_failed` naming the path (KeyError) | Accepted. My plant disabling the `except` now fails a test |
| LR1's boundary test | Uses the shared reader | Not weakened: it now also sees `from x import y` as `x.y`, a superset, so it is only stricter |

**Gates on b0556129:** full suite 6,109 passed; ruff and format (1,125 files) clean; `check_imports` clean.

**Verdict: PASS for b0556129.** Merge with the full suite on the merged tree. Whichever of T2 and O1 merges second
resolves `constants.py` (347 lines here).

---

## Addendum 2 (judge E): merge check at 38699fee (main merged into b0556129): PASS

- **Parents:** b0556129 (the passed tip) and 46980e99 (`main`).
- **The hand resolution is right.** The only hand-resolved file is `fno/cards/wiring.py`. Its difference from `main` is
  only T2's addition: the `rule_checks` and `ruled_status` imports, and `build_status`. `build_status` wraps
  `RegistryStatus(records, DownloadedRecords(root))`, which is E2c's Drive accounts reader, kept unchanged.
- **E2c does not touch T2's sources.** Its `ACCOUNT_FILES` (`fno/desk/private_files.py:24`) holds the five account
  files only. The run log and `validity_failures.csv` stay in the repository.
- **Gates on 38699fee (full history):**
  - full suite 6,139 passed; `tests/cards` 75 passed;
  - ruff clean; format clean (1,131 files); `check_imports` clean;
  - `constants.py` is 349 lines, inside the limit.

**Verdict: PASS for 38699fee.** It may go to `main`.
