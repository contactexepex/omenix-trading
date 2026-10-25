# Judge 62: stories F1 (forecast part) and G5, Hybrid and AI team daily forecasts

Date: 13 Oct 2026 (UTC; 14 Oct early IST). Claims: `reviews/claude/response_67_f1-g5.md` (ad5de1a) and its
addendum 1; owner decision in `docs/DESK_DECISIONS.md` (14 Oct, `sealed_same_day` with three conditions).
No live run exists yet (the first is 14 Oct about 15:10 IST), so nothing live could be checked.

## Verdict: PASS for the sealed-answer mechanism as built; the owner's conditions 1 and 2 are NOT yet enforced or recorded anywhere; G5 criterion 3 NOT MET

## The owner's three conditions: enforced, audited, or only written?

| # | Condition (DESK_DECISIONS, 14 Oct) | What exists | Result |
|---|---|---|---|
| 1 | Every session transcript audited for the first 10 session days, then 2 random sessions a week; a breach makes that book's day unscored; two breaches in 20 days stop the book | **Nothing beyond the sentence.** No place records an audit (who, which session, result), no random selection, no `breach` status in the audit file, no code that unscores a breached day, no stop rule. The audit file holds the session link (`fire.session`) so an audit is possible, but none is defined. G4 does not read the AI records at all yet (judge 58), so "unscored" has no consumer | **NOT MET** (written, not enforced or audited) |
| 2 | Label "isolation: sealed same day (not full F1)" on every record and every report | Audit JSON carries `"isolation": "sealed_same_day"` (`fno/ai/record_writer.py`). The forecast CSV (frozen v2 schema) has no such field. G4's report has no isolation text. Not the agreed words either | **PARTLY** |
| 3 | Trading decisions (slice 4) still need full F1 | Written in F1's status line and in DESK_DECISIONS; no slice-4 code exists to enforce | MET (as a written rule; nothing to enforce yet) |

Why it matters (statistician, red team): condition 1 is the only control on the open gap (the routine has the public
repository and network: it can re-run the baselines, read old records, or look at the market after 15:00). Without
a recorded audit, the first 10 days pass unaudited by default and the scores later cannot show which days were
clean. It is cheap now: an audit record per session (for example a row in a file next to the audit JSON with the
auditor, the time and the result) and a G4 rule that skips breached days.

## F1 criteria (forecast part only)

| # | Criterion | My check | Result |
|---|---|---|---|
| 1 | Real isolated session: reads of other books' data fail | Not built: the routines have the repository and network. The owner accepted `sealed_same_day` instead for forecasts only | NOT MET, accepted by owner decision for forecasts (not for trading) |
| 2 | Export lists only allowed items; a planted file is refused | Tests in `tests/ai/test_inputs.py` (planted file, edited prompt refused) pass | MET |
| 3 | Output after the receipt deadline ignored | Receipt time is GitHub's push timestamp from the activity log, not the commit's own date (`fno/ai/receipts.py`); unknown receipt fails closed as late. Planted `elif False:` for the deadline: caught | MET |
| 4 | A served model different from the registered one gives unscored and pauses scoring | Audit status `model_mismatch` (plant caught). It relies on the model the session **reports about itself**, not the session record; and no scorer pauses (G4 does not read AI records) | PARTLY |
| 5 | Failed or limited session gives "AI unavailable" | `no_submission`, `not_fired`, `not_revealed` statuses, five "no forecast" rows, never imputed | MET |
| 6 | No secret in the session; export and prompt scanned (O5) | Pushes go through the O5 hook (`GitMainTransport`). The routine environment's setup (no variables, no connectors) is the owner's; I cannot see it | Not verified by me |
| 7 | Pack hashes match the committed pack | `brief` refuses a pointer whose hash differs; `collect` rebuilds the export and refuses a different `export_sha256` | MET |

**Seal mechanism, checked:** salt `secrets.token_hex(16)` (128 bits), commitment SHA-256 of salt and canonical
answer; a reveal must hash to it. A book whose commitment GitHub received after the other book's reveal is marked
`exposed`; my plant reversing that comparison was caught. All 31 `tests/ai` tests pass.

## G5 criteria

| # | Criterion | Result |
|---|---|---|
| 1 | Five probabilities per session day, or a recorded "no forecast" | MET by tests; no live file yet ("judge verifies: one week of files" impossible today) |
| 2 | Late forecasts ignored | MET (above) |
| 3 | G4's report shows each AI book's coverage | **NOT MET**: `fno/ai/coverage.py` computes it ("for G4's report") but G4's report does not include it |

