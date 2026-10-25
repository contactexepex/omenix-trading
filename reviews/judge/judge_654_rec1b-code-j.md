# Judge 654: REC1b daily record, code, story/rec1b-daily-record at 2e039a045 (judge J, 1 of 2, round 1)

**FAIL**, lane 1: 2 should-fix, 2 minor. Trial merge with main 7d94fe02 (d9d312cd): 16,927 passed, 1 skipped,
13 xfailed; ruff, format, check_imports (2,801 files), check_records (9,351) and check_numbers clean.

## Criteria (the orchestrator's checks first)
| Item | Verdict | My evidence |
|---|---|---|
| No source complete unless its own record shows it ran | MET | `school_source.py`: `ok` with OFF or NOT_A_SESSION, `refused` (TOO_LATE), `failed` (any stop or warning exits 1) and missing are all unavailable. An `ok` run with no seal, or a bad seal, is an input failure. `desk_source.py`: a named run whose manifest checks both ways and every hash matches. Plants X3-X7 caught |
| Real money: DO NOT TRADE without rung 3 and RM1 | MET for the answer; criterion 7 PARTLY (S1) | `_eligible` takes established versions that RM1 names only, and none on a failed data check (X14, X15 caught). `NoEligibility` is empty today |
| Sealed before the post | MET | `run.py`: save (receipt pushed) and only then `alerts.send`. A refused push posts only the problem line; a receipted day is never posted again. X16, X17, X22 caught |
| Point in time | MET | `made_at` is taken before any read. Evidence covers sessions first_counted..day-1 only (X8 caught), push receipts strictly before `made_at` (REC1a), closed roads not counted (X9 caught) |
| Card unchanged | MET by reading; test missing (S2) | No file in `fno/cards/` changes. `card` is step 17 and `recommend` step 21 of 30 in `DAILY_RUN_STEPS`, so the day's card is built first |
| Book 1's shadows never traded | MET | `traded` needs outcome `chosen`; Book 1 writes `shadow: would trade` for a shadow (`fno/constants.py:277`). X2 caught. X1 (the mode check removed) survives because the outcome check already excludes shadows: a redundant second guard, not a gap |
| Reason order, rung 3 only (crit. 2, 4) | MET | `test_decide.py` covers each adjacent pair; X13 caught |
| Inputs fail as inputs | MET | Unreadable run log, decision file, seal and weather each give `data_check_failed`. X10, X11, X12, X21 caught |
| Rung rule pinned | MET | X18 caught |
| Line privacy and wording (crit. 10) | MET | Version IDs, codes, counts, path and hash only; "Recommender (not the card)" |

## Findings
**S1 (should fix) Criterion 7's disagreement rule is not built.** Section 1 says: "If RM1 and the rung disagree
(eligible below rung 3), the answer is `DO_NOT_TRADE_REAL_MONEY` with `data_check_failed` and an alert naming both".
- My probe: `decide` with `rm1_eligible={V}` and V at rung 0 or rung 2 gives `do_not_trade_real_money` with
  `no_established_version`, and no alert.
- The answer is safe, but the record hides a contradiction between two gates.
- It cannot happen today (`NoEligibility` is empty), but the rule belongs in `decide`. RM1's reader will be plugged
  into the port without touching `decide` again.
- Fix: `_reason` gives `data_check_failed` when `rm1_eligible` names a version below rung 3; `run` alerts both names.
  Add a test per rung 0-2 and plant "the disagreement ignored".

**S2 (should fix) Three acceptance criteria have no test.** My plants on each survive:
- Criterion 8's import test: the recommender must import no fill, order or desk-writing code. Plant X23 adds
  `from ..desk import exits` to `decide.py`; no test fails.
- Criterion 14: a holiday or muhurat-only day writes nothing. Plant X19 removes `cmd_decide`'s `is_session` check;
  no test fails.
- Criterion 10's golden file: the card is byte-identical with the step on and off. There is no golden-file test.
- The code is right in all three cases by reading. The criteria name these tests and their plants, so add each.

