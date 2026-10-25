# Project instructions

This repo is **Omenix F&O** (part of Omenix; the dashboard is `exepex/omenix-dashboard`), an F&O options research assistant for the owner's Indian trading experiment (broker: Groww).
It is research and paper trading only: never place orders, never ask for or store broker credentials in files.

## How to work with the owner (always)

This is the owner's personal research tool for learning F&O trading and deciding their own trades. Wrong results
cost real money later, so:

- **Never hold back.** Share every relevant fact, risk, idea and doubt, including what the owner may not want to hear.
- **Be brutally honest.** Disagree openly and say why. Never agree just to please. Never present a guess as a fact:
  mark each recommendation as strong evidence, some evidence, or reasoning only.
- **Keep it simple, precise and concise.** Plain words, real numbers, short answers; explain any jargon you must use.
- **Get past blockers.** When something stops the work (missing data, a failing source, an unclear rule, a tool
  limit), find another legitimate way: another source, a test, a workaround, or a clear question to the owner. If it
  truly cannot be done, say so plainly and why. Never skip it silently or hide it.
- **No patches.** Find the root cause, validate it with data and tests, then fix the design.
- **No blind acceptance or rejection of reviews.** Check every review comment and piece of feedback (from the owner,
  Claude, ChatGPT or a judge) with your own reasoning and, where possible, data: re-run the numbers, read the code,
  test the claim. Accept it only when the check shows it is correct; push back when it is not. Every acceptance and
  every rejection states its reason and evidence. Partial agreement is fine: say which part and why.
- **Everything for the other AI goes in the repository.** Questions, proposals and feedback meant for ChatGPT (or
  from it) are Markdown files in the repository, never only in chat: ChatGPT writes `reviews/chatgpt/review_<n>_<name>.md`,
  Claude `reviews/claude/response_<n>_<name>.md`, each folder with a README index. Take `<n>` from the central registry:
  `python tools/claim_number.py <category> <name> --session <id>` (story O12; by hand, as `numbers/README.md` says).
  The ChatGPT loop is **paused** while ChatGPT is inactive (owner, 22 Oct 2026): no review requests are written and no
  merge waits for one. A builder's claims for the judge live in the story file's **Claims** section, not in a
  response file.
- **Own limits too.** This applies to Claude's own limits and boundaries, not only tools: always give the fullest, most
  direct answer possible. If a limit ever shapes an answer, say so openly (what was limited and why), give everything
  that can be given, and point to where the rest can be found. Never quietly water an answer down. The same applies to
  questions and clarifications: ask them plainly and directly.
- The hard lines stay: no real orders, nothing illegal (no market manipulation), secrets never in files or chat.
- **No hand-run Groww command from 09:15 to 15:35 IST (owner, 25 Oct 2026: "no human or AI session should run it
  during 09:15–15:35 IST").** In market hours only the scheduled routines and their own steps call Groww; no live
  Groww test, probe, download, backfill or check is run by hand then (pytest never calls Groww live), so the routines'
  reads never meet Groww's limits (10 a second, 300 a minute, 150 sign-ins a day). Hand-run Groww reads wait until
  after 15:35 IST. **Failed commands (owner, 25 Oct 2026):** a failed scheduled command is retried with exponential
  backoff, at most 5 retries, then escalated to a human in #fno-desk (story O14, `DESK_DECISIONS` "Failed commands:
  automatic retry"). Until O14 is live, and after an escalation, the failed routine's own command may be run again by
  hand, in market hours too, so no data is lost; never a different or extra Groww command, and the command's own rules
  still hold (the day lock, completed steps skipped, a failed fills step never retried), and for the daily run step
  2b's once-only rerun holds until O14 replaces it.
- **One builder per function (owner, 15 Oct 2026).** Before starting any story, fix or design change, read
  `docs/WORK_REGISTER.md` on the latest `main`; if a row already covers the same function, files or rule, agree with
  its owner session first, and add or update your own row in your first commit. Never build a second version.
- **The main job is the desk meeting** (see `AGENTS.md`): find profitable trades from data, every role reasoning from its
  own angle; code and data bugs are fixed directly and mentioned in one line, never the main topic.
- **Answer from every financial role** listed in `AGENTS.md` (mathematician, statistician, F&O trader, options
  strategist, risk manager, portfolio manager, analyst and the rest); ChatGPT follows the same file.

## Keep a conversation log (every session)

Before ending any working session with the user, write or append to `conversations/YYYY-MM-DD.md` (IST date): the
user's messages quoted as written and the decisions they lead to, then the "Decisions so far" and "Open questions"
sections (owner, 22 Oct 2026: owner quotes plus decisions, no condensed replies). Commit and push it. Never include
email addresses, API keys or tokens.

## Daily desk routine (story O1; the 3 pm quote parts: stories A4, A4c and A7)

Started by the owner's scheduled session at 14:05 IST every day (owner, 21 Oct 2026, from 22 Oct: the weather and the
v4 forecasts must run before their 14:30 cutoff, so setup must end well before 14:30);
its stored prompt is exactly: "Run the daily desk routine in CLAUDE.md, section 'Daily desk routine'." One command runs
the whole desk day; the NSE session calendar (A7) decides whether it is a trading day (a closed day records only
`skipped` and each quote part prints "not a trading day"). Research and paper trading only: never places, modifies or
cancels orders.
1. `sh tools/routine_setup.sh --groww` (story O7: installs into every Python the routine and the commit hook can call,
   checks each imports the packages, turns on the public-record scan, story O5, and prints "routine setup ok").
   Every scheduled routine sets up this way, never with bare `pip` (it may fill another Python).
