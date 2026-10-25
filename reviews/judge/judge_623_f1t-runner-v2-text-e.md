# Judge 623: F1t revision 2 story text, the AI books' trading runner (story/f1t-runner-v2 @ 470cbdc5c), judge E

**FAIL (round 1 of 2, text; 2 should-fix, 1 minor). Lane 1** (the AI books' paper trades; judge 1 of 2). Judge E,
own session; judge K's verdict not read. I was given 2bc4005d. The head moved to edbc939a and then 470cbdc5c (the
orchestrator's later messages): I judge 470cbdc5c. Text only: two files, +620 and +103 against main. Judged by
reading. Doc-reading tests with the token kept: 922 passed, 14 xfailed.

## "No passed criterion removed or loosened" (against judge 301 add. 1's text, c2d2b922)

**True for the criteria.** I extracted the acceptance criteria of both versions and compared them: criteria 1-15 are
identical, line for line. 16, 17, 17b and 18 are added. The go-live list gains F4, D6 registration and a full clone.
It loses one item, "at least one `paper` strategy exists". That item is backed by the owner's own words: DESK_DECISIONS
25 Oct row 344, item (1) lists "the 15 Oct 'AI books trade only after a strategy has passed' rule: AI paper trades are
allowed, each labelled 'strategy not yet passed'". Criterion 17b carries the label.

## Facts checked

| Claim | Result | My evidence |
|---|---|---|
| Forecast routines, 15-23 Oct | True | `ai_v1/2026/*_audit.json`: 12 book-days, 7 `on_time`, 4 `late` (15 Oct both, 22 and 23 Oct Book 2), 1 `no_submission` (Book 3, 22 Oct); 14 Oct `no_submission` both |
| `model_reported` `unknown` on 10 of 11 answered | True | Only Book 3 on 16 Oct reported `claude-opus-5-5` |
| G11's `RunTerms` chain | True | `fno/ai/run_terms.py:27-62` (paths, deadlines, reveal) |
| `ROUTINE_POINTER_MAX_BYTES` 64 KiB on main | True | `constants_operations.py:104` |
| `DECIDING` in G11's not-a-money-piece test | True | `tests/ai/test_v4_not_a_money_piece.py:13` |

## Findings

1. **Should fix: the model check reads the configured model, not the served one.**
   - `model_reported` comes from "the exact model ID the session's own instructions state (its identity line)", or
     else the session tool's `session_context.model` (Design, "Model reported"). The decider then records
     `model_served` equal to `model_reported`.
   - Both sources name the model a session is configured with. A turn can be served by a fallback model: this judge's
     own `get_session` reports `configured_model`, `session_context.model` and `external_metadata.last_served_model`
     as separate fields, and its instructions say the serving model can differ and change mid-session.
   - So a decision made by a fallback model is recorded as the registered model and passes the `model_mismatch` check.
     The record would claim a model that did not decide the trade [strong: the session tool's documented fields].
   - Fix: take the served model from `last_served_model` where the tool exists, or check it after the fact in the
     transcript audit, and record a mismatch or `unknown` as no trade. Add the case to criterion 3c.
2. **Should fix: the budget stop names G11's class, whose rule is not the one the text states.**
   - The Firing order says decisions stop "at BG1's level `stop`, before the forecasters, design 7.6", through G11's
     `BudgetStop` (`fno/ai/budget_stop.py`).
   - G11's only implementation, `MeterBudgetStop`, stops the books only when the level is `stop` **and** the books'
     own minutes reach the cap: the forecasters-last rule (`budget_stop.py:1-5`).
   - Reused as is, decisions would keep firing at level `stop` until the books alone filled the cap. Criterion 12 lists
     "budget stop" without pinning which rule. Moot under today's no-cap, but the text promises "a cap set later
     applies with no code change".
   - Fix: name a second `BudgetStop` implementation (level `stop` alone) for decisions, and add a criterion-12 case:
     level `stop` with the books below the cap gives decisions `not_fired` while G11's forecasts still fire.

## Minor

1. An unreadable meter "fires the books ... as G11 does" (fail open). That was G11's choice for forecasts (a miss
   costs a slot). For trading decisions, say whether fail open is the owner's choice too, or fail closed (no trade).
   Either is safe on paper; the text should say why.

## Notes

- The four routine sessions overlapping around 15:00-15:11, with an unknown platform concurrency limit, are stated as
  a known limit to be measured on the non-counted fire. Accepted.
- `NoJudge` failing Book 2 closed until F4 merges (criterion 16) is right.

## Addendum 1

**F1t revision 2 story text, round 2 of 2 (story/f1t-runner-v2 @ 4dbf786d): PASS. Lane 1.** Judge E, judge 1 of 2;
judge K's verdict not read. Since 470cbdc5c only the two story files change (+81/-28). Judged by reading. Doc-reading
tests with the token kept: 922 passed, 14 xfailed.

| Round-1 item | Outcome | My evidence |
|---|---|---|
| SF1: the configured model checked, not the served one | **Accepted, fixed** | `brief` makes the session report `model_reported` = `external_metadata.last_served_model`, with `model_configured` = `session_context.model` and `model_source` beside it. These are the fields this judge's own `get_session` returns. `instructions` or `none` is `model_unverified`. A served or configured model different from the registered one is `model_mismatch`; both are no trade. A false copy is a transcript-audit breach (`model_misreported`). The latest-turn limit is stated, with the audit's coverage (every session of the first 10 days, then 2 a week). Criterion 3c has each case; the go-live fire needs `session_tool` with the registered model |
| SF2: the budget stop's rule | **Accepted, fixed** | `LevelBudgetStop`, a second implementation of G11's interface, stops decisions on level `stop` alone. Criterion 12 has the case "level `stop`, books below the cap: decisions not fired, forecasts fired" and the `alert` case |
| Minor 1: fail open on an unreadable meter | Fixed | Stated as the orchestrator's choice, on cost only: it never makes a trade, since every trade still passes C2, C4 and the judge |

**New text this round, checked.**
- Q9 to Q11 are the owner's: DESK_DECISIONS 25 Oct row 345, "9 yes, 10 yes, 11 yes". Q11 (Book 2 alone may take D2's
  research candidates as rule defaults, under D2's unproven limit) is placed in F5's revision, not here.
- The 15:10:10 row's claim holds by its own timeline: every seal deadline (15:10:00) comes before any reveal
  (15:10:10).
- The reveal race is a stated limit: a reveal missing at 15:11:00 is `not_revealed`, never a trade.

## Findings

None blocking, none should-fix, none minor.

## Note

The fix depends on routine sessions having the session-description tool. Without it every day is
`model_unverified` (no trade). The go-live fire checks this, so the gap fails closed.
