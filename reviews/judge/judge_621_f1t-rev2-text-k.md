# Judge 621: F1t revision 2 story text, `story/f1t-runner-v2` at 2bc4005d4 (round 1 of 2, judge K, judge 2 of 2)

**FAIL, lane 1** (books' paper trades), text only. 1 should-fix, 2 minor. Judged by reading, against the passed text
c2d2b922 (judge 301 addendum 1). The diff c2d2b922..2bc4005d4 touches only `docs/stories/F1t-ai-trading-runner.md` and
`F1t-owner-checklist.md`, so this is a text-only change. Doc-reading tests on 2bc4005d4, Slack token set: 922 passed,
14 xfailed. I did not read judge E's verdict.

## Checks (the orchestrator's five)

| Check | Verdict | Own evidence |
|---|---|---|
| Nothing passed was loosened | MET | criteria 1-15 are unchanged; 16-18 are added. Addendum A's judge step is folded in unchanged. F1t's base `seal` check now also needs `action`, which is stricter and matches F5's passed shape (`F5-book2.md:82-88`). The old go-live check 3 ("a paper strategy, or no trade daily") becomes check 4 with the same effect. New go-live checks: F4 for Book 2, D6 registration, full history, the model on the test fire |
| Deadline and seal under v4's timeline | MET | decision seal by 15:10:00 (observation 1), reveal 15:10:10, observation 2 15:11:00, E3 deadline 15:12. G11's v4 forecast routines of the same books reveal at 15:10:10 (`fno/ai/book.py:9`, "15:10:10 under v4"), after every decision seal, so one book's v4 forecast cannot reach the other book's decision before it is sealed. The overlap is safe on the clock, but the text does not say so (m1) |
| Unknown model = no trade, and its proof before go-live | **PARTLY** (SF1) | `model_unverified` is no trade (unchanged), and go-live check 6 requires the test fire to report the registered model. But the reported model can be the wrong one; see SF1 |
| A rehearsal never fires a routine | MET | criterion 18: under `rehearsal()`, no `RoutineTrigger` is built, no HTTP call is made, and the step is `refused` with `ai:REHEARSAL_NO_FIRE`; with no book live it is `not_live` as in a real run; the trigger factory is a spy |
| NoJudge fails closed | MET | until F4 merges, `NoJudge` gives `unavailable` ("judge not built (F4)"), so Book 2 is `judge_failed` every day; Book 3's verdicts never block (F4's design); criterion 16 tests both; Book 2's go-live needs F4 |

## Findings

1. **Should fix: "model_reported" can claim the registered model while another one serves.**
   - The fixed answer rule (unchanged from judge 301) takes first "the exact model ID the session's own instructions state", then the tool's `session_context.model`.
   - Both name the model the session is *set* to run, not the one serving it. A Claude Code session's own instructions say plainly that the serving model "can differ from that and can change mid-session" (fallbacks). The tool reports the served model apart: `external_metadata.last_served_model`.
   - So on a fallback day, a book could report and record a "match" while an unregistered model decided: a wrong attribution in a lane-1 record. That is the opposite failure to "unknown".
   - The 15-23 Oct evidence (10 of 11 `unknown`) makes this rule the one that decides whether the books ever trade, so it must be right.
   - **Fix (text):**
     - with the tool, `model_reported` is `external_metadata.last_served_model`, recorded beside the configured model;
     - a difference between them is `model_mismatch`, no trade;
     - with the instructions line only, record its source (`instructions`), and state whether that counts as verified: an owner or orchestrator ruling, put plainly;
     - go-live check 6 names which source the test fire must show.

## Minor

- **m1:** state in the timeline that every decision seal (15:10:00) comes before any reveal (forecast or decision, 15:10:10). That ordering is what keeps the overlap honest. Also add to Known limits: four reveal pushes to `main` at 15:10:10, beside the daily run's own pushes, can race; a reveal that still loses at 15:11:00 is `not_revealed`, never a trade. Add it to the test fire's checks.
- **m2:** "a meter that cannot be read fires the books ... as G11 does" is fail-open on cost. Say it is deliberate: cost only, never a trade risk, and the owner set no cap.

## Plants

None: text round.

