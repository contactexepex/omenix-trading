# Judge 640: REH1o, G13's issuers take the rehearsed live date (story/reh1o-issuer-live-dates @ 07c06957e, PR #155), judge B, round 1 of 2

**PASS (no findings). Lane 1** (forecast records written in rehearsals). Story and code in one round; I did not read
judge F. Code: `rehearsed_date(key, real, env)` in `fno/rehearsal/live_wiring.py`, one line in each of
`premium_ranges/wiring.build_issuer`, `price_distribution/wiring.build_live_recorder` and `price_ranges/wiring.build_issuer`,
and `tests/rehearsal/test_issuer_live_dates.py`.

| Check | Result | My evidence |
|---|---|---|
| A real run is unchanged | MET | `rehearsed_date` is `rehearsed_live({key: real}, env)[0][key]`, which returns `real` without a rehearsal mode (`live_wiring.py:24-27`). Plant "real run altered" fails 4 |
| The right key | MET | each module's `STEP` (`premium_ranges`, `price_distribution`, `price_ranges`) is its `daily.live_from` key and in `LIVE_STEPS` (my run), so the child gets the date the daily root made live |
| No live record touched | MET | the three issuers write through `build_store` → `build_owner_drive` → REH1's `rehearsed_drive` (`dryrun/<run_id>/`), unchanged |
| No look-ahead; nothing absent counted | MET | the issuers read only what REH1's recorded sources serve at the replay clock (unchanged). The stated limit (price_ranges before 21 Oct has no close table and stops after 10 minutes) is a not-live step, so REH1j records it `not_live` with the outcome under `exercised`: never success, never a failure of the day |
| Gates | MET | trial merge into origin/main cbd3937a4 (clean, 09598bdd7): ruff, format (2,635), imports (2,764), record scan (9,295), check_numbers clean; **16,597 passed, 1 skipped, 13 xfailed** (token kept) |

## Plants

5 planted, 5 caught: `rehearsed_date` returning the real date (4 failed); a real run altered (4); each of the three
builders reverted to `live_from(cfg)` (1 each).