## Claims vs reality, other

- Timing (reasoning only, from the response's own table): the pack exists at about 15:10-15:13 and the commitment is
  due by 15:15:00. Two to five minutes to start a cloud session, pull, read, reason and push is tight; expect `late`
  days. The builder says so. The first week will show it.
- Hybrid sees Book 1's number (Book 1 is the mean of the baselines it gets). Stated openly by the builder; true.

## Project rules

New package `fno/ai/` with two composition roots; frozen v2 code untouched (the freeze test passes in the suite);
no secret in files; prompts versioned by hash. Clean.

## Addendum 1 (re-judge of d6d8c46 and G4 f03cb63): conditions now built on F1's side; G4 does not use them (must fix before the first AI outcome resolves)

**Fire path for today's first live run (14 Oct, about 15:10 IST): nothing found that breaks it.**
- On the real repository, `python -m fno ai audits-due` prints "audits due: 0" and exits 0.
- `stop_reason` is empty for both books under their new labels.
- `tests/ai`: 37 pass.
- The new version label (`.../isolation:sealed_same_day`) has no single quote and stays well under the 2 KB fired-text limit.
- The owner's pasted routine prompt names no version, so the label change needs no routine edit.

| Owner condition | Now | Result |
|---|---|---|
| 2: label on every record and report | Every record's `method_or_version` ends `/isolation:sealed_same_day` (test passes); G4's report prints `ai_isolation` per AI book beside coverage | MET |
| 1a: audits recorded | `transcript_audit.py`: one written-once file per audited book-day, auditor, time, named breach kinds; refused for a session never fired | MET |
| 1b: which sessions | `audit_plan.py`: all sessions of the first 10 fired days, then 2 per finished ISO week; due count in the daily #fno-desk line | MET, with a weakness below |
| 1c: breach makes the day unscored | `scoring_gate.scoring_status` does it (breach: unscored; selected but unaudited: pending). **But G4 never calls it.** `fno/forecast_scoring/ai_sources.py` (f03cb63) unscores only on a non-`on_time` status or `"unscored": true` inside the collection audit JSON. F1 records breaches in a separate `<d>_<book>_transcript_audit.json`, and the collection file is write-once. **My test:** collect both books, record a `read_other_records` breach for Hybrid. The gate says `unscored` (and `pending` before the audit), yet `ai_forecasts` scores both books with nothing unscored. The two sessions built two contracts that do not meet | **NOT MET end to end (must fix)** |
| 1d: two breaches in 20 days stop the book | `stop_rule.py`, asked by the fire step before each book; test with two planted breaches stops Book 3 and fires Hybrid; a new version starts clean | MET |
| 3: trading needs full F1 | Unchanged rule | MET |

**G5 criterion 3 (coverage in G4's report): MET.** `fno/forecast_scoring/coverage.py` counts, per book, the days with
scored-eligible probabilities out of v2 pack days since `COMMON_START = 14 Oct 2026`, and the report prints it. Because
it counts what G4 scores, it inherits the gap above: a breached or unaudited day counts as covered.

**Why it matters and when.** G4's daily report mixes AI forecasts into its scores as soon as their outcomes resolve.
The first, question 4 (VIX in 10 sessions), resolves about 28 Oct. Fix before then: `ai_sources._unscored_reason`
should call `fno.ai.scoring_gate.scoring_status` (one rule, as response 67 addendum 2 asks), score only `scored`,
and list `pending` apart from `unscored`. Add a test with a planted transcript breach through G4's own reader.

**Weakness in the audit draw (should fix, reasoning only).** The weekly seed is the ISO week label, public and known
in advance. Each routine has the repository, and the fired sessions of a week are predictable (2 books, 5 days).
A session can therefore compute whether it will be drawn before it acts, which removes the deterrent the random
audit exists for. Drawing only after the week ends does not help when the seed is known. Fix: a seed nobody knows
before the week ends, for example the SHA-256 of the first commit on `main` after the week closes, or of the last
capture receipt of the week, recorded beside the draw. Anyone can still redraw it.

**Verdict now:** the fire and collection side is ready for today. The scoring side is NOT MET until G4 reads the gate.

## Addendum 2 (G4 reader through F1's gate, 22ace2f with 44090c1 and 904c036; weekly audit seed, 0688ad5)

**1. A breach is now unscored in G4: MET (the must-fix is closed).** `fno/forecast_scoring/ai_sources.py` now calls
`fno.ai.scoring_gate.scoring_status(root, day, book)` for every AI book-day. I ran my scenario from addendum 1 through
G4's real reader:
- **Before any audit:** nothing scored; both book-days are `pending` ("transcript audit due") and listed apart.
- **After the audits:** a `read_other_records` breach recorded for Hybrid and a clean audit for the AI team. Hybrid's
  day is `unscored` ("transcript breach: read_other_records") and the AI team's is scored.

Coverage counts only scored forecasts, so pending and unscored days count as not covered. The report lists
`unscored_ai_days` and `pending_ai_days` separately. `tests/ai` and `tests/forecast_scoring`: 78 passed.

**2. The weekly audit seed: MET for "not known in advance" and "deterministic"; one should-fix on tampering.**
- **The seed** is the SHA-256 of the week label, its last session's date and that session's official NIFTY 50 close,
  as the text stands in `warmup_closes.csv`.
- **Timing:** a week gets a seed only when a later week's close is in the file. My plant, giving the newest week a
  seed as well, is caught.
- **Determinism:** the seed is a pure function of the file's text. Each draw is recorded once in
  `ai_v1/draws/<week>.json` with its seed inputs, so anyone can redraw it.
- **Content:** my plant, a seed from the week label alone, is caught (1 failed).

**Can a routine or builder push influence it? Yes, though only visibly (should fix, reasoning only).**
- The draw is recorded by `ai audits-due` in the capture job at about 15:20 IST.
- That is after the next week's first routine sessions have run with push access to `main` (from about 15:11).
- On that Monday, the week's last close (Friday's) is already final and public in `warmup_closes.csv`. A routine,
  or anyone with push rights, could push an edited Friday close before 15:20. That would set the seed to a value of
  their choice and steer the draw away from a session.
- It would show in git history and is a breach under condition 1. But nothing checks it, and the transcript audit it
  would dodge is the very check that would catch it.
- **Fix (either):**
  - record the week's draw in O6's `index-closes` job, in the same run that appends the close completing the week
    (no AI session runs in between);
  - or have `record_draws` verify the seed close against the archived NSE index file's own value (the row carries
    `index_sha256`).

  Today no draw exists yet: the first 10 days are all audited. So this is not urgent, but it must land before the first
  weekly draw, about 10 session days from 14 Oct.

