# Judge 167: story LR1 text, the weekly post-mortem v1 (quality rule 1; judge C)

Date: 15 Oct 2026 (UTC). Branch `story/lr1-weekly-postmortem` at **cb632340b67d33c0f88c44e42f4d93e91ffa2102**
(`docs/stories/LR-learning.md`). Builder session_0145TfSwzmpk6MBrH92f5h4G; claims response 162.
- Judged under the owner's "keep the design simple" rule and the coordination rule.
- Judged with the builder's recommended options: retire G4's Monday post, the AI writer later, Saturday 10:41 IST.

## Verdict: PASS (text); 3 notes

| Check | Status | Evidence |
|---|---|---|
| No second scoring path | MET | The story reads G4's report through the existing `weekly_summary` (`fno/forecast_scoring/score_report.py:99`), G8's committed `research/forecasts/v4_scores/<d>.json` with its `EXPLORATORY` line (`fno/forecast_scoring/v4/records.py:16`), M1's `WeatherRecords` (`fno/weather/records.py:21`) and G7's `big_move_outcomes` (`fno/forecast_v4_rules/series.py:67`). All exist on `main`. "New this week" is a subtraction of two committed counts. Test 7 fails if `fno/learning/` imports G4's or G8's scoring modules: a sound guard |
| Three sections | MET | Forecasts (G8, then G4 unchanged), weather (colours, label, status, GREEN-day misses, counts per colour, M1's own RED share) and data health (3 pm marker and lateness, card delivery, A16 session count, one completeness line). Each has an empty-state line, and V1, V4 and V5 show G8's status, never an error |
| Never decides a trade | MET | Criterion 12's AST test forbids imports from `fno/desk/`, `fno/books/`, `fno/risk/` and `fno/checks/`. The text says "reports and never decides a trade" |
| 13 criteria | MET | Each is testable and tied to a test in the plan: dry run, write-once, Slack failure, equality with the named report, exploratory line, holiday week, `test: true` cards, the workflow's schedule, secret and commit scan |
| Coordination | no duplicate | No other row of `docs/WORK_REGISTER.md` builds a weekly report. S4 (the monthly report) is slice C, by design apart |

### The pending owner choices

- **Retire G4's Monday post (recommended): the verdict holds.** If the owner keeps it, the same `weekly_summary` text
  goes to #fno-desk on Monday (`forecast-scores.yml`, cron `41 3 * * 1`) and again on Saturday: one function posting
  twice. Under the coordination rule that is a duplicate. With that option LR1 must show the G4 part as one line
  naming the Monday post, not the text again. Either way, the workflow change to G4's cron is lane 1 and belongs in
  this story's code.
- **AI writer later: the verdict holds.** The text is code-built lines, so there is no AI cost and nothing for an
  advocate yet.
- **Saturday 10:41 IST: the verdict holds.** G4 scores daily at 22:41 IST, so Friday's report is the latest. LR1 runs
  G8's own `report --as-of <Saturday>` first. The owner's routine-timing rule (setup well before any market time) is
  not touched on a Saturday.

## Notes (none changes a trade)

1. **One writer of `research/forecasts/v4_scores/`.** Today no workflow writes it, and LR1's job would be the first.
   If G8 later gets its own schedule, only one job may write that folder. Record it in the register now: the LR1 row
   says "writes v4_scores on Saturdays until G8 has its own job", so the G8 builder sees it.
2. **Reuse readers that exist (DRY).** A16's session rows already have a reader, `RvTable`, used by G8
   (`fno/forecast_scoring/v4/wiring.py:36`, `INTRADAY_FOLDER`). The 3 pm canonical marker is already read by the
   quote recorder (`QuoteSnapshotRecorder.canonical`). Use them behind the new interfaces rather than new parsers of
   the same files.
3. **Today's data.** `research/forecasts/v4_scores/` and M1's weather folder do not exist on `main` yet. The first
   Saturday's report will print mostly "no v4 score report yet" and "missing" lines. That is correct by the story's
   empty states; the owner should expect it.

**Verdict: PASS for cb632340b67d33c0f88c44e42f4d93e91ffa2102** (story text), with the builder's recommended options.
Code may start. It posts to Slack and adds a schedule (lane 1), but decides no trade, so rule 9 applies only if the
orchestrator says so.

## Note (15 Oct 2026): on hold for a revised text

The owner chose the AI writer and the devil's advocate **in v1**, not later. So the PASS above, which assumed "AI
writer later", does not cover the coming revision. The other two answers match the assumptions: retire G4's Monday
post, Saturday 10:41. I will judge the revised SHA as an addendum here. Points I will check there:
- BG1's budget meter counts the AI cost;
- the AI text never changes a committed number (it may only reword or comment on code-built lines);
- the advocate's checks;
- the week's post still goes out when the AI part fails.

## Addendum 1 (15 Oct 2026): revision 1 at 86f46232b28b8e583b64706d273143ccc0b49007

Owner answers (relayed by the orchestrator): one weekly report, so G4's Monday post is retired in LR1's change; the AI
writer and the devil's advocate are both in v1, the simple way; Saturday 10:41 IST. The forecasts, weather and data
health sections are unchanged and stay MET as above.

## Verdict: PASS (text); 1 note

| My hold-note point | Status | Evidence |
|---|---|---|
| The AI cost is counted | MET | The writer routine records its run with F8's `budget record-usage --self-timed --purpose books_and_roles` (`fno/budget/cli.py`). It is not fired when BG1's month signal (`accounting/budget/<YYYY-MM>_signal.json`, `fno/budget/signal.py`) is `stop` |
| The AI never changes a number | MET | The code-built lines stay the source of truth and are posted every time. The prose is shown only if the code advocate passes four rules: the SHA line ties it to the committed lines; at most 150 words with no link, mention or code block; every number in the prose copied from the lines; no number written in words |
| The post goes out if the AI part fails | MET | A `stop` signal, missing secrets (`UnconfiguredTrigger`), a failed fire (`FireFailed`), no prose by 11:41, or any failed advocate rule each give the lines alone plus one line naming why (criteria 15-17) |
| No second AI caller | MET | The writer is fired through the existing `RoutineTrigger`/`RoutineFireTrigger` (`fno/pipeline/trigger.py`), as the AI books do (`fno/ai/fire.py`), with a pointer holding only the Saturday and the lines' SHA-256. All named classes exist on `main` |
| Only the publisher reads the prose | MET | Criterion 18's AST test |
| Merge-tree with `origin/main` | MET | No conflict |

**Choosing a code check, not a second AI call, for the advocate is right.** It is cheaper and certain for "numbers
copied exactly". An advocate that argues in words is T3 (slice B), as stated.

## Note (does not change a trade)

**Rule 3 must compare whole number tokens, not substrings.** As written ("appears as the same text in the lines"), a
substring match would let a prose "4" pass because "40%" or "2026-10-14" contains it. Extract each number token from
both texts with the same pattern (digits with their decimal point, sign and `%`, dates as one token) and check the
prose's tokens are a subset of the lines' tokens. Add one test: prose "4 sessions" against lines holding only "40%"
fails. Test 11's 41% vs 40% case does not cover this.

**On coordination:** the builder sent me this SHA directly, as the orchestrator said it would. I told the orchestrator.

**Verdict: PASS for 86f46232b28b8e583b64706d273143ccc0b49007** (story text). Code may start.

## Note 2 (15 Oct 2026): addendum 1's PASS is superseded

The owner chose, in v1, both the code number check **and** a second, objecting AI: the devil's advocate, built as the
reusable piece T3 will use later. So addendum 1's PASS on 86f46232, whose advocate was code only, is superseded. I will
judge the builder's next SHA as addendum 2. The same four points apply, now also for the second AI:
- its cost is counted and it stops on BG1's `stop`;
- it can only object, never change a number or a line;
- the week's post goes out when it fails;
- it is built once, as the piece T3 reuses, not as a second AI caller.

## Addendum 2 (15 Oct 2026): revision 2 at 2c67480b211c626688da6cd53d766014568e9953

The owner's choice is that the devil's advocate is both the code number check and an objecting AI, built once for
T3. The forecasts, weather and data health sections are unchanged and stay MET.

## Verdict: PASS (text); 1 note

| Note 2's point | Status | Evidence |
|---|---|---|
| Cost counted; stops on BG1 `stop` | MET | One fire, one F8 `record-usage --self-timed` row for the routine's role bundle. BG1's `stop` skips both steps. BG1's signal is all-or-nothing at 100% (`stop_ai_roles`; `AI_ROLE_STOP_ORDER` in `fno/budget/constants.py` is a listed order, not a per-role switch), so one routine with one record fits it |
| It can only object | MET | Objections are their own labelled section ("they change no number and decide no trade"). `ObjectionCheck` enforces: the SHA line; 1 to 5 objections of at most 40 words, each tied to an existing `[L<n>]` line; no link, mention or code block; numbers only as whole tokens of the lines; none in words. Only `publish.py` reads the prose and objection paths (AST test). Neither `fno/learning/` nor `fno/advocate/` imports desk, books, risk or checks |
| The post goes out when it fails | MET | No file, a failed rule, `stop` or no configuration give "advocate not run: <reason>" and change nothing else. The lines are posted in every case (criteria 15-17, 20) |
| Built once, for T3 | MET | `fno/advocate/`: the `Advocate` port, one adapter `RoutineFileAdvocate`, `ObjectionCheck`, and `NumberCheck` with the single tokenizer. `publish` depends only on the port (criterion 21, test 15). The register row "Devil's advocate objections" says T3 (#105) reuses it and never builds a second |
| My addendum-1 note | MET | Rule 3 compares whole number tokens from one regex. Test 13: "4 sessions" against "40%" fails |
| Known limits | ACCEPTED | One routine writing then objecting is less independent than two (the owner chose one routine for a small setup; T3 may revisit). Objections are checked for form and numbers, not fairness; they are labelled AI and change nothing |
| Merge-tree with `origin/main` | MET | No conflict |

## Note (does not change a trade)

`docs/stories/T-cards.md:53` lists "the devil's advocate (T2, T3)" as out of scope. When T2 or T3 is written, its text
must name `fno/advocate/` as the one objecting AI to reuse, as the register now says, so no second one is built.

**Verdict: PASS for 2c67480b211c626688da6cd53d766014568e9953** (story text). Code may start.

## Addendum 3 (15 Oct 2026): LR1 code at b7b0ed49fd57b15ea7cbc3184cc00ce9f5ba8849

Claims: `reviews/claude/response_167_lr1-weekly-postmortem.md`, "Code round". The builder sent the SHA to me directly.
Judged on the real paths.

### Gates

- 5,971 passed (the builder's figure); ruff, format and imports clean.
- `merge-tree` with `origin/main`: conflicts in `CLAUDE.md` (both sides add a composition root to the same list: keep
  both lines) and `reviews/claude/README.md` (index rows).

## Verdict: PASS (code); 1 note

| Real path | Status | Evidence |
|---|---|---|
| The live dry run writes nothing | MET | `python -m fno postmortem weekly --week-ending 2026-10-17` on the repository printed the report, and `git status` stayed clean. The G4 part is `weekly_summary` of `research/forecasts/scores/2026-10-15.json` verbatim. The capture lateness lines are 2.7 and 10.7 minutes after 14:55 for 14 and 15 Oct. The weather rows show M1's back-fill labels. A16: "not enough data yet (0 of 20)". Each is a plain empty state where data is missing |
| G8's report runs in the job without Drive | MET | I ran `forecast-v4-scores report --as-of 2026-10-17` with every `FNO_GDRIVE_*` unset: exit 0, report written (removed afterwards). The new workflow passes no Drive settings, and it does not need them |
| Whole-token number rule | MET | `fno/advocate/numbers.py`: one `NUMBER` pattern for both texts (`40%`, `-0.0042`, dates and times as single tokens; `[L12]` is not a number, because of the lookbehind), a subset test, and number words refused. Tests 13-14 include "4 sessions" against "40%" |
| Only the publisher reads the AI files | MET | `publish.py` (summary) and `routine_file.py` (objections, through the `Advocate` port) are the only readers. `test_boundaries` forbids desk, books, risk, checks and G4/G8 scoring imports |
| The lines always post | MET | `Publisher.publish` sends summary or reason, objections or "advocate not run", then the lines in one message. The publish record is written once, and a second publish says "already posted" |
| G4's Monday post retired | MET | `forecast-scores.yml`: the Monday cron, the `WEEKLY` env, the summary input and the `--send` step are removed. The daily 22:41 IST scoring stays |
| Workflow | MET | Saturday 05:11 and 06:11 UTC (10:41 and 11:41 IST). Build: G8 report, lines committed and pushed, then the separate `postmortem fire` once the lines are on `main`. Publish: pull first. Only `FNO_SLACK_BOT_TOKEN` for Slack, the two routine secrets, the public-record scan on, no `--no-verify`, and an alert when the job fails |
| Secrets | MET | The two names are in `fno/constants.py`, and the token is classed as a live credential in `tests/live_credentials.py` |
| Coordination | MET | Register rows for LR1 and for the one objecting AI (T3 reuses it). `CLAUDE.md` lists the new composition root |

## Note (does not change a trade)

**The checklist must say the routine pushes before 11:41.** If the routine's two files arrive after 11:41 IST, publish
posts "summary: no summary received" and "advocate not run", and the late files are never posted (once a week, no
retry). That is the stated design. The owner checklist should say plainly that the routine must push before 11:41, so
a slow run is understood.

**Verdict: PASS for b7b0ed49fd57b15ea7cbc3184cc00ce9f5ba8849** (code). It merges with `CLAUDE.md`'s list keeping both
lines. Rule 9 is the orchestrator's call: it posts to Slack and adds a schedule, but decides no trade.
