# Judge 587: BG1-w story text, the AI books' reveal wait does not count in BG1's cap (story/bg1w-reveal-wait @ 7b3ccbff5), judge E

**FAIL (round 1 of 2, text; 1 should-fix, 5 minor). Lane 1** (BG1's cap decides when the AI roles and books stop).
Judge E, own session. Text only (one file, `docs/stories/BG-budget.md`, +87): judged by reading. The doc-reading
tests, with the Slack token kept (DESK_DECISIONS 24 Oct, row 330): 853 passed, 15 xfailed.

## Rulings asked for

| Choice | Ruling | My evidence |
|---|---|---|
| The wait leaves the measured basis too | **Accepted, with the reason corrected (minor 2).** "BG1 counts working minutes only" (DESK_DECISIONS row 334) covers the basis too, and a smaller basis means a smaller cap: the books stop earlier, never later | `cap.py:73-79`: the cap and the basis are both sums of `minutes` |
| `sealed_at` null refused: never 0, never the whole run | **Accepted as the design; its cost and its source are not stated (finding 1).** 0 would understate the use. Start to end would put the wait into the cap, against Option A | `self_timed.py:33`; `cap.py:85-96` |
| Ledger column migration | **Accepted.** `rows()` refuses any other header (`usage_ledger.py:70-71`) and `_write` rewrites the whole file with `COLUMNS` (`:97-106`). So the file must change in the same commit as `COLUMNS`, as the text says. The old values can be tested with `git show`. No test or tool pins the header text (grep on main and on G11's branch) | |
| G11 interface | **Accepted.** G11 writes the `sealed_at` key in every file: `now_ist().isoformat()`, or null when the run never sealed (`run_timing.py` publish; `book_wiring.py:23`). `ist_time` refuses a value with no zone (`usage_reader.py:48-56`). The key is absent only from files written before G11 | |

## Findings

1. **Should fix: criterion 2's rule is presented as the owner's, and its cost is not said.**
   - **The source.** The gap list lists "No seal: working unknown, never 0, never the whole run" among "the decision's
     parts". The owner's words are only "Waiting minutes - Option A" (`conversations/2026-10-24.md:233`, DESK_DECISIONS
     row 334), so the rule is the builder's.
   - **The cost.** A refused file never becomes a ledger row: `ai collect` offers it again on every run
     (`usage_record.py:5`). Its fired session therefore stays not captured for the rest of the month, so a month under
     the alert line reads `unknown` until the month ends (`cap.py:94-95`). G11's C8 stop then fires the books, failing
     open (`budget_stop.py` on G11's branch: it stops only on `stop`).
   - **It happens.** A book run never sealed on 14 Oct (`conversations/2026-10-15.md:398`). Today such a file records
     its start-to-end minutes.
   - **Fix.** Mark the rule as reasoning (the builder's choice). State the month-long `unknown` plainly. Either put the
     choice to the owner through the orchestrator, or name the alternative weighed (for example start to end as an
     upper bound: it caps a little of the wait, but keeps the level known) and why it was dropped.

## Minor

1. Context says "4 book rows"; the ledger holds 7 (book2_hybrid 4, book3_ai 3) and 3 post-mortem rows. The gap list
   says "the 4 v2 book rows" too.
2. The reason given for leaving the wait out of the basis is not true: the basis does not stand for model capacity. Its
   development rows are turn wall times (`duration_ms`, `usage_export.py:7,106`), which include those sessions' own
   idle tool waits. Give the true reason: the owner's "counts working minutes only", and the smaller cap that follows.
3. Criterion 3's "byte for byte the row BG1 writes today" cannot hold with a new column. Say "the same values, with
   `wait_minutes` blank".
4. Criterion 5's C8 test ("after G11 merges (G11's file)") names no one who writes it. `MeterBudgetStop` sums
   `row["minutes"]`, so the claim holds by the code. Name the test's builder, or test the meter's rows here.
5. The gap list leaves out the things this change makes wrong. The dashboard contract (`fno-budget.yaml:19`: "session
   minutes") becomes untrue. G11's `usage_gaps.py` alert ("stopped before its reveal, or its timing could not be
   published") would give the wrong reason for a never-sealed refusal. Each collect also repeats the refused line. And
   criteria 3, 4 and 6 name no broken-code plant.

## Checked and true

The split in criterion 1 (3.50 and 26.17 minutes). The 10 ledger rows, all start to end. `minutes` alone feeds the
cap, the basis and C8. Until G11 merges, main's timing files have no `sealed_at`, so nothing changes in practice.

## Plants

None (text round). The text's plants: the wait into the cap and into the basis, a never-sealed run as 0 and as start
to end, the migrated values against `git show`.

## Addendum 1

**BG1-w story text, round 2 of 2 (story/bg1w-reveal-wait @ 57736a342): PASS. Lane 1.** Judge E. The only story change
is `docs/stories/BG-budget.md` (`git diff origin/main...57736a342 --stat`: that one file, +124); the rest is main merged
in. Judged by reading. Doc-reading tests with the token kept: 853 passed, 15 xfailed.

| Round-1 item | Outcome | My evidence |
|---|---|---|
| SF1: the no-seal rule called the owner's; its cost unstated | **Accepted, fixed** | Context now says only Option A is the owner's. The rule is "the builder's choice, one switch, for the owner", with both rules and their costs: under `no_seal_unknown`, the month reads `unknown` until it ends and C8 fails open, citing `usage_record.py:5` and `cap.py:94-95` as I found them. Criterion 2 tests both rules (G, E, B), with plants for the default, a row written as 0, and the unknown rule writing a row. The 14 Oct case is cited |
| m1: 7 book rows | Fixed | Matches the ledger: book2_hybrid 4, book3_ai 3, plus 3 post-mortem rows |
| m2: the basis reason | Fixed | It now gives the owner's "working minutes only" and the smaller cap (`cap.py:73-79`) |
| m3: "byte for byte" | Fixed | "the same values ..., with `wait_minutes` blank" |
| m4: who writes the C8 test | Fixed | This story's test checks that the meter's rows carry only working minutes in `minutes`. The `MeterBudgetStop` test is assigned to G11's builder session. C8 sums `row["minutes"]` (`budget_stop.py` on G11's branch) |
| m5: gap-list omissions | Fixed | The contract (`fno-budget.yaml:19`, `x-fill: not_built` at line 11, true), the `usage_gaps` alert text, the repeated refused line, and plants for criteria 3, 4 and 6 are all named |

**Ruling on the constant instead of a config key: accepted.** BG1's tunable numbers live in `config.yaml`'s `budget`
section (`CapSettings.from_config`). This is a rule choice that changes once, when the owner answers, and is lane 1
either way. As a config key it would have to be passed to every place that builds the reader, and one of them is
G11/F8c's `usage_record.py:47` (`SelfTimedUsageReader(path)`), which BG1-w does not edit. A named value in
`fno/budget/constants.py` (that module's own constants file, by its docstring) is one line to change and keeps
`fno/ai/` untouched. Condition for the code round: the tests pass each rule explicitly, not only the default.

**Ruling on the default `no_seal_upper_bound` (reasoning only, pending the owner).** It is safe for the budget: an
over-count makes the books stop earlier, never later. It keeps the level known. It caps idle minutes only of runs
that never sealed. Those runs have no seal-to-reveal split, so Option A's "the wait is never capped" has nothing to
apply to; the text says so. The owner's answer decides.

## Findings

None blocking, none should-fix, none minor.

## Plants

None (text round). The text's plants: one per criterion, plus the switch flipped. The code round runs them.

## Addendum 2

**BG1-w code, round 1 of 2 (story/bg1w-reveal-wait @ 3d19625a2): PASS. Lane 1.** Judge E. The code is
`self_timed.py` (83 lines), `usage_ledger.py`, `report.py`, `usage_reader.py`, `constants.py`, plus the ledger file
and two test files.

| Criterion | Result | My evidence |
|---|---|---|
| 1 working minutes | MET | `_split`: working = seal − start, wait = whole − working (the parts add up). The example recomputed by hand: 29.67 − 3.50 = 26.17. B1 caught (6 failed) |
| 2 never sealed, both rules (587.1's condition) | MET | `SelfTimedUsageReader(path, no_seal)` is tested under each rule. B4 (upper bound written as 0), B5 (unknown writes a row), B6 (default flipped) and B14 (unknown rule name accepted) each caught |
| 3 no key | MET | B7 (a missing key read as never sealed) caught |
| 4 the column | MET | `_check_row` refuses negative, nan, inf and text; a blank is allowed (B9 caught). The migration test compares the file at `git show` before the column; my B13 (one old value 0.42 → 0.43) caught. The diff shows only the column added, blank in all 10 rows |
| 5 never capped | MET | B2 (wait added to the cap) and B3 (wait added to the basis) each fail `test_the_cap_and_the_measured_basis_count_working_minutes_only` |
| 6 meter | MET | B10 (sums `minutes`), B11 (row's wait blank) and B12 (a 0.00 wait not counted) caught. Real meter, before and after: `diff` shows exactly one added line, "none recorded" |
| 7 gates | MET | Trial merge a68b11b10 with origin/main 68721eed0: ruff clean, format clean (2,515 files), imports clean (2,644 files), record scan clean (9,095 files). Full suite with the token kept: **15,662 passed, 1 skipped (`growwapi`), 15 xfailed, 0 failed** |

**Plants:** 14 planted, 14 caught, each alone on `tests/budget` and `tests/ai` (257 tests), restored after each.

**Stated limits, ruled:**
1. **Cost allocation by `minutes`** (`allocation.py:38-43`; F9a's `role_value/cost.py:43-44`). **Accepted as the
   right consequence:** the plan is used by work, not by a timed sleep, so the books' cost share should follow working
   minutes. But it moves an evaluation input: F9a's per-unit cost falls for v4 days. October mixes the two bases (the
   v2 rows include v2's short wait). Tell F9a's owner and the owner; no code change here.
2. **The branch rewrites every ledger line.** **Accepted, with conditions for the merge.** Merge outside 15:15-15:35
   IST. Main's ledger still has the same 10 rows (the trial merge has no conflict). A row added on main before the
   merge conflicts loudly and needs its blank `wait_minutes` in the merge. After the merge, old code reading the file
   fails on the header check (`rows()`), and that shows as a "refused" line, never a silent wrong row.

## Findings

None blocking, none should-fix, none minor. The owner's no-seal answer is still pending; the default is the upper
bound, as 587.1 ruled.
