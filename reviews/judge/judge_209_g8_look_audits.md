# Judge 209: G8 look audit gate: `story/g8-look-audits` 4b8912fc (lane 1, the looks)

Judge B. A16/G8 builder. It builds the G8 side of judge 206's should-fix on G11 (`open_audits.csv`). It lands before
the v4 freeze; response 157 says so.

## Checks
- **`audits.py`.** `OpenAuditFile` reads `day,forecaster,question`. A bad header or day raises `AuditFileError`, which
  stops the look. A missing file returns `[]`. `require_settled` raises `LookBlocked` when any open day is `<=` the
  look's date.
- **`cli._look`.** Only a recorded (post-freeze) look is checked, before `run_look`. If blocked, it prints "look NOT
  run, nothing recorded: ..." and exits 1, before anything is written. An exploratory look is not stopped. The check
  uses `decided_at.date()`, so any open audit up to the day the look runs blocks it, which matches G11's rule.
- **Changed tests are not weakened:** the four `_look` calls only gain `NO_AUDITS`.
- **My plants:** `<` for `<=` fails 1 test; skipping the check in `_look` fails 1 test.
- **Gates.** `-n auto`: **6,573 passed, 0 failed**. Ruff is clean. `tests/forecast_scoring_v4`: 61 passed.

## The orchestrator's point: once AI rows exist, should a missing file refuse the look?
**Ruled: not needed as a FAIL (reasoning only). One-line note.**
- The normal paths cannot lose the file. G11 adds a row in the same commit as the collected submission and removes it
  in the same commit as the v4 record row (judge 206 addenda 1-2), and the file is committed, so a fresh checkout has
  it.
- The file disappears only through a hand deletion or a writer bug that deletes it. That is the kind of imagined case
  the owner's simplicity rule keeps out of should-fixes.
- It is cheap to close by contract instead. **Note:** G11's writer keeps the file with its header when no audit is
  open, and never deletes it. G8 could then treat "AI rows exist under `research/forecasts/v4/book2_hybrid` or
  `book3_ai`, but no file" as `AuditFileError`. That is optional, a few lines, and both builders' choice. If they make
  it, it fits the existing error path.

**Verdict: PASS for 4b8912fc.** Merge it before the freeze commit.

## Addendum 1 (15 Oct 2026): my note built, `story/g8-audit-file-required` 16e082a7

- **The change.** `OpenAuditFile(path, ai_rows_exist)`: a missing `open_audits.csv` raises `AuditFileError` ("never
  deleted") once any v4 record row has `kind == "ai"` (`V4_KIND_AI` in `constants.py`). `has_kind` scans
  `research/forecasts/v4/*/*.csv`, which matches G7's layout and will match G11's `book2_hybrid/` and `book3_ai/`
  folders (every v4 CSV today sits at that depth; checked). A header-only file still means nothing is open.
- **Agreed with G11:** their text now says the file always exists from the first live day (judge 206 addendum 4).
- **My plants:** skipping the raise fails 1 test; `has_kind` always False fails 1 test.
- **Gates.** `-n auto`: **6,798 passed, 0 failed**. Ruff is clean.

**PASS for 16e082a7.** Merge it before the freeze.
