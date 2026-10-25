# Judge 422: FL1-1 code, the 15:45 forecast lab report (story/fl1-forecast-lab at ad13de4e)

**Verdict: FAIL: 4 should-fix findings and 4 minor.** The gates are green and most of the design is sound. The
problem is in production: the match report and the late-seal alerts sit behind a check on today's official close,
which is almost never archived by 15:45. So in production they would almost never appear, and nothing tells anyone.

## What I ran and checked myself
- **Gates:** I ran them on ad13de4e merged with today's `main` (892b16b8, no conflicts; G13b is on `main` now).
  - 8,855 passed, 18 xfailed;
  - `ruff check` clean; 1,639 files formatted;
  - imports clean; record scan clean (7,276 files).
  - The builder reported 8,854 and 19 on its own tree; `main` has moved since. Strong evidence.
- **Channel IDs:** I checked them in Slack with a read-only channel search. #fno-forecast and #fno-intraday were
  created on 21 Oct, and their IDs match `fno/constants_channels.py` and DESK_DECISIONS row 263. #fno-desk's matches
  CLAUDE.md. The IDs are not quoted here, because `main`'s scan allows only #fno-desk's until FL1 merges. Strong.
- **Record scan:** it allows exactly these three IDs, and a fourth ID is caught (`test_patterns.py`). Strong.
- **O1 step:** `lab_close` is last, after `candles`. It is wrapped as `Alerted(LiveFrom(NotBefore(15:45)))`, with
  `live_from` null, and its receipts are limited to the lab's own Drive folder. I read the code; the wrapper order
  means a day before go-live does not wait. Strong.
- **18 planted mutations:** 14 caught, 4 survived (M3, M5, M13, M17). One more mutation survived on a path
  should-fix 4 needs (M16). Details are at the end.

## Findings

**Should-fix 1. The match report and the late-seal alerts almost never happen at 15:45.** Strong evidence: probe test
plus reading the code.
- `MatchSection.lines` (`match.py`) returns at once when `outcomes.close(underlying, day)` is None. It prints
  "today's official close is not archived yet; today's match comes in the next report" and returns **no alerts**.
- The builder's own open point 2 says the close is almost never archived at 15:45; judge 406.2 found the same: NSE's
  official close lands in the evening.
- The next report does not do what that line promises. `CloseReport.build` matches only the targets of its own `day`.
  So day d's targets are never matched, and their missing or late seals are never alerted.

My probe ran day d and the next session with closes archived only from the following day, as in production. The
setup had a late N1 seal for day d. Result:
- zero alerts on either run;
- neither report mentions the late forecast's issue day;
- both reports say "today's match comes in the next report".

That breaks criterion 2 (a late seal is recorded and alerted) and the owner's "matching report" (row 262), silently.

Fix:
- Check seals and send the missing or late alerts whatever the archive state; the seal check needs no close.
- Have each report match the latest target day whose close is archived and that has not been matched yet. In practice
  that is the previous session's targets, labelled with their date.
- Or put the evening-report option to the owner. Either way, the report must never promise a match it will not
  deliver.
- Add a two-day test like my probe.
- Open point 3 belongs here too: with no daily `pricerange score` step, G13b's scores are not refreshed, so even an
  archived close shows "no scored row yet". Name the step's owner and its place in `DAILY_RUN_STEPS` before go-live.

**Should-fix 2. Desk alerts that fail to send are reported as sent.** Strong evidence: probe.
- `LabClose.run` collects `self.desk.send(...)` but throws the outcome lines away. `POSTED` prints
  "{len(sent)} alert(s) to #fno-desk" whatever the outcomes said.
- With `NoAlertSender` (no token) and a late seal, the run printed `#fno-forecast: alert sent; 2 alert(s) to
  #fno-desk`, exit 0. No "alert NOT sent" line appeared.
- CLAUDE.md's routine step 3 depends on that line to post by hand with the connector. So a missing or late forecast
  alert is lost silently.
- Second, a rerun after a "not posted" failure posts the stored report and **sends every alert again** (the stored
  alerts are re-sent on each run). That breaks "alerted once".

Fix:
- Print each alert's outcome line.
- Count only alerts that were sent.
- Send the alerts once: mark them sent in the posted marker, or in a second marker written when they are sent.
- Test both cases.

