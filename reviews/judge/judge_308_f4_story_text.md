# Judge 308: F4 story text, the judge of the AI books' daily decisions (story/f4-ai-judge at 80c3ca5f)

**Verdict: FAIL on the story text: 2 should-fix findings and 2 minor.** Numbering: the builder asked for "judge_271",
but 271 is already the R1c verdict, and judge E's range is 300-349 (orchestrator, 16 Oct), so this is 308.

The design is clean and small:
- citations are JSON pointers, so no private value is copied;
- `numbers.py` is reused unchanged;
- Book 2 blocks and Book 3 records;
- there is no override path;
- verdicts are written once, with a reproducible audit draw and seeded cases.

The timing argument for a code gate is strong (strong evidence):
- F1t's reveal is at 15:10:10 and observation 2 at 15:11:00, with E3's deadline at 15:12:00;
- the forecast routines' best fire-to-answer time was 66-99 s (16 Oct), and 15 Oct's commitments landed about 12-15 s
  after their deadline (audit files read by me for judge 301);
- an AI judge session would have to start after 15:10:10 and answer by about 15:11:30, which no measured session has
  done.

## Findings

**Should-fix 1. The code gate replaces what the owner just chose; the owner's word comes before code.** Strong
evidence. `docs/DESK_DECISIONS.md` line 254 (16 Oct): "**F4, the AI judge, is built before Book 2 switches on**"
(owner: "Build F4 first (Recommended)"); "F4 follows its amended text". The amended text says "`fno/ai/judge.py` as its
own session (different model from the author)". This story makes the daily judge code and moves the model check to a
monthly F4b, which is out of scope. It says so honestly, as open question 1. But building it before the owner answers
would hand the owner something other than what they chose minutes earlier ("I don't want any surprises").

My view (reasoning, with strong timing evidence): the code gate plus a monthly model re-check is the right design, for
the reasons the text gives.

Fix: the orchestrator takes Q1 to the owner, with the two honest options:
- (a) a code gate daily, with F4b's model re-check monthly;
- (b) an AI judge session daily, which with today's latencies makes Book 2 no-trade on most days unless S1's timetable
  moves.
The text records the answer, and code starts after it.

**Should-fix 2. The interfaces are not yet in the partners' texts, and one value is stale.** Strong evidence:
- F4 says a departing Book 2 decision has `action` "`change`". F5 at a32f8ff7 (judge 307 addendum 3) now uses
  `follow_rule | trade | no_trade`. Write "Book 2: any `action` other than `follow_rule`".
- F1t (13653f05) has no `judge_failed` status, no `JudgeStep` call before `decide()` and no `AcceptedDecision.judge`.
  Its text even says "the red team and judge (F3, F4): they travel inside the answer's book-specific `decision`
  object", which contradicts F4 as a separate step in `ai_collect`.
- F5 (a32f8ff7) and F6 (b096a4a2) have no `evidence` key, and no call to `evidence_problems` in their
  `check_decision`.

Fix: put each agreement in each partner's text (F1t: the status, the call, `AcceptedDecision.judge`, and the judge
time inside the 15:11-15:12 window; F5 and F6: the `evidence` key and the check). I will check them as addenda to
judges 301, 302 and 307.

**Minor.**
1. **What can be cited from the private pack.** Account files sit in the private pack as whole texts
   (`{"path", "sha256", "text"}`, `fno/desk/private_pack.py`), and a citation must resolve to a scalar of at most 200
   characters. So the AI can cite day-sheet (`evaluation`) values but never its cash or positions, which is consistent
   with F1t's 3d refusal of private figures. Say so in the prompt lines and in design 2, so the strictness is not a
   surprise.
2. **Where the audit runs.** It re-reads private packs "through E2c's Drive files", so it needs the Drive settings.
   Name where it runs (an Actions job or an owner session) in the claims, beside the scheduling note.

## Owner expectations
- No override: met (criterion 3).
- Failures alerted and recorded (row 246): the audit alerts; a judge failure is an outcome record via F1t.
- Simplicity: no AI session is added to the daily window.
- Completeness: research theses are out, with a reason (no producer). Accepted.

## Note: efcb7bc9 (12:06)
The diff from 80c3ca5f adds one sentence to design 2: the number rule runs one way, so a reason may rest on a cited
private value without quoting it, which matches F1t's 3d. It also adds F6's answer to response 271. Both are fine.
**Both should-fix findings stand.** Minor 1 also stands: account files are whole-text items, so a pointer into them
cannot resolve to a scalar. Even "cite without quoting" works only for `evaluation` values.

## Addendum 1: 992a3f89

