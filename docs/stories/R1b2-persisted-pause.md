# R1b2: the pause is remembered between runs, and the desk is told

Lane 1, two judges (NSE and other hosts, all the schedules and workflows that call them, #fno-desk). Branch
`story/R1b2-persisted-pause`. **Story text only; no code until it is judged.** Rules and design:
[R1-resilience.md](R1-resilience.md); the layer this builds on: [R1b-nse-source.md](R1b-nse-source.md) (R1b1, merged on
its double PASS). R1b2 is the part of R1b that touches workflows, so it is judged separately.

## What changes

R1b1 keeps the pause in the process: every scheduled run is a new process and forgets it. R1b2 gives the pacer's
breakers their memory (`TransitionLog`, R1a) and an alert sender:

1. **Persistence.** `NsePacer` accepts a `TransitionLog` and an `AlertSender` (`attach`, called once by
   `fno/ingestion/cli.py:main` before any command, with `research/data/resilience/paced-hosts.csv` and
   `build_alert_sender()`). Each host's breaker is built on first use, restores from the log's last row for that host
   (a missing file, an empty history or a last row `closed` means closed; anything else means open from that row's time)
   and appends one row per transition. The breaker label changes from `nse:<host>` to `paced:<host>`, because the shared
   session also paces non-NSE hosts (global cues); the labels are internal, no test or message pins the old one.
2. **Alerts.** One line to #fno-desk per transition to open or re-open, and one when it closes again (`ALERT_OPENED` /
   `ALERT_CLOSED` in the library), through the only sender the repository has (`FNO_SLACK_BOT_TOKEN`, #fno-desk,
   never #market-brief). Without the token the sender says so and nothing is sent; the log row is still written.
3. **Committing the log.** A new last step in every workflow that can reach a paced host (all but `data-checks`, which
   reads Drive only): "Commit the pause log". It runs `if: always() && !inputs.dry_run`, `continue-on-error: true`
   (failing to remember a pause must never fail a data run: a lost row fails open), and only when the file exists:
   `git add` that one path, **stop successfully if it is unchanged**, otherwise commit, then `git pull --no-rebase origin main` and `git push origin HEAD:main`,
   three tries. It is last so it cannot interfere with the Python committers (`GitManifestRecorder` refuses to push
   while the checkout carries unpushed commits outside its paths, `manifest_commit.py`), and it adds only the log's one
   path, so the record scan has nothing to find. `.gitattributes` already marks `research/data/resilience/*.csv` as
   `merge=union`, so two workflows appending at once keep both rows.
4. **A test that no workflow is missed:** every workflow that runs a `python -m fno` command (other than `--help`) has the
   step, with the same text, except `data-checks`.

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
  `quotes record`, `participant-oi watch`, `participant-oi check-once`, `closes read` and `preopen record` (the
  09:12 pre-open capture, read through `PacedSession`, `preopen/wiring.py:63`; judge 1, round 1).
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

## Verification (no claim that `--help` proves anything)

Unit tests with a real file and a fake clock (claims 1 to 4, 6, 7), a static test over the workflow files (claim 5), and
after the merge the same active comparison as R1b1: the first scheduled run of each affected workflow is read and
compared with the previous one (tries, waits, counts, statuses, and now the log file: it should not exist unless a host
was refused). **Stop rule:** a live command that made no attempt while a host was cooling, a pause row on a day with no 403 or 429 in any log, an alert with no matching row, a run
that fails because of the new step, or a workflow whose commit step was disturbed, means R1b2 is reverted at once and
reported. The reversible stage-only dispatch at the owner's validation step stays the controlled real proof.

## Judges

Two judges. Freeze rule: one SHA, no push after sending it.
