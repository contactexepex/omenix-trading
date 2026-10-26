# Judge 16: P1d first stage-only runbook (judge #2, single judge)

Branch `story/P1d-first-stage-only-runbook`, SHA `7e7c035bf4516b1be208ecbfd5502ef0b08e69fd`; one section added to
`docs/stories/P1b-stage-only-input.md`. **PASS**, lane 1, text only. Gates: doc-reading tests 73 passed; record scan
clean.

| Runbook claim | Verdict | Evidence (`main`) |
|---|---|---|
| Inputs and their defaults | MET | `pipeline-staging.yml` inputs: dataset choice (5, default participant-oi), `days` "7", `promote` false, `dry_run` false |
| The range: IST start, UTC end, the 00:00-05:30 IST edge | MET | `--from` is `TZ=Asia/Kolkata date -d "-$DAYS days"`; the `--to` default is `today_local() - 1`, and `today_local()` is the container's local date (`models.py:29-31`), UTC on the runner |
| A dry run proves the hashed install | MET | the install step has no `if`, so it runs on a dry run; the dry-run step only prints `--help` |
| Stage-only output line | MET | `runs.py:41-42` format; `result: complete` only when nothing was unpublished or refused |
| Drive object path | MET | `staging/` + `nse/` + `ParticipantOiSource.path_for(day)` (`nse/derivatives/participant-oi/YYYY/MM/fao_participant_oi_DDMMYYYY.csv`) + `/<UTC stamp>` |
| Promote skipped; nothing under `raw/` or `revisions/`; no commit | MET | promote `if: !dry_run && promote`; `cmd_stage` commits nothing |
| Failure signs turn the run red | MET | an incomplete stage exits 1; `continue-on-error`, then the final `exit 1` step |
| Promote is the owner's separate decision | MET | stated |

## Minor (not blocking)

1. "Run it again: it should report `staged 0, unchanged N`." That holds only if NSE has not rewritten a file in
   between. NSE does rewrite participant-OI files: the repo tracks `RELEASE_REWRITTEN` (`constants.py:53`). A rerun
   showing `staged 1` for a rewritten day is correct behaviour (a new staged copy), not a fault. Say so.
2. "(yesterday's participant-oi file appears in the evening)" is hard to read. A session's file appears that
   evening, and the range ends yesterday (UTC), so an unpublished day inside the range is rare and is a real NSE
   delay, not timing.
