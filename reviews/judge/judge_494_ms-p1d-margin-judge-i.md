# Judge 494: MS-P1d follow-up part 1, law 3 on MS-P1m's margin (second judge)

**Scope:** story/ms-p1d-margin at 6ef6f40b (on main a275a0ff), diff a275a0ff..6ef6f40b. Judge I
(session_01MvZneCLZqBuiGyNxawdVee), the second judge (money piece). I did not read Judge B's verdict. Lane 1. Round 1 of 2.

**Verdict: FAIL.** 1 should-fix, a test only; the code itself is right.

## Claims checked
| Claim | Result | Evidence |
|---|---|---|
| Law 3 runs C2's `MarginRoom`, unedited, on `build_road_margin` | MET | `margin_law.py:21-23`, `wiring.py:28-30`. `MarginRows` is gone. With the real archive for 22 Oct, the margin is found for a probe bull put spread on all 4 indices, where round 1 refused every index but NIFTY |
| An unreadable margin refuses with "margin not checked: <cause>" | MET | `c2_laws.py:40-43`. MS-P1m turns every failure (Drive, manifest, damaged file, outside the model) into `RiskInputError`. Plants: note dropped, refusal turned into a pass, `startswith` turned into `==`; all caught |
| C2's terms and units come from one `RoadTradeTerms` | MET | `c2_inputs.py:104-117`. Plants: the terms' lot set to 1, the expiry guard dropped, a leg dropped, the contract name changed; all caught |
| The desk's two codecs never see school terms | MET | `test_terms_never_reach_desk_codecs.py` (fresh interpreter); it passes in my suite run |
| Gates | MET | full `pytest -n auto` 11,266 passed, 1 skipped, 16 xfailed, 0 failed; ruff check and format, check_imports and check_records clean |

## Finding
1. **Should-fix: a held trade's cash flow given to C2 is untested.**
   - `c2_inputs.py:96` passes `position.entry_net` to `road_open_trade`. C2's `PositionRisks` uses it for the held trade's maximum loss (`risk/open_risk.py:80`), which the bucket, open-risk and new-risk caps add up.
   - My plants, entry net set to 0 and entry net doubled, both survive (933 school tests pass). The doubled one understates a held credit trade's risk, so the caps would let more through.
   - The gap predates this diff: the same plant also survives at d's b9900351, which I passed (judge 486). This diff rewrites the line, so the test belongs here.
   - Fix expected: a test where a held credit spread's open-risk value equals C2's held maximum loss at its own `entry_net`, and where a changed `entry_net` changes the open-risk verdict at the cap.

## Plants
10 planted, 8 caught. Both survivors are finding 1.

## Notes (no action required)
- The margin note now carries MS-P1m's or C2's message, which can name a contract or legs. No report reads `LawResult.note` today, and the records are Drive-only. g and j must not show the note in Slack: the privacy rule bans live strikes.
- A missing mid inside `MarginRoom` (a quote problem) is now also noted "margin not checked: ...", so `margin_not_checked` counts it as no margin. The cause text tells the two apart; a report that counts "no margin data" should read the cause.
- Still to come in part 2, as the Claims say: `_verticals` on b's function with its 1e-9 tolerance, and settlement on b's `build_archive_stores`.

## Addendum 1: round 2 at 4d5ac7f6 (diff 6ef6f40b..4d5ac7f6)

**Verdict: PASS** (Judge I, second judge; Judge B passed 6ef6f40b).

- **Finding 1: FIXED.** `test_a_held_trade_s_entry_net_is_its_cash_flow_in_c2_s_max_loss` checks two things:
  - the held trade counts at C2's own held maximum loss for its `entry_net`;
  - the open-risk verdict at the cap moves with it: no credit breaks the cap, a double credit lowers the loss.
  My two plants (entry net set to 0, entry net doubled) now both fail it.
- **The diff is tests and story only:** `tests/school/safety/test_margin_law.py` and the story's MS-P1j note requirement. No code changed since 6ef6f40b, whose full suite I ran (11,266 passed).
- 934 school tests pass at 4d5ac7f6, and ruff is clean.
