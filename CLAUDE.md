# Project instructions

This repo is **Omenix F&O** (part of Omenix; the dashboard is `exepex/omenix-dashboard`). It is the
**data-ingestion backend**: it fetches Indian F&O and market data from NSE (and Groww, for market data only) and
archives it write-once to Google Drive, the system of record. It is research only: never place orders, never ask for
or store broker credentials in files. The Python package is `fno`, split into `fno/shared/` (models, config,
constants, HTTP pacing, the record scan and other building blocks) and `fno/ingestion/` (the fetch workflows, their
providers, storage and CLI).

## How to work with the owner (always)

This is the owner's personal research tool for an Indian F&O trading experiment. Wrong or missing data costs real
money later, so:

- **Never hold back.** Share every relevant fact, risk, idea and doubt, including what the owner may not want to hear.
- **Be brutally honest.** Disagree openly and say why. Never agree just to please. Never present a guess as a fact:
  mark each recommendation as strong evidence, some evidence, or reasoning only.
- **Keep it simple, precise and concise.** Plain words, real numbers, short answers; explain any jargon you must use.
- **Get past blockers.** When something stops the work (missing data, a failing source, an unclear rule, a tool
  limit), find another legitimate way: another source, a test, a workaround, or a clear question to the owner. If it
  truly cannot be done, say so plainly and why. Never skip it silently or hide it.
- **No patches.** Find the root cause, validate it with data and tests, then fix the design.
- **No blind acceptance or rejection of reviews.** Check every review comment and piece of feedback (from the owner or
  a judge) with your own reasoning and, where possible, data: re-run the numbers, read the code, test the claim.
  Accept it only when the check shows it is correct; push back when it is not. Every acceptance and every rejection
  states its reason and evidence. Partial agreement is fine: say which part and why.
- **Written feedback, questions and proposals meant for another agent** go in the repository as Markdown, never only
  in chat, so each side can read them directly.
- **Own limits too.** This applies to Claude's own limits and boundaries, not only tools: always give the fullest, most
  direct answer possible. If a limit ever shapes an answer, say so openly (what was limited and why), give everything
  that can be given, and point to where the rest can be found. Never quietly water an answer down. The same applies to
  questions and clarifications: ask them plainly and directly.
- **One builder per function.** Before starting a change, check whether another session already owns the same code,
  files or rule, and coordinate first; never build a second version.
- The hard lines stay: **no real orders**, nothing illegal (no market manipulation), **secrets never in files or chat**.
- **No hand-run Groww command from 09:15 to 15:35 IST (owner, 25 Oct 2026: "no human or AI session should run it
  during 09:15–15:35 IST").** In market hours only the scheduled workflows and their own steps call Groww; no live
  Groww test, probe, download, backfill or check is run by hand then (pytest never calls Groww live), so the scheduled
  reads never meet Groww's limits (10 a second, 300 a minute, 150 sign-ins a day). Hand-run Groww reads wait until
  after 15:35 IST. A failed scheduled Groww command may be re-run by hand so no data is lost, but only that same
  command, never a different or extra one.

## Keep a conversation log (every session)

Before ending any working session with the user, write or append to `conversations/YYYY-MM-DD.md` (IST date): the
user's messages quoted as written and the decisions they lead to, then the "Decisions so far" and "Open questions"
sections (owner, 22 Oct 2026: owner quotes plus decisions, no condensed replies). Commit and push it. Never include
email addresses, API keys or tokens.

## Ingestion workflows

The repository's job is to fetch data and archive it write-once to Google Drive, with one SHA-256 receipt per Drive
file kept in GitHub. The entry points are `python -m fno <command>` (run `python -m fno <command> --help` for each);
`.github/workflows/` holds thirteen GitHub Actions workflows, one per data source, that call these commands on a
schedule. **The schedules were re-enabled at cutover (26 Oct 2026); each workflow now runs on its cron schedule and by
`workflow_dispatch`.** Each workflow fetches only its own source and commits only its own output paths
(manifest rows, receipts and run logs); it never edits a recorded file. Research only: no workflow places, modifies or
cancels orders, and the Groww-reading ones honour the market-hours rule above.

Every push from a workflow or a session is `git pull --no-rebase origin main`, then `git push origin HEAD:main`, with
the public-record scan on (story O5): never `--no-verify`. If the scan refuses a commit, do not commit and never
bypass it; it posts its finding lines (file, line and kind of value, never the value) to #fno-desk when
`FNO_SLACK_BOT_TOKEN` is set, and prints "alert NOT sent" otherwise, which you then post to #fno-desk yourself.

## Branch

**Judge lanes (owner, 14 and 22 Oct 2026; details in `docs/JUDGE.md`).** A change's lane is set by what it can
damage, not by its size; when unsure, lane 1.
- **Lane 1, the code judge's PASS before `main`:** secrets; outside services (Slack, Groww, Drive, NSE) and the
  schedules and workflows that call them; write-once data and the receipts that prove it; frozen files; the
  public-record (privacy) rule. Push to a branch `story/<id>-<short>`, tell the orchestrator, merge after the PASS
  (merge procedure in `docs/JUDGE.md`). At most two judge rounds; after that the owner decides.
- **Lane 2, the orchestrator's check before `main`, the lane-2 auditor after:** everything else outside lane 3 (tools,
  CI, tests, docs, rule documents) when it changes no record. A rule-document change that narrows lane 1 or touches a
  hard line (no orders, secrets, privacy, write-once data, frozen files) stays lane 1 (owner, 22 Oct 2026).
