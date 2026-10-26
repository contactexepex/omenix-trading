# P1b: stage-only first dispatch for pipeline-staging.yml

Lane 1 (a workflow that calls Drive; the write-once Record). Branch `story/P1b-stage-only-input`. Follow-up to P1
(`docs/stories/P1-staging-record-split.md`). Story text first; the one workflow change follows once it is accepted.

## Problem

`pipeline-staging.yml` always runs `promote` after `stage`. `stage` writes only the Drive `staging/` area, never the
Record, so a stage-only run validates the NSE fetch, the Drive write and the staging layout with no write-once risk.
`promote` is the only step that can write the Record; its first real run is a separate owner decision.

## Claims

1. A new boolean `workflow_dispatch` input `promote`, default **false**. With it false the `promote` step does not run,
   so a dispatch only stages.
2. With `promote` true the workflow behaves as P1 left it (stage, then promote even if stage failed, then fail the run
   if stage failed).
3. `dry_run` is unchanged (CLI `--help` only, no Drive).
4. No other workflow, no schedule, no Python code and no test changes; the workflow stays `workflow_dispatch` only.

## Gap list

- No Python or test change, so no unit test covers the workflow; the check is the YAML parse in the review and the first
  dispatch (owner coordinated). The judge reads the diff (about 10 lines).
- It does not add a Record-only credential (P1 gap list: credential separation).

## Follow-up (labels and the failure signal)

Two labels made stale by the `promote` input were corrected (the `days` description and the last step's name). A failed
stage-only run posts nothing to #fno-desk, by design for now: the run is a manual dispatch, its last step exits 1, so the
run turns red in GitHub and the dispatcher sees it at once. An alert step is not added: nobody is waiting on an
unattended run. Revisit when the workflow is scheduled.

## First stage-only run (runbook; nothing here runs by itself)

The owner holds the trigger. `stage` writes only the Drive `staging/` area, never `raw/` or `revisions/`; `promote` (the
only step that can write the Record) is off unless the `promote` input is true.

**Inputs of `pipeline-staging.yml`:** `dataset` (participant-oi, participant-volume, fii-stats, fo-bhavcopy, cm-bhavcopy;
default participant-oi), `days` (default 7; the run stages from today minus `days`, IST, to yesterday), `promote`
(default false), `dry_run` (default false). One dataset per dispatch. The end of the range is the CLI default, yesterday
by the runner's clock (UTC) while the start uses IST, so between 00:00 and 05:30 IST the range ends one day early; harmless.

**Step 1, dry run** (writes nothing to Drive, no commit, no Slack; the hashed install step runs before it, so it proves the
`--require-hashes --only-binary=:all:` install on the real runner):
`gh workflow run pipeline-staging.yml --ref main -f dataset=participant-oi -f days=7 -f promote=false -f dry_run=true`
(or Actions, "pipeline-staging", "Run workflow", branch `main`, same fields). Success: every step green; the install log
shows the locked set installing with no "Hashes are required" or hash-mismatch error; both `--help` outputs print.

**Step 2, stage only:** the same command with `-f dry_run=false`. Dataset `participant-oi` is a small CSV from NSE (no
Groww, so no market-hours rule), checked by its title date, and also fetched by a live workflow. Success: a green run;
the `stage` step prints `nse/derivatives/participant-oi: staged N, unchanged 0, 0 with a sourced exception` and
`result: complete`; the promote step is skipped; no commit. In Drive:
`staging/nse/nse/derivatives/participant-oi/<YYYY>/<MM>/fao_participant_oi_<DDMMYYYY>.csv/<YYYYMMDDTHHMMSSZ>`, one object
per fetch (the UTC fetch time is its name), and nothing new under `raw/` or `revisions/`. Run it again: it should
report `staged 0, unchanged N`, unless NSE has rewritten a file since the first run (it does this for some participant-OI
files); then `staged 1` is correct, a new copy beside the old one, not a failure.

**Failure signs:** `not published` or `source refused` for a day turns the run red by design (NSE publishes a day's
participant-oi file in the evening of that session, so a run that includes today or a day not yet published will be red); a Drive sign-in refusal prints the owner's fix and exits 1; a hash error at install means a
wheel the runner needed is missing from the lock (a lock fix, `ops/relock.sh`, not a data problem).

**Promote is a separate owner decision**, after the staged files are confirmed.
