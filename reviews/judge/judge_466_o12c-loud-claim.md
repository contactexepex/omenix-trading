# Judge 466: O12c, a refused number claim ends on its verdict line (story/o12c-loud-claim at f396f5bd)

**Verdict: PASS at f396f5bd (one commit on main ffa9e367). Lane 1. Merge go.** No should-fix. Two notes, neither
blocking.

## Criteria (docs/stories/O12-number-claims.md, section O12c)
| Criterion | Result | Evidence |
|---|---|---|
| A failed git step prints git's whole output first, then one last verdict line | MET | `tools/claim_number.py`: `GitFailed` is caught on its own, prints `failed.output`, then `NOT_CLAIMED` with the step's reason; `GitFailed` now carries `step` and `output` (`fno/numbering/git_main.py`), `_printed` joins stdout and stderr |
| The commit refusal's line is the story's text word for word | MET | `GIT_REASONS["commit"]` plus the `NOT_CLAIMED` tail give the story's sentence exactly; the test asserts its start and end |
| Every refusal ends with "Nothing was pushed: do not write the file" | MET | the tail is in `NOT_CLAIMED`, used by all three refusal paths (git, `ClaimRefused`/`ValueError`, `ClaimNotPushed`); `test_a_refused_or_lost_claim_exits_1` updated |
| Exit 1, nothing pushed | MET | unchanged return 1; the test checks origin's registry is unchanged |
| Planted hook (crashing, or refusing with findings): exit 1, the hook's words before a last line starting "number claim: NOT claimed", `main` unchanged, worktree removed | MET | `test_a_refused_commit_stops_loudly_with_the_hooks_own_words_and_pushes_nothing`, both cases, through the real `GitMain` and the real CLI against a local origin |
| One builder per function | MET | O12 and O12c rows have the same builder (main steward); the new row is in the commit |

## Claims against reality
- "9,751 passed": confirmed on a trial merge of the branch with main (merge 12205865 in a scratchpad worktree,
  removed): 9,751 passed, 16 xfailed; `ruff check` clean, `ruff format --check` clean, `check_imports` clean,
  `check_numbers` clean.
- "Printing the verdict before the output fails both cases": confirmed (2 failed).

## Plants
| Plant | Caught |
|---|---|
| Verdict printed before git's output | yes (2 failed) |
| git's output not printed at all | yes (2 failed) |
| The "Nothing was pushed: do not write the file" tail removed | yes (3 failed) |
| `_printed` keeps only stdout | yes (3 failed) |
| `_printed` keeps only stderr | **no** (see note 1) |

## Notes (not blocking)
1. **The stdout half of `_printed` is not tested, and the test's comment is off.** The second case's comment says the
   scan's findings "are on stdout, which must not be lost". But git sends a hook's stdout to its own stderr (as the new
   `GitFailed` docstring says), so the findings reach `done.stderr` and the stderr-only plant passes. Keeping stdout is
   harmless and cheap. Only the comment should change ("the hook's stdout reaches git's stderr"), on the next push to
   these files.
2. **The commit reason always blames the record-scan hook.** I ran the real CLI with an empty git identity. git
   printed "fatal: empty ident name (for <>) not allowed" above, and the last line still said "refused, by the
   record-scan hook ... run `sh tools/routine_setup.sh`". That advice does not fix it. No path from normal running gets
   there: every session and routine has a git identity, or none of its other commits would work. And the safety goal
   holds anyway: exit 1, nothing pushed, "do not write the file". The story text fixes this exact wording, so the code
   matches the story. A wording that names the hook only as the usual cause ("the commit was refused (usually the
   record-scan hook) ...") would be more exact; that is the builder's call.

## Side finding (confirmed)
Sessions set up before A23 lack `xlrd`, which the record scan's code now imports, so their hook crashes and every
commit is refused. `pip install -r requirements.txt` or `sh tools/routine_setup.sh` fixes it; this session hit it
earlier today.

No Drive, Groww or Slack access was used for this verdict.

## Addendum 1

**O12d, the two notes (story/o12d-claim-wording at 184ef5ca, one commit on main bf1c78e2): PASS, merge go. Lane 1.**

| Note | Result | Evidence |
|---|---|---|
| 2: the commit reason names the hook only as the usual cause | MET | `GIT_REASONS["commit"]`: "the commit was refused, usually by the record-scan hook: git's output is above; ..."; the O12c story text says the same; no other "by the record-scan hook" wording is left in code or docs |
| 1: the test comment matches git's behaviour | MET | "git passes a hook's stdout on through its own stderr" |

- Plant: back to the old wording, and 2 tests fail. The assertion pins the new wording.
- Gates on 184ef5ca: `tests/numbering` 63 passed; `ruff check` and `ruff format --check` clean; `check_imports`
  clean.
- I did not run the full suite myself: the diff is two message strings, one comment and one story line. The steward's
  full run (9,809 passed) is the one run for this merge.
- Main has moved 10 commits past bf1c78e2. None touch `tools/claim_number.py`, `tests/numbering/` or the O12 story,
  so the merge cannot conflict on judged lines.
- Cosmetic: the changed story line is longer than its neighbours, not re-wrapped. Not blocking.
