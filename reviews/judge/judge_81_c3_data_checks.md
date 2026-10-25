# Judge 81: story C3, data checks before every decision (branch, before merge)

Date: 14 Oct 2026 (UTC). Branch `story/c3-data-checks` at 566e209 (from main 8c5bd5f). Claims:
`reviews/claude/response_82_c3-data-checks.md`. Story: `docs/stories/C-code-roles.md` C3.

## Verdict: FAIL, two must-fixes in the spot check (both small, both would bite on the first real day)

The checks, the gate and the entry and exit wiring are well built, and every plant I made is caught. But the spot
check:
- treats two different spot values in the pack as a failure, which a real A4 snapshot will almost always have;
- marks its failure as "prices unverified", which turns every due exit into a pending exit on any day that moves more
  than 2%.

Together they would stop entries every day and exits on exactly the days exits matter.

## Gates (my runs, `python -B`, caches cleared)

- Full suite: 2,498 passed. Ruff, format (553 files) and imports: clean.
- `git merge-tree` with `main`: clean.

## The story's own check: a deliberately stale snapshot

`test_the_committed_stale_snapshot_is_refused_by_the_real_checks` passes. It runs the real checks on
`tests/fixtures/c3_stale/`, a capture stamped 13:31:02-13:31:40 IST, outside the 14:55-15:10 window. It is refused as
stale.

**Information:** that fixture is synthetic. It is stamped 14 Oct 13:31 IST, which was still in the future when it was
committed. That is fine for a planted stale snapshot, but the claims should not call it a real capture.

## My plants (`tests/checks` and `tests/desk`, 83 tests): all 9 caught

| Plant | Result |
|---|---|
| The window check off | 6 failed |
| The capture's end time not checked | 1 failed |
| The hash check off | 1 failed |
| The leg check off | 8 failed |
| The previous NSE file check off | 2 failed |
| A crossed book allowed | 2 failed |
| Entries ignoring the report | 8 failed |
| No alert | 4 failed |
| The spot limit at 3% | 2 failed |

## Must-fix

1. **One spot, not one per chain.**
   - `SpotNearPreviousClose` fails when the pack's option items carry more than one spot value.
   - The A4 recorder takes `MONTHLY_EXPIRIES = 2` chains, each by its own provider call (`provider.chain(...)`).
   - Each row's `spot` is its chain's spot (`fno/quotes/recorder.py`). For Groww that is the `underlying_ltp` of that
     call (`fno/providers/groww.py`).
   - Two calls seconds apart on a live index almost always differ by a few points. So on a real day the pack holds
     two spot values, and the check refuses every new trade. The builder's test asserts exactly that ("two values
     fails").
   - The golden fixture hid this: it has one spot for every row.
   - **Evidence:** strong by code; the first real capture (the NSE recorder at 14:20 IST today) will confirm it.
   - **Fix:**
     - compare each distinct spot with the previous close (all must be within the limit); or use the snapshot's own
       `meta.spot`;
     - refuse only spots that disagree with each other by more than a small stated tolerance (for example 0.2%);
     - add a test with two realistic spots a few points apart.
2. **A big real move must not block exits.**
   - The spot check has `prices_unverified = True`. On a day NIFTY moves more than 2% (a crash or budget day), the
     snapshot's prices are declared unusable, and every due exit becomes a pending exit.
   - That holds even when the snapshot is in its window and its hash matches the pack, which proves it is the day's
     real data. Design 9: missing or stale data stops new trades, and **risk-reducing exits still run**.
   - **Fix:** make the spot move a new-trades-only check (`prices_unverified = False`). Staleness and tampering are
     already caught by the window and hash checks. One test: a 3% move with a good snapshot refuses the entry, and a
     due exit fills at valid quotes.

## The builder's open points: rulings

1. **No shock flag source, so any move beyond 2% stops new trades: agreed.** It is strict for entries only, once
   must-fix 2 lets exits run. A flag file is the owner's choice later; it is one class and one wiring line, as built.
2. **The hash match for E3's 15:15 capture: a real design gap for E3, and it needs more than a note.**
   - The common pack is built at the 15:00 cutoff, refuses items after it, and is written once. So it can never
     record a 15:15 execution capture, and `SnapshotMatchesPack` would refuse every E3 execution.
   - E3 needs its own hashed, committed execution record: the capture's ID, its times and its quote file SHA-256,
     written before any fill. The check then compares against that record.
   - Until E3, `PackSnapshotSchedule` (the pack's own A4 snapshot) is consistent.
3. **The strict window: agreed.** A capture that starts inside the window but finishes after its end is refused, and
   there is no trade that day. Point in time beats one more trade.
4. **An unreadable snapshot gives no pending-exit row per open trade: accepted, with a condition.** A desk event needs
   a snapshot ID, so one gate alert is the record. The alert must name every open trade whose exit is due that day,
   so the owner sees what is waiting (should fix; one test).

## The A4 rule moved into `ExecutionQuote.a4_problem`: E4's behaviour

- Before, a quote passed when the recorder's `valid` flag was true and the touch had a price and size. Now it also
  needs bid > 0, ask > 0, bid ≤ ask and both sizes above 0.
- The recorder already sets `valid` only under A4's rule, so for real snapshots nothing changes. The difference is
  defence against a `valid` flag on a crossed or one-sided book (test).
- All 32 desk tests pass, and E4's plants are untouched. **No regression.**

## Project rules

- New package `fno/checks/` behind the `DataCheck`, `ExecutionSchedule` and `ShockFlags` interfaces.
- Its composition root `fno/checks/wiring.py` is listed in CLAUDE.md.

## Addendum 1 (round 2, branch 0cc22a2): PASS, with one check to make on the first real capture

**Must-fix 1: met.**
- Every spot in the pack is compared with the previous close, and they must all be within the 2% limit.
- The spots must agree with each other within `SPOT_AGREEMENT = 0.2%` (about 50 points). A larger gap is refused by
  name: it would mean a chain carried a wrong underlying, for example a future's price with its basis.
- **0.2% is reasoning only;** no real A4 capture is committed yet.
- If the real gap is larger, the check **refuses entries and alerts**. That is the safe direction, so it does not
  block the merge.
- **Follow-up I will make:** when today's first real capture is committed (the NSE recorder from 14:20 IST, the Groww
  fallback around 15:13 IST), I measure the gap between its two chains' spots and report it.

