# Judge 507: MS-P1j, the fleet join-up (first judge)

**Scope:** story/ms-p1j-fleet at 7f757504 (builder session_01CmKJ6taCLzfEGg7wt6RC4N); the MS-P1j section and its
Claims. It covers `fno/school/fleet/*`, `fno/school/wiring.py`, `fno/school/cli.py`, two lines in `fno/cli.py`, the
tests, and two touches of f (`OwnedFill.is_exit`; `TicketBook.price`/`open`/`close`). Lane 1, money piece (fills,
exits, records): first of two judges, independent of judge K. Round 1 of 2. The builder's round-3 list (already ruled
by the orchestrator) is not re-raised.

**Verdict: PASS.** Nothing blocking, no should-fix. Notes below.

## Gates (my run)
- pytest -n auto: 11795 passed, 9 skipped (the real acceptance test until d's `entries` merges), 16 xfailed.
- `ruff check`, `ruff format`, `check_imports` and `check_records` (8372 files) are clean.

## The three checks asked for
1. **A crash anywhere between the seal and the counts' commit is completed once.**
   - A sealed session is never decided again: `dashcam.find(DECISIONS)` leads to `_finish`.
   - `_finish` is rebuilt from the sealed records and the ledgers (`Recorded`). A recorded opening or closing is read
     back, never re-priced. A recorded position is never opened again. Outcomes and drift are each sealed once. The
     counts are write-once, so other text raises `ReplayConflict`, never a silent overwrite. A crash after the counts'
     write only commits.
   - The size allocation is seeded by (session, slot, road), so a rerun serves exactly what one clean run would.
2. **Entries before exits.** `allocate` ranks (is_exit, is_ticket, seeded owner). An account entry it cannot serve
   is `size_shared` and stays in the denominator. A ticket it cannot serve is not opened. An exit it cannot serve
   fills nothing and waits. No ledger holds an unservable fill.
3. **Pairing and settlement.** A decision of another driver, road or session, or a position of another driver or
   reviewed on another road's snapshot, makes that driver's whole slot `unavailable: driver_error`, never an exit.
   Expired positions settle before the session's first `view`, and the settlement exit records are sealed with the
   decisions.

## Plants: 11 on the fleet, 8 caught
- **Caught:** recorded entries re-priced; recorded entries opened again; an exit closed without size; an unservable
  entry recorded; exits ranked with entries; the counts never written; settlement after the first view; a rerun
  skipping the finish.
- **Survived, equivalent today:**
  - Recorded exits re-priced: a closed position is no longer in `still_open`, so the recorded fill is used anyway.
  - Outcomes sealed every run: sealing the same records again is a no-op, and outcomes are rebuilt deterministically
    from the ledgers.
  - The commit-only branch removed: before 15:30 the counts' write is a same-text no-op that then commits.
    - After 15:30, refused entries would re-price as `stale_seal` and the write would raise `ReplayConflict`, so the
      branch matters there. Round 3's "rerun after 15:30" test should also kill this plant.

## Notes (no action in this round)
- **Margin time inside the first driver's limit.** The first margin check of a session downloads and parses the SPAN
  file inside the first driver's 60-second limit. I measured it on 21 Oct: download 9.1 s for 9.1 MB, and 2.3-2.6 s
  to parse each of the four indices, about 19 s in all. That is inside the limit, but a slow Drive day could time out
  the first driver alone. Warming the margin before the driver loop would remove the case [reasoning only].
- **Unmeasured sizes (a3, for SIM-c).** `_displayed` reads a missing size as 0, so a quote whose sizes were not
  measured can never serve a fill in `allocate`. That is correct for live fills. The simulator must not route its
  unmeasured history through this allocation, or every simulated fill becomes `size_shared`.
- **The real acceptance test** (9 cases) skips until d's `SchoolAccounts.entries` (judge 488.4) merges. I did not
  see it pass. That should be shown before j merges.

## Addendum 1

**Scope:** MS-P1j "round 3" (the builder's numbering), story/ms-p1j-fleet at cb059340, main merged in. It applies the
orchestrator's rulings on round 2 and judge I's note, and touches a, f, g, i and the lab's reserved line on purpose.
This is my round 2 of 2 (first judge, independent of judge K).

**Verdict: PASS.**

- **Gates (my run):** 12087 passed, 16 xfailed. `ruff check`, `ruff format`, `check_imports` and `check_records`
  (8426 files) are clean.
- **Real acceptance on the real wiring: 9 of 9 pass** (`test_acceptance_real.py`, run by me). My round-1 note 3 is
  met.
- **The new pieces, checked.**
  - **Settlements.** `LedgerEntry.recorded_for` is a session date, kept in d's canonical position records. The
    session's settlement exit records are rebuilt from every expiry closing recorded for that session, so a crash
    between a settlement and the seal still seals its exit and outcome, and an earlier session's settlement is never
    sealed again.
  - **Late rerun.** A rerun that finishes after 15:30 writes the "rerun after 15:30, fillable may differ" mark;
    counts already written only commit.
  - **Accounts.** Every account and ticket-ledger call goes through `account_call`, so an unreadable account stops
    the run by name with nothing sealed, and `school run` exits 1.
- **Plants: 15 of my own re-run here, 14 caught.**
  - From round 1, now caught: the commit-only branch removed (the 15:30 test kills it, as round 1 asked) and
    recorded exits re-priced.
  - New, caught: every session's settlements sealed; an account settlement without its session; a late rerun never
    marked; the view unguarded.
  - Survived, equivalent: "outcomes sealed every run" (re-sealing the same records is a no-op).
  - One round-1 plant no longer applies, because the code changed.

**Notes.**
1. `recorded_for` joins `LedgerEntry`, and the position records decode strictly, so a line written before this field
   fails to decode. No school account exists yet (the school is off). If one ever does before this merges, it needs
   a schema step.
2. My round-1 note 1 (the SPAN download inside the first driver's limit, about 19 s of 60 s) and note 2 (`allocate`
   reads a missing size as 0, so practice fills must not go through it) still stand.

## Addendum 2

**Scope:** the delta `7f757504..1da5ffcd` on story/ms-p1j-fleet, as the orchestrator asked. Round 3 (cb059340) is
already judged in addendum 1. This covers round 4 (1da5ffcd): the builder's answers to my notes, and judge 506's live
guard.

**Verdict: PASS.** My round-1 notes 1 and 2 are closed at their root.

- **Gates (my run):** 12097 passed, 16 xfailed; real acceptance 9 of 9. `ruff check`, `ruff format` and
  `check_imports` are clean.
- **Only the driver's code is timed.** The builder rejected my "warm-up" suggestion with a better root cause: the
  60-second limit timed the fleet's own laws.
  - `DriverStep` now isolates and times only the driver's code: its decisions (real, plus the hypothetical ones on
    roads where it holds a ticket), then its exit reviews, each with its own limit. The laws run untimed between
    them, so a slow margin read is never a driver's deadline.
  - A law that throws unexpectedly is now the fleet's loud error, never the driver's. A failed SPAN read still
    refuses each entry by name inside C2's law.
  - I accept this. It is the right fix, and mine was a patch.
- **A road is never ticketed twice.** A ticket on a road where the driver already holds one stands only if the
  driver, deciding again with its tickets, still trades. That answer is now asked inside the timed driver call.
- **Live guard (judge 506).** `plan_slot` closes any road whose capture holds an unmeasured quote
  (`sizes_not_measured`), so the live fleet never trades on one. That makes my note 2 (missing sizes read as 0 in
  `allocate`) moot for live runs until d's QuoteRules reaches it.
- **Plants: 4, 4 caught.** An unmeasured road left open; exit reviews untimed; the laws timed with the driver; a road
  ticketed twice.

## Addendum 3

**Scope:** 8d4d6fb2..5395948a on story/ms-p1j-fleet. Most of it is main merged in (d's part 4, judged in 488.6). The
builder's own change is 5395948a: `allocate` and f's shared size read sizes through d's `QuoteRules`.

**Verdict: PASS.** My note 2 is closed.

- **Gates (my run):** 13511 passed, 16 xfailed. `ruff check` and `ruff format` are clean.
- **The rule.** `_displayed` reads each size through `rules.sizes`.
  - Under LIVE, a missing or unmeasured size serves nothing: it is no fill and no ticket, never unlimited.
  - Under PRACTICE, an unmeasured size has no limit (`inf`).
  - The fleet passes `LIVE` by name; the default is also `LIVE`.
- **Plants: 4, 4 caught.** The rules ignored (raw size); bid and ask swapped; a missing size made unlimited; the fleet
  passing practice rules (caught by the practice-isolation test).

## Addendum 4

**Scope:** 5395948a..fec42868 on story/ms-p1j-fleet, answering judge K's judge 512. The composition root is split so
a replay cannot build a real store.
- `fleet_wiring.fleet_on` wires what both roots share, over the stores handed in.
- `wiring.build_fleet` is the record root: the Drive dashcam, the account sync and the committer.
- `replay_wiring.build_replay_fleet` uses a local dashcam, accounts and counts under its folder, with no commit and a
  fixed clock.
- `cli.py` picks the root. Tests are added; no fleet logic changed.

**Verdict: PASS.**

- **Gates (my run):** 13535 passed, 16 xfailed. `ruff check`, `ruff format` and `check_imports` are clean.
- **A refactor only.** The removed `build_fleet` body is the same wiring, now in `fleet_on`. The record root builds
  the same three real stores as before, and the replay root imports none of them. The mode switch is gone, so a
  replay is a different root, not a flag.
- **Plants: 2, 2 caught.** The replay root using the Drive dashcam; the replay writing accounts at the repository
  root.

## Addendum 5

**Scope:** MS-P1j follow-up, the instructor wired into the fleet: story/ms-p1j-ins-wiring at eb5ec57a, which is
MS-INS part e (63cabe67) merged with main. It merges after part e. Judged on the fleet side only (part e has its own
judges): `SchoolFleet.after_outcomes`, `IsolatedSessionStep`, `UnfilledEntries`, `SealedDayInputs.why` and the
record root's wiring. First of two judges, independent of judge K.

**Verdict: PASS.**

- **Gates (my run):** 14026 passed, 16 xfailed. `ruff check`, `ruff format` and `check_imports` are clean.
- **The step after the outcomes.** It runs after the outcomes' (and drift's) seal and before the counts are written
  and committed, and again on a rerun's commit-only path.
  - The step is isolated: an exception or its 300-second limit gives one alert naming only the class, and the
    school's own counts are still written and committed.
  - Only the record root wires it. The replay root and the tests use `no_step`, and the replay root imports nothing
    of `instructor.wiring`.
- **`UnfilledEntries`.** Every sealed trade or ticket whose position neither ledger ever opened, derived read-only
  from the dashcam and the two ledgers.
- **Plants: 6, 5 caught.** Caught: the rerun skipping the step; the step not isolated; a failure not alerted;
  tickets left out of unfilled; unfilled always empty.
  - Survived, equivalent: the step run before the drift seal. Part e reads no drift (grep), so the order between
    the two does not matter.

**Note.** A step past its limit keeps running. If it is still writing when the counts are committed, part e's
temporary file (`.<name>.part`, in the counts folder) could be caught by the commit's `git add` of that folder. The
write is one small file, so the window is tiny, and `.gitignore` has no rule for `*.part` there [reasoning only]. An
ignore rule for `research/school/counts/**/.*.part` would close it.

## Addendum 6

**Scope:** MS-P1j seams for the simulator, story/ms-p1j-sim-seams at a02d1eb9 (from main). I am the only judge
(orchestrator: seams, not money logic).
- `fleet_wiring.books_on(cfg, stores, fills)` is the one construction of the accounts and the ticket ledger.
- `ReplayDashcam.encode`/`decode` are the only places a subclass changes.

**Verdict: PASS.**

- **Gates (my run):** 13799 passed, 16 xfailed. `ruff check` and `ruff format` are clean.
- **A refactor.** `fleet_on` builds its books through `books_on` with the live fill port, exactly as before.
  `ReplayDashcam.seal` and `read` go through `encode`/`decode`, and the write-once and seal checks stay in the base
  class. The pilot's `decode_slot_file` reads lines that carry an extra label, because it reads only `type` and
  `record`.
- **Plants: 3, 3 caught.** `seal` bypassing `encode`; `read` bypassing `decode`; the ticket book ignoring the given
  fill port.

## Addendum 7

**Scope:** MS-P1j follow-up, a comparison-card mismatch is loud: story/ms-p1j-card-mismatch at 199017ce (from main),
on the orchestrator's ruling of 23 Oct. First of two judges, independent of judge K.

**Verdict: PASS.**

- **Gates (my run):** 13806 passed, 16 xfailed. `ruff check`, `ruff format` and `check_imports` are clean.
- **The check.**
  - After the decisions' seal (and again on a rerun), each sealed decision is put to h's `CountingRule` at the
    seal's receipt commit.
  - Only `comparison_card_mismatch` gives the line. A counted or not-yet-counted decision gives none.
  - The line goes in `SessionRun.warnings` (additive to a's contract; a run that did not run carries none), and
    `school run` prints it and exits 1.
  - Only the record root wires it; a replay uses `no_check`. No record changes.
- **Plants: 5, 4 caught.** Caught: any not-counted reason named as a mismatch; a warning exiting 0; a rerun skipping
  the check; the record root wiring no check.
  - Survived: the line's "N of M" with N set to M. The tests plant every decision as mismatched, so the two numbers
    are always equal. It is an alert's text, not a record or a decision, so this is a note.
  - A test with one card-mismatched decision among several would pin N [reasoning only].

## Addendum 8

**Scope:** story/ms-p1j-sim-seams, a02d1eb9..6d3aa180: a third seam, `SchoolFleet.rules: QuoteRules = LIVE`, passed
into `plan_slot`. It touches the live gate, so it is lane 1: first of two judges, judge I second. The first two seams
are judged in addendum 6.

**Verdict: PASS.**

- **Gates (my run):** 13800 passed, 16 xfailed. `ruff check` and `ruff format` are clean.
- **Live is unchanged.** `plan_slot` still closes any road whose capture holds an unmeasured quote
  (`sizes_not_measured`), unless the rules passed are practice ones. The fleet's default and every pilot root
  (`fleet_on`, so record and replay) leave it at `LIVE`. The practice-isolation test still bars `practice=True` from
  every school module except `execution/practice_wiring.py`.
- **Plants: 4, 4 caught.** The guard inverted; the guard removed; the fleet defaulting to practice; the rules not
  passed into `plan_slot`.

## Addendum 9

**Scope:** story/ms-p1j-ins-wiring at bcf9ab21, diff eb5ec57a..bcf9ab21: the builder's fix for my 507.5 note.
- The counts commit now names the session's files instead of the folder (`SessionFilesCommitter` over a's
  `OwnedPathsCommitter`).
- `.gitignore` ignores `research/school/counts/**/.*.part`.

**Verdict: FAIL on one test-only should-fix.** The design is right and fixes the cause, not only the symptom.

- **Gates (my run):** 14034 passed, 16 xfailed. `ruff check` and `ruff format` are clean.
- **Checked.**
  - `SessionCounts.files(session)` names the three own files plus the files the record root names. Missing files are
    skipped by `OwnedPathsCommitter` (git refuses a pathspec that matches nothing).
  - The real-git test commits the named files and leaves both a stray `.part` and an un-ignored stray uncommitted.
- **Plants: 3, 2 caught.** Caught: the extra (instructor) files not committed; the whole folder committed.

**Should-fix.**
- **Defect:** the record root can stop naming the instructor's counts file. Dropping the
  `lambda session: (str(instructor_counts_path(session)),)` from `wiring.build_fleet` passes every test. In the real
  run, the instructor's public counts would then be written each session and never committed.
- **Test it must pass:** `build_fleet`'s `SessionCounts.files(session)` includes `instructor_counts_path(session)`.
  `test_wiring.py` builds the record root already.

## Addendum 10

**Scope:** story/ms-p1j-sim-seams, 6d3aa180..54ef5d40 (6d3aa180 is judged in addendum 8). Two changes:
- `FillStep.rules` (no default) now carries the fleet's own rules. This fixes the SIM builder's bug: a practice entry
  was judged `size_shared` under LIVE.
- `school.enabled` moves out of `SchoolFleet.run()` to the record root (`SwitchedOff`, the school-off line, nothing
  built), on the orchestrator's ruling.

**Verdict: PASS.**

- **Gates (my run):** 13803 passed, 16 xfailed. `ruff check` and `ruff format` are clean.
- **The switch.**
  - The record root reads `school.enabled` first and returns `SwitchedOff` before any store is built.
  - The replay root has no switch: it writes only under its folder, so the CLI no longer forces the switch on a
    copy of the config.
  - The fleet itself has no switch, so the simulator's practice command runs the same fleet.
- **The fill step.** It uses the fleet's rules, and `allocate` receives them.
- **Plants: 3, 3 caught.** The record root ignoring the switch; the fill step always LIVE; `allocate` given the
  default rules.

## Addendum 11

**Scope:** story/ms-p1j-sim-seams, 54ef5d40..1f767528 (6d3aa180..54ef5d40 is judged in addendum 10): the
first-ticket bug the SIM builder found. A driver's first ticket stopped the run, because the ticket ledger was never
viewed and d's store refuses a record before the first view. The fake had accepted one, which hid it.

**Verdict: PASS.**

- **Gates (my run):** 13807 passed, 16 xfailed. `ruff check` and `ruff format` are clean.
- **The fix.**
  - `Books.stores` lists every store the fleet records into (the driver account, then the ticket ledger).
    `SchoolFleet._open` views each before any fill, and the laws read the driver account's view.
  - a's `AccountPort.record` docstring now states the rule. `FakeAccounts` and the conformance check enforce it, so
    the fake can no longer hide the bug. The new test runs on d's real stores.
  - A rerun's fills find the ledger already opened: d's `started` is the persisted cash file.
- **Plants: 3, 3 caught.** The ticket ledger never viewed; the fake accepting a record before a view; the laws reading
  the ticket ledger's view.

## Addendum 12

**Verdict: PASS** on story/ms-p1j-ins-wiring, `bcf9ab21..4f5f8297` (test and story text only). This closes 507.9's
one should-fix, so ins-wiring now has no open finding.

| Criterion | Reality |
|---|---|
| The record root's `SessionCounts.files(session)` includes `instructor_counts_path(session)` | Yes: `test_the_record_root_names_the_instructor_s_counts_file_in_the_counts_commit` builds `wiring.build_fleet` over the real composition (stores stubbed) and asserts the path is in `counts.files(SESSION)` |
| A replay names no instructor file | Yes: the same test asserts it is absent from `build_replay_fleet(...).counts.files(SESSION)` |
| My 507.9 plant is caught | Yes: `fno/school/wiring.py:44`, with the lambda returning `()`, fails exactly this test (1 failed, 3250 passed in `tests/school`); reverted |
| Story text | `MS-market-school.md` adds the test and its plant under part j; matches the code |

Gates on 4f5f8297 (run by me): 14,035 passed, 16 xfailed; ruff clean; format clean; check_imports clean.
No code changed, so 507.9's other findings stand as judged there.

## Addendum 13

**Verdict: FAIL, one should-fix.** Story/ms-p1j-ins-wiring, judged as the change it adds to main: merge-base
2f3833de to tip bda6a49d (I was asked to judge 4f5f8297..94d3acb1; the branch has moved on to bda6a49d). This is the
second judge on the round-2 code. I did not read judge K's 523.1 or 523.2 before writing this.

### What meets the brief

- **One committer per run:** the instructor's work runs on its thread over `DeferredInstructorStore` and
  `RunReceipts`. It keeps its writes and runs only read-only git (`log`, `show`). `prepare`, the one fetch, and the
  writes (`flush`, then the counts file) run on the run's own thread, and only when the work ended in time. On a
  deadline, `isolated` returns `Isolated(None, DEADLINE)`, so a late thread has nothing to write.
- **Commit and order:** `SessionCounts.files` names the counts, the instructor's counts file and its two session
  receipts (`instructor_files`), and one `NamedFiles` commit takes exactly those. The step runs after the outcomes and
  drift seals and before `counts.write`; a rerun runs it again.
- **Plants:**

  | Plant | Result |
  |---|---|
  | deferred write writes through | caught (3 failed) |
  | deferred read ignores pending | caught |
  | the receipts left out of `instructor_files` | caught |
  | no `prepare` | caught |
  | `RunReceipts.publish` fetches on the thread | caught |
  | `extra` dropped from `files` | caught (4 failed) |
  | late writes run after a time-out | equivalent: the value is `None` on a deadline |

- **Gates on bda6a49d:** 14,340 passed, 16 xfailed; ruff, format and check_imports clean; the largest file is 106
  lines. It merges cleanly with current main.

### SF1 (should-fix): a refused counts commit is silent, and it now carries the instructor's receipts

- **Path:** `SessionCounts.write` and `commit` return `GitManifestRecorder`'s outcome line. `runner.py` drops it
  (line 131, and the `counts.write` call after `after_outcomes`), and `cli.py` `cmd_run` exits 0 on an empty
  status with no warnings.
- **Before this branch:** the instructor's store pushed its own receipts, and a receipt not on main raised
  `SealNotPushed`, which the isolated step alerted.
- **Now:** those receipts ride on the counts commit. A normal failure (three lost push races, the pull refused
  because the checkout carries other unpushed changes, or the hook refusing) leaves them unpushed with no line,
  no alert and exit 0. The next session's re-checks then read `None` for that session (`store.read` looks only at
  main) and skip it silently.
