# Judge 539: DR1-d, every routine starts on latest main (story/dr1-routine-start at 8d35eeb5)

**Verdict: PASS. Lane 1 (a rule document about the scheduled routines). Round 1 of 2.** Text only. No should-fix.
Two notes.

## Criteria
| Criterion | Result | Evidence |
|---|---|---|
| Narrows no lane-1 rule and touches no hard line | MET | The diff is limited to the routine push lines (CLAUDE.md 70, 85, 140, 164), one new Branch-section paragraph and two owner checklists. The lane table, the hard lines, the record scan ("never `--no-verify`" kept) and the channel rules are untouched |
| Each routine's first line: `git fetch -q origin main && git checkout -q --detach origin/main`, and on failure post and stop | MET | The CLAUDE.md Branch paragraph; step 0 in `A16-owner-checklist.md` and `F1-G5-owner-checklist.md`. In F1-G5 it comes before the background pip install, and the old `git checkout -q main && git pull` step is replaced. That run has no Slack, so its failure message is its final message |
| Detached HEAD plus `pull origin main` and `push HEAD:main` works with every committer | MET | Every pull and push in `fno/` names origin main or `HEAD:main` (git grep): O1's `Git` (`PUBLISH_BRANCH`, judge 474), `GitManifestRecorder` (A16, pre-open, closes, librarian), `receipt_publisher`, the AI books' seal (`ai/transport` `BRANCH`), `PlaybookGit`. None reads the checkout's branch name; `abbrev-ref` and `symbolic-ref` appear nowhere. Numbering works in its own worktree |
| The same flow on real git | MET | My scratch repos: a clone on a session branch, detached at `origin/main`, commits, pulls another writer's newer main commit, then `push origin HEAD:main`. The push lands on main as a merge, and origin gets no session-branch ref |
| Text-only gates (owner, 23 Oct) | MET | Every changed file is `.md`. The doc-reading tests on the branch: 785 passed, 16 xfailed. The record scan runs at commit |

## Plants
None: a text-only change has no code to break. The real-git check above stands in for one.

## Notes (not blocking)
1. **"Matches what the owner pasted" is not verified.** I cannot see the owner's stored routine prompts. I checked the
   repository text against the line the orchestrator quotes. If the owner's pasted line differs by a character (for
   example, without `-q`, or `checkout` without `--detach`), the routine still works, but the documents and the
   prompts would then disagree. The owner can compare them once.
2. **Two awkward wraps.** In CLAUDE.md quote-parts step 3, the line breaks after "then `git push origin HEAD:main`);
   never". The A16 checklist's step 4 reads "then (push with `git push origin HEAD:main`)", inserted mid-sentence.
   Both read correctly; tidy them on the next edit.
