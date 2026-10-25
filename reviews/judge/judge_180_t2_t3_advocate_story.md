# Judge 180: T2 + T3 story text, the devil's advocate on the card (quality rule 1; judge E)

Date: 15 Oct 2026 (UTC). Branch `story/t2-t3-advocate` at **1468fde744dae4219ac2cc6fe4018b2e63b2e191**. Diff:
`docs/stories/T-cards.md` (T2 + T3), response 174, the register row, a log line. Text only. The builder's options
A/A/A are assumed.

## Verdict: FAIL (story text): 2 blocking, 3 should fix

The core idea is right: T2 reports, T3 reuses `fno/advocate`. The text fails on the timeline it reads from, and on two
design 7.3 items that are in neither list.

### What I checked and found right

| Check | Status | Evidence (mine) |
|---|---|---|
| C4 already blocks and logs | MET | `fno/checks/validity_failures.py` appends to `journal/<book>/validity_failures.csv`. `BookTradeValidator` writes it at the book's decision (`fno/checks/wiring.py:109`, `DESK_DECISION_TIME` 15:00) |
| No AI caller added | MET | `fno/advocate/` holds `Advocate`, `RoutineFileAdvocate` and `ObjectionCheck` (`MAX_OBJECTIONS, MAX_WORDS = 5, 40` as module constants, so moving them to the constructor is the only change). `SignalFile` is in `fno/learning/writer.py:41` today, as the text says |
| Privacy | MET | The subject is the card's public lines only, with a planted-strike test (criterion 6). This fits the Drive-only card records decision |
| The three missing rules exist nowhere | MET | My grep: no holding-window event block, no stock-option settlement block, no failed-variant search (R1 is not built). Out, with the owner question |
| Weather RED not enforced | MET | Correctly out. The card shows the colour and claims no block |

### Blocking

