# Judge 630: A14c part 2, the daily read-only Groww margin check, code round 1 (judge 2 of 2)

Branch `story/a14c-part2-broker-check` at `5f7dc5d7c`; claims: response 291, "Round 2". **FAIL**, lane 1 (money and
risk, Groww): 1 blocking, 2 should-fix, 2 minor. Trial merge with main `378dbe30f` (register conflict only).

## Criteria

| Criterion (A14c part 2 text, criterion 10) | Verdict | Evidence |
|---|---|---|
| From 09:30 on a session day; outside: "outside market hours", exit 0 | MET | `broker_check.py:66`; plant 09:00 caught |
| No request at or after 14:50; the rest `error` "deadline", exit 1 | MET | `_ask` :136 checks before every request; plants `>` and the index's deadline branch caught |
| One request every 2 s, the NIFTY quote first; no retry storm | MET | `_ask` :134; no retry anywhere; a sign-in failure stops at the first request (quote), `providers/groww.py:143` caches the client; pacing plants (check, wiring) caught |
| Basket rebuilt from the row's own SPAN file: source and SHA-256, three figures to the paisa, legs and sides | MET | `broker_basket.py:240-254`; plants source, figures, sides, 2 lots caught |
| SPAN vs `max(0, scan - NOV)` within Rs 1; exposure at this caller's quote within 0.1% | PARTLY | rule as written (`broker_compare.py:295-301`, 6 plants caught); the level is wrong in a moving market (finding 2) |
| Mismatch: own line, exit 0, never moves the factor | MET | `_finish` :148; no reference to the factor in `broker_*.py`; plants exit 1 and no alert caught |
| Errors: exit 1, reason last, no own alert, class name only | MET | `_one` :121, `_named` :171; text-leak and errors-exit-0 plants caught |
| Read-only allow-list; order calls refused | MET | SDK 1.5 signatures read: both calls take `timeout`; its 6 order names all refused; widened-list plant caught |
| O9 write-once record and receipt; idempotent; first run of the day | MET | `broker_record.py:164-190`; plants error-as-done, done ignored, shortcut off caught |
| O1 step: `DAILY_RUN_STEPS[2]`, own receipts only, behind `live_from` (null) | MET | `fno/daily/wiring.py:144-151`, `config.yaml:210`; receipts-all plant caught |
| Gates: full suite | NOT MET | finding 1 |

## Findings

1. **Blocking: the suite fails without the Groww SDK, which is CI's environment.** `test_before_09_30_the_check_needs_no_drive_or_groww_settings`
   fails on the branch and on the trial merge: `RuntimeError: Install the Groww SDK first` (`broker_wiring.py:30` builds
   `GrowwProvider`, whose `__init__` imports `growwapi`, `providers/groww.py:132`). `checks.yml:35` installs only
   `requirements.txt`; `growwapi` is in `requirements-groww.txt`. Passes after `routine_setup.sh --groww`. So the claim
   "needs no Groww settings" is false for the SDK too. Fix: build the provider on first use (as Drive already is), then the test passes without the SDK.
2. **Should-fix: exposure is compared at a level read once, but Groww charges each basket at the live level when it is asked.**
   The quote is the run's first request; baskets follow 2-3 s apart (60.7 s for 15 on 25 Oct; about 2 min for 40).
   Exposure is linear in the level, so a move above 0.1% in that time flags a correct row. Reproduced with the
   branch's fakes: NIFTY +0.12% after the quote gives 6 of 6 `mismatch`, one "review the stress factor" alert, exit 0,
   and those baskets are `done` (never asked again that day). +0.10% passes. The 21 Oct evidence was after the close,
   when the level does not move, so it cannot show this. How often a 15-basket run sees it is reasoning only: about 1%
   of normal days, more on volatile ones and on 40-basket runs. Fix (text and code): read the level before and after
   each basket, or once more at the end, and call a basket a mismatch only when it is outside tolerance at every level in that range. Test it with a level moving under the check.
