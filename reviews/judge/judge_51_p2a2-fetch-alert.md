# Judge 51: P2a2 (the news-fetch failure alert), judge #1, single judge

**SHA:** `11b25dbcefc96407428ef7e5ee472b986d511adf` (`story/P2a2-fetch-failure-alert`). Lane 1 (a workflow).
**Verdict: PASS.**

The diff is `news-fetch.yml` (+5) and one test (+10).

**The step** is the repo-standard "Alert the desk channel when the job failed":
- `if: ${{ failure() && !inputs.dry_run }}`, with no `continue-on-error`;
- it posts through `build_alert_sender()`;
- the text is fixed: the run link plus `steps.fetch.outcome`, which is a GitHub status word, not input;
- no secret is in the command: `FNO_SLACK_BOT_TOKEN` comes from the job-level `env` (line 31).

It sits before "Commit the pause log", which stays the last step (`always()`, `continue-on-error`), as
`test_pause_memory_wiring` requires.

**Gates:** 765 passed, 2 runs out of 2. ruff is clean.

| Plant | Result |
|---|---|
| The condition replaced with `false` | caught |
| `continue-on-error` added to the alert step | caught |

**Effect.** A news-fetch job that dies before or inside the command (a dependency failure, a Drive outage, OOM) now
reaches #fno-desk. This closes the news-fetch half of the silent-failure gap from judge_50.
