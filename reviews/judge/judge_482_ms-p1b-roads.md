# Judge 482: MS-P1b, roads and the quality gate

**Scope:** story/ms-p1-roads at 183783bd (code 2ed9bbbf; builder session_01F1RVMF8MNngi97JVNs99L5), diff
756e6545..183783bd only. Story MS-market-school.md part b, its Claims, and the orchestrator's 4 accepted decisions.
Lane 1. Round 1 of 2. Judge H (session_01KNkZVoWvXMkoihKrrXk5Xa).

**Verdict: FAIL.** 2 should-fix, 2 minor.

## Criteria
| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | 5 roads on a trading day, none on a holiday | MET | `catalogue.py:27`; plant (weekday instead of A7) caught |
| 2 | Each closure reason from a planted fixture | PARTLY | All 7 reasons are planted. Several checks inside them are untested (finding 2) |
| 3 | Exactly one reason per closed road | MET | all-pairs test; the gate keeps the catalogue's reason |
| 4 | Gate at 10/10 vs 9/10, and at 95.0% vs 95.1% | MET | `capture_gate.py:47-52`; plants on the session count and the snapshot condition caught |
| 5 | Conformance | MET | a's checks pass on both classes |
| 6 | Read-only run on October days | MET | My run of the command `--through 2026-10-22` gives byte-identical lines. `git status` is clean. A request log shows only `oauth2.googleapis.com` (3) and `www.googleapis.com` (113): no NSE or Groww host |
| - | Gates | MET | pytest -n auto: 10,449 passed, 16 xfailed. ruff check/format, check_imports and check_records are clean. Largest file is 184 lines |

**The orchestrator's decisions, checked:**
1. **Ranges, not mids: ACCEPTED.** In the band, ranges flag 0 of 716 legs on the 9 road-days (I reproduced both
   figures). The fill is at the touch, so the bid-ask bounds are the ones a fill can break. The "8-72 legs a day" on
   mids is not reproduced exactly (minor a).
2. **Any impossible band leg closes the road-day: ACCEPTED as conservative.** It never fired on real data under
   ranges. MS-P1h must freeze it with the band (judge 480 SF3).
3. **Unreadable listing gives `expiry_mismatch`, a Drive outage raises: ACCEPTED.** Tests and plants confirm it
   (catching `Exception` was caught as a plant). Reports will count "unconfirmed" as "mismatch" (minor b).
4. **Lots only from the session's own A20a copy: ACCEPTED.** `lots.py:27` reads only that session's copy. The
   manifest `fo-lot-sizes.csv` starts on 2026-10-21, which matches the `lot_mismatch` counts. The lot file is archived
   at 07:45 IST, so the 15:00 slot has it.

Also met: a failing road never closes another (test, `catalogue.py:29`). The capture-gate denominator is the band's
recorded legs of passed sessions, fixed by `DEFAULT_BAND_STEPS`, but see finding 1.

## Findings
1. **Should-fix: one strike step, taken from the nearest expiry, is applied to every expiry.**
   - Real data, 22 Oct: FINNIFTY's 27 Oct monthly is recorded at 50-point strikes (49 strikes). Its 23 Nov monthly
     is recorded at 100-point strikes (25 strikes).
   - `Capture.strike_step` returns 50, and `band_keys` reaches 10 × 50 points on both expiries. So the Nov band holds
     11 strikes, not 21: FINNIFTY has 64 legs a day against 84 on every other road. The denominator now depends on a
     listing accident.
   - `RoadDay.strike_step = 50` is also wrong for that expiry: a driver stepping "1 step out" lands on an unlisted
     strike.
   - Expected: a step per expiry, a band of N steps of each expiry's own step, and a fixture with two steps. If a's
     single `RoadDay.strike_step` must become per expiry, that is a contract question for the orchestrator.
2. **Should-fix: the claim "25 mutations, 25 caught, 0 survived" is not reproduced.** I planted 33 and 9 survived
   (one more, a locale-free month label, is equivalent here):
   - `row["valid"] == "true"` replaced by `True`: an invalid A4 leg counts as passed.
   - the sidecar's `failures` check removed;
   - the `spot` finite and positive check removed;
   - the `finished < started` check removed;
   - both date checks in `window_problem` removed (a capture stamped on another day passes);
   - the IST conversion removed (real sidecars are +05:30, so this one is low risk);
   - `strike_step` taking the least common gap (the test chain has one gap only).
   - Expected: a failing test for each.

**Minor:**
- (a) The Claims' "8-72 legs a day" on mids: over whole chains I get 8-61 legs (neighbours) and 9-87 (all pairs) per
  road-day. In the band, mids flag only MIDCPNIFTY: 15 legs on 21 Oct and 6 on 22 Oct. Correct the figure; the
  decision stands.
- (b) Name the unreadable-listing case in the line or a detail, so reports can tell it apart from a true mismatch.

## Plants
33 planted; 23 caught, 9 survived (finding 2), 1 equivalent.

## Notes
- The NSE archive files (lots, F&O listing) are read through `RawFileLibrary`, like `intraday`, not against their
  manifest SHA-256. This is existing practice and not a finding here.
- A store outage on one dataset raises for the whole day (all 5 roads). That is consistent with "an outage is never a
  closure".
- This part closes roads, so it decides trades. Under JUDGE.md "Two judges for money pieces" the orchestrator decides
  whether a second judge is needed.

## Addendum 1

**Round 2 of 2:** story/ms-p1-roads at fdbea6c7, b's files diff 183783bd..fdbea6c7 (it answers judges 482 and 483
together; Judge I judges separately). **Verdict: PASS**, lane 1.

**Gates (my run):** pytest -n auto: 10,539 passed, 16 xfailed. ruff check/format, check_imports and check_records
are clean. Largest file is 183 lines.

**Real data (my run of `python -m fno.school.quality.command --through 2026-10-22`):**
- The output equals the Claims block byte for byte.
- FINNIFTY now has 168 scheduled legs (21 strikes on each expiry in its own step), 95 passed (56.55%).
- `git status` is clean. A request log shows only `oauth2.googleapis.com` (3) and `www.googleapis.com` (115): no NSE
  or Groww host.

**Round-1 findings:**
1. **One strike step: ACCEPTED for b's part.**
   - `quality/strikes.strike_steps` gives each expiry its own step. `band_keys` reaches N steps of each expiry's own
     step from that expiry's money.
   - Plants caught: the least common gap, and the smallest step across expiries.
   - The scheduled legs now come from NSE's listing (`NseListedContracts`), so a dropped strike counts as observed and
     not passed. Plant (denominator taken from the capture again) caught.
   - `RoadDay.strike_step` is still the nearest expiry's. Per-expiry steps on `RoadDay` wait for a2, and b fills them
     as the orchestrator's known follow-up. That isn't this verdict's.
2. **The surviving plants: ACCEPTED.** All 9 of my round-1 survivors are caught now:
   - both date checks, the IST conversion, the sidecar failures, the spot check, the time order;
   - `valid == "true"`, the step choice.
   - Also caught: the new Drive-outage pass-through (`requests.RequestException` before the parse catch) and the
     recorder's 5% band on the listing.
- **Minors (a) and (b): ACCEPTED.**
  - (a): the mids figure is corrected in the Claims.
  - (b): an unreadable listing is now `ListingUnavailable` (`ExpiryUnavailable` is a subclass). It still closes as
    `expiry_mismatch`, and the reason text says why.

**Plants:** 12 this round, 12 caught.
