# Judge 102: NP7b company-list pin (code), round 1 at aee8a96: FAIL (one small test)

**Lane 1, two judges; this is judge #1.** Branch `story/NP7b-company-list-pin`, frozen SHA aee8a96. I reviewed `git diff origin/main...aee8a96`: the grouping, run, cluster file, company model and adapter, tests, and contract rows Z17 to Z23.

## Gates (strong evidence)
In a venv installed from `requirements.lock`:
- 1976 passed;
- ruff check and format are clean, and check_imports is clean;
- contract plants are all `ok`, Z17 to Z23 included.

## The change from the plan (compare in the grouping, not `used=`): accepted (strong evidence, by case)
I traced both designs against `VersionedFiles.latest` (`versioned.py:50-69`):

| Case | Plan (`used=` + refuse `Picked.damaged`) | Built (compare with the previous file) |
|---|---|---|
| The used version was edited in place and is still the newest | skipped, then refused: damaged | same version, other SHA: damaged |
| The used version was deleted and an older one remains | rolled back | older version: rolled back |
| A newer version was added | accepted | accepted |
| The used version was edited, and a newer one was added | accepted (the newest is read first) | accepted |
| Every list was deleted after one was used | missing, then **version 0** | stop: `company_list_missing` (better) |

The outcomes are the same, the code is simpler, and the last row is stricter than my plan. `VersionedFiles` is untouched.

## B1 (required, small; strong evidence, plant survived): which previous file is compared is not pinned
- The whole guarantee rests on comparing with the **latest** earlier file (`run.py`, `max(earlier)`).
- My plant `max(earlier)` → `min(earlier)` passes the **full suite** (1976 passed).
- With that plant, every run compares with the first version 2 file ever written. Take a list used as v1 in the first file and v3 in a later one, then rolled back to v2: the plant accepts it silently. That is the exact harm NP7b exists to stop.
- The `max` line predates this story, but NP7b is now what depends on it.
- **Fix:** one test with two earlier version 2 files that recorded different list versions, where the run must compare with the newer one. Add it as a contract row with this plant.

## My other plants (each one undone; all fail tests, strong evidence)

| Plant | Result |
|---|---|
| a newer list refused (`<` → `!=`) | 1 failed |
| the edit-in-place check removed | 1 failed |
| a list that was used and is now missing becomes version 0 | 1 failed |
| a run that never had a list stops | 2 failed |
| the adapter hands over a wrong SHA | 1 failed |

## What holds
- **Privacy:** the list's SHA-256 is kept only in the private Drive cluster file, and every stop is one fixed code.
- **Write-once:**
  - every stop rejects before `_write`, so no file is written;
  - format 2 gains one field before any file uses it (no `clusters/2/` receipt or manifest row on `main`);
  - the parser reads 0 and "" for a file without the fields, so version 1 files still parse.
- **Size and structure:** every changed file is small, the compare is a single-purpose function, and no new wiring is needed.

## Notes (not blocking)
- **N1.** `ClusterRun._previous` is now used only by tests. Production goes through `_previous_file`. Remove it and point the tests at `_previous_file`.
- **N2.** The comparison is with the latest file **before the run's `as_of`**. A hand-dispatched re-run of an older window compares with files older than that window, not with the newest one. Since the run writes a file for that older window, an old list could be recorded there. That is a narrow case, needs the owner's own dispatch, and does not change later runs, which compare with the newest file. Say it in the story's "Said plainly".
- **N3.** A format 2 file with a list version but an empty SHA (written by a version 2 dispatch before this merges) would stop every later run as damaged. No such file exists. Do not dispatch algorithm 2 before NP7b merges.

## Hard lines
No order path, no secret, no Groww call. No new workflow or schedule.

## Verdict: FAIL round 1 at aee8a96. B1 (pin which previous file is compared) required; N1 to N3 requested.

## Addendum 1: round 2 at 7d496ae: PASS

I reviewed `git diff aee8a96 7d496ae`. It adds one test, removes `_previous`, adds two story lines and contract row Z24.

**Gates (locked venv, strong evidence).**
- 1977 passed.
- ruff check and format are clean; check_imports is clean.
- Contract plants are all `ok`, including Z24.

**B1 fixed (strong evidence, replanted).** The new test runs list versions 5, then 7, then a rollback to 6. It expects `company_list_rolled_back` and checks that the compared file is the one that recorded 7. My plant changing `max(earlier)` to `min(earlier)` now fails that test (1 failed).

**N1, N2 and N3 done.**
- `_previous` is removed, and the two tests that used it now call `_previous_file`.
- "Said plainly" states the re-run of an older window and the "do not dispatch algorithm 2 before this merges" rule.

**Scope (owner's ingestion-only rule, 27 Oct 2026, as relayed by the orchestrator).** This is a derive-side safeguard on the cluster run; it has no consumer-facing part.

**Verdict: PASS round 2 at 7d496ae.**
