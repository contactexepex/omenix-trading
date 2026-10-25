# Judge 419: O1 fix text, a quote part's unpushed commit never stops the desk (story/o1-own-commits at 3e15cf3a)

**Verdict: PASS (text). Lane 1. Its code has its own verdict.** It follows judge 412 addendum 3 point for point.

| Point | Result |
|---|---|
| One `GitCommitter` per run, shared by the parts and the desk's `PendingCommitter`; it remembers its unpushed commits as content-checked `OwnCommit`s; a stranger is still refused | MET |
| A git-ignored list (`journal/runs/.own_unpushed.json`) for a same-container rerun; a new container has none (its clone holds only origin's history) | MET, and correct |
| No reset | MET |
| The wording "committed, NOT pushed (the next push carries it)" | MET |
| Tests: refused and hung part pushes carried by the next desk push with one alert; a stranger refused; a rerun accepts by content and refuses changed files; G4's xfail made real | MET |

## Notes for the code
1. **Add `journal/runs/.own_unpushed.json` to `.gitignore`, with a test.** `journal/runs/*.json` are committed run logs,
   so one wrong glob would publish the list.
2. Clear an entry once a push carries it, so a later stranger with the same message cannot ride on a stale entry. The
   content check makes this unlikely, but clearing keeps the list honest.
3. **Book 1's own decision commit, made by the `desk book1` child, is deliberately not covered:** E5b's rule
   (`fno/books/book1_cli.py`) is that an unpushed decision is "not on time unless pushed before E3's deadline, and a
   daily run in this checkout stops at its first commit until this is resolved". That stop protects decision timing,
   so it is right to keep. Say so in the section, so nobody "fixes" it by adding the child's commits to the list.
