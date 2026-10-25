# Judge 559: REH1b, the rehearsal's recorded sources (judge B's part)

Judge B, 24 Oct 2026. Story/reh1b-sources at 311bc999, 3 commits on REH1a b2e5337d; lane 1, two judges (judge E takes
the push receipts and git). My focus: the recorded sources' timing, NSE's archive, and the git date shim. I did not
read judge E's verdict.

**Verdict: PASS for my part.** No blocking or should-fix finding. It merges as one stack with REH1a, whose SF1 (judge
557) is still open. That SF1 matters here too; see the notes.

## (a) The recorded sources: byte for byte, at their own times, no look-ahead

- **A4's 3 pm parts and the 15:15 capture (`RecordedRecorder`):**
  - Each attempt's quote file and sidecar are the record's own bytes. Groww's files come through `DriveOnlyQuoteStore`,
    checked against the sidecar's SHA-256, and a differing file is refused (tested).
  - `_publish` sleeps until the attempt's own `finished_at` before writing anything. The canonical marker is
    republished only for the attempt the record's marker names.
  - With no in-window attempt, the day ends "none", as A4 does.
- **A4h's index list (`RecordedCloseList`):** it serves the day's raw answer saved within [now - 5 s, now + 10 min],
  then sleeps until its save time. The 15:40 read gets the first answer and the 16:00 recheck the recheck; any other
  moment raises `rehearsal:NOT_RECORDED`.
- **A16b's candles (`RecordedCandles`):** the same window on the manifest's `fetched_at`. The bytes are checked against
  the manifest row's SHA-256, and a window the day never asked for is the back-fill's own `CandleCallFailed`.
- **The recorded sources read the real record through `record_view()`** (`RecordReader`, writes refused), not
  through REH1a's visibility filter. Each gates by its own recorded time instead, which is the right rule for a
  source that replays a call.
- **My plants (`tests/rehearsal`):**

  | Plant | Result |
  |---|---|
  | close served before its save time | 2 failed |
  | close window unbounded ahead | caught |
  | candles served early | caught |
  | candles without SHA check | caught |
  | quote attempt published early | caught |
  | record view writable | caught |

## (b) NSE's archive never fetches or archives

- **`build_nse_source`**, the one builder of every archive source the daily steps use, gets `NotRecordedSession` when
  rehearsing. Its `get` and `head` raise `NotRecorded`, an `InvalidURL`, which the source's retry policy treats as a
  request that could never be sent: no retry, no wait, `RawSourceUnavailable`, nothing archived (the library archives
  only bytes it received). The archive store is REH1a's dryrun store anyway.
- **Plants:** a live session (3 failed); `NotRecorded` made a retryable `ConnectionError` (caught).

## (c) The git shim cannot leak into a real run

- **Where it lives:** `install_git_shim` writes into `~/.fno/rehearsals/<run_id>/bin`, and only the child's `env`
  dict carries the `PATH` that puts it first (`daily.py:45-46`). The parent's `os.environ`, the source checkout and any
  git config are untouched, and no real wiring names it.
- **What it does:** it sets both git dates from the shared offset file and then runs the real git, found on `PATH`
  without its own folder.
- **Plant:** the shim ignoring the offset fails `test_git_dates.py`.

## Gates (run by me on 311bc999 merged with current main, 21905011)

15,001 passed, 1 skipped, 15 xfailed; ruff, format, check_imports and check_records clean. The merge with main is
clean.

## Notes (not findings)

- **My plant on the 15:15 capture survives:** dropping `finished_at >= now` in `RecordedRecorder._next` passes every
  test. It cannot cause look-ahead (a chosen attempt is still held until its own `finished_at`). It would only let a
  late capture take an attempt that finished before it, where the code now says "window closed". A test of a late
  capture would pin the rule.
- **Direct sessions:** five modules build their own `PacedSession()` or `requests.Session()` outside
  `build_nse_source` (circulars, flow history line 94, global cues, pre-open, the public provider). In a rehearsal only
  REH1a's HTTP guard stops them, and judge 557's SF1 is exactly that nothing tests the guard's install in a rehearsing
  process. Fix that SF1 before this stack's first real rehearsal.
- **A failure that is loud but unclear:** `candle_wiring` and `quote_wiring` call `build_owner_drive().record_view()`;
  with no Drive settings this is an `AttributeError`, not a named line. A rehearsal needs Drive anyway, so the step
  still fails loudly, just unclearly.
