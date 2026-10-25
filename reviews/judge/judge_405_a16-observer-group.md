# Judge 405: A16 ObserverGroup (story/a16-observer-group at 6de320d2)

**Verdict: PASS. Lane 1 (A16's recorder). The builder may merge after the full gates pass on the exact pushed tree.**
Conditions below bind the member stories (LM1, A21) when they plug in.

## The orchestrator's question: can a hung member (LM1 at 90 s) delay the next mark's capture or commit?
**No, for the next mark. Yes, for its own mark's commit, by at most its limit.** I read `fno/intraday/recorder.py`:
`run(until)` is one process looping over the marks; `notify` (line 211) runs before that mark's `sync.commit`
(line 218). Each member runs in a daemon thread joined for at most its own limit, so:
- the current mark's commit waits at most the sum of the members' limits (LM1 90 s plus A21 10 s, so 100 s);
- the next mark comes 15 minutes later. Its claim and snapshot do not wait on any thread, so a hung member cannot
  delay them.

**Two things the group does not prevent** (no path today, because `_observers()` is empty; conditions for the member
stories):
1. **A timed-out member keeps running beside the commit and the next marks.**
   - Its files can be staged half-written by this mark's commit: the docstring says they "go up with the next mark's
     commit", but they can also be caught mid-write by this one.
   - At the next mark the same member is called again while the old thread may still run, so two copies run at once
     (for LM1, possibly two Slack posts for one event).

   Conditions:
   - every member writes its files atomically (temp file plus rename);
   - the group should skip a member whose previous call is still alive ("still running since <mark>"). That is a few
     lines and could be added now.
2. **There is no cap on the sum of limits.** Each member is capped at 300 s, but three members at 300 s would hold a
   mark's commit for 15 minutes. Today the sum is 100 s. Add a total cap (for example 300 s) when a third member
   comes.

## Criteria
| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Members run in order, isolated; a failure never skips the next | MET | `after_mark` collects every member's name, then raises `MembersFailed` once |
| 2 | Per-member limit in (0, 300] s, named at the owner's wiring line | MET | the constructor check; `_observers()` returns `()` until LM1 and A21 plug in |
| 3 | Only class names in the line, never a text | MET | `MembersFailed.names`; `notify` joins them |
| 4 | In the real recorder a hung or broken member never stops the row or the commit | MET | `test_in_the_recorder_a_failing_or_hung_member_never_stops_the_rows_or_the_commit` |
| 5 | Gates on a trial merge with main | MET | 8015 passed, 18 xfailed; 2 failed, the 2 that fail on main itself (not this change); ruff and check_imports clean |

## Planted mutations (all reverted)
| Mutation | Caught |
|---|---|
| `join()` with no limit (wait for ever) | yes, 3 failed (after the hung fakes ended) |
| A member's exception swallowed | yes, 2 failed |
| The (0, 300] check removed | yes, 3 failed |
| `MembersFailed` never raised | yes, 4 failed |