- **Lane 3, no judge:** judge files, conversation logs, and data commits by scheduled jobs (their own output paths only).

A checkout on a detached HEAD pushes with `git push origin HEAD:<branch>`.

**Every scheduled workflow starts on latest main (story DR1, owner 23 Oct 2026; amended 25 Oct 2026).** Each
workflow checks out with `actions/checkout@v4`, which for a scheduled run checks out the latest `main`. Every push is
`git pull --no-rebase origin main`, then `git push origin HEAD:main`.

Work on `main` (`git pull --no-rebase origin main` before every push). Every session commits with the public-record
scan on (story O5): `.claude/settings.json` runs `git config core.hooksPath .githooks` at session start; run it
yourself if `git config core.hooksPath` is empty. Never commit with `--no-verify`.

## Code

- `python -m pytest -q -n auto` (parallel, pytest-xdist), `ruff check fno tests tools ops` and
  `python tools/check_imports.py` must pass before pushing code changes; format with `ruff format`. On `main` (after
  `git pull --no-rebase origin main`), `python tools/check_numbers.py` must pass too. When the gates run:
  `docs/JUDGE.md`, "Merge procedure".
- **Functional documents are reviewed like code (owner, 25 Oct 2026: "let us make our documentation review strong
  like we have for code").** A change to a document that describes how something works (a design, a story, a rule, a
  roadmap or status page) takes the lane of the functionality it describes, never a lower one: lane 1 needs a judge
  PASS before `main`, lane 2 the orchestrator's check and the auditor. The Rule-document guard still applies.
  **One functionality, one owning document:** describe a functionality in exactly one document and, everywhere else,
  give one line and a link to it. **No document over 500 lines.** Update the owning document in place; never write a
  new dated summary or handover as the place a decision lives (the daily conversation log stays a log, not a source of
  rules).
- **Text-only changes skip the full suite (owner, 23 Oct 2026: "for doc or text file changes, we don't need to run
  tests").** When every changed file is Markdown (`git diff --name-only <base> | grep -v '\.md$'` prints nothing),
  the gates are the commit hook's record scan, `python tools/check_numbers.py` on `main` and, unless every file is a
  lane-3 path (`tools/ci_scope.sh`), the doc-reading tests (about 1 minute; some tests read docs and READMEs):
  `python -m pytest -q -n auto $(grep -rlE "docs/|\.md['\"]" tests --include=*.py)`. Never the full suite, for
  builders, judges and the orchestrator alike. Any other file in the change (`.py`, test, config, workflow,
  requirements, data) means the full gates above. The lane is unchanged: a text change still needs its lane's judge.
- **Engineering standards (owner, mandatory for every agent and every session), applied across `fno/shared/` and
  `fno/ingestion/`:** SOLID, DRY, KISS and clean code (clear names, small single-purpose functions and classes, no
  duplication, no dead code, comments only for the "why"). **No file and no class over 350 lines.** Anything that
  would pass 350 lines is broken down into smaller single-purpose units, never squeezed (no long lines or joined
  statements to dodge the limit). Enforced by `tests/test_code_size.py` and checked by the judge (`docs/JUDGE.md`).
- **Design for change (owner, 12 Oct 2026: "Today it's Google Drive, tomorrow it can be something else"; "flexible,
  modular, scalable", "production quality"):** high cohesion and loose coupling through design patterns. Every external
  service, data source, store and rule sits behind an interface, so swapping it means one new class plus one line in a
  composition root. Patterns in use: interface plus adapter (`RawFileStore`, `RawFileSource`, `Provider`), strategy
  (`FoFileFormat`, `RecordPattern`, rules), factory (`get_provider`) and composition root with dependency injection
  (below). Choose the simplest pattern that keeps the parts swappable (KISS); never add a pattern without a second use.
- Fixed strings, enum values and environment-variable names live in `fno/shared/constants.py`; module-specific
  URLs, SQL and message templates are named constants at the top of their module.
- Names say what things do. Small single-purpose modules; new behaviour goes in a new class behind an existing
  interface (`Provider`, `RawFileStore`, `RawFileSource`, `FoFileFormat`, `ListedExpiries`, and those the stories add)
  rather than into an existing one. Follow SOLID, KISS and DRY: high cohesion, loose coupling, depend on interfaces.
- Concrete classes are wired together only in the composition roots: `fno/ingestion/composition.py` (the app's
  services) and each package's `wiring.py` (or `<part>_wiring.py` where a freeze or the size limit keeps a second one
  apart); the root's docstring says what it wires (and for which story, where it has one).
- Nothing in this repository places real orders. Every data file (fetched or derived) lives write-once in Google Drive
  and is read through the verified Drive cache; GitHub keeps code, docs and one SHA-256 receipt per Drive file (owner,
  16 Oct 2026; story O9, built step by step).
- F&O alerts go only to Slack #fno-desk (`C0C89E8QCCD`) with `FNO_SLACK_BOT_TOKEN`, never to #market-brief or the
  market-brief tool's `SLACK_*` variables. The record scan allows exactly the three public channel IDs in
  `fno/shared/constants.py` and `fno/shared/constants_channels.py` and no other.
- Settings live in `config.yaml` (allowed keys only, see `fno/shared/config.py`); see README.md for the layout.
