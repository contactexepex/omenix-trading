# Judge 159: E2c code, paper fills, marks and equity history in Drive: `story/e2c-fills-to-drive` 7823796c (lane 1)

Judge B. Story `docs/stories/E-paper-desk.md` E2c (text PASS, judge 148 addendum 1). Claims: "Code round" in
`reviews/claude/response_148_e2c-fills-to-drive.md`. Base `main` eef75e44, trial merge with `main` ed488089.

## Gates (run myself)
- Trial merge 7823796c + `origin/main` ed488089, clean merge, FNO_SLACK_BOT_TOKEN unset: **5,882 passed, 0 failed**.
  `ruff check` clean, `ruff format --check` clean, `check_imports.py` clean. `tests/test_code_size.py` passes (largest
  new file `private_files.py`, 101 lines).
- **The rename to response 150 is not in at 7823796c**: the branch still adds `response_148_e2c-fills-to-drive.md`,
  which collides with G9's `response_148_g9-miss-rule.md` on `main`. Fix it before the merge.

## Criteria
| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | No committed file holds a fill price, mark, cash or marked equity after a fixture day | MET | I ran both fixture days myself and read every committed file (16 paths). Account files and `private.json` never appear; only `private.sha256`. The run log holds outcomes, snapshot IDs and hashes, plus the closed trade's net (`net Rs -513.64`), which is public as closed equity anyway. None of the 28 private values (fills, quotes, mids, ledger amounts, open-book cash) appears |
| 2 | `daily_totals.csv` has the five columns, matching Drive by hand | MET | Recomputed by hand: 14 Oct opening 2,000,000.00 with t1 open and 4 fills; 16 Oct t1 closed at net -513.64 gives 1,999,486.36, 0 open, 1 closed, 4 fills. The Drive ledger's amounts sum to the same |
| 3 | The readers read the same values after the shared download | MET | Eight reader tests and six command tests. Deviation 3 accepted below |
| 4 | A failed Drive write stops with E3's alert; nothing committed; the rerun repeats the write | **NOT MET** | Blocking 1 |
| 5 | A last session with no `exits` step blocks entries, one alert, exits run | **PARTLY** | Works for a stop after a step. Fails for a stop at the download or recovery: should-fix 1 |

## Blocking 1: one failed upload after the ledger leaves Drive half-written, and every rerun then crashes
- **What happens.** `PrivateFiles.push` uploads the five files one by one, ledger first: ledger, equity history,
  positions, desk fills, desk events. A single 503 on any file after the ledger leaves Drive with the new ledger but the
  old desk records.
- **The rerun crashes.** The rerun (fresh container, as the alert tells the owner to do) pulls that mix. E1's
  `apply_fill` finds the fill IDs already in the ledger. The desk's `open_positions` then finds an open trade with no
  desk fill row: `IndexError` at `fno/desk/status.py:60` (`fills[0]`), from `entries.py:119` in the fills step.
- **No recovery.** It is not a `CommitFailed`, so no alert. Drive stays in that state, so every rerun crashes the same
  way, and later days crash too (exits also call `open_positions`).
- **Reproduced.** The test's `FailingWrites`, failing `replace` only for paths ending in `equity_history.csv`,
  `positions.json` or `desk_fills.csv`. Run 14 Oct: `RunStopped`. Then `fresh_container`, then `run.run(14 Oct)`:
  `IndexError` in all three cases. Failing on `desk_events.csv` recovers.
