# Judge 557: REH1a, the rehearsal mode's safe frame (judge B's part: clock, Drive, import closures)

Judge B, 24 Oct 2026. Story/reh1-rehearsal at b2e5337d (O1 builder); lane 1, two judges (judge E covers git, Slack and
the guard). Story: `docs/stories/REH1-rehearsal-mode.md`, "Claims / REH1a". I did not read judge E's verdict.

**Verdict: FAIL, round 1 of 2: one should-fix that needs only a test.** The code in my three areas is correct.

## (a) The clock change

- **Real run unchanged:** I read all 31 replacements in 25 modules.
  - `now_ist()` is `_clock().astimezone(IST)`, with `_clock = datetime.now(UTC)` by default: the same instant as
    `datetime.now(IST)`.
  - `now_utc()` replaces `datetime.now(UTC)`, and `now_utc().astimezone()` replaces `datetime.now().astimezone()`.
  - `today_local()` (`_clock().astimezone().date()`) replaces `date.today()`. Every one gives the same value.
- **Money paths:** the school's fills, seals and late-rerun mark read `IstClock.now()`, which is `now_ist()`
  (`fno/school/wiring.py:42`). The quote recorder, close read, price ranges and margins take injected `now` callables
  whose defaults are `now_ist`. None changes in a real run.
- **Forbid-test:** my search finds no remaining wall-clock read in `fno/`: no `datetime.today()`, `time.time()`,
  `Timestamp.now`, aliased `datetime` import, `utcnow` or wall-clock `fromtimestamp`. The `fromtimestamp` uses convert
  NSE, Yahoo or Groww stamps, and `pyotp`'s TOTP sits inside the Groww provider, which the guard refuses.
  - **It can be bypassed by forms it does not match:** my plant `datetime.today()` in `close_read/reader.py` passes
    `test_one_clock.py`, and so would `time.time()` or `from datetime import datetime as dt; dt.now()`. None exists
    today, so this is a note, not a finding. A broader pattern (`\.today\(`, `\bnow\(\)` on a datetime alias,
    `time\.time\(`) would close it (reasoning only).

## (b) The Drive side

- **The dryrun store:** `build_owner_drive` is the only constructor of an owner (writable) store. `drive_check.py` and
  the service-account path build `GoogleDriveStore`, whose `put` raises `ReadOnlyStoreError`. Every `put` in
  `fno/storage` goes through a store, and the only writers on the upload store are `put` and `replace_contents`.
  `DryrunDrive` routes `put` under `dryrun/<run_id>/`, hands out only its own file IDs, and refuses
  `replace_contents` of any other ID.
- **The HTTP guard** allows `www.googleapis.com` writes by design, so the containment rests on that single
  constructor, which holds.
- **Point-in-time reads:** a real file is served only when its receipt's `written_at` is at or before the replay
  clock. Own files come first, and `paper/` is read as of now (the stated limit). The story text says "commit time";
  the code uses the receipt's save time, which is when the bytes existed and is no less strict. This is a wording note.
- **My plants (`tests/rehearsal`):**

  | Plant | Result |
  |---|---|
  | `put` writing the real path | 2 failed |
  | visibility ignoring the time | caught |
  | a real file ID handed out (a replace of a real file) | 2 failed |
  | no dryrun store | 2 failed |
  | `get` ignoring visibility | caught |
  | everything visible | caught |

## (c) Import-closure split

- **Closures computed by AST** for `drive_wiring`, `alert_label`, `card_label`, `report_label`, `process` and
  `http_guard`: 1 to 10 modules each, with no risk, cost, desk, books, AI or provider module.
- **The two roots:** `storage.wiring`'s closure grows from 60 to 65 modules, and `composition`'s from 121 to 127, with
  no new risk or cost module. `waits` (books and costs) is chosen only in the daily run's root, which already imports
  them. `guard` (895 modules) is imported only by the rehearse command.
- **Existing tests:** the read-only closure tests (intraday, intraday backfill, owner timing, ft1, book1 no-AI) pass.

## SF1 (should-fix, test only): nothing tests that a rehearsing process installs the replay clock and the HTTP guard

- **The plants that survive:** in `fno/rehearsal/process.py`, replacing `install_clock(ReplayClock(mode.state))` with
  `pass` leaves `tests/rehearsal` at 26 passed. Replacing `http_guard.install()` with `pass` also leaves 26 passed.
- **Why it matters:** the guard's live probes only ask the policy function `allowed()`. They never check that this
  process refuses a call or runs on the replay clock. So a rehearsal whose children skipped either install would pass
  the guard, then:
  - reach Groww, NSE or Anthropic live (acceptance 3);
  - run on the real date instead of the replayed one.
  Both are the safe frame's purpose, and the Claims state that `process.py` does this.
- **Test it must pass:** a `python -m fno` child started with `FNO_REHEARSAL` set, running a trivial command, sees
  `now_ist()` at the replay clock's time on the replayed day, and gets `RehearsalCallRefused` for a live URL. Each
  plant above must fail it. Better (reasoning only): `guard.py`, which already runs in such a child, checks both
  itself, so a rehearsal stops before its first step if either is missing.

## Gates (run by me on b2e5337d merged with current main, dd33adf4)

14,911 passed, 1 skipped, 16 xfailed; ruff, format, check_imports and check_records clean. The merge with main is
clean.

## Addendum 1

**Verdict: PASS** for my part, on story/reh1-rehearsal at d362737c. Round 2 of 2: one commit on b2e5337d. It closes SF1
and the forbid-test note.

- **SF1 met:** `python -m fno rehearse check` runs inside a process started through the real entry point with the mode
  set. `process_problems` reports a problem unless `fno.models._clock` is a `ReplayClock` reading within 60 s of the
  shared replay time, and a live `requests.get` to NSE raises `RehearsalCallRefused`. Any other exception counts as
  "attempted".
  - `daily run --rehearse` now runs this check in the rehearsal checkout before the first step, replacing the old
    `-c` child, which never went through `install_process`.
  - My plants: `install_clock(...)` replaced by `pass` fails `test_process.py`, and so does `http_guard.install()`
    replaced by `pass`.
- **Note closed:** `test_one_clock.py` is now an AST check that resolves aliased imports. My `datetime.today()` plant
  in `close_read/reader.py` fails it, and so does a planted module with `import time as t; t.time()`.
- **Gates on d362737c merged with current main (run by me):** 14,986 passed, 1 skipped, 15 xfailed; ruff, format and
  check_imports clean.
- **Merge note:** REH1b (judge 559, PASS) is stacked on b2e5337d, not on this commit. Its merge with d362737c must keep
  `rehearse check` as the guard step in `daily.py`, which both branches touch.
