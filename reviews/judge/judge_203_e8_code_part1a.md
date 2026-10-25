# Judge 203: E8 code part 1a at 0516cfb0 (clock, mark snapshots, sealed availability, timed reads, price cap)

Judge C. Branch `story/e8-code-part1`, head `0516cfb0`. Lane 1. The story text passed at 78a51301 (judge 193
addendum 6). The new package `fno/desk/owner_timing/` has 9 files, the largest 148 lines, plus 43 tests in
`tests/desk_owner_timing/`. The step itself (DayStep), the funds re-check, the exits and the verdict account come in
part 1b.

**Verdict: FAIL, two should-fixes.** Both would change fills in normal running. Everything else checks out.

## Gates (trial merge with origin/main, 23d802a7)

| Gate | Result |
|---|---|
| `env -u FNO_SLACK_BOT_TOKEN python -m pytest -q -n auto` | 6,633 passed in 2 min 33 s |
| `tests/desk_owner_timing` | 43 passed |
| ruff check, ruff format --check, check_imports | Clean |
| merge | Clean (`docs/WORK_REGISTER.md` auto-merged) |
| size | No file over 350 lines (largest 148) |

## Should-fix 1: in a shallow clone, GitSealLog gives every seal the wrong time

`GitSealLog._committed_at` reads `git log origin/main --format=%cI --reverse -S <hash> -- <seals file>` and takes the
first hit. In a shallow clone, the boundary commit carries the whole file, so every seal's "first commit" is that
boundary commit, with the boundary's time.

**Probe** (a real repository, seal rows added on 11, 12 and 13 Oct, then a later commit on 15 Oct):

| Seal | Full clone | `--depth 1` clone |
|---|---|---|
| h1 | 2026-10-11T09:03 | **2026-10-15T09:03** |
| h2 | 2026-10-12T09:03 | **2026-10-15T09:03** |
| h3 | 2026-10-13T09:03 | **2026-10-15T09:03** |

So for an order whose T is earlier than the boundary, `sealed_before(T)` returns None. `SealedDriveAvailability.away`
then answers False ("nothing sealed yet: every session counts as available"), and an away day is filled as if the
owner were there.

This happens in normal running: cloud sessions clone with limited depth (story X's shallow-message line in
`docs/JUDGE.md`; 50 commits by default for a new session), and main takes far more than 50 commits a day.

**Fix:**
- `GitSealLog` refuses in a shallow repository (`git rev-parse --is-shallow-repository`), raising
  `AvailabilityRefused` with "shallow clone: run git fetch --unshallow origin main". That is a step failure, so new
  entries fail closed and exits still run.
- The same rule applies anywhere else part 1b reads seal times.
- Add a test on a real `--depth 1` clone, like `tests/test_history_guard.py`.

## Should-fix 2: TimedStore abandons writes, and a late write can overwrite a newer one

`TimedStore.put` runs the write in a daemon thread and gives up after the cap. The thread goes on, and the write can
land later. Part 1a has no caller of `put` in the package (checked with grep), but part 1b's writes will go through
E2c's `PrivateFiles.push`, which overwrites whole account files in Drive. Two paths follow:

- The fill step's put of a book's account times out. The step fails, and the run goes on to `exits`, which pushes the
  same account file. The abandoned fill write then lands and overwrites the exit. The exit is lost from Drive, and
  the next run reads the wrong positions.
- A late write can also land after a rerun has written the correct state.

Reads are safe to abandon, because their late results are ignored. Writes are not.

**Fix:**
- `TimedStore` caps reads only (`get`, `checksums`, `folders`); `put` is not offered on the timed path.
- Part 1b states how its writes are bounded without being abandoned. One way: all writes come after all reads, go
  through E2c's journal, and use write-once new paths, so that a late write can never replace newer content. A
  time-out before any write then leaves nothing behind.
- A test shows that no write is started after a timed-out read.

## The orchestrator's two questions

- **Can the daemon thread leave a late write after the step fails?** Yes, through `put` (should-fix 2). For reads, the
  thread's late result is dropped (`outcome` is no longer read) and the step has already failed, so it is harmless.
- **Can "first published commit on origin/main" be faked by a local commit?** Not by an unpushed one: the log reads
  `origin/main`, never `HEAD`, so a local commit that was never pushed never counts.
  - Two limits remain. In a shallow clone it gives wrong times (should-fix 1).
  - The time is the committer time, which whoever makes the commit can set. A seal pushed with a back-dated committer
    time would count. That is deliberate forgery, not normal running; the run writes its own seal, and O8 keeps
    GitHub push receipts if a stronger check is ever wanted. A note, no change.

