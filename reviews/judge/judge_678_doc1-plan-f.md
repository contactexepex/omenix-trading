# Judge 678: DOC1, one clean current document set, plan (story/doc1-clean-docs @ a482f2d7e)

**FAIL on 3 should-fix, plan round 1 of 2, judge F (judge E the other; not read). Lane 1.** Own session
(session_01A8XfbTUVgeeEpqatHaWbtP). Text only. Labels: strong, some, reasoning only.

## Section 1 counts (re-counted at 8edc21139 with `git ls-tree`, `git show | wc -l`)

| Claim | My count | Result |
|---|---|---|
| 1,296 Markdown files; `docs/` 108 files, 44,865 lines, 33 over 350, largest 5,057 (HANDOVER_2026-10-16) | 1,296; 108 Markdown (112 files in all), 44,865, 33, 5,057 | TRUE (say "108 Markdown files") |
| `docs/stories/` 75 files, 31 over 350 | 75, 31 | TRUE |
| `conversations/` 36 files, 9,511 lines; `reviews/` about 950 | 36, 9,511; 956 | TRUE |
| 95 doc-reading test files | 95 | TRUE |
| DESK_DECISIONS.md "345 rows" | 345 lines, 339 dated rows | minor: lines, not rows |
| DESK_DECISIONS.md "18 references" in code | 9 path mentions in `fno/`, 44 mentions in `fno/` and `tools/`; one runtime read (below); 20 test files | minor: not reproducible; name the readers |

Gates (trial merge with main; only `.md` files change): record scan clean (9,537 files); doc-reading tests 963 passed,
13 xfailed.

## Findings

