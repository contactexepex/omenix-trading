# Judge 441: A4f, NIFTY weekly expiries and open interest in the 3 pm capture, code (story/a4f-nifty-weekly-oi @ 51c74e8a)

Judge F (independent). The story text passed in judge 433. Claims: `reviews/claude/response_302_a4f-nifty-weekly-oi.md`.
The builder sent 4b22d35f; the head is 51c74e8a, whose only change is a rewrap of CLAUDE.md step 3b. Lane 1 (the 3 pm
quote record, Groww calls, O1's parts). Labels: **strong**, **some**, **reasoning only**.

## Verdict: PASS. A4f may merge (pull, full suite on the merged tree, `check_numbers.py`, then push). 3 minors.

## Gates (exact head 51c74e8a)

| Gate | Result |
|---|---|
| pytest `-n auto` (no Slack token, no growwapi) | **8963 passed**, 17 xfailed, 349 s |
| `ruff check`, `ruff format --check` | clean, 1663 files formatted |
| `tools/check_imports.py`, `tools/check_records.py` | clean (1753 files); record scan clean (7349 files) |

## Claims checked

1. **The split moves code without changing it** [strong]. The row builder and CSV writer in `snapshot_rows.py` match
   the removed `recorder.py` code, apart from `open_interest`. The two re-exports (`COLUMNS` for the frozen golden
   tool, `quote_validity` for E8) carry their reasons.
2. **Judge 433's minors** [strong]:
   - today's weekly is refused (`e > day`);
   - the band edges and the 15:12:59, 15:13:00 and 15:13:01 stop edges are tested;
   - a missing leg gives an empty cell, and OI 0 gives "0", with the reader rule in the docstring.
   - On the builder's question: keep A4c's inclusive stop (a request at 15:13:00 may start). My minor asked for
     tests on both sides of the edge, not a change of rule. Changing it would be an A4c change, and nothing here
     needs it.
3. **The weekly fits the window** [strong, from the 19 and 21 Oct sidecars]. BANKNIFTY started 15:01:00, FINNIFTY
   15:02:50-51 and MIDCPNIFTY 15:03:57-15:04:00. The last finished at **15:05:32 (19 Oct) and 15:05:36 (21 Oct)**,
   leaving about 7.5 minutes to 15:13. The builder estimates 40-75 s for the weekly [reasoning only until the first
   live day].
4. **Its own dataset, stem and commit glob.** `niftyweekly_*` never matches NIFTY's `nifty_*` glob. The weekly
   recorder's store keeps `quote-snapshots-weekly/` quote files in Drive only. O1's indices part lists the weekly
   pathspec and its canonical marker.

## My plants (each reverted)

| # | Plant | Caught |
|---|---|---|
| 1 | weeklies do not exclude the monthlies | yes, 5 failed |
| 2 | no `weekly` stem (files named `nifty_*`) | yes, 2 failed |
| 3 | O1's indices part without the weekly canonical marker | yes, 1 failed |
| 4 | the weekly recorder wired to A4's quote store (private prefix A4's dataset) | **no**: 240 passed (minor 1) |
| 5 | "no weekly listed" retried instead of final | yes, 1 failed |
| 6 | the recorder passes no monthlies to `nearest_weeklies` | yes, 2 failed |
| 7 | OI 0 written as an empty cell | yes, 10 failed |

## Minor

1. **The composition root's weekly store is untested [strong: plant 4].**
   - `DriveOnlyQuoteStore` sends a file to Drive only when its path starts with the store's own dataset.
   - Wired to A4's store, the weekly quote files would go to the local folder. `.gitignore`
     (`research/data/quotes/groww/**/*.csv`) would keep them out of commits, but they would never reach Drive: a
     silent loss in the routine's short-lived checkout.
   - `test_weekly.py` builds its own store, so it cannot see this.
   - Add a test on `build_index_quote_recorders` showing the weekly recorder's store routes a `quote-snapshots-weekly/`
     quote file to the private store.
2. **Fewer than two monthlies found [reasoning only].** In the weekly branch, `_targets` does not report "only N
   monthly expiries found". If A5's point-in-time rule returns one monthly, a nearer monthly that it missed could be
   recorded as a "weekly" without a word. The sidecar keeps the expiry, so a reader could still tell. Record the
   same failure line, or skip the weekly attempt, when `len(months) < 2`.
3. **Quality rule 8, after the merge:** the first live day's `NIFTY weekly` line, its expiries, row count, request
   times and end time against 15:13, as the claims promise.

The pre-existing `bid_qty`/`ask_qty` `:g` precision note is correctly left to its own A4 change.