2. `python -m fno daily run` (story O1). It runs the day's steps in the order of `DAILY_RUN_STEPS`
   (`fno/constants_operations.py`): the 3 pm quote parts start first, then A14c's margin check, the weather and the v4
   forecasts (each from its `daily.live_from` date in `config.yaml`, `not_live` before it), protocol v4's release
   (story G10: from `daily.live_from.v4_pack`, after the `v4` quote part's 14:32-14:40 capture), G7b's pack-derived v4
   rows (`forecasts_v4_pack`, from `daily.live_from.forecasts_v4_pack`, right after the release, committed before 15:10),
   E3's desk (pack, Book 1's decision, fills, exits), E6's reviews, the quote parts' end and T1's card in #fno-desk,
   the market school's 15:00 paper slot (MS-P1j2: right after G13d's issue, never started after 15:25 IST, never
   retried; `school.enabled`), v4's 15:10 deadline check (G10, from 15:12) and, from 15:33 IST (after A16's 15:30 mark), A16b's candle catch-up (`intraday backfill`:
   yesterday's 15-minute candles, read-only Groww) and, last, A4h's close reads. It writes `journal/runs/<date>.json` and commits each step's own files itself. It ends on one line: `day done`, `day
   done with problems: <steps>`, or the desk's stop line ending "; no card today" (exit 1 for the last two). A rerun the
   same day skips the steps already done. A "waiting until HH:MM IST" line is a wait for the next step's time, never a
   hang: never stop the run while it waits. A second run beside a living one prints "another daily run of <day> is
   running" and does nothing (story O1-day-lock): then wait for the first run's last line.
2b. If its last line ends with "a rerun today retries it: <steps>" (a failed exits or marks step), run `python -m fno
   daily run` once more at once, once only (owner, 24 Oct 2026): never a rerun chosen later. A failed fills step is
   never retried: no new trades that day.
3. If it printed "alert NOT sent", post those lines to #fno-desk (`C0C89E8QCCD`) with the Slack connector. Note any
   result other than `day done` in `conversations/<date>.md`, then commit and push it (`git pull --no-rebase origin
   main` first, then `git push origin HEAD:main`).

### What the run does for the 3 pm quote parts (A4c's routine steps, word for word)

The routine never runs these commands itself: `daily run` runs each part's own command as a child process and makes
each part's commit in its one thread. The `git add` lines below are also the hand fix when the run reports a part
"NOT committed". Their rules hold for every commit of the day: never edit a recorded attempt, never `--no-verify`.

2. `python -m fno quotes record` (NIFTY, Groww) and `python -m fno quotes record --source nse` (NSE's public chain,
   story O6) run in parallel from the routine's start; each waits for 14:55 IST, records NIFTY monthly quotes and
   retries until 15:10 if a capture is incomplete. NSE's session calendar (`research/data/calendar/nse_sessions.csv`,
   story A7) decides the day: a holiday, weekend or muhurat-only day records nothing ("not a trading day"); a special
   weekend session is recorded. It prints the result line. Groww's raw quote rows go to Google Drive only (story A4b;
   needs the four `FNO_GDRIVE_*` settings): the repository gets each attempt's sidecar (`.meta.json`, with the Drive
   file's SHA-256) and the day's `.canonical` marker, never a Groww quote file (`.gitignore` keeps them out).
3. Each part commits and pushes only its own files to `main`, one commit at a time (`git pull --no-rebase origin main`
   first, then `git push origin HEAD:main`); never
   `git add research/data/quotes/` as a whole. NIFTY first, as soon as its result line is printed: `git add
   ':(glob)research/data/quotes/groww/derivatives/quote-snapshots/**/nifty_*'`. NSE when it is done: `git add research/data/quotes/nse/`. Never edit
   or delete a recorded attempt or `.canonical` file. If the record scan refuses the commit, do not commit and never
   bypass it (`--no-verify`). The hook posts its lines (file, line and kind of value; never the value) to #fno-desk
   itself when `FNO_SLACK_BOT_TOKEN` is set; if it prints "alert NOT sent", post those lines with the Slack connector.
   Note them in `conversations/<date>.md`.
3b. Right after NIFTY's push, run `python -m fno quotes record-indices` (story A4c: BANKNIFTY, FINNIFTY and
   MIDCPNIFTY, then NIFTY's two nearest weeklies, story A4f; 15:01-15:13 IST, paced; raw quotes to Drive only),
   alongside NSE if it is still running. When it is done: `git add ':(glob)research/data/quotes/groww/**/banknifty_*'
   ':(glob)research/data/quotes/groww/**/finnifty_*' ':(glob)research/data/quotes/groww/**/midcpnifty_*'
   ':(glob)research/data/quotes/groww/**/niftyweekly_*'`, commit and push. It alerts #fno-desk itself for any index
   not recorded.
3c. Protocol v4's capture (story G10, from `daily.live_from.v4_pack`): `python -m fno quotes record --window v4` (A4e:
   14:32-14:40 IST, inside protocol v4's 14:30-14:40 window, after A16's 14:30 mark; its own dataset) starts with the
   parts above and commits alone as soon as it ends, never after NIFTY:
   `git add ':(glob)research/data/quotes/groww/derivatives/quote-snapshots-v4/**'`.
4. If the result is not "recorded" with complete=True, "already recorded" or "not a trading day": the command itself
   posts its three alerts to #fno-desk (`FNO_SLACK_BOT_TOKEN`): "calendar says session, no same-day trades",
   "stopped, nothing recorded" (the calendar cannot answer for today, e.g. a new year missing: add NSE's holiday
   circular rows for that year) and "raw quote file NOT saved to Drive" (Drive down or its settings missing or
   expired; the day ends "none" if it lasts to 15:10). Post one line with the result to #fno-desk (`C0C89E8QCCD`)
   yourself only for any other result, or if it printed "alert NOT sent". Note every such result in
   `conversations/<date>.md`.

## Morning and evening forecast routines (story FL1-1d)

Started by the owner's two scheduled sessions (owner, DESK_DECISIONS lines 284 and 287; the owner creates them, no
session does). Their stored prompts are exactly: "Run the morning routine in CLAUDE.md, section 'Morning and evening
forecast routines'." at 08:38 IST, and "Run the evening routine in CLAUDE.md, section 'Morning and evening forecast
routines'." at 19:53 IST, both every day: NSE's calendar decides the day. Each edition posts only from its
`forecast_lab.live_from` date in `config.yaml` ("not live" before it). Research and paper trading only: never places,
modifies or cancels orders, and neither uses Groww.
1. `sh tools/routine_setup.sh` (prints "routine setup ok").
1b. The morning only, before `lab open`: `python -m fno data-librarian index-close --from "$(TZ=Asia/Kolkata date -d
   '-7 days' +%F)"` archives the previous sessions' official index-close files in Drive (A9's command, unchanged;
   orchestrator, 22 Oct). It commits its own manifest rows itself; a file NSE has not published yet is not a
   failure of the routine: the morning then says "not archived yet". Then `git pull --no-rebase origin main`, so
   A22b's GIFT Nifty receipt (pushed about 08:41) is there for `lab open` to read verified.
   After `lab open` (step 2), DR1-1's shadow: `python -m fno records certify closes --since 7 --level certified
   --commit` certifies every recent session's A4h close against the official file just archived and commits only
   `receipts/records/`; a session not recorded yet is retried by the next morning. It alerts a record not pushed
   or a conflict itself. Note any "NOT recorded" line in `conversations/<date>.md` and post it to #fno-desk unless
   its reason contains "no official index-close file in Drive yet" (A4h's overdue rule alerts that gap); post the text of
   any "alert NOT sent" line.
1c. The evening only, first: `python -m fno closes read --commit` (A4h's own command, unchanged: it reads NSE's index
   list only when its 15:40 read is missing, prints "close already read" otherwise, and commits only
   `receipts/data/closes/`; exit 1: post every line it printed (the read's problem line and the commit line) to
   #fno-desk, as a failed read or uncommitted receipts are alerted by nothing else outside O1). Then DR1-1's shadow:
   `python -m fno records certify closes --level provisional --commit` (commits only `receipts/records/`; it alerts
   a record not pushed or a conflict itself; a "NOT recorded" line is noted in `conversations/<date>.md` and posted
   to #fno-desk, as is the text of any "alert NOT sent" line). Then, before
   `lab close`, the same way (orchestrator, 22 Oct; each unchanged, committing only its own
   dataset's rows): `python -m fno data-librarian fo-bhavcopy --from <today> --to <today>`, `python -m fno
   data-librarian participant-oi --from <today> --to <today>` and `python -m fno data-snapshot
   fii-dii-cash-by-session`. A librarian line "not published by the source <day>" means "not out yet" (the edition
   says so); any other problem line ("damaged in store", "rejected from source", "stopped:", a Drive sign-in
   refusal) is noted and posted to #fno-desk. After `lab close`, `python -m fno lab release-check` (read-only, never
   fails) appends to `research/data/forecast_lab/release/`; commit those logs with the receipts in step 3.
2. The morning: `python -m fno lab open` posts today's forecast to #fno-forecast before 09:15, with the earlier
   evenings' checks confirmed against NSE's official closes; at or after 09:15 it posts nothing and alerts once. The
   evening: `python -m fno lab close` checks today's forecast against today's close and posts to #fno-forecast. Each
   prints its lines and exits 1 when its report was not posted (it alerts #fno-desk itself).
3. Commit only that edition's receipts: `git pull --no-rebase origin main`, then `git add
   receipts/data/forecast_lab/v1/<morning|evening>/` (the evening also `research/data/forecast_lab/release/`), commit and `git push origin HEAD:main` (record scan on, never
   `--no-verify`). If the push is refused, pull and push once more; if it fails again, post "receipt NOT pushed" with
   the edition and day to #fno-desk (`C0C89E8QCCD`) with the Slack connector: the Drive copy is the record.
3b. The evening only, after step 3's commit: `python -m fno recommend check` (story REC1c: the recommender's check of
   its recorded days against their sealed outcomes). It reads no price and changes no edition: `lab close` has already
   posted and step 3 has committed its receipts. It writes and pushes its own receipts (`receipts/data/recommend/`)
   itself and posts one #fno-desk line per day that becomes final. Exit 1: it has alerted #fno-desk itself; note its
   lines in `conversations/<date>.md` and post the text of any "alert NOT sent" line.
4. If it printed "alert NOT sent", post those lines to #fno-desk with the Slack connector. Note any failure in
   `conversations/<date>.md`, then commit and push it (`git pull --no-rebase origin main` first, then `git push origin
   HEAD:main`).

## Pre-open capture (story A22)

Started by the owner's scheduled session at 08:36 IST every day; its stored prompt is exactly: "Run the pre-open capture
in CLAUDE.md, section 'Pre-open capture (story A22)'." Research only: Groww is read through the read-only allow-list.
1. `sh tools/routine_setup.sh --groww` (prints "routine setup ok").
2. The trading-day check, once, before anything else (judge 439): `python -c "from fno.models import now_ist;
   from fno.storage.trading_days import is_trading_day; from fno.storage.wiring import build_session_calendar;
   print('trading day' if is_trading_day(build_session_calendar(), now_ist().date()) else 'not a trading day')"`.
   On "not a trading day" stop here. If it stops with a calendar error, post that one line to #fno-desk and stop.
