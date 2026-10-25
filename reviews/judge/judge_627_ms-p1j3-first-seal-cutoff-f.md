# Judge 627: MS-P1j3, the school runner's first-seal cutoff, text and code (story/ms-p1j3-first-seal-cutoff @ 17ed4bad7; text 81eeefb4a)

**FAIL on 1 should-fix (a test only; text and code are right), round 1 of 2, judge 1 of 2. Lane 1.** Judge F, own
session (session_01A8XfbTUVgeeEpqatHaWbtP); I did not read judge E. Text and code were judged together: the code had
landed before I started, as the orchestrator allowed. Labels: strong, some, reasoning only.

## Criteria

| # | Criterion | Result | My evidence |
|---|---|---|---|
| 1 | RECORD after 15:25 with no seal: nothing sealed, settled, filled or counted; "stopped: ..." so exit 1 and alerted | MET | `runner.py:98-100` returns before `settle_expired`, `_decide` and `dashcam.seal`; `FIRST_SEAL_TOO_LATE` starts `FLEET_STOPPED` (the CLI exits 1, j2's `school:STOPPED`); plant "refusal removed" caught (5) |
| 2 | 15:25:00 seals, 15:25:00.000001 refused, IST, a past session refused | MET | `started <= last`, `last` on the session's date in IST (`runner.py:108-114`); plants `<`, the run's own date, and the clock's zone all caught |
| 2b | the start decides | MET | `started` is read before `plan_slot` (`runner.py:89`); the builder's plant is caught |
| 3 | already sealed reruns; REPLAY exempt; closed day unchanged; **a REH1 rehearsal seals by 15:25 replayed time** | PARTLY | sealed: the check comes after the rerun branch (test); REPLAY: `mode is not RunMode.RECORD` (plant caught, 27 tests); simulator practice is REPLAY (`practice/runner.py:48`); closed day: the check comes after `plan_slot`. **Rehearsal: right by reading, but untested** (finding 1) |
| 4 | one value | MET | `SLOT_LAST_START` (`school/constants.py`); `SCHOOL_STARTS_BY = SLOT_LAST_START` (`daily/wiring.py`); plants (15:30 at the source, a separate daily value) caught |
| gates | | MET | trial merge with main 7dd0e1672 (clean): **16,556 passed, 1 skipped, 14 xfailed** (token kept); ruff, format (2,631 files), `check_imports`, `check_records` (9,263 files) clean |
| QR1-6 | text, gap list, self-review, plants, cases, sample | MET, rule 3 thin | the gap list and runbook line are present; the Claims table names a plant per criterion; the real output sample is given. No self-review section is listed for j3: minor 1 |

## Findings

1. **Should fix: criterion 3's rehearsal clause has no test.** By reading it holds: `IstClock.now()` returns
   `now_ist()` (`school/wiring.py:41-43`), and `now_ist` reads REH1's installed replay clock (`models.py:18-29`). But
   my plant making `IstClock` read the wall clock (`datetime.now(IST)`) passes all 4,072 tests in `tests/school`,
   `tests/daily/test_starts_by.py`, `tests/e2e/test_school_step.py` and `tests/rehearsal`. That is exactly the
   regression that would refuse every rehearsal of a past day once the school is on. Fix: one test that installs a
   replay clock (REH1's `install_clock`, or the mode) at a past session's 15:20 IST and shows the wired clock gives that
   time and the fleet seals; at 15:26 replayed time it refuses. The plant must then fail.

## Minor

1. Quality rule 3: add one line on the self-review (an independent review agent on the diff, its findings and the
   dispositions), as j2's Claims did.
2. The few-seconds boundary (a daily step started at 15:24:59 whose child reads its clock after 15:25:00) fails
   closed: both refuse and both alert, as the Claims state. Accepted.

## Plants

8 planted on 17ed4bad7, one at a time, each restored: **7 caught, 1 survived** (finding 1). Caught: refusal removed;
`<=` as `<`; REPLAY not exempt; the run's own date instead of the session's; compared in the clock's zone; last start
15:30 at the source; the daily value not shared.

## Addendum 1

**Round 2 of 2 at story/ms-p1j3-first-seal-cutoff @ aa94ad726 (code aeecdeebe; later commits Markdown only), judge F,
judge 1 of 2: PASS. Lane 1.** Own session; I did not read judge E. Round 2 changes only
`tests/school/fleet/test_first_seal_cutoff.py` and the story (`git diff 17ed4bad7 aeecdeebe -- fno/` is empty).

| Item | Answer | My check | Result |
|---|---|---|---|
| SF1: the rehearsal clause untested | a test on REH1's own `ReplayClock`, installed with `models.install_clock`: wired `IstClock` at the past session's 15:20 seals, at 15:26 replayed refuses with nothing written | my round-1 survivor (`IstClock` on the wall clock) now **fails** (1 of 33) | **Accepted** |
| Minor 1: self-review | an independent review on the diff; 6 findings, 4 accepted with tests, 1 rejected with its reason, 1 left out of scope | read; the two new should-fix tests plant-checked by me: the cutoff moved after `settle_expired` **fails**, and the clock read after `plan_slot` **fails** | **Accepted** |
| The new "start decides" test | the snapshot source moves the clock past 15:25 while the captures are read | my plant (the clock read after `plan_slot`) fails it, so the test now carries its claim (round 1's version did not) | **Accepted** |
| `SLOT_LAST_START` stays 15:25 with the measured 6 min 13 s | the orchestrator's ruling; gap list, watch rule (fills after 15:29, or a start after 15:24 on 2 of the first 5 sessions) and timing runbook | see below | **Accepted** |

**The measured run length [some evidence, one cold-cache sample].** Fills land about 5 min 50 s after the start, so a
start after about 15:24 risks fills after 15:30. Law 6 then refuses them as `stale_seal`: recorded, never invented, so
the risk fails safe; it costs records, not money. The 21-23 Oct starts would have been about 15:19-15:23 (my judge 608),
inside the margin. The watch rule and the runbook are adequate for the first 5 sessions; the 15:22 option stays open.

Gates on a trial merge with main 1145872d9 (clean): **16,575 passed, 1 skipped, 14 xfailed** (token kept); ruff, format
(2,633 files), `check_imports`, `check_records` (9,286 files) clean.

Plants, both rounds: 11 planted, **11 caught** (round 1's 7, round 1's survivor, and round 2's two plus the
start-decides re-plant). The school's switch commit may go ahead once judge E's verdict also passes.