**m1 (minor) Criterion 9 says "different bytes refused and alerted".**
- The design adopts the first record and prints "already recorded" without an alert. That is safer, but the text
  should say so.
- A run that pushed the receipt and then died before `send` never posts that day's line, and nothing alerts it. A
  rerun only prints ALREADY. Say this in Known limits or alert it.

**m2 (minor, for the owner, reasoning only)** A rung-3, RM1-eligible version is shown ELIGIBLE on a `step_problems`
or `weather_red` day while paper says NO_TRADE. My probe shows this; it follows section 1's text, which ties real
money only to rung 3 and RM1. Worth one line of the owner's confirmation before rung 3 is reachable.

## Plants (mine): 20 of 23 caught
X2-X18, X20-X22 caught: the desk outcome, hash and both-ways manifest; school OFF, status, missing seal; day d; closed
roads; missing weather; quote gate; school in step problems; the unread source; eligible on a data failure; the rung-3
rule; post before save; already posted again; the rule pin; candidates from an unavailable source; problems not
failing the step; adoption overwritten. Survivors: X19 and X23 (S2), X1 (redundant, above). Targeted tests:
`tests/recommend` and `tests/daily`, run in their own worktree with PYTHONDONTWRITEBYTECODE=1.

## Notes
- Slack, with FNO_SLACK_BOT_TOKEN set (1792890618-1792891186): nothing in any of the three channels.
- I did not coordinate with judge K.

## Addendum 1: round 2 (the last), story/rec1b-daily-record at d82e459d7 (4908677a plus a merge of main)
**PASS**, lane 1: S1 and S2 closed, m1 closed, m2 ruled by the orchestrator. Trial merge with main e114ed99
(a2fe22bb): 16,992 passed, 1 skipped, 13 xfailed; ruff, format, check_imports (2,807 files), check_records (9,362)
and check_numbers clean.
- **S1 closed.** `disagreeing()` makes `_reason` give `data_check_failed` when RM1 names a version below rung 3 or not
  rated, and `gather` alerts it by name. Plants Y1 and Y2 are caught.
  - My X15 (`_eligible` without its rung-3 check) now survives, as an equivalent mutant: such a version always triggers
    `disagreeing`, and `data_check_failed` blocks real money.
- **S2 closed.**
  - Criterion 8: `test_reads_only.py` catches my X23 import.
  - Criterion 14: `test_cli.py` catches X19 for a weekend, 26 Jan and Sunday 8 Nov.
  - Criterion 10's card part is now a construction argument: `recommend` runs after `card`, and
    `test_no_card_module_reads_the_recommender` checks no card module imports it. That proves the card unchanged at
    least as well as a golden file would.
- **m1 closed.** A receipted day re-sends its own stored line, labelled "Re-sent". The discarded answer's problems are
  not alerted. Y6 and Y7 caught.
  - Note: a rerun after an input-problem day re-sends the record that stands, and the step then reads `ok`. The record
    still says `data_check_failed`, and the first run alerted it. Acceptable; say so if the run log's `ok` ever matters.
- **m2 and `quote_gate_failed` (the orchestrator's question): I agree with the addition** (reasoning only).
  - A failed quote gate means the day's prices are unusable; the card already maps it to `data_check_failed`.
  - An "eligible for your own review" on such a day would point the owner at a trade whose day inputs failed.
  - `BLOCKS_REAL_MONEY` = {data_check_failed, step_problems, quote_gate_failed, weather_red}. Y3, Y4 and Y5 are caught.
  - Left open for the owner: `brake` (the version's own drawdown brake) still allows ELIGIBLE. I would block that too;
    it is a version condition, outside the ruling. Not reachable before rung 3.
- **Plants: 12 of 14 caught.** Caught: X13, X16, X17, X19, X23, Y1-Y7. Survivors: X1 (redundant guard, as in round 1)
  and X15 (equivalent, above). Run with PYTHONDONTWRITEBYTECODE=1 in their own worktree.
- Slack, with the token set (1792892265-1792892845): nothing in any channel. I did not coordinate with judge K.