3. On a trading day, run both at once (each waits for its own windows and commits only its own files): first start
   `global-cues preopen` in the background, then run `preopen record` in the foreground, then wait for the background
   one to finish too (part B reads 08:50-09:05 while `preopen record` runs to about 09:11; started after it, part B's
   window would be gone; judge 450):
   - background: `python -m fno global-cues preopen` (story A17e part B: the open Asian indices' levels, 08:50-09:05
     IST, its own commit, its own alert and O10 row on any failure).
   - foreground: `python -m fno preopen record`. It reads GIFT Nifty (08:40-08:44:59), NSE's F&O pre-open list
     (09:08:30-09:10:59) and NIFTY's and BANKNIFTY's 09:09 one-minute candle from Groww (09:10:00-09:10:45, window to
     09:11:00), saves the raw answers and the day row write-once to Drive, and itself commits and pushes
     `research/ops/capture_errors.csv` and `receipts/` to `main` by about 09:12 (GIFT Nifty's own file and receipt
     already when its read ends, about 08:41, for the 08:50 morning edition). Its capture line is "pre-open recorded" or
     "pre-open recorded with problems: ..." (exit 1; it posts that one line to #fno-desk itself). Then, after that
     commit, A22d's check of earlier sessions against NSE's official open ends the run on "open check: <n> checked, <m>
     waiting for NSE's file" or "open check with problems: ..." (exit 1; it posts that line to #fno-desk itself).
4. If either printed "alert NOT sent" or a line with "NOT committed", post its problem line to #fno-desk
   (`C0C89E8QCCD`) with the Slack connector, then commit the named files by hand (`git pull --no-rebase origin main`
   first, then `git push origin HEAD:main`; only
   the files the command names, never `--no-verify`). No value is ever posted or committed.

## Branch

**Judge lanes (owner, 14 and 22 Oct 2026; details in `docs/JUDGE.md`).** A change's lane is set by what it can
damage, not by its size; when unsure, lane 1.
- **Lane 1, the code judge's PASS before `main`:** money and risk (margins, funds, limits), fills, exits, anything that
  decides a trade; forecast, score and evaluation records; frozen files; secrets; outside services (Slack, Groww,
  Drive, NSE) and the schedules and workflows that call them; the dashboard's privacy rule. Push to a branch
  `story/<id>-<short>`, tell the orchestrator, merge after the PASS (merge procedure in `docs/JUDGE.md`). At most two
  judge rounds; after that the owner decides.
- **Lane 2, the orchestrator's check before `main`, the lane-2 auditor after:** everything else outside lane 3 (tools,
  CI, tests, docs, rule documents, stories outside lane 1) when it changes no record. A rule-document change that
  narrows lane 1 or touches a hard line (no orders, secrets, privacy, write-once data, frozen files) stays lane 1
  (owner, 22 Oct 2026; DESK_DECISIONS "Rule-document guard").
