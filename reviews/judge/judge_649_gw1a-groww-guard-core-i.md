# Judge 649: GW1a, Groww's sign-in guard, read-only client, 429 name and 429 stop (story/gw1a-groww-guard-core at 98e5dcfcb)

**PASS, lane 1.** Narrow check as asked; judge I (one of two; K is the other, not consulted), own session
(session_01CHtddAzFcEdQh4HFiz3mqU), 25 Oct 2026. Parts 1-4 of GW1, which judge 638 and its addendum found clean.

## Checks

| Check | Verdict | My evidence |
|---|---|---|
| It is the judged code | MET | Against GW1 at 33f34e571, `fno/providers/groww_sign_in.py`, `tests/test_groww_guard.py`, `tests/test_groww_provider.py` and `tests/groww_sdk_fake.py` are byte-identical (sha1 of each). `groww.py`, `groww_rate_guard.py` and `__init__.py` differ only by the removed quiet-window hooks (`quiet` argument, the `expiries` wait, the `check` call, `MarkQuietWindows`). `feed_wiring.py` and two tests go back to `GrowwProvider` directly (no `get_provider` without quiet windows) |
| Nothing from parts 5-6 | MET | no `groww_quiet_windows.py`, no change in `fno/intraday/groww_source.py`, `recorder.py`, `claims.py`, `source.py` or `fno/storage/manifest_commit.py`; the diff is 11 files, all parts 1-4 or their story |
| 3 tries a day per process is right | MET | back-off 5 then 10 minutes (`FIRST_WAIT * 2 ** (failures - 1)`), the 4th try is never made, a new token day resets. Worst case 38 processes × 3 = 114, under Groww's 150 per 24 h: the builder's count (A16's 7 fires and their reruns up to 21; the daily run's Groww children 5, 10 with a rerun; pre-open 1; the school 4; by hand 2), reasoning only. With 6 tries the same count would allow 228, over the cap, so 3 is the safe choice. Plants K1 (4 tries) and K2 (2 tries) caught |
| Read-only, 429 named, 60 s pause | MET | as judged in 638 (the installed SDK's `GrowwAPIRateLimitException` passes code "429"); K6 (detect by class name), K7, K8, K10, K11 caught |
| No frozen v4 file | MET | none of the 232 frozen paths in the diff (as in 638) |

## Plants

11 on 98e5dcfcb, one at a time on `tests/test_groww_guard.py`, `test_groww_provider.py`, `tests/intraday`,
`tests/quotes`, `test_composition.py`, each restored, tree clean after: K1 4 tries, K2 2 tries, K3 no doubling, K4 no
back-off check, K5 no day reset, K6 a class-name 429 detector, K7 no pause, K8 raw client, K9 no sign-in alert, K10 a
swallowed next-year 429, K11 Groww's text carried on. **11 caught.**

## Gates (98e5dcfcb merged with origin/main dd8992423 as d20e54f51, clean; FNO_SLACK_BOT_TOKEN kept)

- `ruff check` clean; `ruff format --check` clean; `check_imports` clean (2779); `check_records` clean (9325).
- `python -m pytest -q -p no:cacheprovider -n auto`: **16757 passed, 13 xfailed, 0 failed** (573 s).
- Slack in the window: one labelled "DRY RUN, 2026-10-22 replay" line on #fno-desk (a rehearsal, built from a real
  recorded day), no test post.

## Notes (not findings)

- On its own, GW1a keeps the overlaps that exist today (A16 with the 15:00 and 15:15 captures). Its 60 s pause after a
  429 now ends an A4 attempt at once instead of letting it ask for every contract. For E3 that likely starts its retry
  sooner than on 22 Oct, when the retry began at 15:18:24 and ended at 15:21:10, outside C3's window (reasoning only).
  Parts 5-6 remain the fix for the overlaps.
- A16 builds `GrowwProvider` directly, so a failed sign-in there sends no #fno-desk alert: its own records name
  `GrowwSignInPaused` (as the story says).
