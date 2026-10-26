# Judge 21: R1b NSE source onto the resilience layer (story text), branch `story/R1b-nse-source`, SHA b9ef26a

**FAIL (round 1), lane 1, judge 1; 1 blocking, 3 should-fix.** Story text only (82 lines). Applying R1 in two steps,
in-process first (R1b1) and then persisted with alerts (R1b2), is the right shape. The deliberate differences are
honestly listed.

## The three deliberate differences, judged against "never weaker than today"

| Difference | Verdict | Reason |
|---|---|---|
| 1 Upward jitter (5 s becomes 5-10 s) | ACCEPTED | Never shorter than today (proven in R1a). The slower worst case needs the timeout table (finding 3) |
| 2 One probe after the 15-min pause | ACCEPTED | Stricter than today. Today, after `SourceCoolingOff` ends, the next call runs its full retry loop (up to 4 requests); the probe sends 1 |
| 3 Drop `nse_json`'s wait after its last failed try | NOT ACCEPTED | Finding 4 |

## Findings

1. **Blocking: the post-merge check does not run the refactored code.** `index-closes.yml`'s `dry_run` step only runs
   `python -m fno data-librarian index-close --help`, `data-revisions sweep --help` and `pipeline index-closes --help`
   (`index-closes.yml:52-57`). No NSE request is made, so "the refactored code ran on the real runner" is false, and
   with the V1 gate lifted this was the only real-runner safeguard. Fix: name a check that fetches from NSE through
   the new path and writes nothing. For example, a librarian or snapshot read of one recent day into a scratch
   folder, with `fetch` only and no Drive settings, or a `--check` command. Or state plainly that the first scheduled
   cron is the real test, and who reads its log, when, and what makes them stop.
2. **Should fix: today's pacing and pause are per host, but the story makes one `nse` breaker and limiter.**
   `RequestPacer` keys spacing, refusals and pauses by host (`http_pacing.py:38-39`, `wait_turn(host)`).
   `www.nseindia.com` (the `nse_json` API) and `nsearchives.nseindia.com` (the archive files) are paced and paused
   separately today. One `nse` breaker would pause archive downloads when the website API refuses. That is stricter,
   but it changes availability, and a single 1 s limiter halves throughput across the two hosts (slower runs:
   finding 3). State the key: per host, as today, or a reasoned change.
3. **Should fix: the timeout margin is pushed onto the judge.** The story says "the story's judge checks that no
   workflow's timeout is within that margin". That is the builder's evidence to give. Tabulate, per NSE-calling
   workflow, the worst case with doubled waits against its `timeout-minutes`. The short ones are 15 min:
   `flows-download.yml` (two `data-snapshot` downloads, both on `NseArchiveSource`) and `participant-oi-watch.yml`.
   A job killed mid-run skips its commit step.
4. **Should fix: keep `nse_json`'s final wait.** The "never weaker" rule decides it, since dropping the wait shortens
   the gap between a failed request and the caller's next one (`close_read`, `quotes/market_levels`, the public
   provider). The story offers to keep it, so keep it, and leave that characterization assertion untouched.
   Adaptations then shrink to one: zero-jitter injection.

## Notes

The claims list (classification parity over 2xx/404/429/5xx/403/418/451, byte-identical exceptions, a static `sleep`
allowlist, zero writes when deferred) is right, and I will plant against each at code review.