3. **Should-fix: the basket's lot is read twice, and the check's copy is untested (plant survived).** The row builder
   uses `cfg["lot_sizes"]["NIFTY"]` (`nse_margins/wiring.py:46`) and the check reads it again (`broker_wiring.py:35`). Plant: the
   check's lot set to BANKNIFTY's: 573 tests passed. Neither copy is dated: A20a's archived `fo_mktlots.csv` (read by
   `fno/school/roads/lots.py`) gives the lot by expiry month. A config left behind an NSE lot revision then sends the
   wrong quantity, and the row's figures still prove themselves. Fix: one source (the row builder's calculator), a
   wiring test, and an `error` when A20a's dated lot for the basket's expiry differs.
4. **Minor: stale story text.** `A-data-foundation.md:2040` says the step runs "about 14:35 IST, after the weather and the v4
   forecasts". The code runs it third (`constants_operations.py:62`), right after the 14:05 start and before weather;
   at 14:35 it would overlap the 14:30-14:40 v4 capture. "About 35 seconds" was measured at 44.7 s and 60.7 s.
5. **Minor (rule 3):** round 2's change (the first-run shortcut, the REH1j test edits) has no self-review entry.

## Plants

27 planted one at a time on `5f7dc5d7c`, each restored with `git checkout`. 25 caught. Survivors: finding 3's lot, and
`level <= 0` loosened to `is None`, which is equivalent except for a negative level (`quote_reading` already maps 0 to
None).

## Notes

- Trial merge without the SDK: 16,624 passed, 1 failed (finding 1), 1 skipped, 14 xfailed. With the SDK: 244 of 244 in
  `tests/nse_margins` and `tests/daily/test_steps.py`. ruff, format, imports and the record scan are clean. Slack token kept.
- Open item, not a finding: the market-hours sample owed Mon 26 Oct about 10:00 IST. It is also the first real test of finding 2.

## Addendum 1: round 2 at `c2ed049e6` (the last round)

**PASS**, lane 1, judge 2 of 2: every round-1 finding fixed, 2 minor left (test gaps; the code is right).

| Round-1 finding | Verdict | Evidence |
|---|---|---|
| 1. Suite red without the Groww SDK | FIXED | `broker_wiring.py` builds `GrowwProvider` and the lot library through `functools.cache` on first use. Trial merge with main `c6b1bdf22`, `growwapi` shadowed to fail on import: 16,682 passed, 13 xfailed, 1 failed (`test_feed_tls` real-SDK test; my shadow raises ImportError, which `importorskip` does not skip; fails the same on plain main, passes with the SDK). Plants "eager Groww" and "eager lots" caught |
| 2. Exposure at one level | FIXED | `broker_compare.py` `Levels`: NIFTY read before the first basket and after the last (both paced and stopped at 14:50); expected = nearest at any level between; a rate step inside the range, or no second reading with exposure outside 0.1%, is `error`, never `mismatch`. My own run, NIFTY +0.3% during the run: charged at the first reading, the midpoint or the second all `ok`; 0.2% beyond either end `mismatch`; the row carries `nifty_before` and `nifty_after` |
| 3. Lot read twice, undated | FIXED | one source, `BasketBuilder.lot_size` (the row builder's calculator); `broker_lot.py` reads NSE's dated lot with the school's `ArchivedLots` for the basket's expiry month, once per run; differs, missing or unreadable is `error` and nothing is sent. A20a's manifest holds the file for 21-23 Oct (fo-masters job 07:45, retry 11:15 IST) |
| 4. Stale text | FIXED | story: third step after the 14:05 start; 44.7 s and 60.7 s measured |
| 5. No round-2 self-review | FIXED | response 291 "Self-review of rounds 2 and 3" |
| Judge 634's retry promise (read only) | consistent | lines end "lost unless ... run by hand before 14:50", "lost" alone after the stop; test through O1's `outcome()` and `RunLog` |

**Minor 1 (rule 4): a charge at the first reading is untested.** Plant `nearest = last`: 273 of 273 passed. Every move
test charges at the second reading. Expected: one test with a charge at the first reading (or between) under a moving
index.
**Minor 2: the record's two new columns are not asserted.** Plant: `as_row` writing both empty: 273 passed. Expected:
assert `nifty_before`/`nifty_after` in the record test.

**Plants:** 18 on `c2ed049e6`, 16 caught, the 2 survivors above.

**Notes.**
- With only two readings, Groww can still charge a basket at a level outside both, when NIFTY moves and comes back
  within the minute. A false mismatch stays possible on such a day, less often than before. Watch it in the 26 Oct
  sample (the per-basket bracket is the tighter option).
- A late A20a archive (21 Oct: 19:46 IST) makes that day's check `error` and loses the broker figure, with O1's alert.
  That cost is chosen on purpose (fail closed), and it is the owner's to weigh.
- Response 291's lot paragraph still says "a same-day rerun retries"; the story and the code say by hand only.
- Gates on the trial merge: ruff, format, `check_imports` and `check_records` clean.

## Addendum 2: the follow-up `c2ed049e6..df106dc73` (judge 2 of 2; owner's yes to merge, 25 Oct)

**PASS**, lane 1, with 1 minor. The builder's commits: 3dfaa02f4, 99d0a211f, 5748ff107, 371f308ed (reverted by
9e2c535e2), b195ad9a4 and df106dc73. The rest of the range is main's own commits (GW1a, judged on their own).