## Checked and fine

- **Clock:** 15:16 to 09:30 / 09:45 / 10:15 of the next session; muhurat-only days skipped; Friday to the next session.
- **Mark snapshots:** they use A4's own parser and `quote_validity`, never a copy. A late copy and a quote requested
  before the mark are dropped. The A4 stand-in is used only inside the on-time window.
- **Availability:**
  - lines are normalised as the text says;
  - a sealed-prefix mismatch refuses with the repair message;
  - the sealer never re-seals over a mismatch and skips an unchanged file;
  - the salt line is required, with at least 32 hex digits.
- **`ApprovedLimit`:** "missed, price moved" one paisa past the limit; fills at the limit exactly.
- **`call_within` timing:** it caps the whole call, so a trickling read cannot outlast the cap. This answers judge 193
  addendum 6's note. It is tested for a hung read, a trickling read and a passed deadline.
- **Read-only:** the package's import closure reaches no broker order, position, margin or funds call.

## My view on part 1b's plan (asked before the code)

The plan: a fresh C2 check for the fill day, the price cap kept at the decision's approved entry, and per-leg validity
in place of the whole-snapshot "complete" test for A16 copies. **Sound, with four conditions** (reasoning only):

1. **It is a check, not a new decision.** The fill-day C2 run must write no decision record that E6, S1 or S2 could
   count. It gives fill or miss only ("insufficient funds", "over risk cap").
2. **Keep E4's `refusal()` as it is for `e4_1515`.** That view must stay bit-for-bit today's E4 (criterion 9). The new
   rule applies only to the owner-timing views.
3. **Per-leg validity covers every leg of the trade, plus what C2 and C4 read.** All legs or none (rule 5) still
   holds. The spot, futures or VIX values that the stressed margin and the caps use must also be valid in the same
   due-mark copy, or the entry is "missed, no quote". Other strikes in an incomplete A16 copy may be missing.
4. **Earlier fills come first.** The C2 check sees that morning's earlier fills, in the oldest-first order of rule 11,
   as criterion 6's "pending fill earlier that morning" fixture already requires.

Would the two should-fixes change a trade? Yes. Should-fix 1 fills on away days. Should-fix 2 can lose an exit.
Re-review: those two only.

## Addendum 1: fixes at c9f32507: PASS

The only change since 0516cfb0 is `seal_log.py`, `timed_reads.py` and two test files (+69, -11).

**Should-fix 1: closed.**
- `GitSealLog.sealed_before` first checks `git rev-parse --is-shallow-repository`.
- Anything but `false`, including an error or empty output, raises `AvailabilityRefused` with the unshallow message,
  so the step fails, entries fail closed and exits run.
