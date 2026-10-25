# Judge 673: REH1r text, a routine command not yet in its routine is exercised (story/reh1r-command-since @ 4066fdfdb), judge E

**FAIL (round 1 of 2; 1 should-fix, 2 minor). Lane 1** (it changes what a rehearsal counts as a routine's failure;
judge 1 of 2). Judge E, own session; judge F's verdict not read. Text only: the one changed file is
`docs/stories/REH1-rehearsal-mode.md`.

## What I checked myself

- **The CLAUDE.md column.** My own script read every commit in `origin/main`'s ancestry that touches CLAUDE.md, full
  history and not first-parent. For each command it found the first commit whose CLAUDE.md, whitespace folded, holds
  `python -m fno <command>`.
  - Every row matches: e6010ac0a, a2b2ad8c6, 96af942cd, 5c3195ba0, 51cab79b0 (both certify forms), cae76af89,
    49aa26951 (the three data commands and `lab release-check`), and e5ac277e9.
  - The one exception is `lab close` (minor 1).
- **The "first output" column.**
  - The routine's own commits are where the table says: 22 Oct 19:54 (the A4h receipts and the three manifests), 19:55
    (release-check), 23 Oct 08:40 (gift) and 08:51 (A17e).
  - The earliest "Records: DR1 certification" commit is the one the table cites.
- **Design 3 and 4, and R1-R5:** clear and testable. The rule matches the orchestrator's GO ("before `since`,
  exercised, never failed"), and real runs are untouched (no `Command` objects outside a rehearsal).
- **Gates:** record scan clean (9,476 files). Doc-reading tests: 932 passed, 13 xfailed, 0 failed.

## Findings

**Should-fix 1. `index-close`'s `since` is one day early. The source rule misses when the routine itself began.**
Strong evidence: the record.
- The table sets `data-librarian index-close` to 22 Oct from CLAUDE.md's 96af942cd (22 Oct 04:29 IST), "the earliest
  it could have run".
- But the morning routine did not exist on the morning of 22 Oct. `conversations/2026-10-22.md` (Orchestrator, later
  on 22 Oct) says the owner created "the 08:36 pre-open, 08:38 morning and 19:53 evening tasks" on 22 Oct, after that
  day's 08:38.
- The first morning output on `main` is 23 Oct ("Conversation log: morning routine 2026-10-23", 08:45 IST), and no
  morning-routine commit exists on 22 Oct.
- So a 22 Oct morning rehearsal would judge `index-close` by the real rule, on a day it never ran in any routine. That
  is the exact false failure this story exists to remove. It is the only real command left in that morning: `lab open`
  is keyed, and certify starts 24 Oct.
- Fix: the bound is the later of the CLAUDE.md commit and the routine's first run (the owner's task, the first
  routine log). That gives `index-close` 23 Oct. Name that source in Design 2, and keep R3's check to it.

**Minor 1. The `lab close` row cites the wrong commit.**
- 6eced93c2 (21 Oct 16:56 UTC) holds `lab close` only as O1's last daily step, not in the evening routine.
- The evening routine's `python -m fno lab close` first appears in 5c3195ba0 (21 Oct 22:44 UTC), the same commit as
  `lab open`.
- No `since` changes (it is keyed), and the Finding's "after 19:53" still holds.
- Fix: cite 5c3195ba0 in the row and the Finding.

**Minor 2. "First output on main" must mean the routine's own output.**
- The same commands wrote earlier rows outside any routine: `data-librarian participant-oi` on 21 Oct 21:37 IST
  (70a0ff55a), `data-snapshot fii-dii-cash-by-session` on 22 Oct 01:05 (238f8e2c9), and `data-librarian fo-bhavcopy`
  on 22 Oct 01:34 (71ec37be2).
- Read literally, Design 2's "the first day its own output reached `main`" would give participant-oi 21 Oct. The
  CLAUDE.md bound saves the result here.
- Fix: say "the routine's own output", and that `since` is the latest of the three bounds.

## Verdict

FAIL. One date is wrong by the record, and the source rule that produced it needs one more bound. Both minors are
wording.

## Addendum 1

Round 2 of 2, at `07f561343` (text only: the diff from 4066fdfdb changes only `docs/stories/REH1-rehearsal-mode.md`).
**PASS.** Judge F not read.

- **Should-fix 1, fixed.**
  - `data-librarian index-close` is now 23 Oct.
  - Design 2 states the bound: "the later of ... the CLAUDE.md commit ... and the routine's own first run", citing
    `conversations/2026-10-22.md`.
  - The evidence commit 3decf6a60 is "Morning forecast receipts 2026-10-23", at 23 Oct 03:15 UTC (08:45 IST), the
    first morning output I found in round 1.
  - R3 gains the boundary: 22 Oct exercised, 23 Oct the routine's. That is testable.
  - The other rows are unchanged and still meet the new bound. The evening task existed by 22 Oct's 19:53, its first
    output was at 19:54, and the pre-open's first outputs are on 23 Oct.
- **Minor 1, fixed.** The `lab close` row cites 5c3195ba0 (22 Oct 04:14 IST) and says why 6eced93c2 does not count.
- **Minor 2, fixed.** The rule counts only the routine's own output and names the three earlier rows. Their commit
  times check out: 70a0ff55a at 21 Oct 21:37 IST, 238f8e2c9 at 22 Oct 01:05, 71ec37be2 at 01:34, and the routine's
  936611423 at 22 Oct 19:54. The job names given for them are not in those commits' messages, so I could not check
  them; no date depends on them.
- **Gates:** record scan clean (9,476 files). Doc-reading tests: 932 passed, 13 xfailed, 0 failed.

No blocking, should-fix or minor finding is left. The code round must hold each constant to these rows (R3).