| Item | Verdict | Evidence |
|---|---|---|
| **The blocking fix:** GW1a's inner list refused `get_order_margin_details` | FIXED | `broker_wiring.py` builds through `get_provider("groww", cfg, BROKER_CHECK_CALLS)`; `GrowwProvider` passes the list to its own `ReadOnlyGroww` (`groww.py`, b195ad9a4), which still applies both rules; the default is unchanged. The real-chain test passes a fake SDK through GW1a's sign-in and 429 guards: one margin call made, order calls refused, the default list still refusing the margin call. Plants caught: `get_provider` dropping the list, the provider ignoring it, the wiring passing none, the default list widened |
| My 630.1 minors (charged at the first reading; the NIFTY columns) | FIXED | 3dfaa02f4 tests |
| By-hand line (owner's rows 348-349) | MET | "rerun this same ... by hand before 14:50 and its receipts (`receipts/data/margins/broker_checks/`) committed", and "lost" alone at or after 14:50 by the clock or the deadline. Plants caught: the clock check removed, the receipts not named. Dropping the deadline-reason condition survives but is equivalent: a deadline error exists only once the clock has passed 14:50. Row 349 allows the failed command itself to be rerun, in market hours too |
| Lazy Groww | MET | `GrowwBrokerMargins` takes a callable; plant "eager provider" caught |
| Lot timing claims | MET (2 of 3 checked) | A20a's manifest commits at 13:03 (22 Oct) and 13:00 IST (23 Oct); 24 Oct, a Saturday, has no manifest row to check |
| O1 paragraph → link (one owning document) | MET | `O1-daily-run.md` keeps one line and a link to A-data-foundation's A14c section |

**Minor (document rule, owner's intent):** the story still says "Adding a retry is the owner's call, not this story's",
but the owner decided it on 25 Oct (DESK_DECISIONS row 350: automatic retry with exponential backoff, at most 5, then
escalate; to be built as O14). Expected: point to row 350 and O14.

**Gates:** trial merge with main `a351de626` (clean), with the SDK: 18,063 passed, 13 xfailed, 0 failed; ruff, format,
`check_imports`, `check_records` clean. My CI-like run without the SDK (a `ModuleNotFoundError` shadow) of
`tests/nse_margins`, `tests/intraday` and the provider tests: 554 passed, 1 skipped. **Plants:** 8, of which 7 were
caught; the survivor is equivalent. **Note:** A-data-foundation.md is 2,855 lines and O1-daily-run.md 687, both over
500; this is DOC1's work, not this change's.
**Narrow check of the merge resolution (orchestrator's request): `ff978df29` PASS; addendum 2's minor closed.** It
merges main (GW1 parts 5-6) into `df106dc73`.
- `groww.py`: `GrowwProvider(config, on_sign_in_failure, quiet, allowed)`. `RateGuardedGroww(..., self._quiet)` is
  kept, and the caller's list is added only at `ReadOnlyGroww`.
- `providers/__init__.py`: `_groww_provider` passes `alert_sign_in_failure`, `MarkQuietWindows()` and `allowed`.
- The default `READ_CALLS` is unchanged and holds no margin call.
- Plants caught: quiet windows dropped from `get_provider`, and the rate guard bypassed.
- The retry sentence now points to DESK_DECISIONS (25 Oct, row 350) and to `O14-retry-policy.md`, which exists.
- Trial merge with main `e3f1d0572` (clean): 18,160 passed, 13 xfailed, 0 failed; ruff, format, `check_imports` and
  `check_records` clean.