1. **Should fix: `docs/DESK_DECISIONS.md` is a live input and a record, not only a document (strong evidence).**
   - The money and risk code reads it. `fno/risk/overrides.py:51` checks every brake restart against its rows by title
     (`DESK_DECISIONS_FILE`, story C5b, `decision_rows.py`): the title must belong to exactly one dated row that quotes
     the owner. Removing "superseded" rows or splitting the table into `docs/decisions/` can stop a restart from being
     accepted. A changed title can also make another row match.
   - Records require it. `research/evaluation/REAL_MONEY_GATE.md` (in S1's `frozen_files`, line 420) asks for future
     evidence as "a dated row in `docs/DESK_DECISIONS.md`" (lines 133, 144). PROTOCOL.md and FREEZE_v4.md cite its rows.
     Frozen text cannot follow a move.
   - `tools/ci_scope.sh:12` lists it as a lane-3 path.

   The plan treats it as one of the "documents replaced" (section 2 table) and puts it in the register row's scope.
   Fix: keep DESK_DECISIONS.md where it is, append-only, outside DOC1's scope, like `reviews/`; the new `docs/decisions/`
   pages cite its rows by title. Any change to its form or path is a separate lane-1 code story (C5b's reader, the gate
   text before its freeze).
2. **Should fix: citations into moved files break silently (strong evidence).**
   - Frozen and recorded texts cite `docs/` paths. FREEZE_v4.md cites `docs/JUDGE.md` and
     `docs/stories/G6-v4-freeze.md`; judge reports cite story sections and line numbers (e.g. "line 980").
   - There are 138 "DESK_DECISIONS line/row N" citations in Markdown and code (e.g. CLAUDE.md "lines 284 and 287",
     `fno/playbook/decision_record.py:42` "row 229").
   - P6 moves JUDGE.md to `docs/process/`, splits the multi-story files, and safety rule 4 removes the old files. Nothing
     keeps these citations valid, and no test reads them.

   Fix: add a safety rule. A file cited by a frozen file or a record keeps its path, or keeps a short pointer file at that
   path; `docs/README.md` keeps an old-path to new-path map; decisions are cited by title, not by line. Then add the
   cited paths to section 4's check list.
3. **Should fix: the gate that would have caught the Book 2 and market-school misses is not a deliverable (reasoning
   only).**
   - Both misses were a story or design never checked against the owner's intent, and superseded text left in place.
   - P1-P5 would find today's cases. But only principles 3 and 4 say how the next one is prevented. P7 delivers the
     CLAUDE.md/AGENTS.md slimming, the update-in-place rule and a size test. It does not deliver the JUDGE.md change:
     every story cites its intent line, a judge checks the story against it (a FAIL when missing), and a merge that
     changes a rule updates its area page in the same merge.

   Fix: put those JUDGE.md rules, and how they are checked, into P7 and its gate.

## Notes

- Section 4's other risks hold. The routine prompts name CLAUDE.md sections, and those sections stay word for word. PROC1
  item 3 (the docs archive) is taken over with its builder's agreement before P1. The frozen files listed in section 2
  are out of scope.
- P6's window (outside 08:30-20:30 IST) clears every routine. Name the rehearsals and judge sessions too, or keep the
  switch to one merge, so that one read sees one set.

## Addendum 1

**Still round 1, at the new head story/doc1-clean-docs @ b91fb1422 (revision 2 and section 7), judge F: FAIL on 4
should-fix.** I did not read judge E. bba6ad145 and b91fb1422 were committed before my verdict 163fda2fb, so they do
not answer findings 1-3. All three still stand unchanged: DESK_DECISIONS.md as a live input and record, citations into
moved files, and the JUDGE.md rules P7 must deliver.

| Check | Result | My evidence |
|---|---|---|
| New counts: 37 Markdown files over 500 lines, `docs/` 23, `docs/stories/` 21 | TRUE | at 8edc21139, file names with spaces included |
| Section 7: work in review lands in its current file; new pieces get their own file; only DOC1 moves files | SOUND | REH1 2,000, REC1 857, E3 46 lines on main, as listed |
| The interim rule widens checks | YES, in part | documents about lane-1 work now need a lane-1 judge; before, they could go lane 2 |
| Gates (trial merge with main) | PASS | record scan clean (9,539 files); doc-reading tests 963 passed, 13 xfailed |

4. **Should fix: the interim rule in CLAUDE.md disagrees with the lane rules and with section 7 (strong evidence: the
   texts side by side).** Agents reading different lines would act differently, which is the problem DOC1 exists to
   fix.
   - **(a) Lane 3.** The "Branch" section keeps "decision and status rows" in lane 3, with no judge. The new bullet
     needs a judge PASS for "a decision ... a status or roadmap claim", and exempts only "conversation logs, judge files
     and register rows". The two now contradict. Say which wins; the owner's own decision rows are probably meant to
     stay lane 3.
   - **(b) The rule-document guard.** "In the lane of the functionality it describes" can be read as moving a rule
     document to a lower lane. Example: a JUDGE.md or CI-rule change describes lane-2 work, yet narrowing lane 1 keeps
     it lane 1 under the guard. Fix: add the plan's own line ("a functional document's lane is never lower than its
     code's") and "the rule-document guard still holds" to both CLAUDE.md and AGENTS.md.
   - **(c) The limit.** "No document over 500 lines" applies at once in CLAUDE.md, but section 7 lets review work land
     in files of up to 2,000 lines. Read literally, CLAUDE.md fails every REH1 or REC1 story edit. Fix: CLAUDE.md
     states section 7's exception (existing files until DOC1 reaches their area; new documents under 500 lines).
   - Minor: AGENTS.md says "a judge PASS ... in the lane", but lane 2 is the orchestrator's check. Say "its lane's
     check".

For PASS: findings 1-4 fixed in the text. Each is a few lines.

## Addendum 2

**Round 2 of 2 at story/doc1-clean-docs @ 17393a334, judge F: PASS (2 minors). Lane 1, text only.** I did not read
judge E.

| Finding | Answer | My check | Result |
|---|---|---|---|
| 1 DESK_DECISIONS.md is a live input and a record | Out of scope: it stays at its path, append-only, and no row is removed or renumbered. A change to its form is a separate lane-1 story. The new pages cite its rows by date and title | Plan section 2. The new readers it names exist on main: `fno/checks/validity_account.py:159` (`decision_rows` of `DESK_DECISIONS_FILE`) and `fno/budget/items.py:22-27` (the `DESK_DECISIONS <date>: <title>` citation) | **Accepted** |
| 2 Citations into moved files | 2b: a citation check before each switch; an old-to-new path map; pointer files for files that frozen files or judge reports cite; cite by title; `ci_scope.sh` and line-number comments updated. Cited files keep their path | read; it covers FREEZE_v4.md's three paths and the 138 row citations | **Accepted** |
| 3 The P7 gate | JUDGE.md rules: cite the intent line, FAIL when it is missing or contradicted, and update the area page in the same merge | read in the P7 row | **Accepted** |
| 4a Lane 3 | Lane 3 names conversation logs, judge files, number claims, register rows and the owner's dated DESK_DECISIONS rows; it matches the Branch section's list and `ci_scope.sh`'s LANE3 | read side by side | **Accepted** |
| 4b The Rule-document guard | "Never a lower one" and "The Rule-document guard still applies" are in CLAUDE.md; AGENTS.md names the lanes | read | **Accepted** |
| 4c The 500-line limit without section 7's exception | not changed | CLAUDE.md:240 still has no exception | **Now a minor** (below) |
| My note and minors | The switch also avoids rehearsals and judge rounds; the counts are corrected | read | **Accepted** |

The interim rule widens checks only. Documents about lane-1 work now need a judge PASS, and nothing moves to a lower
lane.

Gates (trial merge with main; only `.md` files change): record scan clean (9,539 files); doc-reading tests 963
passed, 13 xfailed.

**Minors (not blocking):**
- **m1 (4c, downgraded).** The owner's revision 2 calls layout and size findings "minors only", so I downgrade it under
  the owner's own rule. The plan's section 7 is linked from the same bullet, and its ruling covers files in review.
  Still, add "(existing files: plan section 7)" after "No document over 500 lines" when the text is next touched.
- **m2.** The DOC1 row in `docs/WORK_REGISTER.md` still says "each under 350 lines"; it should say 500.

## Addendum 3

**Round 2 at the head story/doc1-clean-docs @ 02dd914d1 (17393a334 + da825c6b7 + 02dd914d1), judge F: PASS, no open
finding. Lane 1, text only.** I did not read judge E.

| Item | Change | My check | Result |
|---|---|---|---|
| m1 (my 4c) | CLAUDE.md: "a new document never; an existing one already over 500 may still be edited until DOC1 splits it, per the plan's section 7"; AGENTS.md says the same | read; it matches section 7's ruling | **Fixed** |
| m2 | the register row says 500 lines | read | **Fixed** |
| Section 4, item 2 | "3 runtime reads" named | `fno/budget/wiring.py:54` reads `DECISIONS_FILE`; `validity_account.py:159` and `overrides.py:51` checked in 678.2 | **True** |

Since 678.2 only these three commits changed, and only the lines above. The interim rule still widens checks only.
Gates (trial merge with main; only `.md` files change): record scan clean (9,539 files); doc-reading tests 963
passed, 13 xfailed. Layout note only: the new AGENTS.md line is 184 characters (many lines there are already long).
