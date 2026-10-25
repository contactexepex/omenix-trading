# Judge 521: MS-SIM-d (d2-d4), the practice fleet, runner, report and command

**Scope:** story/ms-sim-d2 at 6812b89c (code 6634659a; builder session_01W2JE3W9xYftEDWTysHkdVC), diff from main. I
judged the simulator's files (`fno/school/simulator/practice/`, `command.py`, the two lines in `fno/school/cli.py`,
tests).
- MS-P1j's seams in the same diff (`fleet/fill.py`, `runner.py`, `slot.py`, `fleet_wiring.py`, `wiring.py`) were judged
  as 507.8/507.10 and 519 (and addendum). I did not re-judge them.
- d1 is judge 515.

Story 7.4 SIM-d criteria 1-16 and the SIM-d2-d4 Claims. Lane 1 (practice). Round 1 of 2. Judge H
(session_01KNkZVoWvXMkoihKrrXk5Xa).

**Verdict: FAIL.** 2 should-fix, 4 minor. The fleet design is right.

## Checked
| Item | Result | Evidence |
|---|---|---|
| A second `SchoolFleet`, no copy of `fleet_on` | MET | `fleet.py` builds the pilot's `SchoolFleet` from injected parts and `books_on`. Plant (`rules=PRACTICE` dropped) caught |
| No write under the pilot's paths | MET | `_refuse_pilot_paths` (journal, research/school, receipts); plant caught. The default home is `work/school_practice/`, git-ignored. After my real run, `git status` was clean |
| DATA_SPEND refusal by name before any read (16) | MET | `RunWindow.check` in the runner and in the command. Plants (check removed, last day not checked) caught |
| 15:30 practice clock | MET | Plant (15:31) caught |
| Practice margin labelled (factor 2.1, after the fact) | MET | It's in the labels. Plant (the pilot's dated lookup put back) caught. See minor (a) |
| "local only, not archived" as the first line | MET | Plant (line removed) caught |
| Label on every line and every record (3, 15) | MET | My run: all 216 stored record lines carry `"label": "practice (simulator)"`. Plants (record label, line prefix) caught |
| AI card refused (5) | MET | Plant caught |
| Archive warmed before the fleet (deadline) | MET | Plant caught |
| Real data | MET | My run of `python -m fno school practice run --from 2024-03-04 --to 2024-03-06`: 3 sessions x 3 scenarios, 9 road-days, 3,528 legs, priced 0, untraded 1,005, impossible 964 (27%), insufficient 1,559. Hosts: Google only (12 OAuth, 187 Drive). 3 min. Every driver `no_trade`, by reason in the records: `no_valid_quotes` (CS1, DB1, DR1, RC1, REF, WS1), `no_expiry_in_window` (PS2-5, KL1), `rule_not_fired` (DR1, 3 times) and N0's `n0` |
| Gates | MET | pytest -n 6: 14,114 passed, 18 xfailed. ruff check/format, check_imports and check_records are clean. Largest new file is 100 lines |

## Findings
1. **Should-fix: criteria 2 and 11 rest only on strict xfails, so their code is untested at this tip.**
   - `test_a_window_runs_every_scenario_over_every_session` (criterion 2) and
     `test_a_position_opened_before_the_stt_change_and_met_after_it_keeps_its_own_charges` (11) are both
     `xfail(strict=True)`, waiting for MS-P1j's ticket-account fix.
   - My plant replacing `cfg_on(parts.cfg, parts.terms, session)` with `parts.cfg` (no dated STT in the fleet)
     **survived**. The Claims list "dated config bypassed" as caught, which is not true at 6634659a: a strict xfail fails
     whatever the cause.
   - Expected: tests that run now and need no second session:
     - one session under all three scenarios, each labelled, with the insufficient list and the unpriced counts;
     - a fleet built for a session before 1 Apr 2023 charges that date's STT on its fill (and one after it the new
       rate).
   - Keep the xfails for the multi-session cases.
