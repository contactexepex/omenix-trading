# Judge 677: DOC1 plan, one clean current document set (story/doc1-clean-docs @ a482f2d7e), judge E

**FAIL (round 1 of 2; 2 should-fix, 3 minor). Lane 1** (it rewrites rule documents; judge 1 of 2). Judge E, own
session; judge F's verdict not read. Text only: the plan (103 lines) and one WORK_REGISTER row.

## Counts re-counted (section 1, at 8edc21139, my own `git ls-tree` and line counts)

| Claim | Mine | Result |
|---|---|---|
| 1,296 Markdown files | 1,296 | MET |
| `docs/`: 108 files, 44,865 lines, 33 over 350, largest 5,057 (HANDOVER) | 108 `.md`, 44,865 lines, 33 over 350, HANDOVER 5,057 (`docs/` has 112 files counting non-Markdown) | MET |
| `docs/stories/`: 75 files, 31 over 350 | 75, 31 | MET |
| `conversations/`: 36 files, 9,511 lines | 36, 9,511 | MET |
| `reviews/` about 950 files | 956 | MET |
| DESK_DECISIONS line 29 quote | holds, word for word | MET |
| DESK_DECISIONS "345 rows" | 339 data rows (340 table lines, less the header) | minor 1 |
| 95 doc-reading test files | 95 | MET |
| code reads DESK_DECISIONS "18 references" | 43 lines in 27 `fno` files; 50 files in code, tools, tests and workflows | minor 1 |

## Findings

**Should-fix 1. `docs/DESK_DECISIONS.md` is a record that money code reads, not a document to rewrite.** Strong
evidence: code read. The plan replaces it with `docs/decisions/` ("superseded rows removed").
- **C5b, risk:** a brake restart is valid only when it cites the title of exactly one owner-quoted row of this file
  (`risk/decision_rows.py`, `risk/overrides.py:51`). C4's validity check reads it too (`checks/validity_account.py:159`).
- **BG1, budget:** `config.yaml` `budget.plan_cost.decision` is "DESK_DECISIONS 15 Oct 2026: Claude plan cost: INR
  20,000 a month". `budget/plan_cost.py` refuses the decided cost when that is not a row of the file.
- **A frozen record cites it:** `research/forecasts/FREEZE_v4.md` (lines 18 and 27) cites its rows by title, and can
  never be edited. CLAUDE.md's routine section, which the plan keeps word for word, cites "DESK_DECISIONS lines 284
  and 287". Workflows and judge reports cite it too.
- **The lane gate names it:** `tools/ci_scope.sh` lists it (and `WORK_REGISTER.md`) as lane-3 paths.
- Removing, renumbering or moving its rows would therefore:
  - make a valid restart or the budget's cost fail;
  - leave frozen citations dangling;
  - change the lane gate.
- Fix: list `docs/DESK_DECISIONS.md` under "Not in scope (records)": kept at its path, append-only, no row removed or
  renumbered. The new `docs/decisions/` pages say what is current and cite its rows.
- The same applies to every document a frozen file or a record cites: `docs/stories/G6-v4-freeze.md` (FREEZE_v4 line
  41) and `docs/JUDGE.md` rule 9 (line 28). They keep their path and their cited sections, or they stay as records.

**Should-fix 2. The register claim and the switch can lose other builders' changes.**
- The row claims `docs/**`, but every story builder edits `docs/stories/` and the register daily. As written, "one
  builder per function" would block them all, or be ignored.
- Between an area's P1 scan and its P6 switch (days), other sessions change that area's documents on `main`. P4 writes
  from the scan's snapshot, and P6 removes the replaced files, so a rule added meanwhile is lost silently.
- Fix:
  - claim only DOC1's own new folders, and each area's files only during its write;
  - pin each scan to a commit;
  - at P6, require `git diff <scan commit>..main` over the area's files to be reconciled. A plant: a rule added after
    the scan must be caught.

**Minor 1.** Correct the two counts above (339 rows; 27 code files and 43 lines, not 18).

