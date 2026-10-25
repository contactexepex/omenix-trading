# Judge 454: FL1-1d go-live (story/fl1-1d3-minors at 6610395a)

**Verdict: PASS (lane 1: schedules and Slack). The builder may merge: pull, one full run on the merged tree, push.**
Both editions go live on Fri 23 Oct.

## What the branch carries, each checked
1. **Judge 451's fix, 6a419dab, unchanged (451.1 PASS).** The evening reads A17 at its 20:05 run time, then falls back
   to the labelled 09:15 reading. The quiet-evening line is in.
2. **The designer's package, byte-identical to story/fl1-1d-design at 4b261d3d.** `git diff 4b261d3d 6610395a`
   shows nothing under `fno/forecast_lab/design/` or the design tests. 4b261d3d's only change since my 446.1 PASS
   (be8fc69f) moves the hostile test reason onto a shown red row, which closes 446.1's minor.
3. **The wiring, one line plus the width.** `ReportMaker(pages, DesignRenderer(), ChromiumCamera(width=1100))`,
   pinned by a test. Putting `InterimRenderer` back fails a test.
4. **`forecast_lab.live_from`: morning and evening on "2026-10-23", pinned by a test.** The owner's decisions cover it:
  - the design is signed off (11ef1b23);
  - "everything in progress joins the go-live as it finishes" (row 282).

## Gates
On 6610395a merged with today's `main` (no conflicts), one run:
- 9,478 passed, 16 xfailed;
- `ruff check` clean; 1,789 files formatted;
- imports clean; record scan clean (7,525 files).

Strong evidence.

## The story's go-live conditions (FL1-1d, "Go-live conditions")
- **CLAUDE.md sections: present on `main`.** "Morning and evening forecast routines" carries the exact stored prompts,
  steps 1b and 1c, and the commit rule.
- **The design sign-off: done** (11ef1b23).
- **Criterion 7, channel membership: met** (judge 422 ruling).
- **The owner's two scheduled tasks (08:38 and 19:53 IST): I could not verify them.** My read-only scheduled-task
  listing shows only one weekly task, not even the 14:05 daily desk routine, which is known to run, so it does not
  see the owner's routines. If the tasks do not exist on 23 Oct, nothing runs and nothing is posted: safe, but no
  report. **The orchestrator must confirm with the owner that both tasks exist with response 304's exact prompts
  before Friday 08:38 IST.**
- **The evening checks nothing until A4h's `TodayCloses` adapter is wired.** It says so plainly ("today's close was
  not read ...; its result appears in tomorrow morning's report"), and the morning's own check on the official close
  gives the result the next day. This is a stated limit, not a defect.
- **The first live run of each edition is to be checked against its record before the next run** (condition 4): the
  orchestrator's task on 23 Oct.

## Minor (carried and new)
1. **From 451.1, still open:** the evening cutoff order in `page_wiring.build_sections` is untested.
   `(OPEN, EVENING_RUN)` still passes all 164 forecast-lab and acceptance tests. Add the assertion in the follow-up.
2. **`InterimRenderer` is unused in production now** (page/simple.py, html.py, bigchart.py, svg.py, grid.py, zoom.py
   and their CSS). The builder proposes removing it after go-live, moving the replay and maker tests to
   `DesignRenderer`. **Accepted as a follow-up**, not in this go-live commit: tests still use it, and removing a
   renderer the day before go-live adds risk for no gain. Under the no-dead-code rule it gets a register row and
   lands within the week.

## Note: e31e46ce (the merge head)
e31e46ce is 6610395a plus 20 lines in `tests/forecast_lab/test_wiring_editions.py`, which pin `build_sections`'
cutoffs. I planted both of my 451.1 variants, `(EVENING_RUN,)` and `(OPEN, EVENING_RUN)`: each now fails that test
(148 forecast-lab tests otherwise pass). Minor 1 is closed. **The PASS covers e31e46ce.** The merge runs its own full
suite on the merged tree.
