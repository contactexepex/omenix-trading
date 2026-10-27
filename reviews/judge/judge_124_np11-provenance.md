# Judge 124: NP11 feed provenance (code, privacy focus), round 1 at e01cb08: FAIL

**Lane 1, two judges; this is judge #1.** Branch `story/NP11-provenance`, frozen SHA e01cb08. I reviewed `git diff origin/main...e01cb08`: 31 files, +1264/−46. That covers:
- `provenance/` (model, file, index, writer, recall, wiring);
- the gate and the cleanup proof;
- the feed-list `scope`, `plan-feeds` and the two workflows;
- tests and rows B1 to B17.

## Gates (strong evidence)
In a venv installed from `requirements.lock`:
- 2015 passed;
- ruff check is clean, and check_imports is clean;
- **plant runner: 280 of 280 `ok`.**

## The privacy core holds (strong evidence, read and planted)
- **The seal.** It is an HMAC of the path keyed with the feed list's salt. The salt must be at least 16 characters (`MIN_SALT_LENGTH`), so it can never be empty or guessable. My plants all fail tests:

| Plant | Result |
|---|---|
| seal keyed with a public constant | 1 failed |
| seal ignoring the path | 1 failed |
| an empty salt in production wiring | 2 failed |
| the open day written | 2 failed |

- **What reaches git.**
  - Manifest ids are `YYYY-MM-DD` or `YYYY-MM-DD-n`, with no feed, key or hash of the pairs.
  - The receipt carries only the SHA-256 and size of a sealed file.
- **The recall report** is counts only, with a whitelist test, and its workflow is `contents: read` with no schedule.
- **Never rewritten.** Writes go through `WriteOnceWriter`, a damaged day is counted and left, and a conflict is counted.

## B1 (required; strong evidence, plant survived the FULL suite): the cleanup gate checks "all", but only "any" is pinned
- `NewsPollProof._recorded_feeds` requires `all(feed in feeds_of(day, key) for article in articles)`.
- My plant changing `all` to `any` passes all 2015 tests.
- With that bug, a poll whose provenance is recorded for one article but not the rest would be trashed, and which feed found the rest would be lost silently. That is exactly what judge 113's and judge 114's B2 exist to stop.
- **Fix:** a test where a poll has two articles, one pair recorded and one not, and the proof says False; plus this plant as a row.

## B2 (required; strong evidence, plant survived the FULL suite): the IST day is not pinned
- `day_of` uses IST, by design: the plan's "IST day of the poll" and "the open IST day is skipped".
- My plant `moment.astimezone(IST).date()` → `moment.date()` (the UTC date) passes all 2015 tests.
- That one function decides which file a pair goes into, when a day counts as closed, and which day the cleanup proof checks.
- **Fix:** a test with a poll at 20:00 UTC, which is the next IST day, asserting its day file and its closed or open state; plus a plant.

## B3 (required, built as planned): `provenance_polls_missing` does not exist
- The plan (round 2, rule 7, row P13) promised the count "`provenance_polls_missing` ... so a day that could not be completed is visible, never silent".
- `git grep` at e01cb08 finds it only in the story; `codes.py` has `provenance_poll_skipped`, `_unreadable`, `_conflict` and `_failed`. A poll the cleanup keeps because its pairs are missing is today counted only as a generic "not proven promoted".
- **This matters because of a real timing case (some evidence, reasoned from the code).** `news promote --from/--to` selects polls by their **UTC** staging day, but provenance days are **IST**.
  - A poll fetched between 18:30 and 24:00 UTC on day D belongs to IST day D+1.
  - A run that reads UTC day D while IST D+1 is still open skips those pairs.
  - Only a later run whose `--from` reaches back to UTC day D writes them.
  - The cleanup gate correctly keeps those polls, so nothing is lost, but without the count the owner cannot see why they stay.
- **Fix:**
  - build the count (in the cleanup report, the promote line, or both);
  - state the `--from` rule in the story: a run must reach back one UTC day to complete the previous IST day;
  - pin it with a row.

## Notes (not blocking)
- **N1.** The scope is part of each pair. If a feed later gets a label, re-promoting its still-staged polls writes a supplement with `(feed, broad)` next to the old `(feed, unknown)`. The recall then counts the article as `broad_only` and also adds it to `with_unknown_feed`. That is not wrong, but say it in the recall docstring.
- **N2.** Promotion now needs `lists.latest()` (for the salt) and fails if the newest feed list is unreadable, where before it only needed `kinds_ever_listed`. That is acceptable, because the fetch needs the list anyway, but state it.

## Hard lines
No orders, no Groww, no secret. The join stays sealed in private Drive.

## Verdict: FAIL round 1 at e01cb08. B1 (pin "all" in the cleanup gate), B2 (pin the IST day) and B3 (build `provenance_polls_missing` and state the `--from` rule) required; N1 and N2 requested.

