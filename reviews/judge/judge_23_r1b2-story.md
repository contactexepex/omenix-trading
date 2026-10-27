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

## Addendum 1: SHA c705ef5 (round 2)

**PASS (story text), lane 1, judge 1.** fc50ebf..c705ef5 changes the story only.
- Finding 1 FIXED: `preopen record` is in `LIVE_WINDOW_COMMANDS`, with its reason and the wiring line.
- All three clarifications are stated: a refused live probe doubles the archive cool-down; overlapping live processes
  each force one probe; the commit step stops successfully on an unchanged log.

On the open edge (no workflow runs `preopen record`, and where it runs is not recorded): acceptable to leave open, and
no question for the owner is needed. The rule is never weaker in every possible run context.
- Where the committed log is absent, the run restores nothing and behaves exactly as today.
- Where the log is present, a cooling host gets one forced probe: fewer requests than today, at least one attempt.

Being in the live set is therefore right whatever the context. The story says so honestly and claims nothing about it.

## Addendum 2: SHA 3ff3358 (delta: judge #2's four fixes)

**PASS (story text), lane 1, judge 1.** c705ef5..3ff3358 changes the story only (+40/-14).
- **B1, two files:** the committed CSV is only read during a run, and rows go to a git-ignored run-local file. Sound:
  a tracked file can no longer go dirty under a manifest committer's `git pull --no-rebase`. It also gives each later
  command in the same job (several `python -m fno` steps per workflow) the earlier commands' transitions. The last step
  pulls first, appends the local rows once, then commits, pulls and pushes. Claim 9's two-clone test and its "rows once,
  header once" check are the right proofs.
- **S1, real UTC for the persisted clock:** correct. Monotonic time means nothing in the next process.
- **S2, the step sets its own hooks path and identity:** correct, and pinned by the static test.
- **S3, the live set grows under a stated rule** ("the source overwrites in place or shows only the current value").
  The rule is sound. Over-inclusion is always safe here: a live command only gets one forced probe while a host is
  cooling, which is still fewer requests than today. So the contestable member (`fpi-daily-by-session`, NSDL) cannot
  make anything weaker, at worst marginally less cautious than an archive command. `fo-masters` is the strongest case:
  the ban list is replaced in place (`fo_masters/job.py`).

Note for the build: a restored breaker's message omits "HTTP" (no status was persisted). That is a new text for a new
case, which no caller pins today. Give it its own test.
