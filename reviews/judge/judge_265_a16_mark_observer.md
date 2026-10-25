# Judge 265: A16's mark observer port (LM1 plugs in behind it)

Trading `story/a16-mark-observer` at 938577b3 (A16 builder 01VK88LxJvV1Gi7Wbr3D4fzp), from main. Lane 1. The interface
is agreed with LM1's owner, and the merge waits for A16's 5-session trial (orchestrator and owner). Judge D, 16 Oct 2026.

**FAIL: one should-fix**, small.

**Met:**
- **The port:** `MarkObserver.after_mark(day, mark, document | None, status)`, with `NoObserver` as the default and
  in the live wiring (`wiring.py`, where LM1 plugs in).
- **Once per newly settled row:** `Settlement.settle` returns only the rows written now (`settle.py:30-49`), and
  `notify` is called on those, before the commit.
- **The document:** this run's own snapshot is passed only for the mark it took. It is None for missed and failed
  marks and for another run's copy, as stated.
- **Isolation:** an observer exception is caught, and the line names the class only, never the message. The rows,
  alerts and commit go ahead (test).
- **recorder.py:** the change is 3 lines beside today's A16f and O9 edits.
- **Gates on 938577b3:** 7166 passed (`-n auto`, Slack token unset), ruff and check_imports clean.

## Should-fix: the catch-up path's notify is untested

`_settle_finished` (the `rv` command and the next session's catch-up of an unfinished one) now calls
`notify(self.observer, day, rows, None)`. The claims give it as the reason "missed marks reach LM1's stale clock".
**My mutation** removing that call passes all 206 `tests/intraday` tests. The only observer test runs through
`_close` (a run starting at 10:20). Add a test where a session's missed marks are settled by the catch-up path (a run
on the next session, or the `rv` command) and reach the observer as `missed` with document None. The mutation must
then fail.

## Note

My mutation narrowing the isolation to `except ValueError` also passes `test_observer.py`. The planted observer
presumably raises a `ValueError`. Raise something that is not a common built-in error (for example a custom class),
so that narrowing the catch fails the test.

## Addendum 1: head cc0a7132

**PASS (merge still held for A16's trial).** Only `tests/intraday/test_observer.py` changes.
- The new `test_the_rv_catch_up_reports_the_missed_marks_it_settles` (no run took the session; `settle_day` writes all
  26 marks as missed and each reaches the observer as `missed` with document None): **my mutation** removing `notify`
  from `_settle_finished` now fails it.
- The planted observer raises a custom `ObserverDown(Exception)`: **my mutation** narrowing the catch to
  `except ValueError` now fails the isolation test.