## Addendum 1: round 2 logic at fa3b90e: PASS (the merge-gating re-confirm is on the post-split head)

I reviewed `git diff e01cb08 fa3b90e`. It adds:
- `provenance/sweep.py` (new);
- in `writer.py`: `open_days`, `first_look` and `provenance_polls_missing`;
- one line in `gate.py`;
- tests and rows B18 to B22.

As the orchestrator directed, `RECORD_CONTRACT.md` running a few lines over 500 is not held against this head: the docs split fixes it before merge.

**Gates (locked venv, strong evidence).**
- 2020 passed.
- ruff check is clean; check_imports is clean.
- **Plant runner: 286 of 286 `ok`.**

**B1, B2 and B3: each now pinned (strong evidence, my own plants against the full suite).**

| Plant | e01cb08 | fa3b90e |
|---|---|---|
| B1: cleanup gate `all` → `any` | passed | 2 failed |
| B2: `day_of` IST → UTC | passed | 3 failed |
| B3: `provenance_polls_missing` dropped | (not built) | 2 failed |
| the sweep not run | n/a | 4 failed |
| the sweep reads only one of the two UTC days | n/a | 2 failed |
| the poll identity is the path only (no fetch time) | n/a | 2 failed |

**B3 is built in a stronger form than I asked (some evidence: read and planted).**
- Every closed IST day of the last 9 that has no file is read from **all** staged polls of its two covering UTC days, whatever `--from` and `--to` say.
- So there is no `--from` rule left to state. The sweep makes the UTC-against-IST gap of round 1 harmless: the first run after a day closes writes its file.
- The 9-day lookback is more than the cleanup's 7-day keep, so the sweep reaches a poll before cleanup could take it. Cleanup's pairs gate still holds a poll whose pairs are not recorded in any case.

**Two plants survive, but neither changes what is written (reasoned from the code).**
1. **The sweep's IST-day filter removed.** `collector.add` files each pair under `day_of(poll.fetched_at)` anyway, so a poll from the neighbouring IST day lands in its own day, and is only an extra read.
2. **`open_days` including today.** `flush` writes only `d < today`, so today's polls are read but not written.

Both are efficiency, not correctness. No test is needed; a comment in `sweep.py` would help.

**Note (not blocking).** A closed day with no articles (all polls empty or rejected) never gets a file, so the sweep re-lists it on every run for 9 days. That cost is bounded and small: say it in the story.

**N1 and N2** are stated in the story.

**Verdict: PASS at fa3b90e (the logic).** I will re-confirm the post-split rebased head (gates and the full runner) before merge.

## Addendum 2: the merge-gating head 423ac92: PASS

423ac92 is fa3b90e plus judge 123's C1 fix plus the post-split `main`. NP11's rows now live in `docs/NEWS_RECORD_CONTRACT.md`. I reviewed `git diff fa3b90e 423ac92 -- fno`. The only NP11 change is in `writer.py` and `sweep.py`:
- `open_days(report)` now decides day by day;
- a damaged day is skipped alone and counted once (`_damaged`, using `reported`).

The rest of that diff is NP10 and NP9b coming in from `main`, each already passed (judge 120, judge 122).

**Gates at 423ac92 (locked venv, strong evidence).**
- 2037 passed.
- ruff check is clean; check_imports is clean.
- **Plant runner: 302 of 302 `ok`.**

**My round-1 findings are closed and pinned (my own plants against the full suite).**

| Plant | Result |
|---|---|
| B1: `all` → `any` in `_recorded_feeds` | 2 failed |
| B2: `day_of` IST → UTC | 3 failed |
| B3: `provenance_polls_missing` dropped | 2 failed |

**Judge 123's C1 is fixed in general.**
- My plant restoring "one damaged day returns no days at all" fails 2 tests.
- My plant counting a damaged day more than once fails 1 test.

**The stated limit (story, "Judge 123 round 2 (C1) and a stated limit"): an acceptable documented limit, not a blocking silent gap (reasoned from the code).**
- A poll staged for a day **after** that day already has a file is not swept again. It goes in only through a range pass whose `--from`/`--to` reaches that day.
- **Why it is not blocking:**
  - **Nothing is lost.** The cleanup gate (B21) keeps the poll staged until its pairs are recorded.
  - **It is not silent.** The recall report counts the affected articles as `no_provenance`.
  - **It touches only the recall-measurement file,** never the archived articles.
  - **It is rare.** A poll is staged in the same run that fetches it, so it is staged during its own day.
- **Recommended later, a small lane 1 change:** have the staging cleanup report count polls kept *because of provenance* separately, so a kept poll says why.

**Verdict: PASS at 423ac92**, the merge-gating head.
