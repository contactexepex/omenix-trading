# Judge 2: story O5, public-record safety scan

Verdict: **FAIL** (0 blocking, 3 should-fix, 3 minor).

Judged on `main` at 8ad2885 (O5 commit 322b8fe, CI f158f7a). Read in full: `fno/record_scan/*.py`,
`tools/check_records.py`, `.githooks/pre-commit`, `.github/workflows/checks.yml`, the CLAUDE.md routine change,
`tests/record_scan/*`, story O5, response 36.

## Checks run by the judge

```
$ python -m pytest -q                       238 passed (16 tests in tests/record_scan)
$ ruff check fno tests tools                All checks passed!
$ python tools/check_imports.py             clean: 89 files, 1 archival skipped
$ python tools/check_records.py             record scan: clean (157 files)
GitHub Actions "checks": runs 1-3 on main (f158f7a, 8acbbe0, 8ad2885) all success
```

Story's "judge verifies", done in a throwaway clone in the scratch area with `git config core.hooksPath .githooks`
(never in the real history). Planted values were assembled in the shell, not written in this file:

| Planted in a record | Hook result | HEAD moved |
|---|---|---|
| Slack bot token (`xoxb-`) in `journal/judge.md` | `journal/judge.md:1: Slack token`, REFUSED | no |
| GitHub token in `conversations/judge.md` | `GitHub token`, REFUSED | no |
| e-mail address in `reports/judge.md` | `e-mail address`, REFUSED | no |
| `GROWW_ACCESS_TOKEN: <16 chars>` in a root yaml | `value of a secret environment variable`, REFUSED | no |
| Slack app-level token (`xapp-1-...`) in `journal/` | clean | **yes, committed** |
| `Groww API key = <23 chars>` in `journal/` | clean | **yes, committed** |
| Slack token in `tools/x/notes.md` | clean (code folder) | **yes, committed** |

The output never printed a value: confirmed.

Further direct scans (`build_record_scanner().scan_text`), realistic forms:

```
MISSED  "Groww API key: <value>"          MISSED  "API secret: <value>"
MISSED  "TOTP secret: <base32>"           CAUGHT  "totp_secret: <base32>"
MISSED  "access token: <non-JWT value>"   MISSED  "GROWW_API_SECRET is <value>"
CAUGHT  "export GROWW_API_SECRET=<value>" MISSED  "password: <9 chars>" (min length 16)
MISSED  Slack app token (xapp-)           MISSED  base64 of a private key (stated limit 6)
CAUGHT  postgresql://user:pass@<host>.postgres.database.azure.com  (only as an "e-mail address", by coincidence)
CAUGHT  Aadhaar (spaced and plain, valid check digit), PAN, +91 phone, groww_order_id in JSON, Slack user ID in a link
MISSED  bare 10-digit phone, "Client Code: AB1234" (both stated limits 4 and 5)
```

## Criteria

| # | Criterion | Builder's claim | Judge's own evidence | Result |
|---|---|---|---|---|
| 1 | Planted examples of each pattern caught; allow-listed channel ID not | 18 kinds, each with a planted example; channel ID gives nothing | Tests pass and read correctly (`test_patterns.py` fails if a pattern lacks an example). True for the patterns as written. But the story asks for "patterns for tokens and keys": the most likely real leaks of this repository's own credentials (the Groww API key, API secret and TOTP secret named in `fno/constants.py`, written the way a person writes them) are missed (finding 3) | PARTLY |
| 2 | Routine refuses to commit and sends an alert naming the file, not the value | Refusal: hook; alert: CLAUDE.md instruction, no code | Refusal: MET, reproduced above. Alert: there is no code, no test and no routine dry run of the alert; I cannot verify a routine sends it. Per `docs/JUDGE.md`, unverifiable is NOT MET. Also the gate is on in one routine only (finding 2) | PARTLY |
| 3 | Scan of the current repository passes | clean | `record scan: clean (157 files)`; CI green; `test_current_repository_records_pass_the_scan` | MET |