**Minor 2. A cross-area pass is missing.**
- The market-school miss was one decision (response 325) that changed several areas at once: Books 1, 2 and 3, the
  plan and the build map. Per-area scanners must also list each cross-area decision and the areas it touches.
- P1 should name `reviews/claude/` responses and `conversations/` explicitly as sources, since that is where 325 and
  the owner's words live.
- With that, P2's "superseded (by what)" and P3's quoted intent would have caught both misses.
- The Book 2 miss is caught by P3: the intent page quotes the 13 Oct words, and P5 checks the design against it.

**Minor 3.** P6 must also update `tools/ci_scope.sh` (a CI file, lane 2) for every moved lane-3 path, and code
comments that cite `DESK_DECISIONS` by line number.

## Checked and sound

- The routine-prompt rule (section 4.1) and P6's 08:30-20:30 IST window.
- No frozen or byte-checked file is in scope: v4's `byte_checked` (149 files) and `RECORDED` name no `docs/` file, and
  no record holds a SHA-256 of any `docs/` file.
- PROC1's item taken over by agreement.
- Delete only with the replacement in the same commit.
- Gates on a482f2d7e in a clean worktree: record scan clean (9,537 files); doc-reading tests 963 passed, 13 xfailed,
  0 failed (no `test_groww_install_command` failure).

## Addendum 1

