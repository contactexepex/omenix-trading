# Judge 100: NP6a grouper version 2 (judge #2, code)

**Subject:** `story/NP6a-grouper-v2` at `7323c3f`: 23 files.
- New: `cluster/url_identity.py`, `cluster/prepare.py`, `cluster_record/grouping.py` and `resolve/effective_url.py`.
- Changed: assignment, the format-2 cluster file, the run and its wiring, the CLI, and the `news-cluster` workflow
  (`algorithm` input).
- Rows Z1 to Z15.
- Lane 1: the write-once cluster record, a workflow that calls Drive, and the company list.

**Gates (locked venv, `__pycache__` cleared):**
- `pytest -q -n auto`: 1958 passed.
- `ruff check` and `ruff format --check`: clean.
- `check_imports`: 615 files clean.
- `test_code_size`: 3 passed.
- `check_numbers`: clean.
- `tools/contract_plants.py`: every plant caught.

## Against the plan (judge 96) and my condition C1

- **B1, identity URL** (`url_identity.py:31-47`):
  - What passes: a query left after `utm_*` and `fbclid` are removed, two or more path segments, or one segment holding
    a hyphen or a digit.
  - What is refused: a bare host, `/`, or `/markets`. A refused URL is counted (`url_refused`, then
    `url_joins_refused`).
  - This matches the plan's rule. The W2b wording is fixed in the docstring.
- **C1: built.**
  - `assign.py:34-36` counts a URL join whose title would not have matched the anchor (`same_story` against
    `clusters[index][0]`, the bar mover included) as `url_joins_unlike_title`.
  - The count is written in the format-2 file (`cluster_file.py:70-77`) and printed in the run line (`report.py`).
- **URL before title, and one URL for one cluster** (`assign.py:31-43`):
  - `_by_url` runs first;
  - `owner.setdefault` keeps the first taker;
  - a title match still compares with the anchor only.
- **B2:** the guarantee is stated as written (`grouping.py` docstring). There is no day cutoff, and
  `resolutions_used` is recorded.
- **B3** (`grouping.py:61-69`):
  - only `company_list_missing` falls back to version 0;
  - invalid, rolled-back or damaged lists, and any store error (`company_list_unavailable`), stop the run with the
    code and write nothing;
  - a damaged resolution file stops the run too (`resolution_unreadable`).
- **Item 4:** `Tagger.tag(article.title, None, article.source)`, title only, with the source passed (`prepare.py:34`).
- **No feed claim:**
  - `effective_url` is the resolution's URL, or `canonical_url`, which is `""` for a Google News item
    (`article_file.py:29`);
  - the claimed domain is never used.
- **Version 1 is unchanged:**
  - `Prepared.of` leaves `url=""`, so version 1 never joins by URL;
  - the file stays format 1;
  - the folder stays `news/clusters/1`.
- **Workflow:**
  - `algorithm` is a dispatch choice that defaults to `"1"`;
  - a scheduled run has no inputs, so it runs `--algorithm 1`;
  - the concurrency group `news-record` is unchanged;
  - the receipts path covers `clusters/2`.

## My plants (each restored afterwards)

| Plant | Mutation | Result |
| --- | --- | --- |
| M1 | an identity needs three segments | caught (9 failed) |
| M2 | the unlike-title count is inverted | caught (3 failed) |
| M3 | the last taker owns a URL | caught (2 failed) |
| M4 | the URL join ignores the 36 h window | caught (2 failed) |
| M5 | a missing list blocks the run | caught (2 failed) |
| M6 | an invalid list falls back silently to 0 | caught (3 failed) |
| M7 | a store error falls back silently to 0 | caught (2 failed) |
| M8 | resolutions are read outside the window | caught (2 failed) |
| M9 | the summary moves the bar | caught (2 failed) |
| M10 | tracking parameters are kept | caught (3 failed) |
| M11 | version 2 reads the PREVIOUS file from version 1's folder | **survives** |
| M12 | a damaged resolution is skipped silently | caught (2 failed) |
| M13 | a digit-only slug is not an identity | caught (1 failed) |
| M14 | title is tried before URL | caught (5 failed) |

## Notes (not blocking)

- **N1, test gap (M11).** `ClusterRun._previous` reads the earlier file from `news/clusters/2` for version 2
  (`run.py:85`), which is correct. No test pins it.
  - If it broke, version 2's write-once `previous_cluster_ids` would be computed against version 1's clusters, with
    every test green.
  - Add a run test that has a version-1 file and a version-2 file, and assert which one supplies the previous ids. Add
    it in the next push that touches these files.
- **N2: the run line should show `companies_version`** (reasoning only).
  - `company_list_missing` falling back to 0 is the plan's rule. But the hand-run line, the one an operator reads,
    prints the URL counts and not `companies_version`.
  - A version-2 dispatch that ran against a wrongly configured config area would look normal and record a file where
    no bar ever moves; only a field inside the file would say so.
  - It is cheap to add to `URL_COUNTS` or the line. Recommend it before the version 1 against version 2 comparison.
- **N3, Drive reads per run** (reasoning only, unmeasured). `_resolutions` makes one Drive `get` per Google News
  article in the 48 h window, every run. The first version-2 dispatch should report its run time.
  - If it is slow, read the window's resolution keys from `resolved.csv` first, which is still read only. That would be
    a later story.
- **N4: rollback protection.** `PrivateCompanyFile` is built with `used=None`, the same as the other callers. Version
  2 is dispatch-only until NP7, so NP7 must decide the rollback rule for the company list.

**Verdict: PASS** (round 1, `7323c3f`).
