# Judge 596: G14 Amendment 1 (story text), story/g14-v5-v1-candle-2 at 2f98d36c5 (judge J, round 1 of 2)

**FAIL**, lane 1 (text): 2 should-fix, 1 minor. The diff touches only `docs/stories/G14-v5-v1-candle.md` (+86 -5).
Doc-reading tests with `FNO_SLACK_BOT_TOKEN` set: 853 passed, 15 xfailed. I take over from judge 497's session, so
this is a new report.

## Criteria
| Item | Verdict | My evidence |
|---|---|---|
| Lifted gates (section 1) | MET | DESK_DECISIONS line 341 names "G14's v5 side-by-side step (built and judged first)" among the held items; line 323 lifts the other "after sign-off" gates |
| Criterion 2 vs FREEZE_v4 | MET | `freeze_check.BYTE_CHECKED_GLOBS` (and the freeze story's new globs: `fno/v4_pack/*.py`, G11's files) match neither `fno/forecast_v5_v1/` nor `research/forecasts/v5/`. The O1 step's three files are outside them |
| Merge order (section 3) | MET | it follows from FREEZE_v5_v1 hashing G7 files that G7b still changes. The freeze story's text has `Frozen on: 2026-10-25` and first counted 26 Oct |
| Criterion 12 | PARTLY | FREEZE_v4 has one row per byte-checked file (`freeze_check.table`), so equality is testable for `fno/forecast_v4_rules/*.py`; see S2 for files with no row |
| One reader (5, criterion 11) | MET | `CandleRvTable` exists (`fno/intraday/candle_rv_table.py:16`); the W8 text on `story/g7b-completion` is the one pairing; criterion 11 is testable |
| Gap table | MET | recomputed from `research/data/intraday/rv/2026` and `rv-candle/2026`: 0.962, 0.997, 1.009 (19, 21, 22 Oct); 16 Oct void live, candle ok; 23 Oct void live, no candle row |
| Live date (4) | MET | DESK_DECISIONS line 340: next NSE session after a judged switch; the 26 Oct `v5c_trailing` gap follows from 23 Oct's void live row |
| Decision-56 statement | NOT MET | S1 |

## Findings
**S1 (should fix) Decision 56's scope is misstated.**
- Response 113 row 56 is general: "rows with provenance backfilled never count as live forecast inputs". It is not limited to v4.
- So "allowed here only because G14 is never a v4 member" has no source.
- The authority for G14's input is the owner's own 23 Oct row (DESK_DECISIONS line 316, "v5 trial ... same V1 forecasters fed by ... candle 2020-2026", owner: "Yes, start it"). That row overrides an orchestrator decision for this trial.
- Fix: cite line 316 as the basis. Say plainly that decision 56 as written also covered v5, and that the owner's row excepts this one measurement. Keep the safeguards: point in time by `first_seen_at`, labelled, never a v4 member.

**S2 (should fix) The freeze misses part of the new input path.**
- With W8, G14's candle input runs through G7b's reader and A16b's `fno/intraday/candle_rv_table.py`.
- `candle_rv_table.py` is in neither of the freeze's lists (`BYTE_CHECKED_GLOBS`, `RECORDED_NOT_CHECKED`, nor the freeze story's section 2). FREEZE_v4 has no row to compare.
- FREEZE_v5_v1 hashes only "this package's files and the imported G7 files". So an edit to `candle_rv_table.py` would change G14's input mid-measurement with nothing refusing it.
- Fix: FREEZE_v5_v1 hashes every file on G14's input path, `candle_rv_table.py` and `rv_table.py` included. Criterion 12 then reads: equal to FREEZE_v4 where FREEZE_v4 has a row, hashed in FREEZE_v5_v1 alone where it has none, with a test listing each.
- Note for the orchestrator: W8's v4 baseline reads the same unhashed file; that is the freeze builder's call.

**m1** Section 5 says the W8 reader "sits in v4's byte-checked files" before G7b has named its module. Write "if it lands in `fno/forecast_v4_rules/` (byte-checked)" until G7b names it.

## Plants
0 (text round).

## Notes
- The "no partial v5" open item (section 6) is stated plainly and routed to the orchestrator and owner; not a finding.

## Addendum 1: round 2 (the last), story/g14-v5-v1-candle-2 at 40bd65e03
**PASS** (text), lane 1, 1 minor. The diff vs main is only `docs/stories/G14-v5-v1-candle.md` (checked).
- **S1 closed.** Section 5 quotes response 113 row 56, calls it general ("as written it covers v5 too"), and cites the
  owner's 23 Oct row (DESK_DECISIONS line 316, quoted correctly) as an exception for this one measurement. It ties
  decision 56's reason (hindsight) to criteria 1, 4 and 6.