**CI note on the G4 fix (orchestrator's request).**
- 22ace2f was pushed through merge a31c36f without re-running the suite after a second pull (the builder confirms this).
- `scoring_status` was called with 4 arguments after 0688ad5 made it 3, so CI was red on runs 332, 333 and 334.
- **Correction to "green from 335":**
  - runs 335 (c1bf97f) and 336 (43b92bd) were green only because they were on a line without 22ace2f;
  - run 337 (39e9173) was red for the same 4-argument call;
  - run 338 (1bec20d) carried the fix, 44090c1, but was red for the luck-dependent look-ahead test (judge 66);
  - that test was fixed in 5c0b366 and 716842d; green CI 38477508528, by the orchestrator's report.

## Addendum 3 (567ceea: the weekly draw's close verified in the Drive archive)

**MET; the should-fix from addendum 2 is closed.** The seed now takes NIFTY 50's close from NSE's index-close file as
first archived in Drive, which the routines cannot reach. The repository's closes file only names the day and the
file's SHA-256, and its own close must equal the archive's or the week is refused.

`tests/ai` and `tests/forecast_scoring`: 84 passed. My three plants:

| Plant | Result |
|---|---|
| The closes file's close no longer compared with the archive's (an edited CSV close would then steer the seed) | caught (3 failed) |
| The "last archived session of the week" check removed (a deleted last row would then move the seed to an earlier day) | caught (1 failed) |
| The archived file's SHA-256 no longer checked against the one the closes file names | caught (1 failed) |

- The builder's test plants an edited close in the CSV and the draw is refused. My first plant shows that test really
  exercises the comparison.
- A routine can no longer choose the seed: the only file with that day's path in Drive's raw area is the first
  archived one, and the routines have no Drive access.
- The capture job that runs `ai audits-due` has the Drive secrets, so draws can happen.
- Without Drive, `NoCloseArchive` refuses every week, so non-first-10 sessions stay `pending`. That fails closed and
  never counts as clean.