**Must-fix 2: met.** The spot check is new-trades-only (`prices_unverified = False`). The test with a +3% move shows
the entry refused and the due exit filled at valid quotes.

**Ruling 4, the alert names due exits: met.** With no readable snapshot, the gate's alert lists every open trade whose
exit is due without a price: an exit already ordered, or the time rule (`ExitDesk.due_exits`).

**Ruling 2, root fix: met.**
- `SnapshotMatchesPack` is replaced by `SnapshotMatchesRecord`. It compares the snapshot read with a committed
  `CaptureRecord` (ID, quote-file SHA-256, sidecar SHA-256) that the `ExecutionSchedule` supplies.
- Until E3, the record is the common pack's provenance: the pack is written once and committed. E3 supplies its own
  execution record without changing C3.
- The sidecar hash now covers the capture times too.

**My plants (`python -B`, caches cleared; `tests/checks` and `tests/desk`, 89 tests): all 14 caught.** That is 7 new
ones plus 7 from round 1, whose earlier strings still apply. The new ones:

| Plant | Result |
|---|---|
| The spot check marking prices unverified again | 3 failed |
| The agreement check off | 1 failed |
| Only the first spot compared | 1 failed |
| The agreement at 2% | 1 failed |
| The sidecar hash not compared | 1 failed |
| A missing record passing | 1 failed |
| The due exits not named | 1 failed |

**Gates:**
- full suite: 2,504 passed;
- ruff and imports: clean;
- `git merge-tree` with current `main`: clean.

**Verdict: PASS for 0cc22a2.**

## Addendum 2 (merge check, e3506ec)

**MET.** e3506ec merges 0cc22a2 (the passed tip) onto `main` with D3 f314254 underneath. It equals my recomputed
merge, with no difference. No other code is on `main` since.
- My full suite at e3506ec: 2,562 passed.
- CI `checks` is green on e3506ec (run 38516503171).

The spot-gap measurement on the first real capture is still owed by me (addendum 1).

## Addendum 3 (the promised real-capture measurement for `SPOT_AGREEMENT` 0.2%)

Source: today's first real 3 pm capture, `nifty_20261014_145500` (commit 5c22bcc; 184 contracts, complete,
`in_window`). The routine's first push failed with a 403, and the data reached `main` at 09:35 UTC.

| Chain | Quotes received | Spot |
|---|---|---|
| 27 Oct 2026 | 14:55:25 to 14:56:36 IST | 22,620.00 |
| 23 Nov 2026 | 14:56:37 to 14:57:45 IST | 22,621.15 |

- **Gap: 1.15 points = 0.0051%.** That is about 40 times inside the 0.2% limit. So C3's spot check would not have
  refused today's entries.
- **Evidence: some evidence (one day).** The two chains are fetched about 70 seconds apart. A fast market, such as an
  event day or a 1% move in a minute, can open a larger gap. Keep measuring over the first weeks.
- **Other checks on the same capture:**
  - all 184 quotes are A4-valid, with prices on 0.05 ticks and sizes in multiples of the 65 lot;
  - the meta's `spot` is the first chain's;
  - VIX is 14.74 (NSE, 14:54).
- **The futures are consistent with the options** (put-call parity on mid prices, my own script, rate 6.5% assumed):

  | Expiry | Parity forward (median of the 5 strikes nearest at-the-money) | Future's last price | Difference |
  |---|---|---|---|
  | 27 Oct | 22,644.63 | 22,650.00 | 5.37 points (0.024%) |
  | 23 Nov | 22,759.49 | 22,760.00 | 0.51 points |

  All three futures last prices are round tens (22,650, 22,760 and 22,910). The code does not round them
  (`parse_index_futures` takes NSE's `lastPrice` as given), and parity agrees with them closely, so I take them as real
  prints. The raw NSE futures response is not archived, so this cannot be re-checked byte by byte later. Storing it
  is a small A4 should-fix, reasoning only.

**Ruling unchanged:** `SPOT_AGREEMENT` 0.2% stands. Today's data supports it.
