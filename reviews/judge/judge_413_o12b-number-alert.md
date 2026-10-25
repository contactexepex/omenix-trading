# Judge 413: O12b, number-check alert (story/o12b-number-alert at 53f83e7b)

**Verdict: PASS. Lane 1 (a workflow and a Slack post). The main steward may merge it after main-green (judge 410).**

| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Posts only new problems on a push | MET | `--baseline` = a worktree at `github.event.before`; `_alert` drops lines the baseline already had; a missing `before` (first push or a force push) means no baseline |
| 2 | Silent when clean | MET | `if not new: return` |
| 3 | Hourly reminder while red | MET | cron `17 * * * *` with no baseline |
| 4 | Least privilege | MET | `permissions: contents: read`; only `FNO_SLACK_BOT_TOKEN`; triggered on push to main, schedule and dispatch only, never on a pull request |
| 5 | The claim prints the exact next step, and the addendum heading is right | MET | `AddendumCategory.next_step` writes `## Addendum <k>` (the 307.307 root cause) |
| 6 | capture-watch leaves it out | MET | its list and test updated |

**Planted mutations, all caught:**
- the baseline ignored (1 failed);
- posting when clean (2 failed);
- the heading carries the full number (1 failed).

**Gates:** tests/numbering plus capture-watch give 67 passed. On the merged tree, ruff and check_imports are clean and
check_numbers is clean.

## Notes (not should-fix)
- **The hourly reminder posts every hour while main stays red,** up to 24 lines overnight. That is intended, but the
  owner should know.
- A problem line that names a line number re-posts if an unrelated edit shifts that line. That is rare and harmless.