- `latest()` and `add()` need no commit time (the sealer compares only the seal's content), so they rightly skip the
  check.
- The new test builds a real origin with two seal commits and a `--depth 1` clone. The clone refuses and the full
  repository answers.

**Should-fix 2: closed.**
- `TimedStore` caps only `get`, `checksums` and `folders`. `put` raises `ReadOnlyStoreError` and never starts a write.
- A test holds a read inside `AvailabilitySealer` until it times out, then releases it, and shows that no seal is
  added.

**Gates** on a trial merge with origin/main:
- `tests/desk_owner_timing`: 46 passed.
- Full suite with `-n auto`: 6,859 passed in 2 min 35 s.
- ruff check, ruff format and check_imports are clean.

**Dependency, not this head's:** the routine's own unshallow at the start of the run lands in O1, with the O1 builder.
Until it does, a shallow routine session gets a refused fill step every day: no new entries, exits still run. It
fails safe, but it would stop paper trading, so O1's change is needed before E8 goes live.

E8 part 1a passes. Part 1b is next, under the four conditions in this file.

## Early view on part 1b's design (asked through the orchestrator; not a verdict, reasoning only)

On the builder's points 2, 4 and 6 and the live switch.

1. **Do not rebuild the order the next session (point 2).** `OrderBuilder` run on the fill day reads that day's pack
   and spot, so it can pick other strikes, other units or another approved entry than the card showed. The trade
   filled must be the trade decided at T. So `entry_pending` stores, at decision time:
   - the decided legs and units;
   - the approved entry (the price cap);
   - the decision's ID;
   - the card's T.

   The E8 step fills exactly those, and never re-decides. The fill-day C2/C4 run is a check on that stored order
   (condition 1). A test: the fill-day pack moves spot by 300 points and the filled legs are still the decided ones.
2. **`e4_1515` stays today's E4 (criterion 9).** If E3's fills step now writes `entry_pending` for the verdict, the
   15:15 fill must still be computed by today's E4 path into the `e4_1515` view account, bit for bit.
3. **Exits.**
   - One exit order ID per position, idempotent. The 15:15 exits step and E4's `due_exits` path (point 6) must never
     both alert or both fill the same exit.
   - T is the first delivered alert's `ts`, resent until delivered.
   - A pending exit retries at each later mark, never counted as risk reduced until it fills.
4. **Writes (point 4): acceptable, read then write per item, with two conditions.**
   - Each item's write is all or nothing on disk: every leg and the cash row in one journal entry, so a crash or
     time-out between items never leaves half a fill.
   - A re-run finds completed items by their fill IDs and skips them.

   Since writes are synchronous and never abandoned, the late-write problem of should-fix 2 is gone.
5. **The live switch `desk.owner_timing.live` (default false).** Good as a safe cut-over, with three rules.
   - It is an allowed `config.yaml` key, and turning it on is an owner decision row.
   - Cut-over: decisions committed after the switch's commit use E8; earlier ones finish under E4. None is ever
     filled twice.
   - **S1's freeze needs it on.** The owner's row (`docs/DESK_DECISIONS.md:181`) makes the 60-minute fill the
     verdict, so a frozen evaluation with the switch off would quietly use the 15:15 fill. Add it to S1's
     preconditions, beside the entry rule.
   - Say whether the step still seals the calendar while the switch is off. Recommended: yes, so the seal history
     exists before go-live.

## Addendum 2: E8 part 1b at 65ec0b05: FAIL, one should-fix

Branch `story/e8-code-part1` at 65ec0b05: part 1a, then the hooks (ec2ef783), the package (49b8eda9) and the early
view (beb89fe3), merged with O1 d123dbb9 and main.

**Gates** (trial merge with origin/main, d4982347; E4d's 35c43e26 is on main but not on this head):
- `-n auto`: 7,057 passed in 2 min 49 s.
- ruff check, ruff format and check_imports are clean.
- The largest file in `owner_timing` has 148 lines.

### Should-fix 3: the due-mark fill skips E4c's and E4d's entry checks

`DueFill.price` prices each leg with `price_leg` on its opening side only. It never calls `entry_problems` or
`taken_units` (`fno/desk/entry_check.py`); a search of `fno/desk/owner_timing` finds neither. So at E8's real fill:

- **E4c (decision 43).** A protective (bought) leg must also be sellable back at the snapshot it fills at. E8 fills an
  entry whose protection has no bid at 10:15. This is the trade E4c exists to refuse: the next exit review marks it
  "protection unverified".
- **E4d (ChatGPT review 126, judge 205).** A book's entries at one snapshot share its displayed size. Two entries of
  one book needing 65 units each against an ask size of 100 at the same due mark both pass `price_leg` alone, and
  130 units fill against 100. E8 makes this more likely than E4 did, because every 15:00 decision of a book lands on
  the same 10:15 mark.

`entry_check.py` says itself that it "depends only on the snapshot it is given, so E8 can apply it at each of its
snapshots", so the fix is one call, not a new rule.

**Fix:**
- In `DueFill.price`, after pricing, run `entry_problems(mark snapshot, order.legs(), units,
  taken_units(book fill rows, mark snapshot, trade_id))` with main's E4d signature after the merge.
- Any problem is "missed, no quote" with E4c's or E4d's code in the reason.
- Earlier fills at that mark come first (rule 11 order), so `taken` sees them.
- Two tests at a due mark:
  - a protective leg with no bid misses;
  - two entries of 65 units against a displayed 100: the first fills, the second misses with `size_shared_in_book`.

Would it change a trade? Yes: it opens trades E4 would refuse.

### The builder's two pushbacks: both accepted

- **(a) T from T1's write-once delivery record, not from `entry_pending`.** Correct: the card is posted after the fills
  step, so T does not exist when `entry_pending` is written.
  - `DeliveredCards` takes the day's first attempt that Slack accepted, skipping test posts, from T1's committed
    record, so a later post cannot move T.
  - Early view 1's real point, that the order must never be rebuilt, is met by `KeptOrders`. The legs, units, cap,
    decision ID and decision time are written once, before the `entry_pending` event, and filled as kept.
- **(b) Switch by day (`daily.live_from.owner_timing_fills`), not by commit time.** Correct and simpler. Each decision
  is handled once, on its own day, by that day's rule; a rerun of an earlier day keeps that day's rule; and a future
  `live_from` set by the go-live row is clean. S1's precondition becomes "`live_from` set, on or before the freeze"
  (sent to S1's text owner).

### Judge 203's four conditions: met

1. **A check, not a decision.** `FillDayRisk.miss` calls `manager.evaluate` and returns fill or miss. Nothing is
   recorded as a decision.
2. **E4 unchanged when E8 is not used.**
   - `EntryDesk` and `ImmediateExits` are the defaults.
   - `_unfilled` blocks entries only when the step's result is failed or refused (not when it is `not_live`, ok or
     absent).
   - Settlement still runs before `defer`.
   - Today's timetable and daily tests pass.
3. **Validity of what C2 and C4 read.** The spot must exist, and every contract held and proposed must be quoted in
   that copy, or the entry is "missed, no quote". C4's maximum loss is recomputed on the fill prices.
4. **Earlier fills first.** Items are sorted by order time. Each item's journal write (all legs, then the outcome
   event) completes before the next item's check. A rerun finishes an item that already has fills without
   re-checking it.

### Known limits (stated by the builder): accepted as notes

- **A second exit alert after a failed alert record.** If the alert record fails after Slack accepted the post, a
  rerun posts again with a later T. That gives a later fill, the cautious direction. Note only.
- **Legs of a non-near-month expiry miss with "no quote"**, because A16 records only the near-month future. This is a
  systematic miss for any strategy that trades the next month. Report it under its own reason ("no future for that
  expiry"), not inside "no quote", so the owner sees it; the remedy is A16 adding the next future. Recommended,
  reasoning only.
- **On a day with no snapshot, an exit is not ordered until the next 15:15.** One day later, the same as E4 today.
  Note.
- **The exit alert text** uses the first part of the exit reason before ":". The code judge should confirm that no
  exit rule's reason puts a price before its first colon (the card rule).

Re-review: should-fix 3 only. The E4/E2c builder's agreement on the hooks is still awaited through the orchestrator.

## Addendum 3: E8 part 1b at 09d14c43: PASS

Two commits since 65ec0b05: 6e85ef7a and 09d14c43.

**Should-fix 3: closed.**
- `DueFill.price` misses an entry with "missed, no quote" only when a leg has no quote or an invalid one (A4's rule).
- It then runs E4c's `entry_problems` with E4d's `taken_units` (the book's fill rows) on the due mark's own copy,
  before pricing or any fill, and misses with the first problem's own code.
- Misses now keep the copy's ID and hash, and the fixed miss reasons sit in one table, `outcomes.MISSED_REASONS`.

**Tests.**
- **E4d:** two entries of 65 units each against a displayed size of 100 at one mark. The first fills its 4 legs; the
  second misses with `size_shared_in_book (..., 65 already taken in this book at this snapshot)`.
- **E4c's thin size:** an ask size of 64 against 65 units on the protection gives `protection_not_buyable`, not
  "no quote".

**The orchestrator's request, a protection-with-no-bid case:** there is no test of its own on this head. I ran one as
a probe in a scratch checkout. A protection bid size of 64 against 65 units gives
`protection_not_sellable (NIFTY26102725200CE, 65 units)` and writes no fill, so the behaviour is right. A literal "no
bid" is a one-sided quote, which A4 treats as invalid, so that case is correctly "missed, no quote". The builder
should add the probe as a test in the next commit:

    marks.put(DUE, fly_rows({(25200, "CE"): {"bid_qty": 64.0}}))
    assert apply(root, entries).startswith(PROTECTION_NOT_SELLABLE)

This is a note, not a blocker: the code path is E4c's own tested function, and the probe passes on this head.

**Hooks:** O1's builder and the E4/E2c builder both agreed (through the orchestrator; 73 E4 tests pass on 6e85ef7a).

**Gates** (trial merge with origin/main, ae7fc6ad):
- Full suite with `-n auto`: 7,060 passed in 2 min 55 s.
- ruff check, ruff format and check_imports are clean.
- The merge is clean.

**E8 part 1 (1a and 1b) passes.** The notes of addendum 2 still stand:
- report the next-month future miss under its own reason;
- the code judge checks the exit-alert text;
- O1 fetches the full history before go-live;
- `live_from` is set on or before S1's freeze.

Under quality rule 9 (money path), ChatGPT reviews it next.

## Addendum 4: E8 part 1b at b79dee94 (the notes of addenda 2 and 3): PASS stands

One commit since 09d14c43, b79dee94.

- **No future for that expiry.** `_missing_reason` returns `MISSED_NO_FUTURE` only when every missing contract is
  quoted in the copy and its expiry has no valid future there; any other gap is still "no quote". The reason is in
  `MISSED_REASONS` (9 reasons, with a test that the table and the code agree). A parametrised test covers a missing
  level against its reason.
- **The exit alert never shows a figure.** The reason before the first colon is used only if it is plain lower-case
  words (`[a-z_ ]+`); anything else becomes "exit ordered". The test checks for "(exit ordered)" and that no digit
  appears after the trade ID.
- **Protection with no bid at the mark.** A one-sided protective quote (ask, no bid) is no longer "no quote". It goes
  to E4c's `entry_problems`, and its opening-side check fails because A4 refuses a one-sided quote, so it gives
  `protection_not_buyable`, with its own test.
  - **Keeping E4c's code is right.** It is exactly what E4c gives for the same quote at 15:15 (`_side_problem` with
    `opening=True` gives `PROTECTION_NOT_BUYABLE`), so E8 adds no second rule and the two paths stay comparable.
  - The name reads oddly for a quote that has an ask, but changing it would be E4c's change, not E8's. Note only.
  - Crossed or two-sided invalid quotes, and quotes with no price on the opening side, still give "no quote".
- **Gates** (trial merge with origin/main):
  - full suite with `-n auto`: 7,062 passed in 2 min 52 s;
  - ruff check, ruff format and check_imports are clean;
  - the merge is clean.

Addendum 3's PASS stands at b79dee94. Next is ChatGPT's review (rule 9).

**Addendum 4, continued: cfd6a95b.** This commit only adds a test (+8 lines in `tests/desk_owner_timing/test_entry_fills.py`). It is addendum
3's probe: a protection bid size of 64 against 65 units gives `protection_not_sellable`, and the account has no fill
row. At cfd6a95b the package's tests give 103 passed, and ruff check and format are clean on the test folder. No code
changed since b79dee94, whose full-suite run above (7,062 passed) stands.

**The PASS covers b79dee94 and cfd6a95b together.**

## Addendum 5: E8 part 1, the delta after ChatGPT review 128 (responses 280 and 286), at 36b31327: PASS

Branch `story/e8-code-part1` at 36b31327, merged with main of 21 Oct. Claimed as 203.5 in the number registry. The
E8 commits since the PASS head are 12360bd9 and cc953337; the rest of the delta is merges of main, judged in their own
stories.

**No owner-timing code changed.** `git diff cfd6a95b 36b31327 -- fno/desk/owner_timing` is empty. The delta is:
- tests;
- the story text;
- responses 280 and 286;
- a test helper move;
- an optional entry-desk factory in O11's replay harness. Its default is unchanged: `EntryDesk(CHARGES, clock)`.

**Review 128's points, each checked against its test or text:**

1. **The live boundary** (`test_live_boundary.py`).
   - A decision the day before `live_from` is filled by E4 and never queued. One on `live_from` is handed over and
     filled at the 10:15 mark. Each is run twice and ends with exactly 4 fills.
   - An E4 exit still waiting across the live date: on the live date, one alert and no close; at the next 10:15, E8
     closes the last leg. 4 closing fills, one per leg, so no leg is closed twice.
   - The rule is in the story's rule 11.
   - This matches `LiveFromEntries` and `LiveFromExits`, which choose by the day of the snapshot (addendum 2,
     pushback b).
2. **An order recovered two sessions later** keeps the card's T and its original due mark. It fills from that mark's
   copy or misses "no quote", and the next day's copy is never read (`marks.read == [DUE]`).
3. **A waiting exit keeps its risk** (`test_waiting_exit_risk.py`), through the real `FillDayRisk` and
   `load_risk_book`.
   - With only the protection still waiting, the next morning's risk book holds exactly 65 units of it, and a second
     entry misses "over risk cap".
   - With an alert delivered and nothing filled, all four legs are held, and a second entry misses.
   - The builder states the limit plainly: the breach comes from the open-trades cap. It proves the units are counted;
     it does not separately prove that stress-loss and margin size the leftover protection. Those rules read the same
     `RiskBook.open_trades`, so I accept it (reasoning only).
4. **Two copies.** A16's copy (ask 101) wins over a cheaper A4 stand-in (ask 81) at the same mark, and the snapshot
   ID and SHA-256 are A16's. The stand-in is shown to be usable on its own, so A16 wins by rule, never by the price
   that favours the trade.
5. **Equal T.** The story's "Order of a morning's fills" says: oldest T first; equal T values in the step's fixed
   order, books in config order, then entries before exits, then the records' order. That is exactly what the code
   does: a stable `sorted` by T over `_pending()`, which loops books, then entries, then exits. Entries before exits
   at an equal T is the cautious order, because the risk check still sees the open position.
6. **Part 2's report text.** One cohort with four views, R = 60 the verdict. The overnight-move split covers opened
   against price-moved misses and net per fill and per opportunity. No-card and away misses stay in the denominator
   on their own rows. The edges (0.25% and 1%) are labelled reasoning only. No new filter, scheduler or service.
7. **O11's E8 xfail is now a real check** (`test_replay_owner_timing.py`).
   - 16 Oct is replayed with E8 live: the trade's outcome is `entry_pending` with the 60-minute hand-over reason, no
     fill row is written, the order is kept at `book1_rules/orders/<trade>.json`, and no alert is sent.
   - The step sits right after `quotes`.
   - Removing `@missing("E8")` in `test_expected_missing.py` is right now that a real check exists.

**Gates** on a trial merge with origin/main (8fcdded6):
- full suite with `-n auto`: **8,285 passed, 2 failed, 17 xfailed**;
- ruff check, ruff format, check_imports and check_numbers are clean.
- The 2 failures fail the same way on origin/main alone, run in a clean worktree, so neither is E8's:
  - `tests/forecast_scoring_v4/test_g7_series.py::test_v1_reads_only_the_a16_rows_it_is_given`;
  - `tests/market_read_models/test_forecast_history_page.py::test_every_point_is_the_reports_own_scored_count_and_mean_brier`.

**PASS.** E8 code part 1 may merge once main is green, or with exactly these two failures if the orchestrator rules so.
The merge procedure's full suite runs on the merged tree.

Still open before E8 goes live (from addenda 2-4, unchanged):
- `live_from` is set by an owner row, on or before S1's freeze;
- O1 fetches the full history before the day;
- A16 runs live.

## Addendum 6: E8 at 3c30e5d0 (SessionOffsetClock for FL1): PASS

One commit since 36b31327. It touches `fno/desk/owner_timing/clock.py` and `exit_fills.py` and adds 5 tests in
`test_clock.py`.

- **`RetryingClock` is a new interface**: `FillClock` plus `marks_from`, which `OwnerTimingExits` already used.
  `OwnerTimingClock` now implements it, and `exit_fills.py` only changes its type hint. The pattern now has two uses.
- **`is_fill_session` and `next_fill_session`** were moved out of the class word for word. `OwnerTimingClock` calls
  them, so its behaviour is unchanged: the earlier clock tests pass as they were.
- **`SessionOffsetClock`** (FL1's time exit):
  - the mark `at` on the Nth fill session after the order's day, skipping holidays and muhurat-only days through the
    same `next_fill_session`;
  - no reaction time, no availability and never a miss;
  - a leg without a quote is retried at every later mark, through the same `OwnerTimingExits`;
  - the constructor refuses N < 1, a time off a 15-minute mark, and a mark after the last fill mark.
  - Tests: N+1 and N+3 across a holiday; retries at later marks; the three refusals.
- **Not wired into E8.** No file in `fno/` uses `SessionOffsetClock` outside `clock.py` (checked with grep), so nothing
  E8 fills changes.
- **Gates** on a trial merge with origin/main (8461cb41):
  - `tests/desk_owner_timing`: 117 passed;
  - full suite with `-n auto`: 8,291 passed, 2 failed, 17 xfailed. The same 2 failures as addendum 5, both main's own;
  - ruff check, ruff format, check_imports and check_numbers are clean.

Notes (no change needed):
- The class sits in E8's package, which joins S1's `frozen_files` at the freeze. If FL1 later needs a change to it,
  that is a frozen-file change.
- FL1's own text is still FAIL (judge 403 addendum 403.1). If FL1 does not land, this class has no caller and should
  go.
- Building it here, by E8's clock owner, keeps one builder per function.

**PASS at 3c30e5d0.** Addendum 5's merge conditions and go-live items stand.
