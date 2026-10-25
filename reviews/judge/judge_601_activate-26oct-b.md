# Judge 601: activation of 26 Oct (story/activate-26oct @ 406a5fcc9), judge B, round 1 of 2

**PASS (no findings; 1 note). Lane 1** (a switch that turns on a Slack post, and one that turns on scored records).
The change is 5 files: `config.yaml` (`card` and `premium_range_scores` set to "2026-10-26"), `tests/daily/test_steps.py`
re-pinned, live-date notes in `T-cards.md` and `G13d-premium-ranges.md`, and the register row. Owner:
`DESK_DECISIONS.md:340` ("Merge and enable/activate everything that has been completed"; it names card and
premium_range_scores).

## Criteria

| Check | Result | My evidence |
|---|---|---|
| Dates match the owner | MET | both keys "2026-10-26"; margin_check and owner_timing stay null, as row 340 says |
| Test not loosened | MET | `None` replaced by `date(2026, 10, 26)` for both keys; plants (each key set to null, or to 27 Oct) fail 4 of 4 |
| Card path on Monday | MET | `cards/issue.py:45-62` posts first, then clocks, Drive record, delivery file. `check_server` turns any `requests` error into "unchecked" (`server_clock.py:49-53, 98-104`); `DriveCardRecords.save` never raises (`record_store.py:28-34`); `_write` catches `OSError`. I found no exception that escapes in a real run, as claimed |
| No second post | MET | `card` is an O1 command step (`daily/wiring.py:103,147`); a failed step is rerun only with `retry: True` (`run_log.py:82`), set only for `RETRIED_ON_RERUN = ("exits", trade_marks)` (`desk/daily_run.py:84`) |
| Scores on 26 Oct | MET | my read through the verified Drive cache (problems: none): NIFTY 23 Oct issue 178 rows, BANKNIFTY 208, both `next_session` 2026-10-26; GitHub's receipt time of both receipts 15:19:11 IST on 23 Oct (`CommitmentTimes`, real push receipts), before the 15:30 seal; step order: `premium_range_scores` after `price_distribution` and `premium_ranges` in the same run |
| 22 Oct "no receipts" stop | MET (replay-only) | the first premium-range receipts are 23 Oct's (receipts folder on main); issuing has been live since 23 Oct |
| Gates | MET | trial merge into origin/main 712386480 (clean, 480f6ea31): ruff, format (2,562), imports (2,691), record scan (9,162), check_numbers clean; **16,067 passed, 1 skipped, 14 xfailed**, token kept |

**Ruling: turning the card on before T1f merges is acceptable.** In a real run the after-post path cannot escape
(above). If it ever did, the post stays and the step fails with its alert: no second post, and nothing else in the run
reads the missing files. The defect T1f fixes is a rehearsal one. REH1's guard raises `RehearsalCallRefused` (a
`RuntimeError`, not a `RequestException`) in the GitHub clock check, so every rehearsed card fails after its post. The
cost is a failed `card` row in each rehearsal until T1f lands; real days are unaffected.

## Plants

4 planted (each key set to null, or to 27 Oct), 4 caught.

## Notes

1. Under pilot mode, rehearsals post to Slack (with REH1's label), so until T1f each rehearsal's card both posts and
   reports "failed". Read it as the known T1f defect, not a real-day risk.
