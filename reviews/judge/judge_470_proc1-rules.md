# Judge 470: PROC1 part 1, rule documents for the owner's cuts (story/proc1-rules at e2df4d97)

**Verdict: PASS. Lane 1 (old lanes, the last such change). Round 1 of 2.** No should-fix. Three minor notes.
Merge not between 14:00 and 16:15 IST.

## Criteria
| Criterion | Result | Evidence |
|---|---|---|
| 1. JUDGE.md, CLAUDE.md and AGENTS.md say each rule of decision 294 item 1, with no contradiction | MET | Each of row 294's rules appears in JUDGE.md, CLAUDE.md or AGENTS.md: lane-1 areas (the "Lanes" table, CLAUDE.md "Judge lanes"); tools, CI and test-only fixes in lane 2 "when they change no record"; at most 2 rounds, then the owner; two judges; the 40-60 line template; claims in the story's Claims section; quality rule 9 and the ChatGPT loop paused (JUDGE.md, AGENTS.md, CLAUDE.md); logs as owner quotes plus decisions. The merge procedure matches the owner's row of 21 Oct (efee41c7) clause for clause. Brake restarts and quality rules 1-8 are kept |
| 2. No routine section changed; the suite stays green | MET | CLAUDE.md hunks only at "How to work", "Keep a conversation log", "Branch" and "Code". On a trial merge with main: every test that reads CLAUDE.md, AGENTS.md, JUDGE.md or the workflow, plus `tests/numbering` and the code-size test, gives 2,089 passed, 16 xfailed. ruff, `check_imports`, `check_records` (7,864 files) and `check_numbers` are clean. The steward's full run (9,812) is the one run for the merge |
| 3. `number-alert.yml` has no schedule, and a test fails if one returns | MET | schedule and cron lines removed; my plant (the cron put back) fails `test_tools.py` (1 failed, 6 passed) |

## The two readings asked for
- **(a) Rule documents and stories outside the lane-1 areas go to lane 2: ACCEPTED.** Row 294 says "lane 1 only for"
  the listed areas, and its parenthetical moves tools, CI and test-only fixes to lane 2. Nothing in the row keeps rule
  documents in lane 1: that rule came from judge 91's refinement, not from the owner.
  - *Risk the owner should see (reasoning only):* a lane-2 change to JUDGE.md or CLAUDE.md could itself move an area
    out of lane 1, with only the orchestrator's check before it lands and the auditor's after.
  - "When unsure, lane 1" and the auditor's power to move a change into lane 1 limit this.
  - A one-line owner answer would close it: "a rule-document change that narrows lane 1 or a hard line is lane 1".
    That answer is the owner's to give, not the judge's to add.
- **(b) Schedules and workflows that call outside services stay in lane 1; CI such as checks.yml goes to lane 2:
  ACCEPTED.** Row 294 keeps "outside services" in lane 1 and names CI in lane 2. A workflow that posts to Slack or reads
  NSE is an outside-service path.
- The added "dashboard's privacy rule" and "owner_overrides.csv rows" are stricter than row 294. They are consistent
  with its "secrets" and with C5b, so this is not a contradiction.

## Plants
1 planted (the hourly cron put back), 1 caught.

## Notes (minor, not blocking)
1. **Two wiring docstrings name no story.** CLAUDE.md's new rule is that each root's docstring "says what it wires and
   for which story". All 55 `wiring.py` files have a docstring (I checked), but `fno/storage/wiring.py` and
   `fno/forecast/wiring.py` name no story. The second is frozen. Either word the rule "and its story where it has
   one", or add the story when each file next changes.
2. **Quality rule 2 lost its consequence.** The old text said "a requirement in neither list is a blocking finding";
   the new text does not. Step 6's "no blocking and no should-fix left" still applies, but stating it again costs one
   clause.
3. **The merge procedure says "lane-3 files" but lists no paths.** The old text named `tools/ci_scope.sh`'s paths. A
   docs file that tests read (CLAUDE.md's routine sections) is lane 2, not lane 3, so it still needs the full run.
   Naming `ci_scope.sh` again would remove the doubt.

## Addendum 1

**The rule-document guard line (story/proc1-minors, commit 49f0a154): CONFIRMED. Lane 1, this line only.**

- **Matches the owner's row.** DESK_DECISIONS "Rule-document guard" (1f039213, line 297, owner: "Yes, judge those")
  says rule documents are lane 2, except a change that narrows lane 1 or touches a hard line. That change stays lane 1
  and needs a judge PASS; the hard lines are no orders, secrets, privacy, write-once data and frozen files.
- **Same wording in both files.** `docs/JUDGE.md`'s new lanes bullet and the sentence added to `CLAUDE.md`'s lane-2
  line say the same, with the same five hard lines, and cite the row. They do not contradict the PASS of 470.
- **Note (not blocking):** JUDGE.md names the rule documents as "`CLAUDE.md`, `AGENTS.md`, this file". The old list
  also counted protocol and freeze documents, owner checklists and stories' acceptance criteria. Freeze and protocol
  documents fall under "frozen files" in any case. Whether an owner checklist is a rule document is now the
  auditor's call; "e.g." would keep the list open.
- **Not judged here:** 4015ae09, judge 470's three minors (docs, lane 2, the orchestrator's check), and the branch's
  later commit d6217efd (PROC1 story part 4).
