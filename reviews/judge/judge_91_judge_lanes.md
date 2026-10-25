# Judge 91: the judge-lanes rule text (trading 63f69d3: `docs/JUDGE.md` "Judge lanes", `CLAUDE.md` Branch, `docs/DESK_DECISIONS.md` row)

The orchestrator asked what I would change, and why. The owner has accepted the lanes. The decision row quotes "Judge
lanes => I accept and confirm". Everything below is a proposal for the owner. None of it reopens that decision. Each
point is marked strong evidence, some evidence or reasoning only.

## What is right

- Lanes are set by what a change can damage, not by its size, and "unsure means lane 1".
- Lane 1 covers what today's FAILs were about:
  - the rewrite re-read (A8);
  - the AI cost subtracted in every section (S2);
  - the funds-at-entry rule (C2);
  - post-freeze edits (S1).
  None of these would have been lane 2 under this text (strong evidence: judges 85, 87, 77 and 89).

## Changes I propose

1. **Decide lane 1 by file path, not by reading intent** (some evidence).
   - The builder, or the orchestrator who wants the merge, decides what "touching" means. "Unsure means lane 1" only
     works when someone is unsure.
   - Today's example: the F1 late-start change moved a constant out of `fno/pipeline/capture_gate.py`. Described as a
     refactor, that sounds like lane 2. It sits on a workflow gate, so it is lane 1.
   - Proposal: any diff touching these paths is lane 1, whatever its description:
     - `.github/`, `.githooks/`, `config.yaml`, `db/`, `requirements*.txt`;
     - `fno/constants.py`, every composition root listed in `CLAUDE.md`;
     - `fno/risk`, `fno/desk`, `fno/books`, `fno/checks`, `fno/scorecard`, `fno/scoreboard`, `fno/evaluation`;
     - `fno/forecast*`, `fno/ai`, `fno/quotes`, `fno/pipeline`, `fno/storage`, `fno/playbook`;
     - every file a freeze lists;
     - `research/data/calendar/`.
   - A short checked-in list keeps this mechanical. A test or the orchestrator can match a diff against it.

2. **"Tests only" is lane 2 only when it adds tests** (some evidence).
   - Deleting, skipping or loosening an assertion in a lane-1 area is lane 1.
   - A weakened guard passes the orchestrator's re-run by construction.
   - Judge 89 found the A8 alert step's `always()` unpinned: a single edit that silently stops a crash alert.

3. **Rule documents are lane 1** (reasoning only).
   - These are: `docs/JUDGE.md`, `CLAUDE.md`, `AGENTS.md`, `docs/stories/*` acceptance criteria, protocol and freeze
     documents, and the owner checklists.
   - They change what every agent does, so "docs" in lane 2 should mean only explanatory text.
   - Lane-3 decision rows stay lane 3 only when they quote the owner.

4. **The gates themselves are lane 1** (reasoning only).
   - These are: `tools/check_imports.py`, `tools/check_records.py`, `tests/test_code_size.py`, `.githooks/pre-commit`
     (the record scan) and `.gitattributes`.
   - Weakening a gate is invisible to a re-run of that same gate.

5. **Lane 3 data means only a scheduled job's own output paths** (reasoning only).
   - A job commit that touches anything else, or data edited by hand by a session, is not lane 3. Examples: calendar
     rows, golden values, margin tables, manifests.
   - Hand-edited calendar rows decide trading days, so they are lane 1.

6. **Make lane-2 merges findable and the audit gap-free** (reasoning only).
   - Each lane-2 merge commit message starts with "Lane 2:". It names the branch tip and the builder's claim, and
     gives the orchestrator's test count.
   - The audit covers every commit on `main` from the last audited commit to the current one, not "that day's" merges.
     A merge just after one audit is then never skipped.
   - I record the audited range and verdict in the judge README, and plant mutations on each lane-2 change as on lane 1.

7. **A lane-2 FAIL that is a correctness bug is reverted at once** (reasoning only).
   - Use `git revert`, never a history rewrite, then fix it on a branch.
   - Docs and test-only FAILs can be fixed in place, first, before new work.
   - The current text says only "fixed first", which leaves a wrong behaviour on `main` while the fix is built.

8. **The dashboard repository needs its own lane-1 paths** (reasoning only).
   - Any change to what data the dashboard reads or renders for strategies is lane 1, under the privacy rule.
   - Lane 2 there would be styling and copy only.

## Daily audit time

17:30 UTC (23:00 IST) is acceptable. It comes after the 17:00 A13 check and after the evening jobs. Each audit covers
`main` from the previous audited commit up to the current one. A lane-2 merge after 17:30 UTC falls into the next day's
audit. Anything urgent can be moved into lane 1 instead.

## Not changed

Lanes 1 and 3 as written; my own standard for lane-1 reviews (`docs/JUDGE.md`); the owner's hard lines.
