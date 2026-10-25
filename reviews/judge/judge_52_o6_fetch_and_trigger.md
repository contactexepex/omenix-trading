# Judge 52: story O6, fetch in GitHub Actions and reason in triggered routines

**Verdict: FAIL for now, with no defect found.**
- **What is built is sound:** the plants are caught, no secret is printed, and a late Actions start cannot corrupt the
  release-time evidence.
- **Why not PASS:** three criteria need time or the owner first:
  - criterion 1 needs 3 side-by-side sessions, starting 14 Oct;
  - the one real fire (criterion 2) needs the owner's routine token;
  - the 3 pm recorder is blocked on the owner's choice ((a) NSE, (b) Groww keys in GitHub, or (c) keep the routine).
- **Minor findings:** 1.

**What I judged**
- **Repository:** trading at 93fa2ee (O6 c0e2663).
- **Claims:** `reviews/claude/response_58_o6-fetch-and-trigger.md`.
- **Story:** `docs/stories/O-operations.md`, O6.

## Checks run by the judge

```
$ python -m pytest -q tests/pipeline tests/research_data/test_release_compare.py      32 passed
$ wc -l fno/pipeline/*.py                                                             601 lines over 11 files (largest under 110)
```

**My plants (each reverted; `git status` clean):**

| Plant | Result |
|---|---|
| Dispatcher ignores the "fired" record (fires every run) | **caught**: 3 failing |
| Dry-run routine ignores the "processed" record | **caught**: 1 failing |

**A late Actions start (GitHub's cron often runs late):**
- The 17:11 IST watch may start after NSE published.
- A8's rule counts a day as measured only when the file was seen **absent and then present**
  (`release_times.py`). So a late first check that finds the file already there adds no release time. **Safe.**
- The Actions log also goes to its own folder, and the rule reads only the routine's log until the owner switches.

**Secrets in the workflows:**
- Secrets enter only as `secrets.*` environment variables. Nothing echoes them.
- The `${{ }}` expressions in `run:` lines are GitHub's own ids (run id, attempt, step outcomes), never user text.
- The fire command passes the watch log's lines as quoted arguments.
- **No broker key in GitHub.**

## Criteria

| # | Criterion | Judge's evidence | Result |
|---|---|---|---|
| 1 | Migrated jobs run on schedule with the same outputs (at least 3 sessions side by side) | The release check (17:11 and 22:45 IST) and the sweep (05:37 IST on the 1st) are built with the routines' own commands; `participant-oi compare` is tested. No session has run yet. The 3 pm recorder is not migrated (owner question). | NOT MET YET |
| 2 | Fires exactly once per batch and version; nothing new fires nothing; a republished file fires again | The tests pass, and my 2 plants are caught. The one real fire waits on the owner's token. | PARTLY (real fire pending) |
| 3 | A failed fire, an expired token or a refused upload posts one clear line | Tests (401, 403, 429, network, missing setting, Drive refusal), and the step exits 1 | MET |
| 4 | No secret value in any file or log; no broker key without approval | Workflows read above; record scan clean; none added | MET |
| 5 | Interfaces, wiring only in composition roots, file size | `RoutineTrigger`, `BatchFinder` and `RawFileStore` adapters; the concrete classes sit only in `fno/pipeline/wiring.py`; all files small | MET (minor 1) |

## Minor 1: the new composition root is not listed in CLAUDE.md

- CLAUDE.md names the only places concrete classes may be wired: `composition.py`, `storage/wiring.py`,
  `risk/wiring.py`, `forecast/wiring.py` and `filings/wiring.py`.
- `fno/pipeline/wiring.py` is a sound per-area root, like the others, but the rule must name it.
- **Expected:** add one line to CLAUDE.md, and check that `tools/check_imports.py` treats it as a root.

## The owner's 3 pm recorder question (my view, reasoning only)

- **Option (a), NSE public data, is the safer choice:** no broker credentials in a public repository's Actions.
- It needs a new dataset (never mixed with Groww's) and a changed freshness rule: day volume plus one page time,
  instead of a per-contract last-trade time.
- That changes what the recorded history means, so it must be stated in A4's story and measured side by side before
  any switch, as the builder proposes.

---

## Addendum 1 (judge E, 15 Oct 2026, 17:50 UTC): re-judge on main's run history. Still FAIL; the cause is GitHub's schedule, not the code

| # | Result now | Evidence (mine) |
|---|---|---|
| 2 | **MET** | The real fire happened, end to end. Run 38762893901 (15 Oct) logged "4 batches in window, 1 fired to dry-run, 3 already fired, 0 failed". In Drive, `pipeline/fired/.../participant-oi/2026-10-15` was written at 15:44:38 UTC, then `processed/` and `derived/` at 15:45:13-15 UTC: the routine ran about 35 s after the fire. The same holds for 14 Oct, and on 13 Oct for the batches of 8, 9, 12 and 13 Oct. Each batch fired once ("3 already fired"). Strong |
| 1 | **NOT MET** | GitHub starts this repository's scheduled runs hours late and skips most of them. Strong (Actions API) |

**Criterion 1 in detail:**
- **3 pm recorder (`quote-recorder-nse.yml`, cron 14:20 IST).**
  - Both scheduled runs started after the market closed: 14 Oct at 19:34 IST and 15 Oct at 19:12 IST.
  - Both runs failed. Both days' `.canonical` is `none` (fe695efc). 0 sessions recorded, so it cannot be compared with
    the routine.
- **Participant-OI release check (cron 17:11 and 22:45 IST).**
  - The scheduled runs started about 4 h late: 14 Oct at 21:27 IST and 15 Oct at 21:13 IST.
  - The second runs (14 Oct 02:14 IST, 13 Oct 03:22 IST) were cancelled after about 6 h.
  - `participant-oi-watch.yml` (28 slots a day) ran once a day: 2 runs in 2 days.
  - So the Actions copy never sees the file absent and cannot measure a release time. `participant-oi compare` gives
    "0 of 4 days the same".
  - The file itself matches the routine's on 14 and 15 Oct (same SHA-256 and Last-Modified). 13 Oct is not comparable:
    the routine never saw that file.
- **Monthly sweep:** first run on 1 Nov.

**What is still missing (plainly):** no code fix can make GitHub's cron keep a time window. O6's premise holds for
jobs with no time window, and fails for timed captures. It needs a scope decision, for the orchestrator and the owner:
- **(a) Recommended. Keep the timed jobs on scheduled routines** (the 3 pm capture already runs from the 14:33
  routine). Narrow criterion 1 to the downloads with no time window: the participant-OI file, matching on 3 sessions
  (14 and 15 Oct match; one more is needed), and the sweep on 1 Nov.
- **(b) Have each routine start its workflow on time** (`workflow_dispatch`) instead of cron.

Until then, `quote-recorder-nse.yml` fails every day and alerts #fno-desk for a capture that cannot succeed.
Disabling it is the owner's call; it is noise now.

**Verdict: FAIL** (criterion 1); criterion 2 now MET.
