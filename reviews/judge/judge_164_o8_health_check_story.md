# Judge 164: story O8, the daily health check (story text, quality rule 1; judge F)

**Commit judged:** `2f3f777511d8dd42a7e78982ecddf7bccc627ea4` on `story/o8-health-check` (story
`docs/stories/O8-health-check.md`, claims `reviews/claude/response_153_o8-health-check.md`, work-register row NF step
6). Builder: session_012eM7Ti8ZaSVowgyMkgoGmM. Lane 1 (new workflow, Slack).

**Verdict: FAIL (text).** No blocking finding. 5 should-fix, 5 minor. The design is sound and mostly simple: one job,
one message, last N sessions, F1's `PushReceipts`, `none` as a miss, counts from constants. The fixes are text only
and make the design simpler, not bigger.

**Gates at the commit (docs-only change):** `pytest` 5,861 passed; `ruff check` clean; `ruff format --check` clean;
`tools/check_imports.py` clean.

## Should fix

1. **Deadline ownership is stated wrong both ways (strong evidence).**
   - 15:13 already has an owner: `fno/ai/timing.py` `LATEST_START = time(15, 13)` ("the capture pulls for the snapshot
     until 15:13 IST at most"), imported by `fno/pipeline/capture_gate.py:21` and `fno/ai/fire.py:24`. The story's
     "the one deadline no module owns ... is a named constant here" would make a third copy. Import `LATEST_START`.
   - Four deadlines have no owning module: A8 "by 23:30", closes "by 12:00 next day", panel "by 13:00 next day",
     FII/DII "by 23:59". I grepped every `time(...)` in `fno/`: none of these exists (23:30 is only a workflow comment,
     `participant-oi-release.yml:13`). So "each deadline is imported from its owner" is false for them. Fix: name
     them as health-owned constants, each with the cron it is derived from, and list them for step 5.
2. **N = 5 does not fit GitHub's one-week log (strong evidence).** `ACTIVITY_PARAMS` uses `time_period=week`
   (`fno/ai/receipts.py:19`, 168 hours). I simulated every daily 17:51 run of 2025 with the real calendar
   (`nse_sessions.csv`): the oldest session's 15:13 push is more than 7 days old on **86 of 365 runs** (N = 4: 12).
   That happens in every holiday week, so about one run in four would carry `unknown` lines in normal running. The
   claim "N = 5 fits" (response 153, choice 1) is wrong. Fix (builder's choice, keep it simple): a window that stays
   inside the log, for example sessions in the last 6 calendar days, and a criterion that a holiday week gives no
   `unknown` from log age.
3. **Criterion 1 contradicts the window rule (strong evidence, reading).** The window is "sessions on or before the
   IST date of the run". A run at 03:10 on D+1, when D+1 is a session, includes D+1 and drops the oldest session, so
   it does not check "the same last N sessions". A test written to criterion 1 fails, or the code is bent to pass it.
   Fix: require what matters, that session D is in the window for every run from D 17:51 up to the measured lateness
   (5 h on 14-15 Oct, `conversations/2026-10-15.md:636`), and define the window once.
4. **What decides `late` differs per row but is not said (some evidence, reading).** Scope says on time "uses
   GitHub's push time ... never a commit date". The table uses the file's own times for two rows: forecasts by
   `generated_at` 15:15, the desk by the run log's `decisions` finish. The evening rows say "present by", without
   saying present by what time measure. Fix: one column in the table, "time used: push receipt / in-file time
   (protocol rule)". Then criteria 2 and 4 are testable per row.
5. **Each problem repeats on five daily messages (strong evidence).** One line per (check, session) over a 5-session
   window repeats every miss for 5 days. The NSE canonicals hold `none` on 14 and 15 Oct (verified on main), so the
   first runs would already carry repeated NSE lines, and every other bad day adds more. Fix: one line per check,
   with its bad sessions listed ("NSE recorder: missed (none) 14, 15 Oct"). This is simpler, not bigger.

## Minor

1. A book stopped by `fno/ai/stop_rule.py` is not fired, and the fire log records `fired: false` with its reason
   (`fno/ai/fire.py:62-65`). The story would show it as `missed (never ran)`. Use the fire log's reason as the detail.
2. Table label "NSE recorder (Actions, 14:20)": on 15 Oct the owner moved NSE into the 14:33 Claude routine and kept
   the Actions job as a fallback (handover section 12; `conversations/2026-10-15.md:628-633`). This changes the label
   only, not the check.
3. Watcher: limit "a calendar day with no row" to the window (the first run has no history), and say what "without
   duplicating the report" means in criterion 6.
4. `not expected: closed day` cannot arise, because closed days never enter a window of sessions. It arises only from
   muhurat, `live_from` and the desk's `skipped` step. Say so, so the tests test something real.
5. The A16 row has no deadline. Name it, or say that A16's own per-mark status is final.

## Notes (no action)

- F1's reader stops at 10 pages × 100 pushes (`receipts.py:21`). `main` had 693 first-parent commits in the last 7
  days, so the cap is near. That limit belongs to F1 and is shared; a "Known limits" line is enough.
- P2's future `health` read model (`docs/stories/P-publishing.md:125`) could later read O8's output. It is no
  duplicate today. No other health or overdue checker exists in `fno/` (grep).
- Scope is bigger than the handover's "about 50 lines", but the orchestrator widened it (recorder, forecasts, desk,
  A16, data jobs). Acceptable, if the build stays lean.

## Per-criterion check (text)

| Criterion | Judge's check | Result |
|---|---|---|
| 1 Right sessions whenever it runs | Window rule and the 03:10 case contradict (S3); log coverage fails on holiday weeks (S2) | NOT MET |
| 2 Each status from its evidence | Six statuses defined, boundary at the deadline included; the time basis per row is missing (S4) | PARTLY |
| 3 Counts and deadlines from owners | Count verified: (FORECASTERS − AI_BOOKS) × 5 = 4 × 5 = 20 (`constants.py:162-171,213`); 20 rows on 14 and 15 Oct. Deadlines wrong (S1) | PARTLY |
| 4 Push times only from GitHub | `PushReceipts.received_at(commit)` fits (`receipts.py:34-37`), with the ancestry rule for merge pushes; `ReceiptUnknown` maps to `unknown`, good | MET (text) |
| 5 One message | One message, a FAILED line, and a no-token print; repetition (S5) | PARTLY |
| 6 Watcher watched | Sound; bounds unclear (minor 3) | MET with minor |
| 7 Workflow | Cron 17:51 IST (12:21 UTC); `contents: write`; commits one file; `GITHUB_TOKEN` read as in `forecast-capture.yml:68` | MET (text) |
| 8 Real sample | Planned; the `none` fact verified (both NSE canonicals hold `none`) | MET (text) |
| 9 Engineering rules | Interface, own wiring, CLAUDE.md list named | MET (text) |

## Claims vs reality

- Table evidence (strong, checked): `NONE_MARKER` (`recorder.py:48`), `GENERATION_DEADLINE = time(15, 15)`
  (`schema_v2.py:18`), the 15:15 commit and 15:30 reveal deadlines (`fno/ai/timing.py`), `decision_deadline: "15:12"`
  (`config.yaml:161`), 26 marks (`intraday/slots.py:9`), `GOOD/MISSED/LATE` (`intraday/status.py:16`),
  `build_alert_sender` (`composition.py:153`), calendar (`fno/research_data/calendar.py`). All true.
- "15:13 lives only in the workflow YAML": false (S1).
- "N = 5 fits the one-week log": false (S2).
- "`journal/runs/` and `research/data/intraday/slots/` do not exist on main": true.
- "NSE canonicals for 14 and 15 Oct hold `none`": true.
- Work register: row NF step 6 moved to this builder, as the orchestrator assigned. No duplicate row.

## Project rules

- Simplicity rule (owner, 15 Oct): S2, S3 and S5 happen in normal running (holiday weeks, the measured cron lateness,
  the NSE misses already in the data). Each fix removes noise and adds no new mechanism. No finding asks for a guard
  against an unlikely case.
- Lane 1 is correct. Gap list: every handover section 11 and response 144 item 18 requirement is mapped. No gap.

## Addendum 1: revision 2 at c5bbfbd2 (story text)

**Verdict: PASS (text).** Code may start. The branch diff against main is only the story, response 153 (addendum 1),
its README row and the work-register row. No other file changed.

| Finding | Fix in revision 2 | Judge's check | Result |
|---|---|---|---|
| SF1 deadline owners | `LATEST_START`, `GENERATION_DEADLINE`, `receipt_deadline` and the desk config are imported. Four health-owned constants (`A8_RELEASE_BY`, `INDEX_CLOSE_BY`, `PANEL_DAY_BY`, `FLOWS_BY`) carry their cron sources and are listed for step 5. Criterion 3 greps that they are the only time literals in `fno/health/` | Each cron source cited is the real line (`participant-oi-release.yml:13`, `index-closes.yml:18`, `panel-days.yml:19`, `flows-download.yml:10`) | Fixed |
| SF2 log coverage | The window holds the sessions from 6 calendar days before the run's IST date up to that date | By construction, the oldest push needed is at most 6 d 8 h 47 min old (15:13 on the first day, read by 23:59 on the last). Later pushes (evening jobs, late pushes) are younger, so the window is inside the 168-hour log on every run. Criterion 1 also replays 2025 | Fixed |
| SF3 criterion 1 | The window is defined once. D is in the window from D 17:51 to D+6 23:59 and out at D+7 00:01, with the boundaries tested | Consistent with the window rule | Fixed |
| SF4 time basis | A per-row column: push receipt, or in-file time (forecast `generated_at`, desk `finished_at`) | Criteria 2 and 4 are now per row | Fixed |
| SF5 repetition | One line per check, listing its bad sessions. Criterion 5: "never one per (check, session)" | Testable | Fixed |
| Minors 1-5 | The fire-log reason, the NSE label, watcher bounds (window and after the first row), `not expected` narrowed, A16's status final | Each is in the text and in criteria 2 and 6 | Fixed |
| F1 page-cap note | Added to Known limits | Shared limit, stated | Accepted |

**Note for the code review (no action now):** the AI row says the reveal and forecasts must be "present" but gives no
time for them. The 15:30 `REVEAL_DEADLINE` exists in `fno/ai/timing.py` if lateness is ever wanted. Presence is
enough under the simplicity rule.
