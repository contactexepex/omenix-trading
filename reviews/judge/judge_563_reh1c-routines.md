# Judge 563: REH1c, the rehearsal of every report and of the other three routines (judge B's part)

Judge B, 24 Oct 2026. Story/reh1c-routines at 90bffac2, stacked on REH1b c317d9e7; lane 1, two judges (judge E the
rest). Story: `docs/stories/REH1-rehearsal-mode.md`, "REH1c". I did not read judge E's verdict.

**Verdict: FAIL, round 1 of 2: two should-fixes.**

**REH1b's follow-up (c317d9e7), checked on the way:** it closes my two 559 notes (a late 15:15 capture is pinned;
no Drive gives a named error in `candle_wiring`) and adds judge E's urllib3 backstop. That backstop wraps the connect
of `http.client`, urllib3's HTTP and urllib3's HTTPS connections. This is sound.

## (a) "Every report runs": rehearsal only; E8 keeps its date

- **Chosen in one place:** `rehearsed_live` and `rehearsed_not_live` are called only in `build_day_runner`. With no
  mode set, `rehearsed_live` returns the live dates unchanged with no notes, so no step is wrapped and `config.yaml` is
  untouched.
- **E8 kept real:** `KEPT_REAL = (OWNER_TIMING_STEP,)`. The other live keys (card, margin_check, premium_range_scores
  and the rest) are reports or checks, not inputs to the desk's fills.
- **The note:** it is set in `os.environ` only while its step runs, and popped after.
- **My plants:** E8 made live (caught); the note leaking past its step (caught); a real run's live dates changed
  (caught).

## (b) The recorded sources: A22, A17e, A16's clock check

- **A17e (`RecordedCueSession`):** a URL's archived copy is served once the replay clock reaches its `fetched_at`,
  checked against the snapshot-log row's SHA-256. My plant dropping that check is caught.
- **A16's clock check:** in a rehearsal it is `RehearsalClockCheck`, UNCHECKED with a plain warning, never a live
  call. My plant using the live check fails 3 tests.
- **A22 (`RecordedPreopenPart`):** the answer saved at or just after now is served once the clock reaches its seen time
  (my plant serving it early is caught). **But its bytes are never checked** (SF1).

## (c) The routines' command lists

- **One failure never skips the rest:** `run_routine` starts background commands first, then runs every other command
  regardless of exit codes, then waits for the background ones. My plant stopping at the first failure is caught.
- **The pin goes one way only** (SF2).

## SF1 (should-fix): A22's recorded answers are served without checking their SHA-256

- **Path:** `RecordedPreopenPart.answer` finds the file through its receipt (`receipts.under(...)`), then serves
  `read_file(path)`, the real Drive's bytes through `record_view()`, without comparing them to that receipt's
  `sha256`. A Drive copy that differs from its receipt would be replayed as the day's pre-open answer.
- **Why it is a should-fix:** every other recorded source checks its bytes (A4's quote files against the sidecar,
  A16b's candles against the manifest, A17e's copies against the snapshot log). CLAUDE.md requires every data file to
  be read through the verified path, and the orchestrator's brief asks for byte-for-byte replay.
- **Test it must pass:** a recorded pre-open answer whose Drive bytes differ from its receipt's SHA-256 is refused
  (`PartFailed`, named), never served. Removing the check must fail it.

## SF2 (should-fix): the routines' command lists are pinned to CLAUDE.md in one direction only, and miss DR1's commands

- **The gap in the test:** `test_every_routine_command_is_its_claude_md_section_s_own` checks that each command in
  `routines.py` appears in its section, not that each command the section names is in `routines.py`. My plant deleting
  the evening's `data-snapshot fii-dii-cash-by-session` survives (60 passed).
- **Concrete now:** this branch's own CLAUDE.md (and main's) names `python -m fno records certify closes --since 7
  --level certified --commit` in the morning routine and `python -m fno records certify closes --level provisional
  --commit` in the evening (DR1-1's shadow, judge 546.1). `ROUTINES["morning"]` and `ROUTINES["evening"]` have
  neither, and neither commits `receipts/records/`. So a rehearsed morning or evening silently skips a step the real
  routine runs.
- **Test it must pass:** every `python -m fno <command>` that a routine's CLAUDE.md steps name is in that routine's
  list, or in an explicit list of commands not rehearsed, each with its reason (for example, the pre-open's
  trading-day `python -c` check, which the rehearse runner replaces). The `data-snapshot` deletion plant must fail it.
  - The morning and evening share one section, so the test needs each command's routine. CLAUDE.md marks them "The
    morning only" and "The evening only" (reasoning only).

## Gates

- **On 90bffac2 alone (run by me):** 14,958 passed, 1 skipped, 16 xfailed; ruff, format and check_imports clean.
- **Merge condition:** merged with current main, the stack conflicts in `fno/close_read/wiring.py`. Main's read-only
  `build_stored_index_close_files()` (O9) meets REH1b's `rehearsed_close_list` source. Keep both lines. The full gates
  must then be rerun on the resolved tree; my trial merge left the markers in, so it could not be tested.

## Notes (not findings)

- **Pre-open window upper bound:** dropping `seen <= now + NEAREST` in `RecordedPreopenPart` survives. It cannot cause
  look-ahead (the answer is still held until its own time), but a part could be served a much later answer.
- **The note's scope:** `NotLiveInRealRuns` sets a process-wide environment variable. An alert the parent sends for
  another step while a not-live step runs would carry that step's note. This happens only in a rehearsal, whose posts
  are all labelled.

## Addendum 1

**Verdict: PASS** for my part, on story/reh1c-routines at 73053f9a (round 2 of 2; REH1b 67e150e3 and main merged in).
It closes SF1, SF2 and the window note.

- **SF1 met:** `RecordedPreopenPart` takes the receipt's `sha256` with the chosen path, and refuses with `PartFailed`
  ("missing from Drive or differs from its receipt") any copy that is missing or hashes differently. My plant removing
  the check fails a test.
- **SF2 met:** `test_routines.py` now compares both ways. Every `python -m fno` command named in the routine's own
  numbered steps (before any `###` subsection) must equal the rehearsed list, and the morning and evening are split by
  CLAUDE.md's markers (1b and "The morning:", 1c and "The evening:"). The two missing `records certify closes ...
  --commit` commands are added in CLAUDE.md's order.
  - My plants: the evening's `data-snapshot` deleted, and the morning's `records certify` dropped, each fail a test.
- **Window note closed:** my plant dropping the pre-open window's upper bound now fails a test.
- **The process-wide environment variable** is stated in the claims (safe while steps run one at a time).
- **Merge resolution:** the merged `fno/close_read/wiring.py` keeps O9's read-only reader with the recorded source.
- **Gates on 73053f9a (run by me):** 15,104 passed, 1 skipped, 15 xfailed; ruff, format and check_imports clean. It
  merges cleanly with current main.
