# Judge 615: G14 package (v5 V1 beside v4), story/g14-v5-v1-candle-2 at d2c5b7e1c (judge J, round 1 of 2)

**FAIL**, lane 1: 1 should-fix, 2 minor. Gates on a trial merge with main 829afdc64 (a3e55be16; `FREEZE_v4.md` not
on main yet), `FNO_SLACK_BOT_TOKEN` set: 16,391 passed, 1 skipped, 14 xfailed, with no Slack post in the run's
window. ruff, format, check_imports (2,740), check_records (9,225) and check_numbers are clean. A first run showed 6
e2e kill-rerun failures; that was my own artifact (my plants were editing `history.py` in the same worktree), and the
clean re-run passed.

## Criteria and the orchestrator's points
| Item | Verdict | My evidence |
|---|---|---|
| Splice (C1) | MET | `history.py`: candle first, then live; `day < d`; `first_seen_at < cutoff`; void never used. My plants G1-G4 caught. A16b's 2026 catch-up rows carry `rv-candle-15m-v1` / `backfilled`, so W8's reader sees them |
| Real output | MET | `forecast-v5-v1 report` shows the five forecasters "not enough data yet" and gap 0.962 / 0.997 / 1.009. `capture` prints "FREEZE_v5_v1.md is missing" (exit 1); `freeze` prints "FREEZE_v4.md is not in this tree yet" (exit 1) |
| (1) Walk scope | MET (note m1) | 38 frozen files. G14's values come only through walked files (`series.py`, `rv_table.py`, `candle_rv_table.py`, `candle_history.py`, `sessions.py`, the calendar classes). The unfollowed imports of v4's `wiring.py` and `pack_wiring.py` (implied, Drive records, option terms...) feed nothing G14 uses |
| (2) Extra byte-checked files | NOT MET | S1 |
| (3) Card in `research/ideas/` | MET | the factory's default folder (`card_paths.py`), like EDGE1's; the ledger row names it |
| (4) Criterion 12's history half | MET for now (m2) | `freeze` refuses without `FREEZE_v4.md` in the tree, and `record_text` refuses a v4-checked file with no or another row |
| (5) Trial 100 | MET | main's ledger ends at 99, `LEDGER.md` "Total trials so far: 99", gates up to 99 |
| Freeze check | MET | my plants G5-G10 and G12 caught: walk list, bytes, v4-row mismatch, `rv_table.py` excluded, wiring unhashed, candle start dropped, frozen-on |

## Findings
**S1 (should fix) Five files are byte-checked only because of one constant, and they change often.**
- `candle_history.py:14` imports only `BACKFILLED`, a provenance string, from `global_cues/table.py`.
- That pulls in `global_cues/{table,collection,source}.py` and `storage/{row_log,raw_store}.py` (walk traced).
- Those five had 10 commits in the 10 days to 24 Oct, 3 of them in the last 3 days (A17, O9b), all outside G14's
  value path.
- Any such edit makes `check` refuse, and the record is written once. So G14's capture would stop for good and lose
  live days with no input changed.
- Fix (judged here): add the five to `SHARED` (recorded, not checked), with a test that `candle_history.py` imports
  only `BACKFILLED` from `global_cues` and that `BACKFILLED == "backfilled"`. That keeps the value pinned and the
  walk fail-closed for any other name.
- Optional, before `FREEZE_v4.md`: G7b imports the label from a stable module.

**m1** `build_session_calendar` lives in `fno/storage/wiring.py` (10 commits in 10 days). It is neither walked nor
hashed. It chooses the calendar class and file, so a swap there could change G14's sessions unseen. Name it in the
record's notes, or hash the single function's module.

**m2** At the record's commit, the orchestrator confirms `git merge-base --is-ancestor <FREEZE_v4 commit> <FREEZE_v5_v1
commit>` (criterion 12's history half). Today it is provable only through the tree check.

## Plants
12 planted, 12 caught.

## Addendum 1: round 2 (the last), story/g14-v5-v1-candle-2 at 9d9b4cafa
**PASS**, lane 1. G14's own change is 9d9b4cafa (`method.py`, `test_v5v1_method.py`, the story); e4f75c4b5 merges main.
- **Gates** on a trial merge with main 6a480457c (9e88ddc3d), `FNO_SLACK_BOT_TOKEN` set, nothing else touching the tree:
  16,500 passed, 1 skipped, 14 xfailed. ruff, format, check_imports (2,756), check_records (9,250) and check_numbers are
  clean. No post in any of the three channels during the run.
- **S1 closed.** The five files join `SHARED` (recorded with SHA-256, not checked). A test reads `candle_history.py`'s
  AST: only `BACKFILLED` is taken from `global_cues`, and it equals `"backfilled"`. `len(SHARED) == 9` is pinned. My
  re-plants were all caught: a second name from `global_cues`, the label's value changed, a tenth `SHARED` entry
  (`rv_table.py`).
- **m1: the pin is enough, with this said plainly.** A judged change can move G14's calendar without the capture
  noticing, because the capture hashes no part of `fno/storage/wiring.py`. Such a change must edit the pin test
  (`test_the_session_calendar_builder_is_pinned`), and the merge gates run that test on every merge. So the change
  cannot land unreviewed. That is the same protection the `SHARED` files have (judge 596 addendum 2, condition 2),
  and the rest of the calendar path is byte-checked: `load_session_calendar` and the classes in
  `research_data/calendar.py`. The CSV's rows are data, unhashed by design (2027 holidays to come). My plants were
  caught: the builder reading another file, and the calendar module moved to `SHARED`.
- **m2** is stated in the Claims and checked at the record's commit.

## Addendum 2: G14 Amendment 2 code, round 1, story/g14-amend2 at 7442d761f
**PASS**, lane 1. The change is in `fno/forecast_v5_v1/cli.py` and `freeze.py` (`FreezeBroken` beside `NotFrozen`),
their tests and the story's m1 word. The O1 step is not in it (checked).
- **Gates** on a trial merge with main 6109e1c18 (099ae0d06), `FNO_SLACK_BOT_TOKEN` set, nothing else touching the
  tree: 16,515 passed, 1 skipped, 14 xfailed. ruff, format, check_imports (2,757), check_records (9,252) and
  check_numbers are clean. No post in any of the three channels.
- **Real output:** `forecast-v5-v1 capture` prints "nothing written: FREEZE_v5_v1.md is missing" and exits 0.
  `fno.daily.steps.outcome` reads that line as `refused`.
- **The split matches 596.4.** Refused, exit 0: no record, 14:30, not today or not a session, frozen after today.
  Failed, exit 1 ("FAILED, no row written:"): a changed byte, another walk list, an unparseable date, `RecordConflict`.
- **The builder's choice, a missing "Frozen on:" line is `failed`: accepted.** `record_text` always writes that line,
  so a record without it was edited or truncated. That is a fault on a frozen input, like an unparseable date.
- **Plants: 9, all caught.** A broken freeze exiting 0; a refusal exiting 1; a changed byte, another walk list, a bad
  date or a missing line raised as `NotFrozen`; a missing record raised as `FreezeBroken`; a conflict refused; the
  "nothing written:" text lost.