- **Why it is real.** Each file is its own Drive request, and a single transient 503 is the failure criterion 4 names
  (and A4b's alerts plan for). The criterion's test fails every account write, so the first upload, the ledger, fails
  and Drive stays consistent; the mid-push case is untested.
- **Root cause.** The ledger is E1's "already done" marker (fills are idempotent by fill ID), yet it is uploaded first.
- **Fix (builder's choice; this is the simplest I see).** Upload the ledger last, after the desk records, equity
  history and positions:
  - the desk records are keyed and idempotent;
  - `positions.json` is rebuilt from the ledger whenever a writer opens (`AccountWriter._recover`);
  - so a partial push leaves Drive's ledger at the old state, and the rerun repeats the whole write.

  Check that `DeskJournal.record_fill` accepts a row it already holds unchanged. Test it with a failure on each of the
  five files in turn, each followed by a fresh-container rerun that fills once.

## Should-fix 1: a stop at the download (or the recovery) does not block the next session's entries
- **What happens.** `_stopped_before_exits` blocks only when the last log has steps but no `exits`. A run stopped at
  `the download of the private paper records`, which E2c adds, writes no step at all.
- **Reproduced.** With Drive reads failing on 13 Oct (token expired), the 13 Oct run stops, alerting "exits not
  reviewed today". With Drive back on 14 Oct (fresh container), t1 and b1 both open, with no alert.
- **Why it is real.** An expired or missing Drive setting is a named normal case (CLAUDE.md step 4, A4b). The story's
  rule reads "a run log holding no `exits` step", and an absent log holds none.
- **Fix.** Also block when the last session has no run log at all, while an earlier run log exists (so the desk's
  first day is not blocked). Or record the download or recovery stop in the day's log. Test: a download stop on 13 Oct
  blocks 14 Oct's entries.

## The builder's three deviations and known limit
1. **Drive path `paper/journal/<book>/account/`** instead of `paper/<book>/account/`: **accepted**. One path rule
   covers accounts, packs and scoreboard B. Nothing reads the Drive path except `PrivateFiles`. Align the story's
   Scope line.
2. **T1's card reads the downloaded `positions.json`**: **accepted**. The story text asks for exactly this
   (`DownloadedRecords`). A missing file says "not downloaded from Drive", and the card still names what it used.
3. **Criterion 3 tested at the record seam for E6 and scoreboard B**: **accepted**. Both build only from
   `paper_accounts` and `DeskRecords`, which the test compares. The commands are shown to download before building.
- **Known limit, shadow accounts unseen in a fresh container**: **accepted as a limit**. `start_shadow_books` has no
  caller (checked). The story that wires shadow starts must list them from a committed source. Record that in that
  story's dependencies.

## Merge steps (checked)
The order is safe:
1. Move to Drive. `move_accounts` never overwrites different bytes (REFUSED, exit 1, and no `daily_totals` then).
2. Commit `daily_totals`.
3. `git rm -r --cached journal/*/account`, which keeps the local copy.

A scheduled run between the merge and step 1 is harmless:
- `pull` leaves local files when Drive holds none, and the account files are still tracked until step 3;
- no strategy is approved, so no fill is written.

Two additions:
- (a) In step 1, check each line says "uploaded" or "already in Drive" for all **nine** files (three books × ledger,
  equity history, positions; no desk files exist yet).
- (b) No `private.json` and no `research/scoreboards/B/` file is tracked on `main` (checked), so step 3 needs nothing
  more.

Rule 8 after the merge: run `python -m fno account show book1_rules` in a fresh checkout with Drive settings. It must
print the opening row.

## Project rules
Interfaces and roots are respected:
- `PrivateFiles` sits on A4b's `IndexFileStore`;
- it is wired only in `fno/desk/wiring.py`, `daily_wiring.py` and `pack_wiring.py`;
- its constants `PAPER_AREA` and `DAILY_TOTALS_FILE` are in `constants.py`.

`GitAccountSync` is removed with its tests (one writer). No secrets, e-mail addresses or model names. WORK_REGISTER row
E2c is this session's; E4c and E5b wait on it, so there is no overlap.

## Notes (one line each, not blocking)
1. `daily_totals.csv` has one row per date with a ledger row, not per session. Closed equity cannot change without a
   fill, so nothing is lost; say so in the story text.
2. The story's Status line still says "story text"; update it at merge.
3. `market publish --local` now needs Drive too (the download runs first); fine for production, but note it for local
   runs.

**Verdict: FAIL for 7823796c**: blocking 1 (criterion 4), should-fix 1 (criterion 5), and the missing response
rename. A re-check needs the fix commits and the new tests only. ChatGPT's review (rule 9) follows the PASS.

## Addendum 1 (15 Oct 2026): fecb99fc (fix commits 30e819e8 code, fecb99fc text; rename dce63510)

Answer table: `reviews/claude/response_150_e2c-fills-to-drive.md`, "Answer to judge 159".

**Gates:** trial merge of fecb99fc with `main` 530bf2a6: **5,887 passed, 0 failed**. The only conflict is the
`reviews/claude/README.md` index; keep both rows. `ruff check`, `ruff format --check` and `check_imports.py` are clean.
`tests/timetable` + `tests/desk`: 163 passed.

| Finding | Status | Evidence |
|---|---|---|
| Blocking 1: a part-way push | MET (fix differs from mine; see the ruling below) | New order: desk fills, ledger, positions, equity history, desk events. My own probe now passes for all five failure points: a 503 on each file, then a fresh-container rerun, leaves Drive with header plus opening plus 4 ledger fills, 4 desk rows and 1 event, with t1 open. The builder's parametrized test covers all five files. Planting the old order back fails 3 of the file's 10 tests |
| Should-fix 1: a download or recovery stop | MET | `_stopped_before_exits` now blocks when the last session has no log and an earlier log exists. My probe without an earlier log: 14 Oct opens (the desk's first day, by design). With a 12 Oct log added: 14 Oct is blocked with one alert naming 13 Oct, and the exits run |
| Response rename | MET | `response_150_e2c-fills-to-drive.md` (dce63510) |
| Notes 1-3, deviation 1 Scope line | MET | Story text updated (fecb99fc) |

**Ruling on "ledger last": the builder's rejection is correct, and I withdraw my order.**
- I missed that an entry's desk event is the desk's own "done" marker (`entries.py:117-119`). With the events uploaded
  before the ledger, a 503 on the ledger leaves the "opened" event with no ledger fills. The rerun returns the recorded
  outcome and applies nothing, so the cash is silently wrong. That is worse than the crash.
- I planted my order (equity, positions, desk fills, events, ledger) myself: the `cash_ledger.csv` case fails
  (`assert 0 == 4`). One of 10 tests fails, not the builder's "3 of 9" (that count was for the builder's own variant),
  but the conclusion stands.
- The builder's order puts each "done" marker after the data it marks:
  - desk fills before the ledger, since a ledger fill without its desk row crashes readers;
  - the events last;
  - the rebuilt views in between.

**New minor (not blocking):** the exits path uses the same order, but only entries are tested part way. An exit's
rerun finds the trade closed in the ledger and skips it, so the order holds there too (reasoning). No test needed under
the simplicity rule.

**Verdict: PASS for fecb99fc.** Next steps:
- ChatGPT's review follows (rule 9, fills). Any change after it comes back to me.
- Merge steps as in the main verdict, plus addition (a): all nine account files must print "uploaded" or "already in
  Drive" before the `git rm --cached`.

## Addendum 2 (15 Oct 2026): ChatGPT review 115 fix, fecb99fc..1ac23294, and `story/e2c-merge` 1cc9d80b

The fix answers review 115's Q3. It is in the builder's response 150, "review 115", and the orchestrator's response
162.

**The fix (`daily_run._unreviewed`, `daily_steps.fill`):**

| Last session's state | Who is blocked |
|---|---|
| No log, while an earlier log exists | every book |
| A log without its exits step | every book |
| An exits step where a book has an `error` or a non-empty `waiting` list | that book only |

Other books fill as usual, and one alert names each blocked book and why. The block is decided per book, as the review
asked. A failure that repeats every day keeps blocking, because each day's exits step records the error again.

**Tests and plants:** `tests/timetable` passes, 96 tests. I planted three breaks myself, and each is caught:
- ignore `waiting`: 1 test fails;
- ignore `error`: 1 test fails;
- block every book whenever one book is unreviewed: 2 tests fail.

The reconcile test is review 115's non-blocking item. The fill reaches Drive, then the push of the daily totals is
rejected. A fresh-container rerun fills nothing twice and commits totals equal to `daily_totals(Drive account)`. It
passes.

**The builder's doubt, ruled: sound (reasoning only).**
- On a day without a snapshot, an open trade's price exits (stop and profit) are not checked, and `waiting` lists only
  exits due without prices.
- Not blocking that case adds no risk beyond a normal day. E3 fills, then reviews exits, at the same execution snapshot,
  so the next valid day checks the unchecked stop at the very snapshot of any new fill. On every normal day a stop and
  a new entry can already share a snapshot.
- C2's decision-time view still counts the old position.
- The real cost of the missed day is the data gap: a stop that would have fired a day earlier fires later, at that
  day's price. Blocking entries would not recover it.
- Blocking every day without a snapshot while a trade is open would stop entries on each data gap for no matching risk.
- If the owner wants price exits re-checked before any new entry, the change is E3's order (exits before fills), as
  the builder says. That is the owner's decision, not a defect here.

**`story/e2c-merge` at 1cc9d80b** (main f23c5166 + fecb99fc, judge 163's `book1_cli.py` resolution, then 1ac23294):
- `book1_cli.py` keeps E5b's single handler.
  - Note a: `PrivateFilesUnavailable` gives its own alert, "nothing decided", before the `CommitFailed` branch.
  - Note b: `--commit-run` skips the download, so it works with Drive down.
- `daily_steps.py` keeps main's `DOUBLE` line and adds the per-book block. A blocked book skips the double-run check,
  which is harmless, since it fills nothing.
- Trial merge of 1cc9d80b with current `main` 9bbb6f43: **5,908 passed, 0 failed**. `ruff check`, `ruff format
  --check` and `check_imports` are clean.
- The only conflict is the `reviews/claude/README.md` index; keep both rows.

**Nit (not blocking):** `test_fills_to_drive.py` has the comment "t1's time exit is due from 16 Oct" moved onto the
`MONDAY` line. Move it back to `CLOSE_DAY` at the next edit.

**Verdict: PASS for 1ac23294, and for `story/e2c-merge` 1cc9d80b as the merge tree.** ChatGPT's points are answered
with tests. Merge steps as before: all nine account files must print "uploaded" or "already in Drive" before the
`git rm --cached`. After the merge, run rule 8: `account show book1_rules` from a fresh checkout.
