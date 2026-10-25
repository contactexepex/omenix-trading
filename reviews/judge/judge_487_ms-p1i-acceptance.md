# Judge 487: MS-P1i, the acceptance harness

**Scope:** story/ms-p1-acceptance at 67b50a0e (builder session_01F1RVMF8MNngi97JVNs99L5), diff 8c7ba1d9..67b50a0e.
Story MS-market-school.md part i and "MS-P1i Claims"; response 327's P1 gate. Lane 1. Round 1 of 2. Judge K
(session_019ZApRwkUiNMKDsf1k4W44z).

**Verdict: FAIL.** 1 blocking, 1 should-fix, 2 minor. Three of the six P1-gate faults are planted as the verdict, not
as bad data, so no fleet can be shown to catch them. The harness's own checks are largely unproven.

## Criteria
| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Each planter gives its exact reason code | PARTLY | missing quote, stale seal, refused entry and replay conflict are real plants; finding 1 for the other three |
| 2 | Comparator fails on one changed byte | MET | `differences` -> `[]` plant caught; counts file dropped from `files_of` caught |
| 3 | Planted refusal survives two runs, both sections, every denominator | MET on the fakes | fleet dropping `refused` records, sections or denominator filtering `refused`, counts' `executed` forced: all caught |
| - | Fixtures inside each road's window | MET | 15:02-15:04 lies inside A4's 14:55-15:10 (`fno/quotes/recorder.py:45`) and A4c/A4f's 15:01-15:13 (`fno/quotes/indices.py:23`) |
| - | Zero unsealed, over-cap, invented, duplicate fills | PARTLY | each has a planted-ledger test; finding 2 |
| - | j's `real_rig` contract is clear | NOT MET | finding 1: j cannot feed the closure planters to real code |
| - | Gates | MET | see Notes |

## Findings
1. **Blocking: expiry mismatch, lot mismatch and impossible price are planted as the road's closed status, not as
   bad capture data.**
   - `closed_road` (`faults.py:50-63`) calls `Scenario.with_road_closed` (`scenario.py:41`). That sets
     `RoadStatus(reason)` and leaves every snapshot unchanged. My run: for all three, `plant(clean).snapshots ==
     clean.snapshots` is True.
   - `FakeSnapshotSource` then just raises the status it was handed, so the test proves the fake copies a verdict.
   - Story j cannot use these planters either. A real catalogue (part b) computes the status from captures, and
     there is nothing wrong in the captures to detect. Limit 1 hands j the job of writing its own planters, which is
     part i's deliverable ("planters for the 6 faults"). A real fleet that never detected a lot mismatch would pass
     this harness.
   - Expected: each planter corrupts the data a real detector reads, and the expected code is unchanged:
     - expiry mismatch: the snapshot's expiries differ from the road day's;
     - lot mismatch: the dated lot differs from the capture's;
     - impossible price: a quote breaking b's bounds.
   - The `Scenario` carries whatever j's rig needs to feed them (e.g. capture rows), and `real_rig`'s contract
     says which reader takes them. If b's detector interface isn't fixed yet, name the data each planter changes,
     with the orchestrator's ruling.
2. **Should-fix: 9 of the harness's own checks can be deleted with every test still green** (my plants 4-6, 8, 11-15).
   j trusts these checks:
   - a closure leaking to another road (`harness.py:83`);
   - a position opened for a refused entry (`:87`);
   - stale-seal fills reaching the ledger (`:96`);
   - a rerun that seals or fills again (`:141`);
   - a scheduled decision with no sealed outcome (`:102`);
   - an over-cap trade decision (`:39`);
   - the refused entry's exact reason (`:89`);
   - the fill-path reason (`:92`);
   - a partial fill (`:48`).
   The Claims' "11 of 11 caught" covers other mutations. Expected: for each check, a test that feeds a bad run or
   rig to the check and sees it fail, as the four fill checks already do.

**Minor (fix with the round):**
- (a) `:92` accepts the reason on any fill of the session, not on the planted driver's own fill. Tie it to that
  decision's fill.
- (b) `check_no_invented_fills` covers entries only. Exits and settlements are fills too (`closes=True`); cover them
  or say why not in Claims.

## Plants
23 planted, 14 caught. Survivors: plants 4-6, 8 and 11-15 (finding 2). Caught: price/touch, seal covers, comparator,
counts file, duplicate per slot, replay unchanged, stale seal on time, lot planted with the expiry code, fleet
dropping refused records, fleet filling refused, fleet never refusing, counts `executed`, sections and denominator
filtering refusals.

## Notes
- **Gates (my run, python3 after routine setup):** pytest -n auto 10,310 passed, 16 xfailed; ruff check and format, check_imports, check_records clean; largest file 252 lines (the test module).
- Limits 2 (missing quote by law or at the fill), 3 (counts, sections, denominator from f/g in j) and 4 (replay
  conflict at the dashcam) are acceptable as stated. Limit 1 is not (finding 1).

## Addendum 1: round 2 at 2b9b45c8

**Verdict: PASS.** Lane 1. Scope: i's commit 2b9b45c8 over 647983f5 (b's round-2b code arrives by merge; b's own
judges cover it). **Merge waits for b's PASS and b's merge**, since i now runs on b's real classes.

| Round-1 finding | Result | My evidence |
|---|---|---|
| Blocking: closure planters set a verdict | ACCEPTED | `Scenario` has no road status. Planters shift the capture's expiries and keys, give the later expiry another lot, and quote a vertical outside 0..width. The rig writes captures as the recorder does and runs b's real `CaptureReader`, `RecordedRoadCatalogue` and `RoadQualityGate`. Breaking each detector fails the harness (plants 1-3), and so does each planter turned into a no-op (16-18) |
| Should-fix: 9 unproven checks | ACCEPTED | all 9 deletions from round 1 are now caught by `test_harness_checks.py` (plants 5-13) |
| Minor a: own fill | ACCEPTED | `own_fill` by decision order; plant returning another driver's fill caught (15) |
| Minor b: exits | ACCEPTED | exits checked at the touch, settlements left to d by name; plant restoring entries-only caught (14) |

- **Plants: 18 planted, 17 caught.** The survivor is b's own second expiry check in `RoadQualityGate.check`.
  The catalogue already closes the road first on the same comparison, so deleting it changes nothing here. That
  check is b's defence in depth, not i's code, and not a finding.
- **j's `real_rig` contract is now clear** (Claims round 2). It writes `snapshots` as captures, `listed_expiries` as
  the archived F&O listing and `lots` as the archived `fo_mktlots.csv`, then runs the real fleet with the planters
  unchanged.
- **Note for j's judge:** the fake rig's `ScenarioLots` re-states `ArchivedLots`' one-lot rule. The lot-mismatch
  plant is fully proven only when j's rig reads a written lot file through `ArchivedLots`.
- **Gates (my run, python3 after routine setup):** pytest -n auto 10,595 passed, 16 xfailed. ruff check and format,
  check_imports and check_records are clean. The largest file is `test_acceptance.py` at 302 lines.
