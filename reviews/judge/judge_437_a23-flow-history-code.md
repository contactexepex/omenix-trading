# Judge 437: A23 FII/DII flow history, code (story/a23-flow-history @ 446a18a9), for response 305

Judge F (independent). Story `docs/stories/A23-flow-history.md` (text PASS, judge 429 add. 1-2), claims
`reviews/claude/response_305_a23-code.md`. Lane 1 (NSE, NSDL, Drive, a workflow). Labels: **strong**, **some**,
**reasoning only**.

## Verdict: PASS for the code, with a merge condition: the back-fill evidence comes back to me before the merge

## Gates (mine, at 446a18a9)

| Gate | Result |
|---|---|
| pytest `-n auto` | **2 failed, 9068 passed, 17 xfailed** |
| `tests/test_fingerprints.py::test_every_raw_dataset_has_a_committed_manifest_in_one_folder` | expected: the two new datasets have no manifest rows until the back-fill (the builder's stated sequencing, no exemption) |
| `tests/playbook/test_activation_gate.py::...[research-STR1b-2]` | **not A23's: a flake.** It passes alone 2 of 2 on A23's head and 2 of 2 on main; it failed only under the parallel run, where that file took 34.9 s. Reported to the orchestrator |
| ruff, ruff format (1677), `check_imports.py`, record scan (7363) | clean |

## Planted mutations (mine, in a separate copy; `tests/flow_history`, 60 tests)

| # | Plant | Caught |
|---|---|---|
| 1 | rewritten boundary `<` → `<=` (written exactly at 09:15:00 would count as rewritten) | yes |
| 2 | a missing `Last-Modified` not flagged as rewritten | yes (2) |
| 3 | NSDL pace 10 s → 9 s | yes (2) |
| 4 | NSDL tries per month 2 → 3 | yes (2) |

## Criteria (code read, tests and plants)

| # | Status |
|---|---|
| 1 Readers: 2019 and 2026 FII-statistics layouts (xlrd 2.0.2, pinned), per-index rows checked against the group within 2 contracts (A8's measure; one real 1-contract miss on 12 Jan 2026); participant volume through A8's reader | MET |
| 2 Point in time: next session; holiday and muhurat stepped over; written at 09:15:00 not rewritten, 09:15:01 rewritten; unknown flagged | MET (plants 1, 2) |
| 2b Rewritten share | pending, from the back-fill |
| 3 Back-fill: A9's librarian, resumable, manifest rows | pending, from the back-fill |
| 4 Daily: `flow-history.yml` 21:30 and 07:15 IST every day, on capture-watch, fallback step `if: ${{ failure() }}`, quiet when each step spoke (judge 359's pattern); O8 rows due 09:00 the next day | MET |
| 5 No value in the repository: manifests, receipts and write-time logs only | MET |
| 6 Real sample | pending, from the back-fill |
| 7 NSDL: readers on the 2019 and 2026 layouts, at least 10 s apart, one retry, resume, no value in lines, alerts or receipts; only the flow-history package names the NSDL table; requests identify as `RESEARCH_USER_AGENT` (an honest identity, row 281 kept rule 2) | MET (plants 3, 4) |

Choices beyond the text, all accepted:
- the sweep's baseline, with an unanswered write time waiting for the next run (never "unknown" for ever);
- O8's 09:00 next-calendar-day deadline, stricter than the text;
- NSDL totals and derivatives not kept;
- the `flows` command name.

Both datasets join `DATED_SOURCES`, so A7's coverage check, A11's revision sweep (the question from my judge 429 add.
1) and the NSE retry policy cover them.

## Merge condition

After the back-fills, before merging, send me:
- the commit with the manifest rows and write-time logs;
- the claims addendum with criterion 2b (rewritten count and share per dataset), criterion 3 (counts, first and last
  sessions, coverage gaps) and criterion 6 (the first back-filled month and the first daily run);
- a full suite where the fingerprint test passes.
I check that addendum, then the merge may go.

## For the owner (not A23's)

P8's dashboard already shows NSDL's latest daily FPI figure. Under row 281 that is fine only if the dashboard is
private ("never in a public place"). If anyone else can see it, the owner decides.

## Addendum 1: the back-fill's refused files, fix at story/a23-volume-fix @ cff14b5e (on the A23 branch)

**Verdict: PASS for the fix. The builder may re-run `data-librarian participant-volume` for 15 Sep 2021, 14 Oct
2022 and 18 Oct 2022 on cff14b5e.** Judge 437's merge condition stands: the back-fill manifest commit, the claims
addendum and a full suite with the fingerprint test green, all sent for my check.

The builder's report so far [as reported, not yet checked by me]:
- NSDL: 93 months, 0 failed, no real figure found in the receipts commit or the run log.
- Participant volume: 1,931 of 1,935 sessions archived. The content check refused 4 files; the builder found the root
  cause of each.

| Item | Change | My check | Result |
|---|---|---|---|
| Stray unnamed sum rows under TOTAL on 3 days | `read_participant_volume` drops body rows whose first cell is empty, then runs A8's reader unchanged; the content check uses it | Plant: unnamed rows kept: 1 failed. Plant: a named row ("Client") dropped: 7 failed. So the five named rows must still pass every identity, and a real participant row cannot be lost silently [strong] | **Accepted** |
| 18 Mar 2019, fractional contract counts (sixths) | a sourced row in `exceptions.csv`; not archived, not in the table | read. Refusing a file that gives fractional contracts is right; guessing a rounding would invent data | **Accepted, with a minor** |

Gates on cff14b5e: **9073 passed, 1 failed**: `test_every_raw_dataset_has_a_committed_manifest_in_one_folder`, the
expected failure until the back-fill's manifests are committed (judge 437). Ruff, ruff format (1678),
`check_imports.py` and the record scan (7551) are clean.

**Minor.**
- `build_file_exceptions` says the file lists sessions NSE "never published a file for", but 18 Mar 2019's file
  exists and is refused for its content. Say so in the reason (it does), and either widen that docstring or give
  refused-content days their own kind, so a coverage reader does not count it as "NSE published nothing".
- Removing the row fails no test (plant 3: 66 passed). Add a test that the participant-volume coverage expects that
  day excused.

## Addendum 2: the merge condition met (story/a23-flow-history @ f2c29ed1; response 305, addendum 1)

**Verdict: the condition is met. A23 may merge** (pull, full suite on the merged tree, `check_numbers.py`, then push).

Gates on f2c29ed1: **9077 passed, 0 failed**, 17 xfailed. The fingerprint test is green now that the manifests are
committed. Ruff, ruff format (1678), `check_imports.py` and the record scan (7556) are clean.

| Condition item | Claim | My check | Result |
|---|---|---|---|
| Manifests committed | Participant volume and FII stats manifests, write-time logs and table receipts on the branch; NSDL receipts | Each manifest holds **1,934 rows**, and each write-time log 1,934 rows | **Met** |
| Criterion 3: counts and gaps | 1,934 of 1,935 sessions each, 2019-01-01 to 2026-10-21. The one gap each is a sourced exception: 18 Mar 2019 (volume, fractional contracts) and 30 Jul 2019 (FII stats, an .xlsx served under the .xls name) | Read the rows. Each exception was judged in addendum 1, or in the builder's note on 30 Jul 2019, which I accepted with a test | **Met** |
| Criterion 2b: rewritten share | Volume 104 (5.4%, 94 in 2019); FII stats 164 (8.5%, 144 in 2019, 11 in 2024) | **Recomputed independently** from the committed write-time logs with A23's rule (written after the next session's 09:15): exactly 104 / 5.4% and 164 / 8.5%, with the same 2019 and 2024 counts [strong] | **Met** |
| Criterion 6: a real sample | January 2019 per table, counts only; totals of 108,304, 98,676 and 120,466 rows, each part matching its receipt | read. Counts only; no figure | **Met** |
| Privacy (rule 281) | NSDL: 93 posts in 15 min 31 s, 0 failed; 3,860 figures searched in the repository and run log: 0 found | The added receipts hold a SHA-256, size, time and writer only. No price-sized number appears in any added receipt, write-time log or claims line I scanned | **Met** |
| The fixes found during the back-fill | Unnamed sum rows (addendum 1); the write-sweep log folder (28ce8c47) | Both checked before the re-runs (plants caught) | **Met** |

After the merge: the first daily run in response 305's addendum 2 (quality rule 8). Also still open: the owner's
openpyxl choice for 30 Jul 2019, where I recommend keeping the exception unless more such files appear (reasoning only).

## Addendum 3: O8's flow-history checks live (story/a23-live-from @ cd33f535)

**Verdict: PASS. It may merge.**
- The first scheduled `flow-history` run, 39842023704, started 22 Oct 19:39:37 UTC (01:09 IST, 23 Oct) and concluded
  **success** (GitHub's API). It ended 19:40:57 UTC, so its push is before O8's 09:00 IST deadline. The push time
  itself comes from the job log, as the builder says [some].
- `FLOW_HISTORY_FROM = 22 Oct` for both rows is right: 21 Oct came from the back-fill, not the schedule. The diff is
  that constant, its use and the test's expected dates.
