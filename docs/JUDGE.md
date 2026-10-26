# The judge

An independent, honest reviewer. It never writes code and never edits files other than its verdict. It trusts
nothing it has not checked itself.

## Lanes: what each change needs

Which review a change needs is set by what it can damage, not by its size. When the builder or the orchestrator is
unsure, the change is lane 1.

| Lane | Covers | Review |
|---|---|---|
| 1 | Secrets; outside services (Slack, Groww, Drive, NSE), including the schedules and workflows that call them; write-once data and the receipts that prove it; frozen files; the public-record (privacy) rule | The code judge's PASS on the branch before merge |
| 2 | Everything else that is not lane 3: tools, CI, tests, docs, rule documents, when they change no record | The orchestrator re-runs the gates and compares the claims with the diff, then it merges; the lane-2 auditor checks that day's lane-2 merges once |
| 3 | Judge files, conversation logs, and data commits by scheduled jobs (their own output paths only; data edited by hand is lane 1) | None |

- A lane-2 merge's commit message starts "Lane 2:" and names the branch tip, the claims and the orchestrator's test
  count. The audit covers every commit on `main` since the last audited one; its range and verdict go in the judge
  README. A lane-2 correctness FAIL is reverted at once with `git revert`, then fixed on a branch; a docs or test-only
  FAIL is fixed in place, first.
- Deleting, skipping or loosening a test in a lane-1 area is lane 1. The auditor may move any kind of change into
  lane 1 when its audit finds problems there.
- **Rule-document guard** (owner, 22 Oct 2026): a change to a rule document (e.g. `CLAUDE.md`, `AGENTS.md`, this file,
  owner checklists, freeze documents) is lane 2, except that one which narrows lane 1 or touches a hard line (no
  orders, secrets, privacy, write-once data, frozen files) stays lane 1 and needs the code judge's PASS.

## Two judges

One **code judge** for lane 1 and one **lane-2 auditor** (owner, 22 Oct 2026). Each is a separate session that did not
build what it judges and shares no context with the builders.

## For each lane-1 story

1. Read the story in `docs/stories/`, including its **Claims** section (the builder's claims live there, updated each
   round).
2. Read the diff (`git diff <base>..HEAD`) and every changed file in full where needed.
3. For every acceptance criterion: find the code and the test, and run what can be run (tests, ruff, the checks, CLI
   commands, small scripts). MET only with your own evidence (file:line, command output); unverified is NOT MET.
4. Hunt for what was not claimed: bugs, edge cases (holidays, special sessions, empty data, missing credentials,
   network failure, time zones), anything that could lose or corrupt data, leak a secret, or write outside the
   expected paths; look-ahead, dead code, misleading docs, tests that pass without testing the claim. Plant your own
   mutations.
5. Check `CLAUDE.md`'s engineering standards (a file or class over 350 lines is a should-fix at least).
6. Verdict: PASS, or FAIL with numbered findings (blocking / should fix / minor), each with evidence and the fix
   expected. A story passes only with no blocking and no should-fix findings left.

## The verdict file: a fixed template, 40-60 lines

`reviews/judge/judge_<n>_<story>.md` (a later round is a `## Addendum <k>` in the same file), indexed in
`reviews/judge/README.md`:

1. Title: story, branch, SHA. One line: PASS or FAIL, lane.
2. Criteria: one row each, MET / NOT MET / PARTLY, with your evidence in a few words.
3. Findings (FAIL only): numbered, severity, evidence, fix expected.
4. Plants: how many you planted, how many the tests caught, and any survivor.
5. Notes (not findings), if any.

Quote a builder claim only when it is wrong. No praise, no restating the story.

## Rounds: at most two

1. On a FAIL the builder fixes each finding, with its proof (commit, test, command output), or pushes back with
   evidence that the criterion is already met. "I disagree" without evidence is not a pushback.
2. The judge re-judges once, in an addendum: each fix or pushback is accepted or rejected, with its own evidence. A
   pushback is accepted only when the judge reproduces the proof.
3. **After two rounds, the owner decides** (owner, 22 Oct 2026). The orchestrator puts both sides' evidence to the
   owner; no third round.
4. On PASS the builder merges under the merge procedure below.

## Two judges for safety-critical changes (owner, 22 Oct 2026)

A lane-1 change that touches secrets, write-once data or the safety laws (no orders, privacy) is judged by **two
different judges**, each independently, each with its own judge file and its own two-round limit; it merges only after
**both** PASS. If the two disagree after their rounds, the owner decides. Other lane-1 changes keep one judge. The
orchestrator names the second judge when it routes the change.

## Quality rules for every lane-1 story (owner, 15 Oct 2026: "rules yes")

1. **Story text first**, pushed alone and checked by the judge against the design and the owner's decisions before
   code starts.
2. **Gap list:** each requirement of the design is covered by a named criterion or listed out of scope with its reason;
   a requirement in neither list is a blocking finding.
3. **Builder self-review:** independent code-review agents on the diff; the Claims section says what they found and
   what was fixed or why not.
4. **Broken-code proof:** each criterion names its code and a test that fails when that code is broken on purpose. The
   judge still plants its own.
5. **Good, bad, boundary and empty cases** for each criterion.
6. **Real output sample** in the Claims section, made by the committed code in a dry run or a test, within the privacy
   rule and the record scan (never secrets).
7. **Orchestrator check before the judge:** a complete story at an exact pushed SHA.
8. **End-to-end run after merge:** whoever merged runs the merged system once on real data (dry-run where it has one)
   and records the command and result in the merge message or its follow-up; a change with no real-data path says so.
   A failed run means `git revert` of the merge at once.

## Merge procedure (owner, 21 Oct 2026: one full run per merge)

- The gates (`python -m pytest -q -n auto`, `ruff check fno tests tools ops`, `python tools/check_imports.py`, `python
  tools/check_records.py`, `python tools/check_numbers.py`) run **once, on the merged tree**. Never push on red.
- A change of Markdown files only (no `.py`, test, config, workflow or requirements file) never runs the full suite
  (owner, 23 Oct 2026): the record scan, `check_numbers`, and the doc-reading tests unless every file is lane-3
  (CLAUDE.md "Code", "Text-only changes"). This holds for the builder, for each judge round and for the merge; a round
  that only rewords text is judged by reading it.
- The gates need the whole git history: in a shallow clone the back-fill tests fail with "shallow clone: run git
  fetch --unshallow origin main"; run that, then the gates again. It is never a code failure.
- A merge that moves data (rows into Drive, a back-fill) also runs the moved data's own command once in a fresh clone
  of the merged `main`, with the Drive settings.
