# Judge 564: REH1c, the routines' rehearsal, story/reh1c-routines

- **Judge:** E (session_01HkXMVPDEqVsmJZtghFrGzM), lane 1, my round 1 of 2. Judge B's round 1 is 563.
- **Heads judged:** 90bffac2 (full gates and 11 plants), then 73053f9a, judge 563's answer (the survivors
  re-planted). Both were merged with main for testing. At 90bffac2 one conflict in
  fno/close_read/wiring.py was resolved locally (main's stored closes plus REH1b's recorded source), never
  pushed.
- **Claims:** docs/stories/REH1-rehearsal-mode.md, "Claims / REH1c" and "REH1c round 2"
- **Verdict: FAIL.** Two wiring points of the orchestrator's (a) and (b) are untested. The design holds.

## Gates (90bffac2, merged)
- pytest -n auto: 15094 passed, 0 failed.
  - A first run beside another suite showed 2 errors; run alone it was clean.
- ruff check, ruff format --check, check_imports, check_records: clean.
- The builder reports 15,104 passed on 73053f9a.

## Findings: still surviving on 73053f9a
1. **F1 (blocking, point b): C4, the daily run's wiring never applies the not-live wrapper.**
   - The plant: in `fno/daily/wiring.py`, `steps = rehearsed_not_live(steps, not_live)` becomes `pass`.
   - It passes the full suite (15,094) and REH1c's tests on 73053f9a.
   - With it, every step made live only for the rehearsal posts without its "not live in real runs" line,
     so the owner would read a not-yet-live report as live.
   - `test_not_live_reports.py` tests the wrapper on its own, not its wiring. Pin: `build_day_runner` with
     the mode set wraps each step that is not live on the replayed day.
2. **F2 (blocking, point a): C10, the routine's receipts commit runs without the rehearsal's environment.**
   - The plant: `commit_receipts`' git runs with `env=None`.
   - It passes the full suite and REH1c's tests. With it, that commit goes past the shim and carries the
     wall clock's date.
   - Pin: a receipts commit made by `rehearse(...)` carries the replay date.
3. **Fixed already in 73053f9a, which I confirm:**
   - The routines are held to CLAUDE.md both ways. I had found the morning's and evening's
     `records certify closes` missing; the two-way test now catches it.
   - C9, the shim off the PATH, is caught at 73053f9a by REH1b round 2's replay-date test (1 failed).

## Checked and right: 8 of 11 plants caught at 90bffac2
- **(a) Commits:**
  - The receipts commit runs the hooks; C1 (`--no-verify`) is caught.
  - It pushes `origin HEAD:main` to the bare origin; C2 (pushed elsewhere) is caught.
  - Every routine command is a `python -m fno` child in the clone. Its committers push to `origin`,
    which is the bare origin.
- **(b) Labels:**
  - The label comes first. The not-live line is added from the step's environment (C3, C5 caught) and
    reaches child steps, since `ChildProcesses` inherits `os.environ`.
  - E8's owner-timing fills keep their real live date (C11 caught).
  - The label no longer has a pending line.
- **(c) The guard:**
  - It runs without Drive: `RecordFiles` signs in only at its first read (C7 caught).
  - A16's clock check must be in its rehearsal form (C8 caught).
  - A guard problem stops the run (C6 caught).
  - The fii-dii snapshot is `rehearsal:NOT_RECORDED` through `NotRecordedSession`, as round 2 corrects.

## Note
`FNO_REHEARSAL_NOT_LIVE` is process-wide. It is safe only while the daily run's steps run one at a time,
which the claims state. A parallel step runner would need the note passed to each child explicitly.

## Addendum 1

- **Head checked:** 320d4810, my round 2 of 2. Since 73053f9a it adds only two test files; no code.
  Merged with main as 33e96d04 for testing.
- **Verdict: PASS (my half). Merge once judge B also passes.**
- **Gates:** pytest -n auto: 15106 passed, 0 failed. ruff check, ruff format --check, check_imports and
  check_records: clean.
- **F1 fixed:** the real `build_day_runner`, with the mode set, wraps exactly the steps in
  `rehearsed_live`'s notes, the card among them. Plant C4 now fails (1 failed).
- **F2 fixed:** an evening rehearsal on a real repository publishes a receipts commit dated within 2
  minutes of 19:53 IST on the day. Plant C10 now fails (1 failed).