2. **Should-fix: DATA_SPEND doesn't name the simulator's read of the forward captures.**
   - `wiring.learn_spreads` reads every recorded 15:00 capture from 13 Oct 2026 to today. Those days are `forward` (row
     26) and `registered` for trial 99 (row 30). Row 30 says they are "read only for the capture gate and the drivers'
     20-session history windows".
   - The spread learning is by design (response 327 correction 6) and reads spreads, not outcomes, but the register is
     now wrong. After `school.first_counted` it will also be learning from counted sessions.
   - Expected: rows 26 and 30 name this read (the simulator's spread model, bid-ask only), or the orchestrator rules
     otherwise.

**Minor:**
- (a) `PRACTICE_MARGIN_LABEL` hard-codes "stress factor 2.1 (set 16 Oct 2026...)". The code uses the file's latest row
  (today 18 Oct, 2.1). The first recompute that moves the factor makes the label false. Build it from the row used.
- (b) The report prints outcome codes without reasons (`no_trade=9`). "No valid quotes" and "the rule did not fire"
  read the same, and they were mixed in my run. Show the reason codes.
- (c) `refused_for_margin` is untested: my plant zeroing it survived.
- (d) Windows start on 1 Jan 2019, but the SPAN archive starts on 2 Jan 2020 (`NseSpanBodSource.first_day`). Every
  2019 entry would be refused by margin with no file. It fails closed and is counted, but say it in the Claims or start
  the margin-checked window in 2020.

**Named exceptions, accepted:**
- Criterion 8: records are local and git-ignored, not in Drive. This is the orchestrator's hard limit, stated in the
  first line.
- Criterion 13 (lot per expiry) follows as its own commit.
- The two strict xfails wait for MS-P1j's fix (see finding 1 for what must not wait).

## Plants
13 planted, 11 caught, 2 survived (finding 1 and minor c).

## Note after the verdict (6d09451e, not a round)
The builder's messages crossed this verdict. The tip 6d09451e merges MS-P1j's ticket-account fix and turns both strict
xfails into plain tests.
- My plant on `cfg_on` is now **caught**, and so is a one-scenario plant. **Finding 1 is met there.**
- Finding 2 (DATA_SPEND rows 26 and 30) and the four minors stand. The `refused_for_margin` plant still survives.
- Round 2 is judged on the builder's next tip.

## Addendum 1

**Round 2 of 2:** story/ms-sim-d2 at 08bfbc1d (code 32195d2c). Against today's main, the branch holds only the
simulator's files, its tests, `fno/school/cli.py` (3 lines) and DATA_SPEND. **Verdict: PASS.** Lane 1.

**Gates (my run):** pytest -n 6: 14,144 passed, 16 xfailed (no strict xfail of this story left). ruff check/format,
check_imports and check_records are clean.

**Findings:**
1. **Untested criteria 2 and 11: ACCEPTED.** These are plain tests that run now.
   - Single-session dated STT: 31 Mar 2023 charged 0.05%, 3 Apr 2023 charged 0.0625%. My `cfg_on` plant is caught.
   - One session under all three scenarios.
   - The two multi-session tests. The Claims now correct the earlier "caught" statement.
2. **DATA_SPEND: ACCEPTED against the orchestrator's ruling.**
   - A new row: "Bid-ask spreads of the 15:00 captures (A4, A4c, A4f) ... `exposed` ... cost input for practice only,
     no outcome".
   - Rows 26 and 30 name the read too.
   - The binding condition ("practice results are never used to choose, tune or rank a counted driver") is in the
     story, the register and the report's second line. Plant (line removed) caught.

**Minors:**
- (a) **ACCEPTED.** The margin label is built from the row used. Plant (2.1 fixed again) caught.
- (b) **ACCEPTED.** The report shows `outcome:reason`. Plant caught.
- (c) **ACCEPTED, and the builder found a real counting error behind it.** A law-3 failure becomes `ticket:
  account_limit`, so "refused" read 0. It is now `failed_margin` over the law results. Plant caught.
- (d) **ACCEPTED.** Sessions before 2 Jan 2020 (the archive's first SPAN file) are refused by name, counted and not run.
  Plant (running them) caught.
- **Criterion 13 (new): MET.** My real read through the practice catalogue: BANKNIFTY-M on 2 Jun 2025 is open, with
  lots 30 (26 Jun 2025) and 35 (31 Jul 2025), `lot_for` the far expiry 35, Google hosts only. Plant (one lot for every
  expiry) caught.

**Plants:** 7 this round, 7 caught.