Revision 2 at `b91fb1422` (the owner's rules of 25 Oct, plus section 7), still round 1 as the orchestrator asked.
**FAIL: SF1 and SF2 are still open, and one new should-fix.**

- **New counts re-counted at 8edc21139:** 23 `docs/` files over 500 lines, 21 stories, 37 in the repository. Section
  7's sizes hold: REH1 2,000, REC1 857, E3 46. All MET.
- **SF1 open.** Line 59 still has `docs/decisions/` replacing "DESK_DECISIONS.md (345 rows, superseded rows removed)",
  and "Not in scope" does not list it. Round 1's evidence stands: C5b, C4, BG1's cited row, FREEZE_v4 and
  `ci_scope.sh`.
- **SF2 partly answered.** Section 7's ruling ("nobody moves, splits or deletes an existing document outside DOC1")
  helps, but two gaps remain:
  - the register row still claims `docs/**` (and still says "under 350 lines");
  - nothing stops a rule added on `main` between an area's scan and its switch from being dropped. Pin each scan, and
    reconcile `<scan>..main` at P6.
- **New should-fix 3: the interim rule contradicts the lane list it sits beside.**
  - CLAUDE.md's new Code bullet says a change to "a decision, a rule, a status or roadmap claim" needs a judge PASS,
    and keeps only "conversation logs, judge files and register rows" in lane 3.
  - The Branch section still lists "decision and status rows" as lane 3 (line 212), and `tools/ci_scope.sh` still
    treats `docs/DESK_DECISIONS.md` as lane 3.
  - So an agent can read either rule. That is the two-documents problem DOC1 exists to remove, inside the rule that
    governs it.
  - It widens checks and narrows no lane-1 rule: the Rule-document guard sentence is unchanged. But it must say which
    wins: amend the lane-3 list in the same change, and plan the `ci_scope.sh` change.
  - AGENTS.md's version, "judged like code (a judge PASS before `main`)", also says nothing of lane 2, which has no
    judge PASS. And it drops CLAUDE.md's qualifier "as the place a decision lives", so read alone it forbids the
    mandatory dated conversation logs.
- **Minor:** say in the new bullet that DESK_DECISIONS "Rule-document guard" still applies, so "the lane of the
  functionality it describes" can never move a lane-1-narrowing rule change to lane 2.
- **Gates at b91fb1422, clean worktree:** record scan clean (9,537 files); doc-reading tests 963 passed, 13 xfailed,
  0 failed.

## Addendum 2

Round 2 of 2, at `765c79001` (153 lines; it also carries revision 2's CLAUDE.md and AGENTS.md lines). **FAIL: 1
should-fix left (677.1's SF3), 2 minor.** Judge F not read. After this round the owner decides.

- **SF1, fixed.** `DESK_DECISIONS.md` is now under "Not in scope": kept at its path, append-only, no row removed,
  edited or renumbered, and any change to its form is a separate lane-1 code story. `docs/decisions/` cites its rows
  by date and title. The files that frozen files or code cite (JUDGE.md, G6-v4-freeze.md, plus whatever the P6
  citation check finds) keep their path and their cited sections.
- **SF2, fixed.**
  - The register row claims only DOC1's own folders, plus an area's files while that area is written, and never
    DESK_DECISIONS or records.
  - P1 is pinned to a commit.
  - Item 2c reviews `<scan>..main` at P6, with my plant.
- **Minors 1-3 from round 1, fixed:**
  - 339 rows;
  - P1 names `reviews/claude/` and `conversations/`, and P2b is a cross-area pass naming response 325;
  - item 2b covers `ci_scope.sh`, line-number citations, an old-to-new path map and pointer files.
- **Should-fix (677.1 SF3), not answered.** CLAUDE.md, unchanged since b91fb1422, still says two things.
  - Its new Code bullet makes "a decision, a rule, a status or roadmap claim" need a judge PASS, with only "conversation
    logs, judge files and register rows" left in lane 3.
  - Its Branch section, line 212, still lists "decision and status rows" in "Lane 3, no judge", and `ci_scope.sh` agrees
    with line 212.
  - The change widens checks and narrows no lane-1 rule. But it ships a rule document with two answers to the same
    question.
  - The fix is two lines in this branch:
    - line 212 reads "... conversation logs, register rows (owner decision rows appended to `docs/DESK_DECISIONS.md` by
      the orchestrator: lane 3 until DOC1's P7), ...", or whichever rule the owner wants;
    - the Code bullet names that exception and says the Rule-document guard still applies.
  - AGENTS.md's line needs the same qualifier ("in that lane's check; lane 3 as listed in CLAUDE.md") and "as the place a
    decision lives", or it forbids the mandatory dated conversation logs.
- **Minor 1:** section 4 item 2 says "1 runtime read". There are three: `budget/wiring.py:54`,
  `checks/validity_account.py:159` and `risk/overrides.py:51`. "Not in scope" names all three, so no harm now.
- **Minor 2:** the register row still says "each under 350 lines" (now 500).
- **Gates at 765c79001, clean worktree:** record scan clean (9,537 files); doc-reading tests 963 passed, 13 xfailed,
  0 failed.

## Addendum 3

Round 2's final head, `02dd914d1` (17393a334 and da825c6b7, plus the minors commit), judged in place of 765c79001
as the orchestrator asked. **PASS.** Judge F not read.

- **677.1 SF3, fixed.** CLAUDE.md's Code bullet and AGENTS.md now name the lanes: lane 1 needs a judge PASS, lane 2
  the orchestrator's check and the auditor.
  - Lane 3 is listed as conversation logs, judge files, number claims, register rows and the owner's dated rows in
    `DESK_DECISIONS.md`.
  - That agrees with the Branch section's lane-3 list (its "decision and status rows" are those rows, while a status
    or roadmap page takes its functionality's lane) and with `tools/ci_scope.sh`.
  - The bullet says the Rule-document guard still applies, and that the daily conversation log stays a log.
  - Against main, the change only widens checks: documents that had no review now take their functionality's lane. It
    narrows no lane-1 rule.
  - The CLAUDE.md diff against main is one added block in the Code section (11 lines). No routine section changed.
- **The 500-line exception** (F's item): a new document is never over 500 lines; an existing one may be edited until
  DOC1 splits it. That is clear, and matches section 7's ruling.
- **677.2 minors, fixed:** three runtime reads named with their lines; the register row says 500.
- **Gates at 02dd914d1, clean worktree:** record scan clean (9,537 files); doc-reading tests 963 passed, 13 xfailed,
  0 failed.

No blocking, should-fix or minor finding is left. P0's own gate still needs F's PASS and the owner's approval.