- **bda6a49d makes it worse:** `NamedFiles.owns` is now the exact names, so a leftover unpushed commit blocks every
  later counts commit in that checkout, still silently.
- **Reproduced:** a scratch test on bda6a49d with a committer returning "school session files NOT committed: push
  failed" gives `status=''`, `warnings=()` and no alert.
- **The same silence held for the counts files alone on main.** I passed that in 507.5 and 507.9 without seeing it.
  That miss is mine.
- **Test it must pass:** with a counts committer whose outcome contains "NOT committed", `fleet.run` reports that line
  (as a status or a warning), so `school run` prints it and exits 1. This holds on the first run and on the rerun
  branch (line 131).
- **Fix (reasoning only):** carry the commit outcome into `SessionRun.warnings` when it is not committed.

### Note

- **Collision with story/ms-p1c-publisher-move (judge 527):** this branch edits `fno/school/dashcam/publisher.py`
  (`RemoteReceipts`) and adds two importers of it (`run_receipts.py`, `instructor_step_wiring.py`), while that branch
  moves the file to `fno/storage/receipt_publisher.py`. A merge-tree of the two reports conflicts. Whichever merges
  second must carry the other's change.
- **Round count:** this is my third look at ins-wiring (507.9 FAIL, 507.12 PASS, now 507.13). The orchestrator
  decides whether this counts as a round over the limit, which goes to the owner.

