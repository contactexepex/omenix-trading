# Judge 402: A21 part 1, RBI's T-bill and repo rates with first-seen times (story/a21-rates-code @ 6cc00168), for response 274

Judge F (independent). Story `docs/stories/A21-rates-first-seen.md` (text PASS, judge 355 add. 1-2), claims
`reviews/claude/response_274_a21-rates-part1.md`. Built on O10's branch for `CaptureErrorLog`, as the orchestrator
directed. Lane 1 (RBI, Drive, Slack, a workflow). Labels: **strong**, **some**, **reasoning only**.

## Verdict: FAIL (1 should fix, 1 merge condition). Everything else is MET.

## Gates and runs (mine)

| Check | Result |
|---|---|
| pytest `-n auto` at 6cc00168 | **8003 passed, 15 xfailed, 1 failed**: `test_every_job_is_watched`. The branch's `capture-watch.yml` has `rates-daily` but not `global-cues` and `vix-history`, which main's A17 added. It is a merge-order artefact, not A21's code (merge condition below) |
| ruff, ruff format (1451), `check_imports.py`, record scan (6811) | clean |
| Parsers on today's live RBI pages (fetched by me) | home page → `CurrentRates(policy_repo_pct=5.5, tbill_91_pct=5.7281)`; release 63803 → 2026-10-14, `2026-2027/1325`, (5.7281, 6.2896, 6.4891); press-release list → newest T-bill prid 63803 |

## Planted mutations (mine, reverted; `tests/rates`, 34 tests)

| # | Plant | Caught |
|---|---|---|
| 1 | grace `<` 24 h made `<=` (24 h exactly accepted) | yes |
| 2 | stale auction at 8 days (`<=` → `<`) | yes |
| 3 | `first_seen_at` taken before the request (judge 355 add. 1 minor) | yes |
| 4 | `RatesAsOf` ignores the cutoff (look-ahead) | yes |
| 5 | an unreadable history no longer stops the run | yes |
| 6 | exit 0 even when the alert was **not** sent | **no**: 34 passed (SF1) |

## Design checks (code read)

- **Failures are one O10 row each, plus one message per run.** `RatesCapture._finish` writes one row per distinct
  problem and sends one message carrying every problem, plus a repo-rate change as information. The CLI exits 0
  when that message was delivered, so O10's watcher does not add a second line (no judge 359 duplicate here). It exits
  1 only when the alert was not sent, and then capture-watch posts. A failed receipts push fails the commit step, and
  capture-watch posts that too.
- **No look-ahead, no re-record.** The history is read from O9's verified cache, and an unreadable history stops the
  run before any write. `first_seen_at` is the response's arrival. `RatesAsOf` filters by first-seen time.
- **Secrets and logs:** unexpected errors are named by class only, never by their text.
- **The first run takes only the newest release** (no back-fill). A release that failed once is retried while it is
  newer than the first recorded one.

## Should fix

**SF1. The one path that turns a refused alert into a notification is untested [strong: plant 6 survives].**
`cli._capture` returns 1 when the alert came back `alert NOT sent`, which makes the run fail so that O10's watcher
posts. Forcing it to always return 0 passes all 34 rates tests. In that case a Slack refusal would leave only the O10
row, and nobody would be told. Add a CLI test with a fake capture whose alert is `NOT_SENT`, expecting exit 1, and
one with `SENT`, expecting exit 0.

## Merge condition

`capture-watch.yml` on the merged tree must list `global-cues`, `vix-history` (main, A17) and `rates-daily` (A21).
O10's own test then passes. Gate the exact merged tree, including `check_numbers.py`, before pushing.