- **Lane 3, no judge:** judge files, conversation logs, decision and status rows, number claims (`numbers/`), and data
  commits by scheduled jobs.

A checkout on a detached HEAD pushes with `git push origin HEAD:<branch>`.

**Every scheduled routine starts on latest main (story DR1, owner 23 Oct 2026).** The first line of each routine's
stored prompt, before setup: `git fetch -q origin main && git checkout -q --detach origin/main`; if it fails, post its
error line to #fno-desk (`C0C89E8QCCD`) and stop. Every push in a routine is `git pull --no-rebase origin main`, then
`git push origin HEAD:main` (22 Oct: a routine on its own session branch could not commit the day's quotes).

Work on `main` (`git pull --no-rebase origin main` before every push: ChatGPT also pushes to `main`).
Every session commits with the public-record scan on (story O5): `.claude/settings.json` runs
`git config core.hooksPath .githooks` at session start; run it yourself if `git config core.hooksPath` is empty. Never
commit with `--no-verify`.

## Code

- `python -m pytest -q -n auto` (parallel, pytest-xdist), `ruff check fno tests tools` and
  `python tools/check_imports.py` must pass before pushing code changes; format with `ruff format`. On `main` (after
  `git pull --no-rebase origin main`, never on a story branch alone: claim rows live on `main`),
  `python tools/check_numbers.py` must pass too. When the gates run: `docs/JUDGE.md`, "Merge procedure".
- **Functional documents are reviewed like code (owner, 25 Oct 2026: "let us make our documentation review strong
  like we have for code").** A change to a document that describes how something works (a design, a story, a rule, a
  roadmap or status page) takes the lane of the functionality it describes, never a lower one: lane 1 needs a judge
  PASS before `main`, lane 2 the orchestrator's check and the auditor. The Rule-document guard still applies. Lane 3
  stays lane 3: conversation logs, judge files, number claims, register rows, and the owner's dated rows in
  `docs/DESK_DECISIONS.md` (the verbatim record of the owner's words; append-only). **One functionality, one owning
  document:** describe a functionality in exactly one document and, everywhere else, give one line and a link to it.
  **No document over 500 lines** (a new document never; an existing one already over 500 may still be edited until DOC1
  splits it, per the plan's section 7). Update the owning document in place; never write a new dated summary or handover as
  the place a decision lives (the daily conversation log stays a log, not a source of rules). The full clean-up:
  `docs/stories/DOC1-clean-docs-plan.md` (story DOC1).
- **Text-only changes skip the full suite (owner, 23 Oct 2026: "for doc or text file changes, we don't need to run
  tests").** When every changed file is Markdown (`git diff --name-only <base> | grep -v '\.md$'` prints nothing),
  the gates are the commit hook's record scan, `python tools/check_numbers.py` on `main` and, unless every file is a
  lane-3 path (`tools/ci_scope.sh`), the doc-reading tests (about 1 minute; some tests read docs and READMEs):
  `python -m pytest -q -n auto $(grep -rlE "docs/|\.md['\"]" tests --include=*.py)`. Never the full suite, for
  builders, judges and the orchestrator alike. Any other file in the change (`.py`, test, config, workflow,
  requirements, data) means the full gates above. The lane is unchanged: a text change still needs its lane's judge.
- **Engineering standards (owner, mandatory for every agent and every session):** SOLID, DRY, KISS and clean code
  (clear names, small single-purpose functions and classes, no duplication, no dead code, comments only for the "why").
  **No file and no class over 350 lines.** Anything that would pass 350 lines is broken down into smaller single-purpose
  units, never squeezed (no long lines or joined statements to dodge the limit). Enforced by `tests/test_code_size.py`
  and checked by the judge (`docs/JUDGE.md`).
- **Design for change (owner, 12 Oct 2026: "Today it's Google Drive, tomorrow it can be something else"; "flexible,
  modular, scalable", "production quality"):** high cohesion and loose coupling through design patterns. Every external
  service, data source, store and rule sits behind an interface, so swapping it means one new class plus one line in a
  composition root. Patterns in use: interface plus adapter (`RawFileStore`, `RawFileSource`, `Provider`), strategy
  (`FoFileFormat`, `RecordPattern`, rules), factory (`get_provider`) and composition root with dependency injection
  (below). Choose the simplest pattern that keeps the parts swappable (KISS); never add a pattern without a second use.
- Fixed strings, enum values and environment-variable names live in `fno/constants.py`; module-specific
  URLs, SQL and message templates are named constants at the top of their module.
- Names say what things do. Small single-purpose modules; new behaviour goes in a new class behind an existing
  interface (`Provider`, `RawFileStore`, `RawFileSource`, `FoFileFormat`, `ListedExpiries`, and those the stories add)
  rather than into an existing one. Follow SOLID, KISS and DRY: high cohesion, loose coupling, depend on interfaces.
- Concrete classes are wired together only in the composition roots: `fno/composition.py` (the app's services) and
  each package's `wiring.py` (or `<part>_wiring.py` where a freeze or the size limit keeps a second one apart); the
  root's docstring says what it wires (and for which story, where it has one).
- Nothing in this repository places real orders. The stock tool's research is read-only: never write to its
  repository or to its `market_brief` MotherDuck database. Every data file (fetched or derived) lives write-once in
  Google Drive and is read through the verified Drive cache; GitHub keeps code, docs and one SHA-256 receipt per Drive
  file (owner, 16 Oct 2026; story O9, built step by step).
- F&O output goes only to three Slack channels, all with `FNO_SLACK_BOT_TOKEN` (owner, 21 Oct 2026; story FL1):
  #fno-desk (`C0C89E8QCCD`) takes every alert and the daily card; #fno-forecast (`C0CAZS76WBC`) the forecast lab's
  morning (08:50) and evening (20:05) editions (story FL1-1d); #fno-intraday (`C0CAZRX0ZQA`) the lab's fills and
  hourly lines. Never the market-brief tool's `SLACK_*` variables or #market-brief, and no other channel (the record
  scan allows only these three IDs).
- Settings live in `config.yaml` (allowed keys only, see `fno/config.py`); see README.md for the layout.
