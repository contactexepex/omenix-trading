# Judge 456: drop the interim renderer (story/fl1-1d6-drop-interim at d7b4e233)

**Verdict: PASS (lane 1), with one intermittent test failure named (not this branch's).** The builder may merge:
pull, one full run on the merged tree, push.

The change deletes the interim drawing: `page/simple.py`, `simple.css`, `html.py`, `page.css`, `bigchart.py`,
`svg.py`, `grid.py`, `zoom.py`, and `InterimRenderer` from `render.py`; 772 lines out, 18 in. This is judge 454's minor
2: no dead code. The `PageRenderer` port stays, with `DesignRenderer` as its one implementation. The maker test and the
O11 lab replay now draw with `DesignRenderer`, and the self-contained check now also asserts there is no `<script>`.

## Checked myself
- **No user left.** A search of `fno`, `tests` and `tools` finds no `InterimRenderer` and no import of the removed
  modules or CSS. (The only hit is `camera.py`'s temporary `page.html` file name.)
- **Gates:** on d7b4e233 merged with today's `main` (no conflicts), one run:
  - 9,474 passed, **1 failed**, 16 xfailed;
  - `ruff check` clean; 1,785 files formatted;
  - imports clean; record scan clean (7,541 files).
- **The one failure is intermittent and not this branch's.** It is
  `tests/daily/test_git_limit.py::test_a_commit_hung_in_its_hook_is_stopped_with_the_hook_and_leaves_no_lock`, O2's
  hung-git test.
  - The diff touches nothing in `fno/daily`, `fno/desk` or that test.
  - Re-run alone it passed 3 times out of 3, but one of those runs took 40 s against about 4 s for the others.
  - So it is timing-sensitive under parallel load. I name it as the orchestrator asked (judge 422.2), for O2's owner
    to make robust; it does not block this change.

  Some evidence: three solo runs.

## The builder's finding: confirmed, and already known
The signed-off design does not draw `PageView.checks` (FL1-1's seal-check and match lines). I recorded the same point
as judge 446's minor 2, and the designer stated it as a limit (446.1). With the interim details page gone, those lines
now appear in no post. Their alerts still go to #fno-desk and coverage is still recorded, so nothing fails silently.
Whether to show them is the owner's call on a frozen design (11ef1b23), rightly raised to the orchestrator.
