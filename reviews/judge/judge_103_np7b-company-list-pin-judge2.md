# Judge 103: NP7b company-list pin (judge #2, code)

**Subject:** `story/NP7b-company-list-pin` at `aee8a96`.
- The version 2 cluster file records `companies_sha256`.
- `ClusterRun` hands the latest earlier version 2 file to `SymbolGrouping`, whose `_refuse_going_behind` stops an
  older list (`company_list_rolled_back`) and the same version with other bytes (`company_list_damaged`).
- A list that was used and is now missing stops the run.
- Rows Z17 to Z23.
- Lane 1: write-once cluster record and private company list.

**Gates (locked venv, `__pycache__` cleared):**
- `pytest -q -n auto`: 1976 passed.
- `ruff check` and `ruff format --check`: clean.
- `check_imports`: 621 files clean.
- `test_code_size`: 3 passed.
- `check_numbers`: clean.
- `tools/contract_plants.py`: every plant caught.

## The deliberate change from the plan: accepted

The plan was to pass `used=` to `VersionedFiles.latest`. The build compares in the grouping instead. I accept it, with
*strong evidence* from reading `versioned.py:50-69`:
- With `used=None`, `latest` always returns the newest version, and `sha256` is computed from the bytes it read. Nothing
  is skipped.
- Comparing that pick with the previous file covers the four cases that matter:

  | Case | Outcome |
  | --- | --- |
  | an older version | rolled back |
  | the same version with other bytes | damaged, a stop (where `latest` would have fallen back to an older good version) |
  | a newer version | accepted |
  | a used list now missing | stopped |

  For a list that has been used, this is equal to or stricter than the plan.
- `VersionedFiles` and the other private files are untouched.

## My plants (each restored afterwards)

| Plant | Mutation | Result |
| --- | --- | --- |
| K1 | the rollback check removed | caught |
| K2 | the edit-in-place check removed | caught |
| K3 | a missing list after use gives version 0 | caught |
| K4 | the previous file is not passed to the grouping | caught (4 failed) |
| K5 | `companies_sha256` not written | caught (5 failed) |
| K6 | `companies_sha256` not parsed | caught (3 failed) |
| K7 | the adapter does not fill `sha256` | caught |
| K8 | the run does not set `companies_sha256` | caught (3 failed) |
| K9 | a newer list is refused | caught |
| M11 | version 2 reads the previous file from version 1's folder | **now caught** (5 failed), so judge 100 N1 is closed |
| K10 | `max(earlier)` becomes `min(earlier)` in `_previous_file` | **survives** (1976 passed) |

**Disclosure:** I found K10 only after reading judge 102's report, which I read after my own ten plants had passed. I
re-ran it myself rather than taking it on trust. The verdict below rests on my reproduction, not on judge 102.

## Blocking (small)

1. **B1: which earlier file the run compares with is not pinned** (*strong evidence*: K10 survives the full suite).
   - The whole guarantee of this story is "compare with the LATEST earlier file" (`run.py:96-104`). Under K10, every
     run compares with the first version 2 file ever written.
   - Example: a list used as v1 in the first file and v3 later, then rolled back to v2, is accepted silently. That is
     the rollback this story exists to stop, recorded write-once.
   - **Fix:**
     - a run test with two earlier version 2 files that recorded different list versions, where the run must refuse a
       list older than the NEWER file's;
     - a contract row with the K10 plant.
2. **B2: `ClusterRun._previous` (`run.py:88-90`) is now dead production code** (*strong evidence*).
   - Production calls only `_previous_file`. The one remaining callers are tests:
     - `tests/ingestion/news/cluster_record/test_write_and_run.py:228-229`;
     - `tests/ingestion/news/cluster_record/test_version_two_run.py:232`.
   - CLAUDE.md's engineering standards forbid dead code. Remove the method and point those tests at `_previous_file`.

## Notes (not blocking)

- **N1: re-running an older window** (*reasoning only*, the same point as judge 102 N2).
  - A dispatch with a past `as_of` compares with the files before that window, so it could record an older list into
    that window's file.
  - Later runs still compare with the newest file, so the guard holds going forward. Say it in the story.
- **N2: do not dispatch algorithm 2 before NP7b merges.** A format-2 file with a list version but an empty SHA would
  stop every later run as `damaged`. No such file exists today; I agree with judge 102 N3.
- **N3: the hash stays private.** The list's SHA-256 lives only in the private Drive cluster file. It is not in git,
  a log or the run line, so no private content is exposed.

**Verdict: FAIL** (round 1, `aee8a96`). B1 (one test, one row) and B2 (remove the dead method) are both small.