1. **T2 reads records that do not exist yet when the card is posted.**
   - Design 4.1 posts the card at 15:08 (`card_sent_at`), with `decision_finalized_at` at 15:06.
   - The desk's own timetable (`config.yaml` `desk.timetable`) runs later: pack 14:58, retried to 15:10;
     `decision_deadline` 15:12; `execution_snapshot` 15:15; fills by 15:20.
   - `DataGateOutcome` reads the run log's `snapshot` step. That is C3's **execution** capture at 15:15
     (`fno/desk/daily_steps.py:124-133`), after any 15:08 card, so on a normal day it is always missing.
   - The decisions step that collects the books' runs, and with them each day's C4 rows, closes at 15:12, also after
     15:08.
   - G10 (register: cutoff 14:30, pack 14:32, deadline 15:10, snapshot 15:15) is moving the timeline again, and
     `CARD_VALID_UNTIL` is 15:25.
   - **Fix:**
     - Fix the card's post time against the desk's real timetable (or G10's), and read only records final by then.
     - For C3, use the decision-time data check, not the 15:15 execution snapshot, or post after the snapshot.
     - Name what the card says when a record is not written yet ("not yet decided"). Today that appears only in the
       test plan (should-fix 5).
     - This is the 15:00-15:08 limit the orchestrator asked about. As written, T2 v1 would print "not yet decided"
       or nothing on every normal day. Strong.
2. **Two design 7.3 rule checks are in neither list, and there is no gap list (quality rule 2).** Design 7.3 names
   seven checks; the text maps five:
   - **"cost wall at today's quotes"**: no code implements it (my grep finds it only as a phrase in
     `fno/budget/items.py:35` and B-research-engine's Out list);
   - **"the card's evidence label matching its rung"**: a card-side check of T1's slice B trade fields, with no other
     owner.

   Each needs "covered by criterion n" or "out, because ..., owner ...". Add the gap list table, as the other stories
   do.

### Should fix

3. **`RungOutcome` re-checks a rule.**
   - It reads the committed registry and decides "version not at paper".
   - That is D1's rule, already applied by Book 1, which commits its own outcome (`fno/books/book1.py:92`,
     `no_approved_strategy.json`).
   - T1's `status.py` already reads the same registry for `no_approved_strategy`.
   - Either read Book 1's committed decision record (the "reads outcomes" claim), or reuse T1's status reading. A third
     registry reader contradicts "re-checks nothing" and the one-builder rule.
4. **Option A of question 2 adds an "event in window" warning line** with no scope item, source or criterion. Say
   where it reads the event and the holding window from, and add a criterion, or drop the line.
5. **"No run log: not yet decided" is only in the test plan.** Put it in a criterion. Criterion 4 covers only an
   unreadable record.

### The owner's options: would another answer change the verdict?

- **Q1 B (T3 every day):** no change; it costs only budget.
- **Q2 B (T2 blocks on the new rules now): yes, it would FAIL.**
  - A block that lives only in the card disagrees with the desk, which would still fill the trade.
  - It is an unregistered filter, design 7.3's own argument.
  - It would put a second rule location outside C4.
- **Q3 B (T3 built now): no change to the verdict.** It builds against nothing until T1's trade fields and O1 exist
  (owner's simplicity rule), so I agree with A.

### Note

T3's 5-minute window (15:00 pack to 15:05 advocate) depends on the same timeline fix. Under G10's 14:32 pack it would
be ample.

**Verdict: FAIL for 1468fde744dae4219ac2cc6fe4018b2e63b2e191** (story text). Fix blocking 1-2 and should-fix 3-5, then
re-judge.

---

## Addendum 1 (judge E): revision 1 at 2b30b09e: PASS (story text)

| Finding | Fix | Accepted? (my evidence) |
|---|---|---|
| B1 timeline | Two outcomes, each final at the desk's own `Timetable` time (`fno/desk/timetable.py` has `decision_deadline` and `execution_snapshot`): `DecisionOutcome` (decisions step plus C4 rows) and `ExecutionOutcome` (snapshot step). Before its time an outcome reads "not yet decided (final at HH:MM)", and the last session's execution outcome is shown. Criteria 1-4; tests at 15:08, 15:13, 15:16 and G10's times | Accepted. **The builder's correction is right:** the decision path calls no C3 check. `DataGate`/`DataChecks` appear only in `fno/desk/daily_steps.py`, `entries.py`, `exits.py` and `execution_capture.py`, and nowhere under `fno/books`, `fno/ai` or `fno/playbook` (my grep). My "use C3's decision-time check" suggestion had no source |
| B2 gap list | A seven-row table of design 7.3's checks. Cost wall: out, a C4 rule when a strategy needs it. Physical settlement: out, C4 before the first stock option. Failed variants: out, R1. Event in window and evidence label: T2b (criteria 12-13). Caps and stale data: reported | Accepted. Each row matches the code (C4's `day` column in `validity_failures.py:15` supports "rows dated d") |
| S3 registry re-read | `RungOutcome` removed; T1's `RegistryStatus` stays the only registry reader; criterion 7's AST test bars `fno.playbook.registry` and the `fno.checks` rule modules | Accepted |
| S4 event warning | T2b scope: A6 `events.csv` rows inside the window from the day after the card to the time exit or expiry; never a block; criterion 12 | Accepted |
| S5 no run log | Criterion 5 | Accepted |

**Owner's A/A/A:** recorded (`docs/DESK_DECISIONS.md` row of 16 Oct). Criterion 14 holds T3 and T2b until T1's trade
fields and O1.

### Notes (no re-judge needed)

1. **Owner's wording vs the text.** The decision row says "an 'event in window' warning on the card **now**". The text
   puts it in T2b, with the trade fields, because the window needs a trade. That is right: a `NO TRADE` card has no
   holding window. Tell the owner in one line, so "now" is not read as "on today's cards".
2. **The post time is O1's.** The recommendation (post after the decisions step; after 15:15 for C3) is sound. O1's
   story must take it, or the card will routinely print "not complete".

**Verdict: PASS for 2b30b09e378b84b1688bcd0f29cfa40f717114a9** (story text). T2's code may start; T3 and T2b wait as
criterion 14 says.
