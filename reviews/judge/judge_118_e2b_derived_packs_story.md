# Judge 118: story E2b text, derived quote figures only in the committed packs and desk records (quality rule 1; judge C)

Date: 15 Oct 2026 (UTC). Branch `story/e2b-derived-packs` at **dd0be6a1015eea8de880b1a0cc43f9049fcd21cc** (text only:
`docs/stories/E-paper-desk.md`, E2b). Checked against:
- the owner's "8 A" and "6 A";
- the orchestrator's decisions 26-27;
- the code on `main` (c428867 and later): `snapshot_inputs.py`, `market_checks.py`, `execution_costs.py`,
  `records.py`, `entries.py`, `execution_capture.py`, `live_pack.py`;
- A4b (judge 111).

## Verdict: FAIL (text), 2 should-fix; 2 minor

**The design is right:**
- **Decision B is right.** The builder's 648/648 finding means per-contract mid plus spread is the raw quote in another
  form, so leaving per-contract figures out is the only way to honour "8 A" in substance.
- **The reader table is complete.** My grep over `fno/` and `tools/` finds exactly the readers it names:
  - `quote_bid`/`quote_ask` in `fno/scorecard/execution_costs.py:61-63` only;
  - pack `option:` items in `fno/checks/market_checks.py:38` only (C3's spot);
  - the forecast v2 pack (`fno/forecast/live_pack.py:133-139`) reads `spot` from the A4 quote rows, not the desk pack,
    so E2b does not touch it.
- **C3's per-chain spot is right.**
  - The recorder writes one `chain.spot` on every row of a chain (`fno/quotes/recorder.py:270`), and C3 today takes the
    set of distinct spots across option items. So `spot:<expiry>`, one per chain, gives C3 the same set by
    construction.
  - Refusing a chain whose rows carry two spots is a correct new guard (today two spots inside one chain would pass
    unnoticed into C3's set).
  - Criterion 2's boundary list (2% and 0.2% at, under and over; none; one chain) is the right regression.
- **No frozen file.** No file it names is in experiment 1's `FREEZE.md`, the G1 v1-v3 freeze records or S1's draft
  list (S1 lists `fno/desk/timetable.py`, which E2b does not touch).

## Should-fix

**1. The unwind publishes both sides of one contract, so criterion 3's "no other column" is false for it.**
- On a failed hedge E4 buys the protective leg at the **ask** (`FILL_OPEN`), then unwinds it at the **bid** of the
  **same** snapshot (`FILL_UNWIND`, `fno/desk/entries.py:147-153`). Both rows go to `desk_fills.csv` with their prices,
  so that contract's bid and ask are both published.
- The event row's `legging_cost_rs` carries the same information: (ask − bid) × units plus charges.
- **Fix:** either name this as the one exception (a failed-hedge day, one contract, both sides) and put it to the owner
  with the orchestrator's fills-in-the-journal question, or keep unwind pairs out of the public journal. Then add a
  test that only an unwind pair can reveal both sides.

**2. Before A4b, E6 cannot read the touch it now depends on.**
- E6's half-spread would read the 15:15 execution snapshot "through the hash-checked store". Before A4b merges, that
  CSV exists only in the run's local quote folder, uncommitted by E2b's own criterion 4.
- So any E6 run outside that checkout (a later session, CI, the scorecard job) reports every fill "touch unknown". The
  reported half-spread would be empty, quietly, for as long as A4b is open.
- **Fix:** make A4b (or the Drive store) a stated dependency of criterion 3 and merge E2b after A4b. Or state that,
  until A4b, the scorecard runs only in the capture's checkout, and that the count of "touch unknown" fills is printed
  on the scorecard so an empty figure is never silent.

## Minor

1. Criterion 3: the scorecard's own output (`fno/scorecard/report.py`) should print the number of "touch unknown"
   fills next to the half-spread, so an excluded fill is visible to the owner, not only in a test.
2. Criterion 5: also test a `.CSV` case variant and a path reached through `..` or a symlink into the Groww folder,
   since the guard matches paths.

## The A4b fit

- Both stories change `fno/desk/execution_capture.py` the same way, and the story says the later merge keeps one
  version.
- Criterion 4 tests the behaviour (record and sidecar, never the CSV), so either merge order is checkable.
- With should-fix 2 the order becomes A4b first.

**Verdict: FAIL for dd0be6a1015eea8de880b1a0cc43f9049fcd21cc** (story text) on should-fixes 1-2. A re-check needs only
criterion 3, the dependency line and the A4b paragraph.

## Addendum 1 (15 Oct 2026): de2830061a845cc366752ab6900da8439ec8abb2

Text only (`git diff dd0be6a de28300`: the E2b section).

| Item | Status | Evidence |
|---|---|---|
| sf 1, the unwind pair | MET | Named as the one stated exception: a failed hedge's `FILL_OPEN` at the ask, its `FILL_UNWIND` at the bid of the same snapshot, and `legging_cost_rs`. It goes to the owner with the fills-to-Drive question (orchestrator's decision 28). Criterion 3 now tests every E4 outcome (opened, partial fill, closed, pending exit, settlement) and finds both sides of one contract only in the unwind pair |
| sf 2, A4b first | MET | A4b is a dependency in criterion 3 and the Depends line, and E2b merges only after A4b (orchestrator's decision 29). E6 reads the 15:15 file from Drive through A4b's hash-checked store |
| Minor 1, the unknown count | MET | The scorecard report prints the number of "touch unknown" fills |
| Minor 2, path tricks | MET | The guard compares resolved paths; tests cover `.CSV`, `../` and a symlink into the Groww folder |

**Code note (I check it when judging the code):** a test that "only the unwind pair reveals both sides" must compare
each pair of rows on the same `snapshot_id` and `quote_contract_id`, across all books' and shadows' fill files, so that
two books filling the same contract in one snapshot on opposite sides is not missed. A buy in one book and a sell in
another at the same snapshot give both sides just as an unwind does. If it can happen, it is a second exception to
state.

**Verdict: PASS for de2830061a845cc366752ab6900da8439ec8abb2** (story text). Code may start. The merge waits for A4b,
and by quality rule 9 the code goes to ChatGPT after my code PASS.

## Addendum 2 (15 Oct 2026): E2b code at b76be4fdf00ab776148d854afde5f69d10782293

Code plus the changed story text (`git diff de28300 b76be4f`). Builder's claims: response 118.

### Gates

| Gate | At b76be4f | Trial merge with `main` b28bc53 |
|---|---|---|
| `env -u FNO_SLACK_BOT_TOKEN python -m pytest -q` | 3,865 passed | 3,919 passed |
| `ruff check` / `ruff format --check` / `check_imports.py` | clean / clean / clean | clean / clean / clean |
| Conflicts | - | `reviews/claude/README.md` only (index rows) |

A4b is not on `main` yet (judge 111 addendum 3: waits for the owner's probe), so this trial merge does not include it.

## Verdict: FAIL (code), 2 should-fix; 3 minor

### Per criterion

| Criterion | Builder's claim | My evidence | Status |
|---|---|---|---|
| 1 No per-contract figure in the pack; spot per chain; two spots refused | `option:` items gone; `spot:<expiry>`, `quote_counts` | On the real 14 Oct snapshot (184 rows), `_spots` gives `spot:2026-10-27` 22,620.00 at the chain's first row (14:55:25.46) and `spot:2026-11-23` 22,621.15. Blanking one chain's spots gives that item with value None. A second level 22,620.05 in one chain is a PackError naming the expiry. 22620.0 and 22620.00 count as one level. No bid, ask or size field in any item. Plants M13, M14, M19 and M20 caught | MET |
| 2 C3 from `spot:` items; one spot per chain | blank or refused `spot:` named | The code names a blank item and a refused item. Plants M11 (refused ignored) and M12 (blank ignored) caught | MET |
| 3 Fill rows carry no touch; exceptions pinned; E6 from the snapshot; unknowns counted | as in response 118 | `FILL_COLUMNS` has no `quote_bid`/`quote_ask`. The cross-account test (`test_public_fills.py:73`) compares across book 1 and book 2 by snapshot and contract, as my addendum 1 note asked. Hand check on the real snapshot: 10 legs at the touch give 5.9325/unit from `half_spread`, and my own arithmetic gives 5.9325. Wrong hash, blank or `../` snapshot ID, absent contract, other contract ID, other day: each is one "touch unknown", no crash. The report prints the count (plant M22 caught). **But a corrupt snapshot and a one-sided quote are untested (should-fix 2)** | PARTLY |
| 4 Capture commits record and sidecar only | `names[1]` | Plant M15 (the CSV re-added) caught | MET |
| 5 Guard: before git, after the add, folders, earlier-staged files | as in response 118 | On real git repositories: a folder, a trailing-slash pathspec and a parent folder are refused after the add, and the add is undone. A file staged earlier is refused and left staged. `.CSV`, `../` and a symlink are refused. A sidecar alone commits. Plants M1-M5 and M21 caught. **But a refusal inside an account write escapes the desk's per-book handling after the fills were applied (should-fix 1)** | PARTLY |
| 6-7 E2 criteria on schema 2; no `option:` reader | existing tests | Full suite green. My grep finds no `option:` lookup left in `fno/` | MET |
| Story text re-check | exceptions 1-3, known channels, kept mids | Exception 3 matches `fno/desk/exits.py:90-106`. The scoreboard B channel matches `daily_values.py:44-55`. All are stated for the owner, not silently kept. One slip (minor 1) | MET |

Plants: 22 of my own. 20 were caught; M16 and M18 survived (should-fix 2).

## Should-fix

**1. A guard refusal during an account write leaves the fills applied but not committed, and escapes the desk's per-book handling.**
- **What happens.** `GitAccountSync.write` runs `apply(journal)` (the fills reach the book's ledger), and only then `commit_paths`.
- **Probe on a real repository.** A raw quote file staged earlier outside the book folder, then one account write:
  - `RawQuoteCommitRefused` is raised. It is a `ValueError`, not `AccountWriteRefused`.
  - `cash_ledger.csv` already holds the new fill row, uncommitted.
  - The next write for that book stops on "uncommitted work in journal/book1_rules/account".
- **Why it matters.**
  - `DailySteps.fill` catches only `AccountWriteRefused` (`daily_steps.py:143`, "never crashes the run before its exits", judge 84). This refusal escapes `fill()`, ends the run step, and the exits step never runs.
  - The paper account then holds a trade that the run log does not record.
  - In `review_exits` the broad handler alerts, but the exit fills are likewise applied and not committed.
  - This is exactly the case criterion 5 was written for ("a quote file staged earlier by anything else"). So when the guard does its job, it breaks judge 84 and splits the account from its record.
- **Expected fix.**
  - Check the whole index in the account write's dedicated check, before `apply`, so a refusal applies nothing.
  - Make the refusal one the desk handles: an `AccountWriteRefused` subclass, or caught and turned into one. The fill step then records "not filled" with an alert, and other books and the exits go on.
  - Test it: with an earlier-staged quote file, the fill step gives "not filled" plus an alert, the journal is byte-identical, and exits are still reviewed. Add the same for an exit write.

**2. "Touch unknown, never a crash" is untested for the two cases that need the code.**
- **M16 survived.** Narrowing `except (SnapshotError, ValueError, KeyError, OSError)` to `SnapshotError` passes all 293 related tests. On a copy of the real snapshot with a corrupt `.meta.json`, the reader raises `JSONDecodeError`, not `SnapshotError`, so without the wide `except` E6 crashes.
- **M18 survived.** Dropping the bid/ask `None` check passes too. `ExecutionQuote.bid/ask` are `float | None`, so a one-sided quote would then crash on `None + float`.
- **Expected fix:** two tests. A corrupt sidecar or CSV gives one "touch unknown", and a one-sided quote gives one "touch unknown"; both still average the other fills.

## Minor

1. **Story text slip.** "**two stated exceptions**" is followed by a list of three. Make it "three", matching criterion 3.
2. **A chain with no rows at all gets no `spot:` item** (the meta's `expiries` lists it, the rows do not). C3's 0.2% agreement then quietly runs on one chain, as it did before E2b. "One spot per recorded chain" could take the chain list from `meta["expiries"]` and give a missing chain a None item. Reasoning only; not a regression.
3. **The guard is path-based by design.** A raw file copied or renamed outside the folder passes. It also refuses a staged deletion of a raw quote file (`diff --cached` lists deletions). That errs on the safe side, but if A4b removes the 14 Oct Groww CSV that is still on `main` (`.../2026/10/nifty_20261014_145500.csv`, public since that day), that removal must not go through `Git`.

## For the merge check (after A4b)

- `fno/scorecard/wiring.py` builds E6's snapshots from the local quote folder. After A4b, it must read through A4b's hash-checked Drive store, or every fill outside the capture's checkout is "touch unknown". The merge must keep one version of `execution_capture.py`.

**Verdict: FAIL for b76be4fdf00ab776148d854afde5f69d10782293** (code) on should-fixes 1-2. A re-check needs only `git_sync.py`, the fill and exit step handling, `touches.py` and their tests.

## Addendum 3 (15 Oct 2026): fixes at c653744aa1e9e75c451e7c272316e441be20415a

E2b's own commit is 8b47713; c653744 merges `origin/main` into it. Gates on c653744: 3,928 passed (the builder's figure);
ruff, format and imports clean. Decision 42's commit (the touch size in E4's reason) was not pushed yet; I check it
with the next SHA.

| Item | Status | Evidence |
|---|---|---|
| sf 1, account write | MET for the account write | `_require_no_raw_quote_staged` runs before the pull and before `apply` and raises `CheckoutNotDedicated` with one alert. My plants caught: N1 (check removed), N2 (check moved after `apply`), N3 (refusal raised as a raw `ValueError`) |
| sf 1, the run as a whole | **NOT MET (new should-fix 1)** | see below |
| sf 2, untested touch cases | MET | Tests read the real `RecordedExecutionSnapshots`; my M16 and M18 are now caught |
| Minor 1, "three" | MET | |
| Minor 2, chain list | MET | Chains come from `meta["expiries"]`; a chain with no rows gets a None item, timed at the first request (plants N5, N6 caught) |
| Minor 3, path-based guard | MET (reason stated) | |

**The orchestrator's question: can the "rows as fallback for older sidecars" path hide a missing chain in a new capture? No.**
- The fallback only runs when `expiries` is missing or empty.
- The recorder always writes `expiries` (`recorder.py:233`). An empty list means no chain was fetched.
- A pack is built only from the canonical capture, which must be `complete`. `complete` requires chains, no failures
  and `rows == expected` (`recorder.py:228`), and fewer than 2 monthly expiries is itself a failure (`recorder.py:206-207`).
- So a canonical capture always lists both chains. A chain fetched with no contracts is listed, gets a None item, and C3
  names it.
- Wording nit: the story says the sidecar's `expiries` are the chains "asked for"; they are the chains fetched. For a
  canonical capture the two are the same.

## New should-fix

**1. In a real run, the daily run's own step commit hits the staged raw file first, and it stops the run with no alert.**
- **How.** `DeskRun._step` commits the run log after every step through `GitCommitter`. With a raw quote file staged, the
  first step's commit (before the fill step) runs `commit_paths`. Its staged check raises `RawQuoteCommitRefused`, a
  `ValueError`.
- **Probe.** Real `Git` and `GitCommitter`, a staged raw quote file, committing `journal/runs/<day>.json`: the refusal is
  unhandled.
- **Consequence.** `_step` does not catch it, and neither does `fno desk` → `book1_cli` (`build_daily_run(...).run(...)`).
  - The run ends at its first step with a traceback.
  - Nothing reaches #fno-desk. There are no exits that day.
  - The new account-write path, with its "not filled" result and alert, is never reached.
- **Why the tests missed it.** `test_raw_quote_refusal_run.py` swaps in a real check for book 1's account sync but
  keeps the fake committer.
- **Exits.** They could not run in that checkout anyway: every account write now refuses while the file is staged. The
  defect is the silence.
- **Expected fix.** The committer's refusal is alerted once to the desk channel, naming the file (the same sender
  `_stop` uses). Test it with the real `GitCommitter` in a run: a staged raw file gives one alert naming it, and nothing
  is committed.
- Today a push rejected three times also ends the run unalerted. That is older than E2b and not E2b's to fix; it is worth
  one line in the story's Out list or a follow-up.

## Minor

1. **N4 survived.** Making `staged()` ignore deletions (`--diff-filter=d`) passes all 310 related tests. Criterion 5 now
   states "a staged deletion there is refused too", so that claim needs a test.

**Verdict: FAIL for c653744aa1e9e75c451e7c272316e441be20415a** on new should-fix 1. A re-check needs the committer's
refusal handling, its run-level test, the N4 test, and decision 42's commit.

## Addendum 4 (15 Oct 2026): af31238713e4bd076524ce6832a77e5bdf76a2fe

New commits: 290a8a0 (decision 42) and af31238 (decision 44). Gates: 3,935 passed (the builder's figure); ruff, format
and imports clean. Decision 45's commit was not pushed yet; I check it with the next SHA.

## Verdict: FAIL, 1 should-fix; 3 minor

| Item | Status | Evidence |
|---|---|---|
| Addendum 3 sf 1, the run's own commit | MET | `GitCommitter` turns the raw-quote refusal and every `GitError` into `CommitFailed`, and `DailyRun._step` is the one handler (one alert, then `RunStopped`); `fno desk run` returns 1 on one line. The tests use the real `GitCommitter` with a bare origin: a staged raw file, an unreachable origin, a pre-receive hook. I read all three and the in-step case (capture commit) |
| Addendum 3 minor 1, staged deletion | MET | `test_a_staged_deletion_of_a_quote_file_is_refused` (this catches my N4) |
| Decision 42 | MET | `pricing.py` `NOT_ENOUGH_SIZE` names only the units. The pending-exit reason reuses `q.reason` (`exits.py:137`), so it carries no size. The test reads the committed `desk_events.csv` row |

### The orchestrator's questions

**1. Is a commit stuck local after a push rejected three times acceptable? Yes, but the alert gives no hand fix.**
- It fails closed: `other_work` refuses every later account write while a commit is unpushed.
- It also heals: the next successful `GitCommitter.commit` pulls and pushes `HEAD`, so a rerun carries the stuck commit
  once origin accepts pushes again.
- The alert says what happened, not what to do. It should say: exits did not run, open positions were not reviewed
  today; fix the cause, then rerun `fno desk run`. That rerun advice is only safe after should-fix 1 below.

**2. Can `RunStopped` skip something that must run? Yes, in two ways.**
- **The exits.** A stop at any step before `exits` skips them. For all three causes this changes nothing, because the
  exits' account writes would refuse anyway:
  - a staged raw file is refused before apply;
  - an unpushed commit fails the dedicated check;
  - a failed pull raises `GitError` in the account write too.

  The exception is a pull that fails once and works minutes later. Then the stop gives up that day's exits, as the old
  crash did. Acceptable only if the alert names it (minor 1).
- **The locks.** Account locks are context managers inside `GitAccountSync.write` (`with self.open_journal(...)`), so
  an exception releases them. Nothing else holds a resource across `_step`.
- **The failed step's own files on a rerun.** This is should-fix 1.

## Should-fix

**1. After a stop, a rerun marks the failed step done, and its files are never committed.**
- **The order.** `_step` calls `log.record(...)` (which writes `journal/runs/<day>.json` to disk) before
  `committer.commit(...)`. `run()` skips every step for which `log.done(name)` is true.
- **Probe.** The real `DailyRun._step` and `RunLog`, a committer that fails once, the pack step with its
  `journal/packs/<day>/common.json`: after `RunStopped`, `RunLog.open(root, day).done("pack")` is True.
- **Consequence.** A rerun skips the pack step, and the next step's commit carries only the log and that step's own
  paths.
  - The pack stays uncommitted for good, while the committed run log says `"built": true` with its hash.
  - That is a silent gap in the public record, after the very recovery an operator would try.
  - A failed `decisions` step leaves its no-decision files the same way. Those sit in the book's folder, so later account
    writes refuse (fail closed, alerted), but nothing says why.
- **Before E2b** the same order existed, but the run crashed. Decision 44 makes stop-then-rerun the designed path, so
  the rerun must be correct.
- **Expected fix.** A step whose commit failed is not "done" on a rerun: either the log records it only once committed,
  or the rerun first commits the paths of recorded but uncommitted steps. No step may run twice, and the fills step must
  never refill. Test it with the real `GitCommitter`: a stop at `pack`, the cause removed, a rerun; the pack file is
  committed, every step ran once, nothing was refilled.

## Minor

1. **The stop alert should say plainly what is missed and what to do.** Name "exits not reviewed today" when the stop
   comes before `exits`, and give the hand fix: remove the cause, then rerun `fno desk run`. For a rejected push, add
   "the local commit is pushed by that rerun".
2. **Possible decision 45 scope (reasoning only).** `exit_rules.py:42,55` write "net Rs X if closed now" into the
   `exit_ordered` reason. That net is worked out at the touch of every leg. If a leg then stays pending (not enough size),
   X minus the published close fills of the other legs gives that leg's touch price at a snapshot where it did not fill.
   That is one side, not both. Fold it into decision 45 if the rule is "no quote figure for an unfilled leg".
3. The new Out line (Book 1's decision command still ends in a traceback on a failed commit) is a fair follow-up, not
   E2b's.

**Verdict: FAIL for af31238713e4bd076524ce6832a77e5bdf76a2fe** on should-fix 1. A re-check needs the rerun behaviour
and its test, the alert text, and decision 45's commit.

## Addendum 5 (15 Oct 2026): a31ea116dfc46bc89b59ffb8df6d3879281d575c

a31ea11 is af31238 plus decision 45. Gates: 3,936 passed (the builder's figure); ruff, format and imports clean.

| Item | Status | Evidence |
|---|---|---|
| Decision 45 | MET | The reason is the fixed text `entry_worse_than_approved: entry price at the touch worse than the approved limit`; `shortfall_rs` is gone from `EVENT_COLUMNS`, `DeskEvent` and `EntryResult`; `worse_than_approved()` returns a bool. Tests cover the iron fly and a single-leg LC, with the exact columns and no digit outside the ID fields |
| Readers of the dropped column | none | `grep -rn shortfall` over the tree finds only `entries.py`, `records.py` (comments), the test, the story and an old conversation log. No hit in `fno/scorecard`, `fno/market_read_models`, `fno/scoreboard`, the pack code, `tools/` or `contracts/omenix-dashboard/` (pin and `paper-portfolios.yaml`). No `desk_events.csv` is committed, so no stored file changes shape |
| The digit test and a future field | acceptable | The test checks only a refused entry's row, and `IDS` lists the fields allowed digits. A future non-quote field such as `lots` makes the test fail until it is named there. That is a deliberate review point, not a lock-out: one line. Calling it `NON_QUOTE_FIELDS` would read better (nit) |
| Addendum 4 should-fix 1, rerun after a stop | **NOT MET** | a31ea11 does not change `daily_run.py` or `run_log.py`. `_step` still records the step before committing, so a rerun after a stop skips the failed step and never commits its files |
| Addendum 4 minor 1, alert wording | open | unchanged |

**Verdict: FAIL for a31ea116dfc46bc89b59ffb8df6d3879281d575c** on addendum 4 should-fix 1 alone. Decision 45 is met
and needs no further check. The next re-check needs only the rerun fix and its real-committer test, and the alert
text.

## Addendum 6 (15 Oct 2026): afafb07fbeaa78f3395219f045519e9bd92debee

Parent a31ea11 (decision 45 already MET). This commit: decision 47 (`PendingCommitter`), decision 48 (fixed exit-rule
reasons) and the alert texts. Gates: 3,943 passed (the builder's figure); ruff, format and imports clean. Files under 350
lines (`pending_commit.py` 77, `daily_run.py` 110, `git_sync.py` 182).

## Verdict: FAIL, 1 should-fix; 3 minor

| Item | Status | Evidence |
|---|---|---|
| Addendum 4 sf 1, rerun after a stop | MET in the same checkout | A marker with paths, SHA-256 and message is written before every run commit and removed on success. `run()` calls `recover()` first, inside the one handler, and commits the files as recorded or stops naming a changed file. My plants: Q1 (no hash check), Q2 (no push when ahead) and Q3 (no recovery) are caught |
| Addendum 4 minor 1, alert text | MET | "exits not reviewed today" before the exits, the hand fix, "the rerun pushes the local commit" (plant Q4 caught) |
| Decision 48 | MET | `TARGET_REACHED`/`STOP_REACHED` fixed texts (plant Q6, a figure put back, caught). "every leg closed; net Rs N" stays: N is the sum of published fills |
| The builder's partial disagreement with my addendum 4 Q1 | **accepted** | I said the next successful commit pushes the stuck one. It did not when that commit had nothing new (`commit_paths` False, so no push), which is exactly the recovery of an already-committed step. The builder is right, and the fix is right |

### The orchestrator's three points

**(1) A rerun in a fresh container (no marker, no uncommitted files). It is safe: fail-closed, no double fill. But the story does not state it (minor 1).**
- **Fills.** `EntryDesk.enter` returns the recorded outcome when the journal already holds an entry event for that
  `trade_id` (`entries.py:116-118`, reading the committed journal). Every book's account write is committed and pushed
  by `GitAccountSync` itself. So a fresh rerun of the fills step never refills a trade whose write reached origin. A
  write that never reached origin is not on the public record, so filling it once on the rerun is not a second fill.
- **Exits.** These work from the journal's open positions, so a closed trade is not closed again.
- **Decisions.** `collect_decisions` started after the deadline plus grace marks every book late (`daily_steps.py:91-94`,
  "fails closed"). A fresh rerun after a stop at the decisions step therefore loses that day's entries for all books.
  That is safe and visible (the no-decision files say why), but a cost.
- **Pack.** The pack rebuilds byte-identically (E2 criterion 6), so re-running it is harmless.
- **Reporting gap (reasoning only).** In a fresh checkout before A4b, the 15:15 raw CSV is absent. `_fill_one` then
  returns "not filled" from the gate before `enter` can return the recorded outcome, so the rerun's log can say "not
  filled" for a trade that was filled. It is a report mismatch, not a fill. After A4b, the snapshot comes from Drive.
- **Conclusion.** No durable marker is needed for safety. The story must state the fresh-checkout rule (minor 1).

**(2) A second capture on the rerun. It is consistent with E3: C3 refuses a capture outside the window.**
- `CommittedExecutionSchedule` picks the latest record, but its window is `execution_snapshot`..`fills_by`.
- `snapshot_checks.py:24-34` refuses a capture "outside its window (stale or early)" as `prices_unverified`.
- So a rerun capture after `fills_by` fills nothing. One inside the window is a legitimate execution time.
- Both records are committed, and each fill row names its `snapshot_id`, so the timing is visible.
- I checked E3 and C3 only, not E8's text.
- Minor 2: the story's "fills read the latest" should add "inside the window; after it C3 refuses".

**(3) Can "push when HEAD is ahead" push a commit the run did not make? Yes, and the raw-quote guard does not stop it.**
This is the should-fix.

## Should-fix

**1. The desk's committer pushes commits whose files the raw-quote guard never checked.**
- **Probe.** Real `Git`, `GitCommitter` and `PendingCommitter`, with a bare origin. A stray local commit containing
  `.../quote-snapshots/2026/10/nifty_20261014_151500.csv` (not made by the run), then one run commit of
  `journal/runs/<day>.json`. Result: committed, and **origin now holds the raw quote file**.
- **Why.** The guard checks the given paths and the index (`staged()`), and `push` sends `HEAD`, which includes every
  unpushed commit. `GitAccountSync` refuses when unpushed commits exist (`other_work`), but `GitCommitter` does not.
- **Before E2b?** Any push already carried earlier unpushed commits. The new "push when ahead" adds the case where the
  run makes no commit at all.
- **Why it matters.** The guard exists so a raw quote file never reaches the public repository, and a push is what
  publishes.
- **Expected fix.** Before every push, check the files changed in `origin/<branch>..HEAD`
  (`git diff --name-only origin/<branch> HEAD`) against `RawQuoteGuard` and refuse naming them. That also covers a
  recovered commit. Test it: a stray local commit with a raw file is refused before any push, and origin is unchanged.
- **Optionally** also refuse unpushed commits not made by the run, as `other_work` does for account writes.

## Minor

1. **State the fresh-checkout rule in the story**, not only in response 118: a rerun in a fresh checkout has no marker
   and starts from what was committed. Fills and exits are idempotent against the committed journal, and a decisions
   step re-run after the deadline makes every book late (fail closed).
2. **"Fills read the latest" needs the window**: inside the execution window; after `fills_by`, C3 refuses.
3. **Plant Q5 survived.** Removing the `STILL_PENDING` refusal in `PendingCommitter.commit` passes all related tests.
   `run()` recovers first, so the branch is defensive, but it should have a one-line test or go.

**Verdict: FAIL for afafb07fbeaa78f3395219f045519e9bd92debee** on should-fix 1. A re-check needs the pre-push check
and its test, and the two story lines.

## Addendum 7 (15 Oct 2026): 8237214f7a523448d1b5a8316f2366f94b816d06

Parent afafb07. Decision 51 adds the pre-push guard and the refusal of stray unpushed commits, plus the story minors.

| Gate | At 8237214 | Trial merge with `main` fdaf4f6 |
|---|---|---|
| `env -u FNO_SLACK_BOT_TOKEN python -m pytest -q` | 3,949 passed | 4,683 passed |
| ruff check / format / `check_imports.py` | clean | clean |
| Conflicts | - | none (`reviews/claude/README.md` auto-merged) |

`git_sync.py` is 217 lines, `pending_commit.py` 73.

## Verdict: PASS (code); 3 minor

| Item | Status | Evidence |
|---|---|---|
| Addendum 6 sf 1, pushing what the guard never saw | MET | Before every push attempt, `RawQuoteGuard` runs on `git diff --name-only -z origin/<branch> HEAD`, deletions included. Before the pull, `_refuse_stray` refuses unpushed non-merge commits that are not the run's own; account writes refuse any unpushed commit through the same `Git.unpushed()`. My plants caught: S1 (no pre-push guard), S2 (`_own` always true), S3 (files rule dropped), S5 (no stray check), S6 (recovery not passing its own message), S7 (merges counted), S8 (account writes allowing strays). **S4 (subject rule dropped) survived** (minor 1) |
| Addendum 6 minors 1-3 | MET | The fresh-checkout rule and "inside the execution window; after `fills_by` C3 refuses" are in criterion 5. The unreachable `STILL_PENDING` branch is removed, and the docstring says why no marker can be left |

### The orchestrator's three points

**(1) A hand-made merge with its own edits passes (b).**
- In the dedicated checkout the run makes merges only through `pull --no-rebase --no-edit`. A conflicted pull fails as a
  `GitError`, so the run stops; it never commits a resolution. So an "evil merge" needs a person to make it in that
  checkout.
- Even then, (a) checks every file it changes against origin, so it cannot publish a raw quote file. What it could push
  is non-quote content.
- A local merge of a local branch brings its commits into `rev-list origin..HEAD --no-merges`, so they are checked as
  strays.
- Acceptable. It is reachable only by hand and cannot leak quotes.

**(2) "Own" is a subset rule, not the same set: `files_of(commit) <= names`.**
- A subset is right for the recovered commit (the commit touches what changed among the marker's files).
- **It does not check content.** A stray commit with the run's message, touching only the marker's paths, with other
  content would pass. To reach that, someone must copy the subject exactly and restore the files on disk to the marker's
  digests (`recover()` checks the disk first). So it is not reachable by accident, and (a) still blocks raw quote files.
- Minor 2: compare each file in the commit with the marker's SHA-256 (`git show <c>:<path>`), which makes "own" exact
  and cheap.

**(3) The new port parameter.**
- The non-test `Committer` implementations are `GitCommitter` and `PendingCommitter`. The callers are `DailyRun._step`,
  `PendingCommitter.recover`, D6's `book_versions.py:51`, the capture `execution_capture.py:52` and Book 1
  `book1.py:74`.
- Only `recover()` passes a value. Every other caller uses the default `""`, which allows no unpushed commit at all.
  That is the safe default: it fails closed with one alert naming the commit.
- One consequence to know: a Book 1 decision commit whose push was rejected stays local. In the same checkout, the
  daily run then stops at its first commit (alert names it), and exits are not reviewed until it is resolved by hand.
  That is consistent: account writes already refuse any unpushed commit, so exits could not run anyway. Pushing that
  decision late would also have been wrong, since a late-pushed decision must stay late.

## Minor

1. **Plant S4 survived.** Dropping the subject comparison in `_own` passes all 43 related tests. The story says the run's
   own commit is "told apart by ... its message", so add a test: a stray commit with another message, touching only the
   marker's files, is refused.
2. **Make "own" exact by content** (point 2 above): each file of the stuck commit must equal the marker's SHA-256.
3. Carried from earlier addenda (follow-ups, not E2b's): a failed commit in `fno desk book1` still ends in a traceback.
   Before A4b, a fresh rerun can report "not filled" for a filled trade.

## Next steps

- **Merge order** (decision 29 and this story's Depends line): after A4b. A4b is not on `main` yet: judge 111
  addendum 3 says its merge waits for the owner's probe.
- **Quality rule 9:** the code goes to ChatGPT after this PASS, before the merge.
- **My merge check** will verify:
  - `fno/scorecard/wiring.py` reads E6's snapshots through A4b's hash-checked store;
  - one version of `execution_capture.py` is kept;
  - the merged suite passes.

**Verdict: PASS for 8237214f7a523448d1b5a8316f2366f94b816d06** (code). Minors 1-2 can ride the A4b merge commit.

## Addendum 8 (15 Oct 2026): 9aefbc0ab1cbf6a1cda5a200cf6500aa0002b231

One commit on top of 8237214 (orchestrator's decision 54): the two code minors of addendum 7.
- Gates: 3,951 passed (the builder's figure); ruff, format and imports clean.
- `git merge-tree` with `origin/main`: no conflict.

| Item | Status | Evidence |
|---|---|---|
| Minor 1, the message rule tested | MET | A `reworded` case covers it. My plant S4 (subject comparison dropped) is now caught |
| Minor 2, "own" exact by content | MET | `OwnCommit` holds the message and each file's recorded SHA-256. `_own` requires the same subject, files within the marker's, and each committed file's content (`git show <c>:<path>`) equal to its recorded hash, where None means deleted. My plants caught: the content check dropped, the files rule dropped, and recovery not passing `OwnCommit` (S6) |
| Nit | - | The `GitCommitter` docstring wraps oddly ("Any / refusal or git failure is / raised"); cosmetic |

**Verdict: PASS for 9aefbc0ab1cbf6a1cda5a200cf6500aa0002b231** (code). The addendum 7 PASS carries to this SHA, and
it is the version for ChatGPT (quality rule 9). The merge still waits for A4b, and my merge check is as listed in
addendum 7.

## Addendum 9 (15 Oct 2026): merge re-check at d410374cdf037ff12d4625d33c1c782215077eb3

d410374 merges `main` 2355b80b (A4b, E1b, C5b and STR1b-1 included) into my PASSed 9aefbc0. These are the merge checks
I set in addendum 7.

| Check | Status | Evidence |
|---|---|---|
| One version of `execution_capture.py` | MET | It is identical to `main`'s (A4b's): `git diff 2355b80b d410374 -- fno/desk/execution_capture.py` is empty. It commits only `(record, sidecar)`, or the sidecar alone when the quote file was not saved. The raw CSV stays in Drive (E2b criterion 4) |
| E6 reads the 15:15 touch through A4b's store | MET | `scorecard/wiring.py` goes through `build_execution_snapshots` → `RecordedExecutionSnapshots(build_quote_store(...))` → `build_drive_only_quote_store`. So a fill outside the capture's checkout reads its touch from Drive, not "touch unknown" |
| Conflict resolutions | MET | `.gitignore` keeps both sides (E2b's pending-commit marker, A4b's raw-CSV ignore). `test_entry_limit.py` combines decision 45's digit-free reason test with E1b's Rs 20,00,000 opening |
| Merged suite | MET | 5,835 passed (the builder's figure); ruff and imports clean |
| ChatGPT review (rule 9) | MET | Review 105, answered in response 131. The public-reconstruction point goes to E2c (text PASS, judge 148 addendum 1) |

**Merge check: PASS for d410374cdf037ff12d4625d33c1c782215077eb3.** It may merge to `main` (pull, then the full suite on
the merged tree).

## Addendum 10 (15 Oct 2026): merge check on `main`

- **The merge is 4da1b850** (parents 8160e992 and d410374, my PASSed merge re-check). `main` f13c6ea2 then merged
  more work on top.
- **No hand edits.** 4da1b850's tree (`85f92e7…`) equals git's own `merge-tree` of its two parents byte for byte.
- **Exactly the PASSed diff.** Against its first parent it carries 47 files, 2,062 insertions and 192 deletions, the
  same as d410374 against `main` 2355b80b.
- **Suite on f13c6ea2** (`main` at the orchestrator's notice): 5,861 passed (Slack token unset).

**Merge check: MET.**
