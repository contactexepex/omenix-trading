# Judge 528: MS-P1c adoption of a stored slot file

Judge B (first judge; judge K second), 23 Oct 2026. Story/ms-p1c-adopt at 743eadca, one commit on main e3486339;
lane 1.

**Verdict: FAIL, round 1 of 2, on one should-fix that needs only a test.** The design and the code are sound.

## Claims vs reality

| Claim | Reality |
|---|---|
| The window: Drive put, then receipt push; a stop between leaves a file with no receipt, and a differing rerun is a `ReplayConflict` forever | True from the code: `DriveDashcamStore.seal` calls `data.put`, then `publisher.publish`, and `SchoolFleet.run` caught only `AccountUnreadable` |
| `recover` = `find`, else adoption after `adoptable`'s checks; receipt from the stored bytes; "adopted" commit | True. `data.drive.get` is on the `RawFileStore` interface (None when absent). `data.put` with the same bytes is a no-op on Drive. A same-container rerun keeps the earlier local receipt (`ReceiptFolder.write` returns it) and the publisher pushes the unpushed commit |
| Checks: decodes, canonical, kind's records only, session and slot (outcomes exempt), writer's own | True, each tested in `test_adoption.py` on real git. My plants: session and slot check removed: 2 failed; slot alone dropped: 1 failed; decisions accepting `OutcomeRecord`: 1 failed |
| Loud stop by name, nothing sealed or filled | True: `DASHCAM_STOP` gives "stopped: dashcam stuck ..." as the status, which `cmd_run` turns into exit 1 |
| `_belongs`: a decision's driver and frozen card; an exit, outcome or drift row's driver | The decision half is tested. **The other half is not tested** (SF1) |
| The runner adopts decisions, outcomes and drift; "all finished" stays `find`; readers keep `find` | True in the code. Changing `_sealed_once` to `recover` survives the suite (3465 passed), but I found it behaves the same as now: the next `_seal_once` adopts anyway. Note only |
| Fakes as strict as Drive; `ReplayDashcam.recover` is `find`; `check_dashcam` covers `recover` | True |

## Hunt

- **Seal before fill, after adoption:** fills use the rerun's clock as `at` (`runner.py`), and the adopted seal's
  `pushed_at` is the adoption commit, before `at`. The stopped run cannot have filled, because `seal` returns only after
  the push. A rerun after 15:30 is refused as `stale_seal` by `_sealed_in_time`, as for any late rerun. No look-ahead:
  the adopted decisions are the ones made at the original slot.
- **Settlement exit records** in the decisions file carry the current session (`settlements_of`), so the session check
  does not refuse a day after an expiry. **Drift rows** exist for trades only, with IDs `driver:road:session`, so the
  `split(":")[0]` driver test is sound.
- **Project rules:** the largest file is 226 lines; `adoption.py` sits behind the existing `DashcamStore` port; the story
  text and the register row match the diff.

## SF1 (should-fix, test only): the fleet's ownership check on exit, outcome and drift rows is untested

- **Plant that survives:** in `SchoolFleet._belongs`, make every non-decision record belong (`return True` in place of
  the driver test). `tests/school` still gives 3465 passed.
- **Why it matters:** the Claims list this check, and an outcomes file decides results, so under the standing rule an
  uncaught plant there is a should-fix. `test_adoption.py`'s "not this fleet's" case passes `lambda record: False` to
  the store, so it tests `adoptable`, not the fleet's `_belongs`.
- **Test it must pass:** a stored outcomes file (or drift or exit rows), with no receipt, holding a row of a driver
  outside this fleet stops the rerun as "stopped: dashcam stuck: ... (a record that is not this fleet's ...)", and
  nothing is sealed for that kind. The plant above must fail it.

## Gates (run by me on 743eadca)

14,299 passed, 16 xfailed; ruff, format and check_imports clean. It merges cleanly with current main.

## Addendum 1

**Verdict: PASS** on story/ms-p1c-adopt at fdb57abc: 66cf5c89 (test only), then a merge of main. Round 2 of 2, and it
closes SF1. Against main, the code is unchanged from 743eadca; only `SealNotPushed`'s import moved to
`fno.storage.receipt_publisher`.

- **The new test:** `test_a_stored_row_of_a_driver_outside_the_fleet_stops_the_rerun_and_seals_nothing_of_its_kind`,
  with one case each for an exit, an outcome and a drift row. Each stores an unreceipted file holding a row of driver
  `ZZ9@1` and goes through the fleet's rerun (no lambda passed to the store). It asserts the "dashcam stuck ... not this
  fleet's" stop and that nothing of that kind is sealed.
- **My SF1 plant** (`_belongs` returning True for non-decision rows) now fails all 3 cases (3 failed, 4 passed in
  `test_adopt_rerun.py`).
- **Gates on fdb57abc (run by me):** 14,357 passed, 16 xfailed; ruff, format and check_imports clean. It merges cleanly
  with current main.

## Addendum 2

**Verdict: PASS** on the merge resolution b8f72a3d (parents fdb57abc, 528.1 PASS, and ins-wiring 98d16fcd, 507.14
PASS). This was a quick look, as the orchestrator asked.

- **Compared with git's own merge** of the two parents (`git merge-tree`): the tip differs only where git marked the
  conflicts.
  - `runner.py`: the resolution keeps adopt's `_belongs` and ins-wiring's `_finish -> tuple[SlotFills, tuple[str,
    ...]]`. It drops only the conflict markers and adopt's old signature line.
  - The story doc: the adopt section is re-added after ins-wiring's sections, and both headings are present.
  - No other file differs.
- **On b8f72a3d (run by me):** `tests/school` 3,568 passed; ruff and check_imports clean. It merges cleanly with
  current main.