## Addendum 14

**Verdict: PASS** on story/ms-p1j-ins-wiring at 98d16fcd. This is the owner's one more check after 507.13: the fix is
52cf0224, followed by merges of main (the publisher move, the instructor's cut-off). It closes 507.13's SF1 and
condition 2 of judge 527.

- **SF1 met:** `SessionFilesCommitter.commit` returns the refusal line (every `_not_committed`, including missing
  hooks, starts with `REFUSED`), or None when the files are on main. `SessionCounts.commit` alerts "counts NOT pushed
  <session>: ..." through `FleetStores.alert` (the record root passes `build_alert_sender().send`) and returns the line.
  The runner carries it in `SessionRun.warnings` on the first run and on the rerun branch, so `cmd_run` prints it and
  exits 1.
- **Exact names no longer block:** `run_paths` (the counts folder and `receipts/data/school/instructor/`) make the
  run's own earlier unpushed commits "own" in `pull`. With nothing new to commit, `_unpushed` still pushes a named file
  that is not on main, so the rerun completes it. The tests run on real git with the push refused.
- **My plants (`tests/school`):**

  | Plant | Result |
  |---|---|
  | committer always None | 3 failed |
  | leftover never pushed | 1 failed |
  | no alert | 2 failed |
  | receipts prefix dropped from the record root's run paths | 1 failed |
  | rerun drops the line | 1 failed |
  | refusal line not prefixed | 3 failed |

- **Judge 527 condition 2:** `RemoteReceipts` now sits in `fno/storage/receipt_publisher.py`, and nothing imports
  `fno.school.dashcam.publisher`.
- **Gates on 98d16fcd (run by me):** 14,404 passed, 16 xfailed; ruff, format and check_imports clean; the largest
  changed file is 152 lines. It merges cleanly with current main.