- **S2 closed and widened.** I checked the import chain: `candle_rv_table.py:7-8` imports `rv_table.py`, which
  imports `row_files.py` (`rv_table.py:10`). None of the three has a hash in v4's freeze. Section 3b hashes the
  import walk, not a hand list. Criterion 12 is testable: the walk is compared with the record, each file is marked
  "v4 row" or "v5 only", and a planted edit to `candle_rv_table.py` must be refused.
- **m1 closed.** The reader's freeze timing is now conditional on its module.
- **m2 (minor, new).** Section 6 quotes the owner, "I want to run v5 dry run tests on weekend". That text is in no
  file on main. The nearest is "do a dry run of V5 over the weekend" (`conversations/2026-10-24.md:92`, earlier that
  day). The conclusion holds on the sign-off row alone (line 341 names G14's step), so cite that row and the exact
  log line.

## Addendum 2: ruling on criterion 12's import walk (builder's proposal via the orchestrator, 24 Oct)
**Yes, with four conditions.** The builder's fact holds: on main, `fno/constants.py`, `constants_channels.py`,
`constants_operations.py` and `models.py` changed in 125 commits in the last 10 days (`constants.py` alone in 99),
so byte-checking them would refuse almost every day. v4 settles this the same way (`freeze_check.RECORDED_NOT_CHECKED`
lists `fno/constants.py`).
1. **Fail closed.** The exclusions are one named list in code (like v4's). A test checks that the byte-checked set
   is the walk minus that list. A file the walk finds later is byte-checked unless it is added to the list by a
   judged change.
2. **Recorded means recorded.** FREEZE_v5_v1 lists each excluded file with its SHA-256 at the freeze, for the record
   (not checked). Their behaviour stays locked by G14's own tests: criterion 1's splice and criterion 3's equality
   with G7.
3. **`rv_table.py` stays byte-checked** although v4 lists it as recorded only. The proposal's "the three intraday
   files stay byte-checked" overrides v4's list for G14, and the record must say so. It changed 6 times in 10 days,
   so a refusal there is honest: the input reader changed, and G14 re-freezes as a new version.
4. **G14's own package is hashed in full.** The walk starts from the value-deciding files (history, capture,
   records, gap) for the imports outside the package. Every file of `fno/forecast_v5_v1/`, wiring and cli included,
   is still byte-checked, as the passed text's "this package's files" says.

## Addendum 3: G14 Amendment 2 (story text), story/g14-o1-step at 4a54c1765, round 1 of 2
**FAIL** (text), lane 1: 1 should-fix. Doc-reading tests with the token set: 920 passed, 14 xfailed.
- **The fact is MET.** `fno/daily/steps.py:43-46`: `refused` only on exit 0 with "nothing written:"; any other exit
  is `failed`. So criterion 7 as written could not hold.
- **The refusal list is complete.** It has v4's own `capture_day` refusals (today only, a scored session, before
  14:30: `forecast_v4_rules/cli.py:33-37`, exit 0) and G14's freeze states. Any other error (a file that cannot be
  read, a traceback) exits non-zero and is `failed`, which is right.
- **S1 (should fix) A broken or changed freeze record must be `failed`, not `refused`.**
  - The text puts "missing, broken, changed or dated after today" together as refusals. A missing record and one
    dated after today are planned states: before the freeze, or a freeze set for later. `refused` fits them.
  - Changed bytes, an unparseable `Frozen on:` and a walk list that differs from today's are faults on a frozen
    input, a possible tampering. They must not read as a planned state.
  - v4's capture checks no freeze at capture, so it is no precedent. The precedent is v2's: `forecast-capture.yml:7`,
    "a difference or a failed freeze check fails the run before any forecast".
  - Both labels are alerted and both end the day "with problems". The difference is the committed run log's honest
    label.
  - Fix: the split the builder proposed through the orchestrator. Missing or future-dated is `refused` (exit 0,
    "nothing written:"); changed bytes, an unparseable date or another walk list is `failed` (exit 1).
    `RecordConflict` stays `failed`. One planned flag, or two `NotFrozen` subclasses. Criterion 7 names both cases
    with a test each.

## Addendum 4: G14 Amendment 2 round 2 (the last), story/g14-amend2 at c20a14926
**PASS** (text), lane 1, 1 minor. The orchestrator named 63c9e6dbe, which is not an object in the repository. The
branch's only head is c20a14926, cut from 4a54c1765 with one Markdown commit (checked). Doc-reading tests with the
token set: 920 passed, 14 xfailed.
- **S1 closed.** Refused (exit 0, "nothing written:"): 14:30 or later; not today or not a scored session; no
  `FREEZE_v5_v1.md`; a record frozen after today. Failed (exit 1): a changed byte-checked file, another walk list,
  an unparseable `Frozen on:`, `RecordConflict`. Criterion 7 names each, with a test at the command and one through
  O1's `outcome`. Both are alerted, and the log label says which.
- **m1 (minor)** The text calls `.github/workflows/forecast-capture.yml` "v4's workflow". It runs protocol v2's G3
  capture (its header, lines 1-7). The precedent is v2's freeze check; fix the word.
