# Judge 674: REH1r, a routine command not yet in its routine on the replayed day is exercised, story text (story/reh1r-command-since @ 4066fdfdb)

**FAIL on 1 should-fix, text round 1 of 2, judge F (judge E the other; not read). Lane 1.** Own session
(session_01A8XfbTUVgeeEpqatHaWbtP). Labels: strong, some, reasoning only.

## Facts checked

| Item | Result | My evidence |
|---|---|---|
| The first CLAUDE.md commit holding each command | TRUE for all ten | `git log --reverse -S"<command>" origin/main -- CLAUDE.md`: e6010ac0a, a2b2ad8c6, 96af942cd, 51cab79b0 (both certify rows), cae76af89, 49aa26951 (fo-bhavcopy, release-check), 6eced93c2 (lab close), 5c3195ba0 (lab open) |
| Their times | TRUE | 6eced93c2 21 Oct 22:26 IST; 49aa26951 22 Oct 04:39 IST (21 Oct 23:09 UTC); 51cab79b0 23 Oct 22:42 IST; etc. |
| First outputs on main | TRUE | d88023df0 23 Oct 08:51 (A17e pre-open), 47a4ff7a8 23 Oct 08:40 (pre-open gift), 2428dac17 24 Oct 08:41 (DR1 certification), f24218f2e 22 Oct 19:54 (A4h close read), 6bdf18007 22 Oct 19:55 (release-check logs); `receipts/records/` holds only the two certified records |
| Design | SOUND | `since` read only by the rehearsal (no real-run `Command` objects); before `since` the command runs and is `exercised` (REH1k's shape), on and after it the real rule; criteria R1-R5 with plants; gap list complete |
| Doc-reading tests (trial merge with main) | PASS | 933 passed, 13 xfailed; record scan clean (9,506 files) |

## Findings

1. **Should fix: `data-librarian index-close`'s `since` is 22 Oct, but the morning routine first ran on 23 Oct.** The
   story's own rule puts the record first and CLAUDE.md only "where the record is silent". The record is not silent
   here:
   - `conversations/2026-10-22.md:153-154`: the owner created "the 08:36 pre-open, 08:38 morning and 19:53 evening
     tasks" later on 22 Oct, after that morning;
   - no morning output exists on 22 Oct; the first morning receipts are `3decf6a60`, 23 Oct 08:45 ("Morning forecast
     receipts 2026-10-23");
   - the same evidence already sets the pre-open rows to 23 Oct, and `lab open`'s key is 23 Oct.

   A 22 Oct morning rehearsal would count `index-close` as a real command, so a missing answer there would be a false
   routine failure. Fix: `since` 23 Oct for that row, citing the conversation log and 3decf6a60, and R3's test with it.
   (The evening's 22 Oct rows are right: its task existed by 19:53, outputs at 19:54-19:55.)

## Notes

- The certify-provisional row's 24 Oct is a Saturday. No evening session can run before 26 Oct, so the date is harmless.

## Addendum 1

**Text round 2 of 2 at story/reh1r-command-since @ 07f561343, judge F: PASS (1 minor). Lane 1.** Own session; I did
not read judge E. Text only (`git diff 4066fdfdb 07f561343`: one file).

| Item | Answer | My check | Result |
|---|---|---|---|
| SF1: index-close's `since` | 23 Oct, citing `conversations/2026-10-22.md` and 3decf6a60; the rule is now "the later of the CLAUDE.md commit and the routine's own first run"; R3 gains the 22 Oct exercised / 23 Oct real boundary | read; consistent with my round-1 evidence | **Accepted** |
| The other dates under the new rule | pre-open 23 Oct, evening 22 Oct, certify 24 Oct unchanged | the evening task existed by 22 Oct 19:53 (its own outputs 19:54-19:55, e.g. 936611423 by the routine); the hand and job rows the text now excludes are other writers: 70a0ff55a `omenix-participant-oi` 21 Oct 21:37, 238f8e2c9 `omenix-flows-download` 22 Oct 01:05, 71ec37be2 `omenix-panel-days` 22 Oct 01:34 | **Confirmed** |
| E's minors (lab close row; "the routine's own output") | lab close cites 5c3195ba0 (the evening routine's) | `git log -S"lab open"` gave 5c3195ba0 22 Oct 04:14 IST in round 1 | **Accepted** |

Doc-reading tests on a trial merge with main: 933 passed, 13 xfailed; record scan clean (9,511 files).

**Minor.** The Finding paragraph (line 980) still names 6eced93c2 as "the first commit holding `lab close` in
CLAUDE.md", while the table now cites 5c3195ba0 for the evening routine. Both are after 21 Oct's 19:53, so the finding
holds. Align the sentence when the code round touches the section.