**Verdict: still FAIL, on one remaining item (F1t's side of should-fix 2). Everything else is closed.**
- **Should-fix 1: closed.** The owner chose "Code daily + AI monthly (Recommended)" (`docs/DESK_DECISIONS.md` line 257,
  16 Oct). It is recorded under "Owner decisions", so the code gate is now the owner's choice, not the builder's.
- **Should-fix 2:**
  - `change` is gone: "any action other than `follow_rule`" (lines 39-40 add that F5's check refuses a top-level
    `follow_rule` whose slots change).
  - F5 (0bb574de, judge 307 addendum 4) and F6 (c625151e, judge 302 addendum 2) carry the `evidence` key and the
    check. Both closed.
  - **F1t's text is not yet updated.** I checked F1t's branch head c96c4923: no `judge_failed` status, no `JudgeStep`
    call, no `AcceptedDecision.judge` or `judge_blocks`. Since 0bb574de, F5's design needs `decide()` always run with
    `judge_blocks`, and F1t's run check must refuse a blocked run with a chosen trade.
- **Minors: closed.** Design 2 says which private values are citable (only `/evaluation` scalars, not account
  files); design 5 item 6 names where the audit runs.

A PASS follows when F1t's text carries the agreed port: the `JudgeStep` call before `decide()`, `judge` and
`judge_blocks` in `AcceptedDecision`, the run check, and the judge's time inside the 15:11-15:12 window. That will be
checked as an addendum to judge 301.

## Addendum 2

**F4 story text (story/f4-ai-judge @ fe5721d3): PASS. Lane 1** (it decides whether a Book 2 trade happens). Judge E,
judge 1 of 2 (the other judge is K, whose verdict I did not read), own session. Text only: `F4-ai-judge.md`,
`F-ai-layer.md` (its old F4 text replaced by a pointer), and response 271 with its README row. Judged by reading.
Doc-reading tests with the token kept: 922 passed, 14 xfailed.

- **Addendum 1's last item: closed.** F1t revision 2, now on `main`, carries the agreed port:
  - the `JudgeStep` call inside `ai_collect` before `decide()`, with `decide()` run in every case (F1t story
    `:360`);
  - `judge` and `judge_blocks` in `AcceptedDecision` (`:328`);
  - the run check refusing a chosen trade under a block (`:351`);
  - the judge's 5 s inside the 15:11:00-15:12:00 window (`:364`);
  - `NoJudge` until F4's code lands, so Book 2 is `judge_failed` and never trades unjudged (`:368`).

  I passed that text in judge 623.1.
- **Changes since 992a3f89, checked:**
  - Design 4 now places the port in F1t's `fno/ai_trading/ports.py`, with F4 implementing it and defining no second
    copy. That is one port, one owner, matching F1t's text word for word on `JudgeCase`, `Judged` and `JudgeStep`.
  - The builder and judge lines are updated.
  - The criteria (1-10), the gap list and the owner's decisions are unchanged.
- **`F-ai-layer.md`:** the superseded F4 section is now a pointer. Its five old criteria are carried in
  `F4-ai-judge.md`: 1 (different model) = new 1; 2 = new 2; 3 (no override) = new 3; 4 (audit) = new 7; 5 (late
  judge) = new 6.

## Findings

None blocking, none should-fix, none minor. The code follows on F1t's port.

## Addendum 3

**F4 story text, round 2 (story/f4-ai-judge @ 1ca9b691): PASS; 308.2 holds. Lane 1.** Judge E, judge 1 of 2;
judge K's verdict 628 not read (its two findings came to me through the orchestrator). Since fe5721d3, F4 changes by
28 lines and F1t's "The judge" by two sentences. The rest of the diff is main merged in: `git diff origin/main...1ca9b691`
shows only F4, F-ai-layer, F1t (+3/-3) and response 271. Doc-reading tests with the token kept: 922 passed, 14
xfailed.

- **The verdict type has one owner.** `JudgeVerdict(status, blocks, reason)` now sits in F1t's `ports.py` beside
  `Judged(verdict, path)`. F4's `verdict.py` writes the full file and returns that small type. F1t's `ai_collect`
  reads `judged.verdict.blocks` and `judged.path`: the same names on both sides, and no second shape for `NoJudge`.
- **`NoJudge` leaves a record.** It writes the day's verdict file once, with design 3's fields where they apply
  (`none:not-built`, `unavailable`, `blocks` true for Book 2 and false for Book 3), and its path is
  `AcceptedDecision.judge`. So Book 2's fail-closed day is recorded like any judged day, with the same write-once rule.
- **Unchanged:** criteria 1-10, the gap list and the owner's decisions. 308.2's reasons all still hold.

## Findings

None blocking, none should-fix, none minor.