## Notes

- Open question 1 (does 25 Oct lift the 15 Oct "strategy passed first" rule?) is correctly put to the owner, with the builder's recommendation labelled. The code is the same either way.
- The orchestrator's two earlier notes hold: the timeline, and that a slow `book1` never moves an observation (the child-process observer, judge 301).

## Addendum 1: the newer head `story/f1t-runner-v2` at edbc939a3 (still round 1, judge K)

**FAIL stands, lane 1.** SF1, m1 and m2 are unchanged. The one new commit (edbc939a3, text only, 21 lines) is sound.

| Item | Verdict | Own evidence |
|---|---|---|
| Decisions as a third `RunTerms` instance instead of path parameters | MET (better: no second mechanism) | `fno/ai/run_terms.py` on main: `RunTerms(protocol, folder, deadline, reveal_from, reveal_by, books_key)` with v2's and v4's instances. `read_submission(..., terms)` (`submissions.py:40`), `TranscriptAudits(root, terms)` (`transcript_audit.py:52`), `stop_reason(..., terms)` (`stop_rule.py:31`) and `fired_sessions(root, terms)` (`audit_plan.py:34`) already take it. Its paths give `journal/ai_decisions/submissions/<YYYY>/<d>_<book>.commitment.json` and `.../<YYYY>/<d>_fired.json`, as the text states (`paths.py:25-54`) |
| Nothing loosened | MET | the change removes the 16 Oct path-parameter plan and names `build_audit_seeds` as the one `fno/ai` change. The fallback (a minimal shared publish helper if `BookSession` needs forecast fields) is bounded, with G11's tests unchanged; the claims must say which was done |

SF1 (the reported model must be the served one, `last_served_model`, not the configured one) is what still blocks the
PASS. Its fix is text only.

## Addendum 2: round 2, `story/f1t-runner-v2` at 4dbf786d7 (judge K)

**PASS, lane 1, text only.** The change since 2bc4005d4 is Markdown only. Doc-reading tests on 4dbf786d7, Slack token
set: 922 passed, 14 xfailed. I did not read judge E's 623.

| Finding | Verdict | Evidence (read) |
|---|---|---|
| SF1 (served model) | fixed | `model_reported` = `external_metadata.last_served_model`, `model_configured` = `session_context.model`, `model_source` in {`session_tool`, `instructions`, `none`}. With `session_tool`, served or configured different from the registered model is `model_mismatch`. `instructions` or `none` is `model_unverified`, by the orchestrator's 25 Oct ruling, stated with its reason. All are no trade. A false copy of the tool's fields is a transcript-audit breach (`model_misreported`) under the stop rule. Criterion 3c covers every case, including "served differs while configured matches". The go-live fire must show `session_tool` with `last_served_model` equal to the registered model; anything else blocks the switch. The limit that `last_served_model` covers only the latest turn is stated in Known limits |
| m1 | fixed | the 15:10:10 timeline row says every seal (decision and v4 forecast, 15:10:00) comes before any reveal. Known limits names the four-reveal race (a reveal not on the remote at 15:11:00 is `not_revealed`, never a trade), and the checklist's test fire records each reveal's push time |
| m2 | fixed | the unreadable meter is a deliberate fail-open on cost only, never a trade (C2, C4 and the judge still apply), with the orchestrator's ruling cited |
| The owner's rulings now cited | verified | `docs/DESK_DECISIONS.md` on main, 25 Oct rows. The 15 Oct "trade only after a strategy has passed" rule is lifted for paper: trades labelled "strategy not yet passed" (row 344). Q9, Q10 and Q11 approved (row 345: "9 yes, 10 yes, 11 yes"). The new criterion 17b (the strategy label; a chosen trade without `strategy_status` is refused) carries the lift with its label, so it is not loosened silently. Q11's research-candidate defaults are F5's revision, correctly kept out of this story |
| Judge E's SF2 (`LevelBudgetStop`) | read only as text | a second `BudgetStop` implementation: decisions stop at BG1's level `stop`, before the forecasters (design 7.6); criterion 12 has the case. Its acceptance is judge E's to give |

Nothing passed is loosened: the only lifted rule is the owner's own, and it is cited and labelled.