**Should-fix 3. Criterion 7's membership check is not built.** Strong evidence: grep. Criterion 7 says "The bot's
membership in both new channels is checked with one read-only `conversations.info` call in setup". No code in `fno/`
or `tools/` calls `conversations.info`. Response 294 mentions it as needed, but not under "Open".

Fix: build it (a few lines in the routine setup, read-only, never a test post). Or record it as a named go-live check
with an owner in the story and the register. The step is off today, so this does not block safety. It does block a
claim that criterion 7 is met.

**Should-fix 4. Criterion 2 is not tested through G13b's real adapter.**
- My mutation M16 changes `G13bRanges.sealed` to pass `late=False` instead of G13b's `found.late`. All tests pass.
- `test_g13b_integration.py` uses only an on-time record.
- FL1's own seal rule (`sealed_at < 09:15 of the target day`) is weaker than the story's rule ("before the next
  session's 09:15"). For an N3 issue sealed two sessions late, G13b's `late` flag is the **only** guard against
  look-ahead. So that is exactly the path that must be tested. Strong evidence: mutation run plus reading
  `sealing.py`.

Fix:
- Add an integration case where G13b's `SealCheck` marks a record late (pushed after the next session's 09:15, but
  before the N3 target's open) and FL1 refuses and alerts it.
- Better still, make FL1's own rule the story's rule too.

**Minor.**
1. **Survived mutations M3 and M13:**
   - M3: today's issue is shown even if `sealed_at > now`. The test covers only `sealed_at=None`.
   - M13: a non-`ok` row is matched.

   Add one assertion each. M5 (the trust line counts only the first underlying) and M17 (no issue-day filter in the
   match) also survive. M17 is harmless today, because back-fill stops before `live_from`. Add a BANKNIFTY-only day
   to the trust test.
2. **Slack wording:**
   - T1's `UNKNOWN` says "(check #fno-desk)", so a lost post to #fno-forecast would point the owner at the wrong
     channel.
   - The POSTED line reads "#fno-forecast: alert sent" for a report.

   Pass the channel name to the wording.
3. **Where the channel constants live:** `fno/constants_channels.py`, not `fno/forecast_lab/constants.py` as the story
   says (row 263 said `fno/constants.py`). The choice is fine, since constants.py is at its size limit; update the
   story line.
4. **O11 (criterion 8):** the strict xfail with its reason is accepted for now (reasoning only). With no G13b issue in
   the replay, `lab close` there could only alert "no forecast was sealed". G13b's replay step plus `lab close` is a
   condition before `live_from` is set, not a later nicety. Record that in the story.

## What is good
- The port and adapter split matches the agreed design: FL1 never builds a Drive path, and G13b's shapes are pinned
  by a real-object integration test.
- The report is written once with an O9 receipt and read back with its SHA-256 checked. M8 caught.
- A rerun posts the stored text, never a rebuilt one (M12 caught).
- A "may have posted" outcome is never retried (M7 caught).
- Method versions are never pooled (M4 caught).
- Only live scores are counted (M10 caught).
- Exit codes follow O1's contract (M15 caught).
- No over-engineering: one `Sections` port waits for FL1-1b, and nothing more.

## Mutation table (each restored; run on `tests/forecast_lab`, `tests/record_scan`, `tests/daily`)

| Result | Mutations |
|---|---|
| Caught (14) | M1 FL1 ignores G13b's late; M2 seal `<` to `<=`; M4 pool methods; M6 no posted check; M7 may-have-posted not marked; M8 no SHA check; M9 direction flipped; M10 history not live-only; M11 closed day runs; M12 always rebuild; M14 a missing issue not alerted; M15 failure exits 0; M18 no target-day filter |
| Survived (4) | M3, M5, M13, M17 (minor 1) |
| Survived, on the criterion-2 path | M16 adapter drops G13b's late (should-fix 4) |

## Addendum 1: 8d2ad78e (response 295)

**Verdict: FAIL: 1 should-fix left. All 4 earlier should-fix findings and minors 1, 3 and 4 are closed; minor 2 is
closed on FL1's side.** The new design takes up any day not yet covered, so a missed or late day is no longer lost.
That design has one gap left.

**Gates, on 8d2ad78e merged with today's `main` (no conflicts):**
- 8,901 passed, 18 xfailed;
- `ruff check` clean; 1,651 files formatted;
- imports clean; record scan clean (7,293 files).

I re-ran them clean after my mutation run had overlapped the first run; the results were identical. Strong evidence.

| Finding | Answer | Judge (evidence) |
|---|---|---|
| SF1 match and seal checks behind the close | The seal check is separate and runs on the target's own day. Each report records `checked` and `matched` per underlying and day. Each report takes up every uncovered day of the last 5 regular sessions, from `live_from.lab_close` on. The header states the lag (owner's decision). | Accepted for seals and archive timing. My mutations all fail a test: earlier `checked` ignored, today not seal-checked, `first_day` ignored, window of 1, a day marked matched while not archived. One gap is left: new should-fix 1 below |
| SF1 extra (builder's own find) | `RegularSessions`: FL1 steps over regular sessions only, as G13b does; `lab close` runs only on a regular session | Accepted. A real bug around the 8 Nov muhurat session. Making a non-regular day pass fails a test |
| SF2 alert outcomes | A write-once `.alerted` marker written after the sends. "n of m alert(s) sent", plus one "alert NOT sent: reason: text" line per unsent alert. A rerun retries only the missing part. | Accepted. Mutations fail a test: outcomes treated as sent, skip on "posted" alone. A crash between the sends and the marker sends again rather than losing them; that is the right trade-off, and it is stated |
| SF3 membership check | `python -m fno lab channels`: `conversations.info` by GET, `is_member` from the answer; unknown never passes; exit 1 unless both channels pass; a named go-live check | Accepted. Mutations fail a test: POST instead of GET, "any channel" instead of "every channel". Not added to `routine_setup.sh` (O7's file): fine as a one-time go-live check |
| SF4 deadline and M16 | FL1's rule is the story's rule: before the next regular session's 09:15 after the issue day. G13b's real `SealCheck` marks a record late, through the adapter | Accepted. Moving the deadline one session later fails a test; M16 is killed (the builder's run) |
| Minors | M3, M5, M13 and M17 asserted; the report line reads "report to #fno-forecast: posted"; "check #fno-forecast before any repost"; story text fixed; criterion 8 is a condition before `live_from` | Accepted. T1's own `UNKNOWN` still says "(check #fno-desk)". It is T1's constant, rightly left to its owner and raised with the orchestrator |

**New should-fix 1. A day matched before G13b has scored it is marked `matched` and never shown with its scores.**
Strong evidence: probe.
- `CloseReport._match` adds a day to `matched` whenever `match_lines` returns lines. That happens as soon as the
  close is archived, even when every in-time forecast shows "no scored row yet (G13b scores after the close is
  archived)".
- My probe:
  - Report 1, on 26 Oct: 23 Oct's close archived, no scores. It matched 23 Oct with "no scored row yet" for N1 and
    N3.
  - Report 2, on 27 Oct: the N1 score for 23 Oct now exists and appears in the scoreboard. The report does **not**
    take up 23 Oct again, so its match lines are never shown.
- This happens whenever `price_range_scores` (judge 423) fails, runs late, or goes live after `lab_close`. The text
  even promises the scores will come, the same false-promise pattern as before.
- Fix: count a day as matched only when every in-time forecast for it has its score row, or none was in time.
  Otherwise leave it for a later report inside the 5-session window. Add a two-day test like my probe.
- Also add the go-live order to criterion 8's conditions: `price_range_scores` live no later than `lab_close`.

**My mutation run (11 new, each restored; `tests/forecast_lab`): all 11 caught.** Strong evidence. The builder reports
15 of 15 on its own set.

## Note: a6396ac3 (sent before addendum 1 reached the builder)
The change since 8d2ad78e: `MatchSection` takes `issues_from`, which is `daily.live_from.price_ranges`. It expects no
forecast from an issue day before G13b's first live day, and none at all while G13b is not live. Such a day says
"none expected (issued before G13b's first live day)" and raises no alert.

**Accepted** (strong evidence, read and checked against the new test). Without it, go-live would have sent false
"missing" alerts for up to 3 sessions. A truly missing N1 after that date is still alerted.

**Addendum 1's should-fix stands**: `_match` still marks a day matched without its scores. Two more items for the
re-submission:
1. **Merge conflicts:** a6396ac3 now conflicts with `main` in 5 files, because G13's score steps merged at d466e3d2:
   `config.yaml`, `fno/daily/wiring.py`, `tests/daily/test_day_run.py`, `tests/daily/test_steps.py` and
   `tests/health/test_desk_and_data_checks.py`. Merge `main` and re-run the gates.
2. **T1's text change (judge 424):** `test_lab_close.py:78` formats `UNKNOWN` without `channel`, which breaks once
   T1's fix is on `main`. Pass `channel=...` there.

## Addendum 2: 4857e539 (response 295, addendum 2)

**Verdict: PASS (lane 1). The builder may merge: pull, full suite on the merged tree, push.** The step stays off
(`daily.live_from.lab_close` null). The story's criteria 7 and 8 now list the go-live conditions:
- the membership check;
- O11's replay with G13b's issue;
- `price_range_scores` live no later than `lab_close`;
- `live_from.price_ranges` set to G13b's real first day.

**Gates:** on 4857e539 merged with today's `main` (no conflicts). The orchestrator asked about an intermittent
failure, so I ran the full suite twice:
- both runs 8,936 passed, 18 xfailed, **no failure in either run**: I saw no intermittent failure;
- `ruff check` clean; 1,654 files formatted;
- imports clean; record scan clean (7,297 files).

Strong evidence.

**Addendum 1's should-fix: closed.**
- `match_lines` now returns `(lines, complete)`. A match is complete only when every ok row of every forecast sealed
  in time has G13b's score row, keyed by forecaster, horizon and issue day.
- Until then the report shows one "archived but G13b has not scored all its forecasts yet" line, with no partial
  match lines. The day is not marked matched, so a later report inside the 5-session window takes it up.
- I re-ran my addendum 1 probe on this head. The 26 Oct report says 23 Oct is waiting for its scores; the 27 Oct
  report matches 23 Oct with the N1 score 12.50 in the match section itself. Strong evidence.

**My mutations (6, each restored): all caught.**
- the match always counted complete;
- a partly scored forecast counted complete;
- the issue day dropped from the score key;
- non-ok rows required;
- `issues_from` ignored;
- a forecast not sealed in time shown as matched.

**The merge with `main` (score steps, T1) checked.**
- `lab_close` is last in `DAILY_RUN_STEPS`, after `price_range_scores` and `candles`.
- `LIVE_STEPS` and `config.yaml` carry all four keys.
- `test_lab_close.py` passes `channel=` to T1's new `UNKNOWN`, so judge 424's merge condition is met.

**Left, not blocking:** O11's replay (criterion 8) is still a strict xfail and a go-live condition, owned by this
builder.

## Note: criterion 7's go-live evidence (orchestrator's run on 87bd21ce, 21 Oct)

**Ruling: criterion 7 is met for go-live. The owner does not need to add the scope first.**

**What the code's check reported.** `python -m fno lab channels` printed "membership unknown (missing_scope)" for
both channels and exited 1. The bot token cannot call `conversations.info`, which needs the `channels:read` scope.
That is the designed fail-closed answer, not a code defect: an unknown never passes.

**What I checked myself, read-only through the owner's Slack connector (strong evidence):**
- `#fno-forecast`, `#fno-intraday` and `#fno-desk` each have exactly two members: `@contact.exepex` and
  `@future_options_bot`.
- The latest #fno-desk messages are posted by "Future Options Bot" (bot `B0C89ER6VUM`): the O8 health report, A8's
  participant-OI line, A20a's master-file alert and the forecast routines. These are the repository's own alerts,
  sent with `FNO_SLACK_BOT_TOKEN`. So the token's bot is that member.

**Why that is enough.** Criterion 7 asks that membership be proved read-only, never with a test post. Membership read
through the owner's connector proves the same fact through another read-only call. It holds the same intent and needs
no scope change.

Two notes:
- Until the owner grants `channels:read` (optional), `lab channels` keeps exiting 1. It is a go-live check, not a
  daily step, so nothing in the daily run depends on it.
- If a bot is ever removed from #fno-forecast, the first failed post shows it: Slack's `not_in_channel` is a refusal,
  `lab close` exits 1, and O1 alerts it once.
