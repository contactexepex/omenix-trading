# Judge 160: A4c code (BANKNIFTY, FINNIFTY and MIDCPNIFTY at 3 pm)

**Verdict on ef043b4234c8865a3492f4ab6960d5e034c6dfe7 (`story/a4c-all-indices`; code a11f21fc and f9ea121e on top of
the text I passed, e10c811; claims `response_151_a4c-all-indices.md`): PASS.** No blocking or should-fix findings and
one wording note.

The merge waits for my A4b rule 8 check of the 16 Oct 3 pm run, as the orchestrator set.

## Gates (run by me on the SHA)

- 5,891 passed with `FNO_SLACK_BOT_TOKEN` unset.
- ruff check, ruff format --check, check_imports and `check_records.py` (5,957 files) are clean.
- `fno/quotes/recorder.py` is 340 lines.
- No existing test was changed; only `tests/quotes/index_fakes.py` and two new test files were added.

## NIFTY's 3 pm capture cannot change (orchestrator's point)

- **The golden cases.** `python tools/forecast_live_golden.py` on the SHA prints "live golden cases unchanged: case_a,
  case_b". A4's byte-for-byte baseline test (`test_recorder_baseline.py`) is untouched and passes.
- **Read in the code.** `NIFTY_SLOT = Slot()` gives:
  - underlying `NIFTY`, stem `nifty` (A4's file names);
  - `cross_check=True`, `check_listed=False`;
  - one worker, no pacer, no stop time.
  With one worker, `BookFetcher` calls `quote_book` in A4's order and takes the send time before and the receive time
  after each call, as A4 did. Failures keep their order too: `pool.map` keeps contract order. NIFTY's window
  (14:55-15:10) and retry rules are unchanged.
- **The NSE-file cache.** `NseDailyFileExpiries._file` parses a day's file once per run and returns the same rows and
  provenance as before, so NIFTY's fallback and monthly check read identical data.

## The index run, read in the code and the tests

- **Window and pace (criterion 3).** No request starts after 15:13:00, but one may start at 15:13:00 exactly
  (`sent > stop_at`; the test covers both). Expiry and chain calls also never start after the window
  (`IndexRecording.run` checks the time before each index's turn; the test covers it). Each index uses
  `RatePacer(2.5)` with 3 workers, and the indices run in turn, so the total stays at 2.5 starts a second.
- **Retry and close.** An incomplete index is retried while the window lasts; at the end it is closed as "none". A
  "not listed" or unreadable NSE file is final, with no retries. A rerun on a recorded day says "already recorded".
- **A quiet index (criterion 4).** `cross_check=False`, so it is recorded complete with invalid rows and raises no
  alert. NIFTY's cross-check is unchanged.
- **One alert per run** names every index not recorded. The command exits 1 if any is missing.
- **Routine paths (criterion 6).** `test_routine_commit_paths.py` stages each part's own files in a real Git fixture,
  and checks that CLAUDE.md gives the same paths.
- **Step 0, re-checked read-only by me with this session's Groww credentials.** `expiries()` returns 3 dates for
  BANKNIFTY (27 Oct, 23 Nov, 29 Dec), 2 for FINNIFTY (27 Oct, 23 Nov) and 3 for MIDCPNIFTY. This matches the builder's
  3 / 2 / 3, so all three names are accepted by Groww. FINNIFTY's two listed dates are exactly the two nearest
  monthlies the story needs.

## Ruling on criterion 5's wording (orchestrator's question)

- **What the code does.** With no NSE file in the last 7 days, each index's attempt asks Groww nothing and writes one
  sidecar saying why (`universe: …`). The day ends "none", with one alert and exit 1.
- **Accepted.** The story says "records nothing". The behaviour is the better reading: no quote is fetched or
  recorded, and A4's convention that every attempt leaves a sidecar with its reason is kept, so the failure is on
  record.
- **Note.** Align the story's criterion 5 to "asks Groww nothing; one sidecar per index names why" when the text is
  next touched. It is a wording change only.

## Coordination (work register)

A4c's row covers `fno/quotes/` (recorder, cli) and the CLAUDE.md 3 pm section. The NSE recorder (O6) and A16 are
untouched, and so is the O7 setup script. No duplicate.

## Addendum: head 0be99326 (16 Oct, before merge)

**The code PASS stands.** `git diff ef043b4 0be99326 -- fno/quotes tests/quotes` is empty. Everything else in the
range is main merged in (`composition.py`'s E2c account sync and the CLAUDE.md gate line are main's). A trial merge
with current main conflicts only in reviews/claude/README.md (the known artifact, both rows kept), and then 7190
passed (`-n auto`, Slack token unset), ruff and check_imports clean.

**Merge condition:** A4b's rule-8 live check of today's 3 pm run (judge 111, my check-in at 15:45 IST). The builder
reports 188 of 188 contracts read back from Drive with equal SHA and no Groww file in the repository. I do my own
check at 15:45 and merge A4c only on its PASS.
