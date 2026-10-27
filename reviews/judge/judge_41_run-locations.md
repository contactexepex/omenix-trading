# Judge 41: `docs/RUN_LOCATIONS.md`, lane-2 check, judge #1

**SHA:** `a924f6c9886c66a6364ea1079e8a7e8fadd66140` (`story/RUN-LOCATIONS`). The doc under review is the new
`docs/RUN_LOCATIONS.md` (55 lines). The branch also carries R1d3, which judge_38 already reviewed.
**Verdict: FAIL, two factual fixes (text only).**

## Checked and right (strong evidence: every workflow file read at this SHA)

**Section 1.**
- All 14 files in `.github/workflows/` are listed.
- Every cron matches its file's comment:
  - circulars `30 2-16` (08:00-22:00 IST);
  - data-checks 09:41;
  - filings every 6 h;
  - flow-history 21:30 and 07:15;
  - flows-download 21:10;
  - fo-masters 06:00, 07:45, 11:15 and 18:45;
  - global-cues 03:41, 04:41 and 14:11;
  - index-closes 21:11, 07:41 and 11:41;
  - participant-oi-release 17:11 and 22:45;
  - participant-oi-sweep on the 1st at 05:37;
  - participant-oi-watch 16:37-23:22 every 15 minutes;
  - quote-recorder-nse 14:20;
  - vix-history 07:11.
- `pipeline-staging.yml` has no `cron:` and runs `stage` / `promote`.

**13 versus 14 is right:** 13 have a schedule, and 1 is manual only.

**Section 2.** Every "from" source exists and says what is claimed:
- `GROWW_CANDLE_ROUTINE.md:26` ("the deferred 3 pm Groww quote recorder ... a session, not a workflow");
- `groww_sign_in.py:8-9` ("A16's 7 fires", "the daily run's Groww children");
- `close_read/cli.py:1` (O1's `close_read` 15:40, `close_recheck` 16:00);
- `preopen/cli.py:1` (the 08:36 IST routine), and `preopen_cli.py:1-4` and `preopen.py:1-2` (A22's routine,
  about 08:36 to 09:11);
- `nsdl_backfill.py:1` ("the one-time back-fill").

No workflow runs `closes read`, `preopen record`, `global-cues preopen` or the NSDL back-fill (grep). The section is
labelled inferred, which is honest. "By hand" for NSDL is an inference within that label. The command is
`flows nsdl-backfill`, per `flow_history/cli.py`'s `NSDL_SUMMARY`; "`flows ... nsdl`" is vague.

**Section 3, second bullet.** Sessions adopt a change only when they next fetch `main`, and the owner confirms at
cutover. Both are correct.

## Required to PASS

### 1. The pause-log sentence names the wrong thirteen

Section 1 says "the last step of thirteen of them commits the persisted-pause log". The thirteen that do are not the
thirteen scheduled ones:
- `data-checks.yml` (scheduled) has **no** `commit_pause_log` step;
- `pipeline-staging.yml` (manual) **has** one.

Fix: "twelve of the thirteen scheduled workflows (all but `data-checks.yml`) and `pipeline-staging.yml` end with
`ops/commit_pause_log.sh`."

### 2. Section 3's first bullet contradicts section 2

"Persistence of an NSE pause across runs needs a committing step, which only the workflows in section 1 have" is false
as written. Section 2 itself says the candle backfill "commits its own rows and manifests". `preopen_cli.py:3-4` pushes
before A22's push. The Claude routines commit too.

What is true: only the section 1 workflows (minus `data-checks.yml`) run `ops/commit_pause_log.sh`, so only they carry
the pause log into the next run. A session commits its own outputs but not the pause log, unless its routine adds that
step.

The difference matters at cutover. The owner could add the pause-log commit to a routine; the doc as written says that
is impossible.

## Not blocking

The "What it runs" column omits some commands:
- `quote-recorder-nse.yml` also runs `quotes compare`;
- `participant-oi-release.yml` also runs `data-librarian participant-oi` and `participant-oi due-day`;
- `flow-history.yml` also runs `flows table`.

The column reads as a summary, but "verified" invites a complete list. Adding them or calling the column "main
commands" fixes it.

## Hard lines

This is a docs-only change: no code, data or service is touched. No secrets: the three known `LICENSE` email findings
predate this change and are unrelated.

## Addendum 1: round 2, 5f4fd8e: PASS

The `docs/RUN_LOCATIONS.md` diff from a924f6c is +10/-7. I checked it against the files at 5f4fd8e.

1. **The pause-log set: fixed.** `git grep -l commit_pause_log -- .github/workflows` lists 13 files: every one but
   `data-checks.yml`, so twelve scheduled workflows and `pipeline-staging.yml`. The doc now says exactly that.
2. **Section 3: fixed.** Only those workflows run `ops/commit_pause_log.sh`, and the sessions commit their own outputs.
   "None does" (no routine runs the pause-log step) is supported as far as this repository can see. Outside
   `.github/`, `commit_pause_log` appears only in the R1b2 story, this doc and two tests. No `ops/` or routine document
   calls it.

**Nits: fixed.** The column is now "Main commands". `flows nsdl-backfill` is right: `flow_history/cli.py:33` adds
`nsdl-backfill` to the parser that `fno/ingestion/cli.py:167` mounts as `flows`.

**A wording nit, not blocking.** Section 3 says "only the section 1 workflows run `ops/commit_pause_log.sh`".
`data-checks.yml` is in section 1 and does not. The paragraph directly above says so, so a reader is not misled.

**Verdict: PASS (strong evidence).**
