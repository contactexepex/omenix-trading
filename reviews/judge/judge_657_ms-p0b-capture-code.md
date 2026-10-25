# Judge 657: MS-P0b code, market school capture probes at a study pace (story/ms-p0b-capture at d4a00822f)

**FAIL, lane 1.** Round 1 of 2. Judge I, own session (session_01CHtddAzFcEdQh4HFiz3mqU), 25 Oct 2026. Judged against
the passed text (judge 626.1, 073b8b9e7), on top of `main` with GW1a merged (d73c75534).

## Criteria and the orchestrator's checks

| Check | Verdict | My evidence |
|---|---|---|
| 1 Pace 1.0 s / 3.0 s | MET | `StudyPace.wait_turn`; Q5 (no sleep) caught |
| 2 Cap and reservation | MET | `_reservation` = min(slot budget, cap − spent); a reservation counts in full until its slot ends; an unpushed reservation starts nothing. Q6, Q7, Q11 caught. Groww's day is 56 + 3 × 50 = 206, under 240 |
| 3 Refusals | MET | `answers.judge`: any other 4xx, any unknown error and any non-JSON or wrong-shape 200 stop the source; Groww stops at its first 429, NSE at its second; a 5xx or timeout is retried once. A stop is pushed at once. Q1, Q2, Q3, Q4, Q14 caught |
| 4 One sign-in | MET | a failed sign-in is judged a stop for the day, so no later slot signs in (`test_a_failed_sign_in_stops_groww_with_no_second_sign_in`) |
| 5 Times | PARTLY | slots 10:07, 11:37, 13:07 and 14:07, each stopped hard 6 min later (`caller._send` checks after the pace wait; Q8 caught); a sixth session refused (Q13 caught). The A16h days are not pinned: finding 1 |
| 6 Read-only | MET | Groww only through `get_provider` and `ReadOnlyGroww`; no `GrowwAPI` in `fno/capture_probes`; NSE only by `NseGet.get` |
| 7 Honest User-Agent | MET | headers replaced, not added; Q10 (a browser string) caught |
| 9 Write-once, 10 nothing secret, 11 own paths | MET | the Claims' tests, with gates green |
| 429 through GW1a | MET | `groww_rate_limited` = `is_rate_limit` or `GrowwRateLimitPaused` (both on `main` now); Q12 caught |
| Clear of A16's marks without parts 5-6 | MET | Slots run :07-:13 and :37-:43. A16's marks end by about :01:23, or a little later for a late mark, and the next mark starts at :15 or :45. Nothing else asks Groww at those times: the daily run's first Groww reader is v4 at 14:32, and A14c reads no Groww |
| First live session Thu 29 Oct | MET | `BLACKOUT_DAYS` holds 26, 27 and 28 Oct; trading days only |
| Nothing v4 or the school reads | MET | it writes only `school/p0b/` in Drive, `receipts/data/school/p0b/`, `research/school/probes/p0b/` and O10 rows; no reader outside the package names those paths (grep); no v4, fleet or v4-pack import (its import-closure test) |

## Findings

1. **Should-fix (rule 4, criterion 5): the blackout test can never fail.**
   - `test_day.py:30` is parametrized over `sorted(BLACKOUT_DAYS)`, the constant itself.
   - So dropping 27 or 28 Oct from it (my Q15) passes, and the probe would read Groww on an A16h probe day. That spoils
     A16h's question 3, which the text names.
   - Fix expected: the test lists the days itself (26, 27 and 28 Oct, as the passed text and the orchestrator's 24 Oct
     answer 5 give them) and checks each is refused.
2. **Minor: the Claims are stale for `main`.**
   - They say "not ready to merge", that imports fail without GW1, and that `get_provider` brings "quiet windows".
   - The same claim about quiet windows is in `wiring.py:39`'s comment.
   - On `main` (GW1a) there are no quiet windows; P0b keeps out of A16's marks by its own slot times. Say so.

## Plants

15, one at a time on `tests/capture_probes` and `tests/test_groww_guard.py`, each restored; tree clean after. **14
caught; Q15 survived** (finding 1). Q5's first form broke the syntax, so I redid it as a real no-sleep, which was
caught.

## Gates (d4a00822f merged with origin/main d73c75534 as ba61d935d, clean; FNO_SLACK_BOT_TOKEN kept)

- `ruff check` clean; `ruff format --check` clean; `check_imports` clean (2810); `check_records` clean (9364).
- `python -m pytest -q -p no:cacheprovider -n auto`: **16970 passed, 13 xfailed, 0 failed** (603 s). Slack in the
  window: one labelled rehearsal card on #fno-desk, no test post.

## Addendum 1: round 2 at bc445819d (the last round)

**PASS, lane 1** (Judge I, own session). The probe's own change since d4a00822f is one comment (`wiring.py`), two
tests (`test_day.py`, `test_readers.py`'s import order) and the Claims. The rest of the diff merges `main`.

| Item | Verdict | My evidence |
|---|---|---|
| 657.1 the blackout test could not fail | FIXED | `KEPT_CLEAR` names 26, 27 and 28 Oct in the test; each is refused; `BLACKOUT_DAYS` must equal exactly those three; 25 and 29 Oct run past the check. My Q15 again (only 26 Oct kept): 3 failed, caught |
| 657.2 stale Claims and comment | FIXED | the Claims say GW1a is on `main` with no quiet windows there, and that P0b keeps clear by its own slots; `wiring.py:45` names only the sign-in guard and the 60 s pause |

Gates on bc445819d merged with origin/main 8f65d0824 as 303cc194d (clean; FNO_SLACK_BOT_TOKEN kept): ruff, format,
`check_imports` (2848) and `check_records` (9434) clean; pytest -n auto **17144 passed, 13 xfailed, 0 failed** (660 s).
Slack in the window: two labelled rehearsal lines on #fno-desk, no test post.
