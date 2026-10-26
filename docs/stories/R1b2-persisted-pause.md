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
   `git add` that one path, commit if changed, then `git pull --no-rebase origin main` and `git push origin HEAD:main`,
   three tries. It is last so it cannot interfere with the Python committers (`GitManifestRecorder` refuses to push
   while the checkout carries unpushed commits outside its paths, `manifest_commit.py`), and it adds only the log's one
   path, so the record scan has nothing to find. `.gitattributes` already marks `research/data/resilience/*.csv` as
   `merge=union`, so two workflows appending at once keep both rows.
4. **A test that no workflow is missed:** every workflow that runs a `python -m fno` command (other than `--help`) has the
   step, with the same text, except `data-checks`.

Not in R1b2: Drive, Groww, the rest (R1c, R1d).

## Data cost, stated (this step is stricter than today by design)

Today a new process calls NSE at once whatever the last run saw. After R1b2, a run that starts inside a cool-down gets
`SourceCoolingOff` from the first request, with no request sent, and a stale row cannot hold a host longer than its
cool-down. This defers data the old code would have tried to read, and for **live windows nothing makes it up**: the
3 pm NSE quote recorder (`quote-recorder-nse`, 14:55 to 15:10) and `participant-oi-watch`. Why it is accepted, with
the evidence it rests on: a breaker opens only after two refusals in a row (403 or 429) from a host, which is NSE saying
it blocks this runner's address; at that point the next run would be refused as well, and the old behaviour of calling
again right away is the thing that lengthens a block (reasoning only; there is no measurement of NSE's blocks in this
repository). Everything that catch-up can repair (fills and sweeps over the last 7 days, the stager) is repaired by the
next run. The cool-down doubles only when a probe is refused, up to 24 h; the first open is 15 minutes. **A host that
stays blocked for a day would also void each day's 3 pm quotes; the alert is how the owner learns of it the first time.**
The judges decide whether live windows need an exception (for example a cool-down cap of 15 minutes for the two live
workflows); the story does not add one on its own, because a second rule per workflow is what R1 removes.

A closed breaker stays closed: no row is written for calls that never failed, so a healthy run changes no file and
commits nothing.

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

## Verification (no claim that `--help` proves anything)

Unit tests with a real file and a fake clock (claims 1 to 4, 6, 7), a static test over the workflow files (claim 5), and
after the merge the same active comparison as R1b1: the first scheduled run of each affected workflow is read and
compared with the previous one (tries, waits, counts, statuses, and now the log file: it should not exist unless a host
was refused). **Stop rule:** a pause row on a day with no 403 or 429 in any log, an alert with no matching row, a run
that fails because of the new step, or a workflow whose commit step was disturbed, means R1b2 is reverted at once and
reported. The reversible stage-only dispatch at the owner's validation step stays the controlled real proof.

## Judges

Two judges. Freeze rule: one SHA, no push after sending it.
