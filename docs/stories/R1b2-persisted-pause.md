# R1b2: the pause is remembered between runs, and the desk is told

Lane 1, two judges (NSE and other hosts, all the schedules and workflows that call them, #fno-desk). Branch
`story/R1b2-persisted-pause`. **Story text only; no code until it is judged.** Rules and design:
[R1-resilience.md](R1-resilience.md); the layer this builds on: [R1b-nse-source.md](R1b-nse-source.md) (R1b1, merged on
its double PASS). R1b2 is the part of R1b that touches workflows, so it is judged separately.

## What changes

R1b1 keeps the pause in the process: every scheduled run is a new process and forgets it. R1b2 gives the pacer's
breakers their memory (`TransitionLog`, R1a) and an alert sender:

1. **Persistence.** `NsePacer` accepts a `TransitionLog` and an `AlertSender` (`attach`, called once by
   `fno/ingestion/cli.py:main` before any command, with `build_alert_sender()` and the two files below). Each host's
   breaker is built on first use, restores from the log's last row for that host (a missing file, an empty history or
   a last row `closed` means closed; anything else means open from that row's time) and appends one row per
   transition. The breaker label changes from `nse:<host>` to `paced:<host>`, because the shared session also paces
   non-NSE hosts (global cues); the labels are internal, no test or message pins the old one.
   **Two files, so the run never dirties a tracked file (judge 2, B1).** The committed log
   `research/data/resilience/paced-hosts.csv` is only **read** during a run. The run **appends** to a run-local,
   git-ignored file `research/data/resilience/.run/paced-hosts.csv` (new `.gitignore` line). A `LayeredLog` reads both
   (committed rows then this run's rows) and writes only the local one. A tracked file modified during the run would
   make the manifest committers' `git pull --no-rebase` fail with "local changes would be overwritten" whenever another
   workflow had pushed the same CSV; an ignored file cannot.
   **Real UTC, not monotonic time (judge 2, S1).** The breaker's clock for a persisted log is `datetime.now(UTC)`;
   an `EPOCH + monotonic` clock is meaningless in the next process. In-process spacing keeps `time.monotonic`. The pacer
   takes the wall clock as its own argument (tests inject one); R1b1's tests, which inject only the float clock, still
   derive the wall time from it. A restored breaker has no refusal status, so its message is built from the log's
   cool-down alone ("HTTP" omitted).
2. **Alerts.** One line to #fno-desk per transition to open or re-open, and one when it closes again (`ALERT_OPENED` /
   `ALERT_CLOSED` in the library), through the only sender the repository has (`FNO_SLACK_BOT_TOKEN`, #fno-desk,
   never #market-brief). Without the token the sender says so and nothing is sent; the log row is still written.
3. **Committing the log.** A new last step in every workflow that can reach a paced host (all but `data-checks`, which
   reads Drive only): "Commit the pause log". It runs `if: always() && !inputs.dry_run`, `continue-on-error: true`
   (failing to remember a pause must never fail a data run: a lost row fails open). **It sets `core.hooksPath` and the
   commit identity itself** (it does not rely on an earlier step, which may not have run; judge 2, S2). It does nothing
   when the run-local file is absent or empty. Otherwise: `git pull --no-rebase origin main` first (the tree is clean:
   the Python committers have pushed and the local file is ignored), then append the local rows (without their header)
   to the committed CSV, creating it with the header if it is missing, `git add` that one path, **stop successfully if
   it is unchanged**, commit, `git pull --no-rebase` and `git push origin HEAD:main`, three tries. It is last so it
   cannot interfere with the Python committers (`GitManifestRecorder` refuses to push while the checkout carries
   unpushed commits outside its paths, `manifest_commit.py`), and it adds only the log's one path, so the record scan
   has nothing to find. `.gitattributes` already marks `research/data/resilience/*.csv` as `merge=union`, so two
   workflows appending at once keep both rows.
4. **A test that no workflow is missed:** every workflow that runs a `python -m fno` command (other than `--help`) has the
   step, with the same text, except `data-checks`, and the step sets the hooks path and the identity (the test reads
   both lines).

Not in R1b2: Drive, Groww, the rest (R1c, R1d). The Groww-side live captures follow the same rule when R1d moves them.

## Data cost, and the live-window rule (never weaker where a miss is permanent)

Today a new process calls NSE at once whatever the last run saw. After R1b2, an ordinary run that starts inside a
cool-down gets `SourceCoolingOff` from the first request, with no request sent. For **archive and end-of-day** work that
is harmless: fills, sweeps and the stager cover the last 7 days and the next run repairs it. For a **live window** it is
not: the 3 pm quote recorder (14:55 to 15:10), `participant-oi-watch` (the release-time log), the 15:40 close read
and the 09:12 pre-open capture cannot be redone, so a cool-down carried over from an earlier run must not cost them their one attempt.

**The rule (orchestrator's design, written here for the judges to test):**
- A command that belongs to the set `LIVE_WINDOW_COMMANDS` (in `fno/shared/constants.py`, so the set is explicit) runs with
  `attach(..., live_window=True)`. The marker is a property of the **command**, read once from the parsed command by
  `main()`; no YAML says anything about it. A static test pins the set, so it cannot grow silently. Proposed set:
  `quotes record`, `participant-oi watch`, `participant-oi check-once`, `closes read`, `preopen record` (the
  09:12 pre-open capture, read through `PacedSession`, `preopen/wiring.py:63`; judge 1, round 1), `fo-masters` (NSE
  replaces the ban list in place, so a missed day is gone: `fo_masters/job.py` says "NSE wrote none, or every run
  before its replacement failed"), `data-snapshot fii-dii-cash-by-session` (NSE's live page shows the latest day; reasoning only, not
  measured) and `data-snapshot fpi-daily-by-session` (NSDL's daily report, not an NSE host; listed with its sibling,
  contestable) (judge 2, S3). The test for the set is the rule: a command is live when its
  source overwrites in place or shows only the current value within the window the next run would read it, so a missed
  run cannot be redone. The other
  `data-snapshot` kinds (reference lists NSE replaces rarely) and `global-cues fill` (a repairable backfill) stay out.
- In such a run, the first request to a host whose persisted breaker is open and still cooling is let through as **one
  probe** per process per host, paced like any request (the 1 s spacing), with R1b1's probe rules: the others of that
  process wait for its answer; a good answer (any status but 403 or 429, or no answer) closes the host and the run goes
  on; a 403 or 429 re-opens it (cool-down doubled, as for any refused probe) and the run defers as now.
- Every other command respects the full persisted cool-down. A refused live probe doubles the persisted cool-down, so
  the **archive** runs that follow are deferred for longer too (the one place a live run's probe costs another command
  data: catch-up repairs it, as above). Two live processes that overlap in time may each force one probe, because the
  log is read at the start of each process: the cost is one request each, never more per process.
- Persistence reaches a run only through the committed log, so a command that runs outside the workflows restores
  nothing and the rule changes nothing for it. No workflow runs `preopen record` today (`grep` over `.github/workflows/`);
  where it runs is not recorded in this repository, so whether it ever sees a persisted pause is open, and the story
  makes no claim about it.
- Library edit (flagged, touches merged R1a): `CircuitBreaker.check(force_probe=False)`: with `True`, an open breaker
  still cooling is admitted once as a probe (state half-open, a `half_open` row), then behaves as after any probe.

**What this costs, stated plainly (reasoning only: there is no measurement of NSE's blocks in this repository):** while a
host is cooling, each live run sends **one** paced request to it, where today it would send its whole retry loop and
every other request of the run. That is not zero, and a block that really persists will refuse that request and extend.
It happens only when the breaker is open (two refusals in a row, rare), and only for the few live commands. It keeps
today's guarantee of at least one attempt for the windows that cannot be redone, at the price of that one request. The
orchestrator accepts that as not meaningfully weakening politeness; the judges rule on it, and if they find it cannot
be both polite and never-weaker, it goes to the owner.

A closed breaker stays closed: no row is written for calls that never failed, so a healthy run changes no file and
commits nothing. The cool-down doubles only when a probe is refused, up to 24 h; the first open is 15 minutes. A host
that stays blocked for a day would also void each day's live data whatever this layer does; the alert is how the owner
learns of it the first time.

## Claims and how each is shown

1. A breaker opened by one process is open in the next, from the log, until its cool-down ends (two `NsePacer`
   instances over one file, with a fake clock); a closed or missing history is closed.
2. After the cool-down the next process's first request is the probe (one request), with R1b1's rules; a refused probe
   writes `reopened` with the doubled cool-down; a good one writes `closed`.
3. One alert per transition and none for a call that fails without opening; the alert text carries no value, only the
   host and the minutes; without the token nothing is sent and the row is still written (spy sender).
4. No row, no file, no commit on a healthy run (a test over a run of 200s).
5. The step list is uniform (claim 4 above) and `continue-on-error`; the step adds one path only (a test reads the YAML).
6. Concurrent appends from two workflows both survive a merge (the existing `test_union_merge` over the new path).
7. Old behaviour inside the process is unchanged: the 42 characterization tests and the R1b1 tests stay green.
8. The live-window rule: in a live command's run, a persisted open breaker still cooling admits exactly one probe per
   host (three threads: one request, the rest wait), a good answer closes it and the run proceeds, a refused one
   re-opens it; in any other command the same state refuses without a request; `LIVE_WINDOW_COMMANDS` is the stated
   set and a static test fails if a command is added or removed without it.
9. No tracked file changes during a run: with the committed CSV changed upstream, a manifest committer's `git pull
   --no-rebase` still succeeds (a git test over two clones); the local file is ignored (`git check-ignore`); the
   restore uses UTC (a breaker opened at 09:00 UTC is still open at 09:10 UTC in a new `NsePacer`, closed after
   09:16, whatever the monotonic clock says); the commit step appends only new rows once, header once.

## Verification (no claim that `--help` proves anything)

Unit tests with a real file and a fake clock (claims 1 to 4, 6, 7), a static test over the workflow files (claim 5), and
after the merge the same active comparison as R1b1: the first scheduled run of each affected workflow is read and
compared with the previous one (tries, waits, counts, statuses, and now the log file: it should not exist unless a host
was refused). **Stop rule:** a live command that made no attempt while a host was cooling, a pause row on a day with no 403 or 429 in any log, an alert with no matching row, a run
that fails because of the new step, or a workflow whose commit step was disturbed, means R1b2 is reverted at once and
reported. The reversible stage-only dispatch at the owner's validation step stays the controlled real proof.

## Judges

Two judges. Freeze rule: one SHA, no push after sending it.

## R1b2 build evidence

Branch `story/R1b2-code`. Code: `fno/shared/nse_pacer.py` (`attach`, real-UTC wall clock, the forced probe once per
process, the restored-pause message), `fno/shared/resilience/breaker.py` (`check(force_probe=False)`, flagged: touches
merged R1a), `fno/shared/resilience/transition_log.py` (`LayeredLog`), `fno/shared/constants.py`
(`LIVE_WINDOW_COMMANDS`, the two log paths), `fno/ingestion/pause_memory.py` (command words, the live decision, the
attach), `fno/ingestion/cli.py` (`main` calls it), `ops/commit_pause_log.sh`, the last step in **13** workflows (every
one but `data-checks`; the story's text said 12, which was a count error), `.gitignore`.

- **Where the live flag comes from:** `main` takes the command words from `argv` (skipping `--config` and `--provider`
  and their values) and looks them up in the set. The set is pinned by a test, and each member is shown to be a real
  command by parsing `<words> --help`.
- **Tests (52 new):** layered log (2); restore by UTC across pacers with different monotonic origins, closed or missing
  history, one alert per transition and none for a failure that does not open, a healthy run writes no file, the
  live-window rule (an ordinary command refused without a request; a live one sends one probe and the other threads wait;
  a refused live probe reopens doubled and is forced only once per process, and a later archive run sees the doubled
  pause; two overlapping live processes each get a probe) (8); command words and the live decision, the set, every
  workflow's last step, hooks and identity, the ignored directory (36); the commit script against real throwaway git
  repositories (6): no transitions commit nothing, header once, no duplicate rows, a manifest committer's
  `git pull --no-rebase` still works while the run has pending rows, **the old design's tracked-file pull is refused (the
  reproduction judge 2 asked for)**, and a failed pull leaves the rows in place and fails loudly.
- **Own test for the restored message** (judge 1's note): it is the first test above ("refused in an earlier run; not
  calling it for 5 more minutes").
- **Mutation plants, each caught:** no hooks path, no identity, no pull before the merge, no dedupe, a wall clock derived
  from the monotonic one in production, force_probe on a non-live command, forcing more than once per process, a live
  command missing from the set, alerts not wired, the log not wired. **One equivalent mutant, stated:** dropping the
  script's `tail -n +2` (the header skip) changes nothing, because the dedupe already skips a header the file has; the
  two protections overlap on purpose.
- **Carried from judge 1 (R1b1):** the threaded tests are bounded (daemon threads, joins with a timeout and an assert).
  One timing assertion (`min gap >= 0.04`) flaked once under load in the full parallel run; the two new-code ones now
  use 0.03, still far above the 0.0 s an unlocked limiter gives.
- **The `preopen record` run context** (judge 2, parked as an owner question): no workflow runs it, and the repository
  does not say where it runs. **Whatever place runs it must not commit the pause log**: the live-window rule reads the
  committed log and would, harmlessly, find nothing. The owner is asked to say where it runs.
- Gates: ruff, imports, numbers, size clean; 484 tests pass.

### R1b2 code round 2 (judge 2, round 1 on c3b50d8: one should-fix, plus an optional line)

- **Q14:** replacing the `attach_pause_memory(...)` call in `cli.main` with `pass` left every test green. Tests now go through
  `main` (command patched out): a live command (`quotes record`, `fo-masters`) and a non-live one
  (`data-librarian index-close`) leave `SHARED_PACER.log` a `LayeredLog` on the committed and the run-local paths, with
  `live_window` true or false accordingly, and `main()` with no argument reads `sys.argv`. With the call replaced by `pass`
  four of them fail.
- **Local sessions** (judge 2's optional line): a hand run or a session on a laptop keeps its own git-ignored
  `.run/paced-hosts.csv` in its checkout; nothing merges it unless someone runs `ops/commit_pause_log.sh`, so a
  local pause is not shared and a local run restores only what the committed log holds.
- Gates: ruff, imports, numbers, size clean; 488 tests pass.