## Claims vs reality

- "The hook scans the staged bytes": true (`record_files.py:65-73`, `git show :path`); the builder's test for staged
  vs working tree passes.
- "`.gz` unpacked; any other binary is a finding, not a silent skip": true (`scanner.py`: NUL byte -> whole-file
  finding; a corrupt `.gz` raises, so the hook fails closed).
- "Everything outside `fno/`, `tests/`, `tools/` is a record": true; it also means anything placed inside those
  folders is never scanned, by hook or CI (finding 4).
- "O1 reuses it unchanged: the hook guards every commit of any routine that runs `git config core.hooksPath`":
  true only for routines that run that line; only the 3 pm recorder does (`CLAUDE.md:48`; `grep hooksPath` finds
  no other place).
- "Groww and MotherDuck tokens are JWTs": reasoning only; not verified by the builder or by me (no real token may be
  used). The JWT pattern itself works.
- "CI cannot block a direct push to main": true; it reports after the record is already public.
- Doubts 1-10: accurate and honestly stated. Doubt 10 (pattern objects created in `catalogue.py`): accepted; they are
  data, the scanner is wired in `fno/composition.py`.

## Project rules

Files under 350 lines (largest 105); `RecordPattern` and `RecordSource` interfaces; scanner built in
`fno/composition.py`; env names and channel ID in `fno/constants.py`; module regexes as named constants; CI uses no
secrets and `contents: read`. No rule breaks found.

## Findings

1. **Should fix. Criterion 2's alert is not built or verified.** Only an instruction in CLAUDE.md step 3 of one
   routine. Expected: either code that posts the finding lines (file, line, kind) to #fno-desk when the routine's
   commit is refused (behind an interface, Slack connector or `FNO_SLACK_BOT_TOKEN`), with a test using a fake
   poster; or the story owner formally moves the alert to P4 and changes criterion 2's text, with a routine dry run
   recorded that shows the refusal and the posted lines.
2. **Should fix. The gate is off for every session except the 3 pm recorder.** Builders, the orchestrator, this
   judge and any session writing `conversations/<date>.md` (which quotes the owner's messages as written, the most
   likely place for a pasted key) commit with no hook; CI catches it only after the push, when the public
   repository already holds it. The story says "before every commit made by a routine". Expected: turn the hook on
   for every session (a general CLAUDE.md rule before any commit, or a SessionStart hook that runs
   `git config core.hooksPath .githooks`), and a test or check that a fresh clone following the rule refuses a
   planted token.
3. **Should fix. Secrets written in words are missed.** `SECRET_WORDS` uses `[_-]?`, so "API key:", "API secret:",
   "TOTP secret:", "access token:" (non-JWT) pass; an env name followed by "is" passes; Slack app tokens (`xapp-`)
   are not covered; a database URL with a password (Azure Postgres is in the plan) is caught only when its host
   happens to look like an e-mail domain. Expected: allow a space as separator (`api[ _-]?key` ...), accept
   "is"/"=" /":" after secret names and env names, add `xapp-` to the Slack token pattern, add a
   `scheme://user:password@host` pattern; a planted example and a no-false-positive check for each, and the
   repository scan still clean.
4. **Minor. Code folders are never scanned.** A real token hard-coded in `fno/` or a file dropped under `tools/`
   passes hook and CI (reproduced above). Scanning tracked code files with the credential-shape patterns only
   (private key, Slack/GitHub/Google/AWS/AI keys, JWT, bearer) looks cheap: my scan of all tracked code files with
   every pattern gave 12 findings, none of them credential-shaped. Expected: scan code with those patterns.
5. **Minor. The hook calls `python`.** On a machine with only `python3` the hook fails (closed, which is safe) with
   "python: not found", which invites `--no-verify`. Expected: `python3`, or a clear message.
6. **Minor (accepted limits, stated in doubts 4-7).** Bare 10-digit phone numbers, spaced labels such as
   "Client Code:", unlabelled random secrets, old-format Slack IDs. Expected: none now; keep listed in the story.
