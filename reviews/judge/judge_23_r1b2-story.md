# Judge 23: R1b2 persisted pause (story text), branch `story/R1b2-persisted-pause`, SHA fc50ebf

**FAIL (round 1), lane 1, judge 1; 1 should-fix, nothing blocking.** Story text only (97 lines). Persistence, alerts,
the uniform last commit step and the live-window rule are sound. The live set misses one live window.

## The three questions

**(a) One paced probe per live run while a host is cooling: never weaker? YES, on both axes. Reasoning only (no NSE
block data exists).**
- Politeness: today a new process ignores any earlier refusal and sends its whole retry loop and every other request.
  The rule sends one request, paced, and the rest of that process waits for its answer. That is strictly fewer
  requests than today.
- Data: the live run keeps today's guarantee of at least one attempt. A good answer lets the window proceed, and a
  refusal defers it, as today's second refusal would.
- The one real cost: a refused live probe doubles the **persisted** cool-down, so later archive runs wait longer.
  Archive work is repaired by the 7-day fills and sweeps, so I accept it. It belongs in the story's cost paragraph.

**(b) The live set: one missing.** `quotes record`, `participant-oi watch`, `participant-oi check-once` and
`closes read` are real CLI paths (`quotes/cli.py`, `research_data/participant_oi_cli.py:20,25`,
`close_read/cli.py:14-15`). But **`preopen record`** is a live window too: "GIFT Nifty and NSE's pre-open result, by
09:12 IST" (`preopen/cli.py:9-11`), and it reads NSE through `PacedSession` (`preopen/wiring.py:36,63`). A miss there is
permanent. Correctly out of scope: `quotes record-indices` (Groww only, no NSE call in `index_wiring.py`, so R1d) and
`global-cues fill` (a back-fill, repairable).

**(c) `CircuitBreaker.check(force_probe=False)`: a clean edit.** It is a default-off flag on the one admission method,
and it leaves the half-open machinery unchanged. Two overlapping live processes can each force a probe (one per
process, bounded); say so with the "one probe" claim, as R1b already does.

## Findings

1. **Should fix:** add `preopen record` to `LIVE_WINDOW_COMMANDS`, and to claim 8's static test.

Minor: claim 4 ("no file, no commit on a healthy run") is right, but the commit step's `git pull`/`git push` runs in
every workflow even when nothing changed. Say that it exits early when the file is unchanged (the story says "only
when the file exists"; "and changed" would be exact).
