# Judge 82: story E3, the daily timetable (branch, before merge)

Date: 14 Oct 2026 (UTC). Branch `story/e3-timetable` at c56c064 (from main e3506ec). Claims:
`reviews/claude/response_84_e3-timetable.md`. Story: `docs/stories/E-paper-desk.md` E3.

## Verdict: FAIL, two must-fixes (both shown by probe)

The timetable, idempotent restart, common retry, exits-always-run and the C4 seam work, and my 7 plants are caught.
But two things break:
- a book recorded as "no decision (late)" is still **filled**;
- the account sync's `git reset --hard` destroys **any** unpushed commit and any uncommitted edit in the checkout,
  not only its own account commit.

## Gates (my runs, `python -B`, caches cleared)

- Full suite: 2,612 passed. Ruff and imports: clean.
- `git merge-tree` with `main`: clean.

## Must-fix 1: a late book can still fill (criterion 1)

**My probe.** In the branch's own fixtures, a Book 1 run was committed at 15:11:50 by the committer's clock (before
the 15:12 deadline) but became visible only at 15:13, as a push that lands after the collector's pull would.
- The `decisions` step at 15:12 wrote "**no decision (late)** ... nothing committed before the deadline".
- The `fills` step at 15:15 then **opened the trade: 4 legs filled.**

**Cause.** `DeskSteps.fill` asks the decision source again (`self.decision(book, day)`). It does not use the runs the
`decisions` step collected and recorded. Any run that becomes visible after the deadline with a commit time before it
joins the fills. That is exactly "cannot join later" broken. It needs no bad intent: the push only has to land after
the collector's pull.

**Fix (and my ruling on point 2):** the `decisions` step is the only truth.
- It records, per book, the run ID and the commit that holds it, plus the `origin` commit it pulled at the deadline.
- `fill` uses only those recorded runs. A book recorded "no decision (late)" never fills.
- On a restart after the deadline when the `decisions` step was never recorded, only runs contained in a commit
  recorded before the deadline count. With none, every book gets "no decision (late)" (fail closed).
- Test: the probe above must end "not filled".

## Must-fix 2: the reset can destroy work that is not the run's (orchestrator's point 1)

**My probe** on the branch's two-checkout fixture. Checkout B held an **unpushed decision-run commit** (as left by an
earlier `GitCommitter` whose push was rejected three times) and an **uncommitted edit** to a tracked file. Then
`GitAccountSync.write` hit a rejected push and ran `git reset --hard origin/main`.
- The decision file was gone.
- The decision commit was gone from B's history.
- The edit was gone.

The docstring says "run it only in the desk routine's own checkout". But even in that checkout, the run's own earlier
unpushed commits (a decision, a capture record, a run log) are destroyed, and nothing checks the precondition.

**Fix:**
- Before any account write: refuse with a named error unless the worktree is clean (`git status --porcelain` empty
  for tracked files) and nothing is unpushed (`git rev-list @{u}..HEAD` empty).
- Before the reset: confirm the only commits ahead of `origin/<branch>` are this write's account commit and the
  pull's merge. Otherwise stop with an alert and never reset.
- Test the probe above: the write refuses and nothing is lost.
- Make the "dedicated checkout" rule a check, not a comment.

## The orchestrator's other points

2. **Commit time as the on-time test (ruling):** git committer time is the committing machine's clock and can be
   edited, so it is not strong enough alone, and must-fix 1 shows the push gap matters more than skew. Use the
   collector's own observation as primary: what it pulled at the deadline (the commit SHA). D3's committer-time check
   at the fill stays as a second check. Server-received time (GitHub push events) would be stronger still, but needs
   the API. Not required now.
3. **Book 1's automatic D6 versions: accepted.**
   - It renews only the playbook component, and that is derived mechanically from committed registry rows (an
     owner's status change or the hard-loss rule). It is not a judgement.
   - It registers and commits before the day's decisions (a strict ancestor, as D6 requires).
   - It never creates the first version, and it refuses (alerting "the owner registers") when any other component
     changed or D6 refuses a second version the same day.
   - This is consistent with D6 and judge 78: it keeps Book 1 scored after its own stops, which is the point of judge
     80's follow-up (a). The reason text names it as automatic.
4. **The seams without real implementations: acceptable for E3's criteria.**
   - The story's test plan is "end to end over 5 simulated days with fakes", and I checked the seams fail safe:
     `build_daily_run` has no default C4, so the run cannot be built without one, and there is no permissive stub.
   - But E3 is **built, not live**: there is no `desk run` command, no routine, no real order builder (E5) and no C4.
   - The story status must say exactly that, and "Judge verifies: one week of run files" waits until it runs for real.
5. **The C3 alert change: no weakening.**
   - The gate sends one alert per distinct text.
   - The "exits due, waiting for a readable snapshot" alert has its own text, the trade list appended, so it is
     still sent, even after the plain failure alert for the same snapshot.
   - Test: `test_the_same_failure_is_alerted_once_however_often_it_is_checked`.
   - The deduplication is per `DataGate` object (one run). That is fine.

## My plants (`tests/timetable` and `tests/checks`, 51 tests): all 7 caught

| Plant | Result |
|---|---|
| C4 problems ignored | 2 failed |
| No common retry | 2 failed |
| Fills on an invalid snapshot | 1 failed |
| A restart repeats steps | 1 failed |
| Exits step removed | 2 failed |
| The late-at-fill check off | 1 failed |
| No reset on a rejected push | 1 failed |

## Per criterion

| # | Criterion | Result |
|---|---|---|
| 1 | Late book: "no decision (late)" committed, others unchanged | **NOT MET** (must-fix 1) |
| 2 | Every timely decision references the same snapshot ID and hash | MET (tests; the result per fill carries both) |
| 3 | Invalid snapshot: no new risk, one common retry, exits run | MET (plants 2, 3 and 5) |
| 4 | A non-session day runs nothing | MET (holiday and muhurat tests) |
| 5 | A restart repeats nothing | MET (plant 4), subject to must-fix 2 for the git side |
| 6 | Every step's times, inputs and result in `journal/runs/<date>.json`, committed | MET (test) |
| 7 | No fill without a completed C4 pass, every book | MET through the `ValidityGate` seam (plant 1); real C4 pending |

## Project rules

- New modules behind ports (`daily_ports.py`). Composition root `fno/desk/daily_wiring.py`.
- The timetable is in `config.yaml` with order checks. No orders and no secrets.

## Addendum 1 (round 2, branch 38d1bdb): both must-fixes MET; not yet PASS (one item carried from judge 83)

**Must-fix 1 (a late book filled): met.**
- The `decisions` step pulls once at the deadline and records the origin it saw. Per book it records the run ID, its
  holding commit and the committer time.
- `fill` reads only those recorded runs, through `DecisionSource.recorded`, which refuses a run not held by the
  recorded commit.
- A collection more than 30 s after the deadline (a restart) marks every book late.
- **My round-1 probe re-run:** the run committed at 15:11:50 but visible at 15:13 is now "no decision (late)", with
  no fills and no account rows.

**Must-fix 2 (the reset destroying other work): met.**
- An account write is refused (`CheckoutNotDedicated`, with an alert) unless the tracked worktree is clean and
  nothing is unpushed.
- Before a reset, exactly one commit (this write's) may be ahead of the pulled origin.
- **My round-1 probe re-run:** with an unpushed decision commit in checkout B, the write is refused ("1 unpushed
  commit(s)") and the decision file is kept.

**"Built, not live"** is in the story status.

**My plants (`python -B`, caches cleared; `tests/timetable` and `tests/checks`, 57 tests): all 11 caught.**
- 4 new ones: the collection grace off, the dedicated-checkout check off, the "only one commit ahead" check off, and
  the recorded commit not compared.
- The 7 from round 1.

**Gates:**
- full suite: 2,618 passed;
- ruff and imports: clean;
- `git merge-tree` with current `main`: clean.

**Still open, so not yet PASS:** judge 83's ruling arrived after this round began, and it is not in 38d1bdb. The only
`ValidityGate` is the port; the run takes one from its caller. E3 must supply the gate itself:
- `ValidityGate` passes an order only when the **committed D3 record** of that opportunity holds a completed C4 pass
  (`validity.c4` with `ok: true`);
- a null or failed `validity.c4` means "not filled";
- it never re-runs C4 against the 15:15 execution capture, whose mids differ from the decision's;
- `build_daily_run` wires this gate itself, not taking any gate from its caller;
- one test with a passing record and one with `c4: null`.

That is one small round. I will check only that.

## Addendum 2 (8502dd1, judge 83's gate): PASS

**The gate:**
- `RecordedC4Pass` (`fno/desk/recorded_c4.py`) is E3's own `ValidityGate`, and `build_daily_run` wires it itself (no
  gate taken from the caller).
- It reads the committed D3 record of the order's opportunity, from the run folder the `decisions` step recorded.
- It passes only when that record exists, the run's files match their committed `records.sha256`, and `validity.c4`
  has `ok: true` with checks.
- It takes no market or snapshot input, so it cannot re-run C4 against the 15:15 capture.

**My plants (`tests/timetable`, 30 tests):**

| Plant | Result |
|---|---|
| The edited-files check off | caught |
| `ok` not required | caught |
| Empty checks allowed | caught |
| A missing record passing | caught |
| **`build_daily_run` wiring an always-passing gate instead** | **not caught** |

**Should fix (not blocking):**
- One test that `build_daily_run` uses `RecordedC4Pass`, so a later edit cannot swap in a permissive gate unseen.
- Once C4 merges, one test building the record with C4's real `ValidityReport.record()` rather than a hand-made
  dictionary, so a C4 format change breaks E3's test and is not missed. C4 is still in its fix round (judge 83).

**Gates:**
- full suite: 2,628 passed;
- ruff and imports: clean;
- `git merge-tree` with current `main`: clean.

**Verdict: PASS for 8502dd1.**
- E3 stays "built, not live" until E5's orders, C4, a `desk run` command and its routine exist.
- After the merge I check `main` against 8502dd1 and CI.

## Addendum 3 (merge check, 79c8fac)

**MET.**
- 79c8fac has parents 510858c (main) and 8502dd1 (the passed tip). It equals my recomputed merge of the two, with no
  difference.
- No other code has reached `main` since.
- My full suite at 79c8fac: 2,628 passed.
- CI `checks` is green on 79c8fac (run 38523328037).

## Addendum 4 (should-fixes, branch `story/e3-gate-tests` ec9be1c, tests only): PASS

Both judge 82 addendum 2 should-fixes are met. No `fno/` file changes. The shared fixture moved to
`tests/timetable/c4_records.py`.
- **Wiring test:** `build_daily_run` must hold `RecordedC4Pass`.
- **C4's real format:** `ValidityReport.record()` is written through D3's own store and read by the gate.
  - The app writes exactly that object: `decision_record.py` stores `c4.record`, which `validity_adapter.py` builds
    from `report.record()`.
  - A passed report fills, a failed one names its failed check, and an empty report is not a completed pass.

**My plants (3), against the two new tests only:**

| Plant | Result |
|---|---|
| An always-pass gate wired in `daily_wiring.py` | caught |
| `c4["ok"]` ignored | caught |
| An empty `checks` list accepted | caught |

**Gates (my runs, `python -B`, caches cleared):**
- full suite: 2,782 passed;
- ruff, format (620 files) and imports (627): clean;
- `git merge-tree` with current `main` (d3668fc): clean.

The builder's merge-order note is right. E5 removes `CommittedDecision.orders`, which this fixture still passes.
Whichever merges second must update the fixture and run the full suite on the merged tree.

**Verdict: PASS.** After the merge I check `main` against ec9be1c and CI.

## Addendum 5 (merge check, 85c570a)

**MET.** 85c570a has parents f6e4b9d (`main`) and ec9be1c (the passed tip), and it equals my recomputed merge. The
later `main` merges 9811203 and 81c9c86 also equal their recomputed merges. The only code changes on `main` since my
last check are the two passed branches (e3-gate-tests and c4-a4-valid-quotes).

CI `checks` is green on 9811203, which holds this merge (run 38532877389). The run on 81c9c86 (both merges) was still
in progress when I wrote this; I confirm it at my next check-in.

**Confirmed:** CI is green on 81c9c86, which holds both merges (run 38533124620). My full suite there gives 2,792 passed.

## Addendum 6 (ruling on the orchestrator's question: scope the clean-checkout check?)

**Question:** today any dirty tracked file anywhere refuses every book's account write. Would "nothing unpushed, and
no dirty file under `journal/` or the account folders" keep judge 82's safety?

**Ruling: yes in part, as a follow-up, and only together with a change to the reset. Reasoning only, not blocking
E5.**

1. **Why the check is repo-wide today.** The rejected-push path runs `git reset --hard origin/<branch>`. That destroys
   **every** uncommitted tracked edit in the checkout, not only the account's. Narrowing the check while keeping
   `--hard` would bring back judge 82's defect: a reset that silently wipes someone's edit outside `journal/`.
2. **What makes narrowing safe.** Use `git reset --keep origin/<branch>`. Git then keeps local edits to files the reset
   does not touch, and refuses (fails closed) if it would overwrite one. With that, the check can become:
   - nothing unpushed besides this write's own commit (unchanged);
   - no dirty tracked file under **this book's** folder (`journal/<book>/`), because `commit_paths` adds the whole
     folder and must not sweep in another writer's partial work.
3. **It would not have prevented D.** D's dirty file was `journal/book1_rules/validity_failures.csv`, inside Book 1's
   own folder, so Book 1's writes are still refused. What scoping per book does change is the blast radius: **Book 2's
   and Book 3's writes would go through** instead of every book stopping. That is worth having.
4. **Tests on real git** (the two-checkout fixture):
   - a dirty file outside the book's folder survives a rejected push and its reset, and the fill is applied;
   - a dirty file inside the book's folder refuses;
   - another book's dirty folder does not refuse this book;
   - an unpushed foreign commit still refuses.

Whatever the scope, the root rule stays: every writer commits what it writes (must-fix D). The check is a backstop,
not the fix.

## Addendum 7 (`story/e3-scoped-account-check` bf4863e, my addendum 6 built): PASS

**What changed:**
- An account write is refused only while something is unpushed, or while **this book's folder** holds uncommitted work.
- The rejected-push reset is `git reset --keep`. If it would overwrite a local edit it refuses, stops and alerts.

**The builder's deviation, ruled: accepted.** It also refuses **new untracked files** in the book's folder (ignored
`.lock` and `*.tmp` files aside).
- My ruling named only "dirty tracked files", but `commit_paths` runs `git add` on the whole folder. An untracked file
  there would be swept into the account commit just as surely.
- This is stricter in the right place, so it is a correct extension.

**My real-git probe** (the two-checkout fixture, token unset):
- Book 1's folder holds a tracked uncommitted edit (the D-case CSV), and `README` has an edit outside every folder.
  - Book 1 is **refused**. **Book 2 writes OK**: before this change it was refused.
  - The `README` edit survives.
- An untracked file in Book 2's folder refuses Book 2.
- The rejected-push reset path is covered by the builder's tests: my `--hard` plant fails 2.

**My plants (5, `tests/timetable`, `desk`, `book1`): all caught.**

| Plant | Result |
|---|---|
| `reset --hard` again | 2 failed |
| Untracked files ignored | 1 failed |
| Whole-checkout check again | 3 failed |
| `--keep` failure not stopped | 1 failed |
| The unpushed check dropped | 1 failed |

**Gates (my runs, `python -B`, caches cleared, Slack token unset):**
- full suite: 2,860 passed;
- ruff, format (640 files) and imports (647): clean;
- `git merge-tree` with current `main` (d053bb0): clean.

**Remaining by design:**
- A dirty file outside the folder that the pull itself would overwrite makes `git pull` fail, so that write is refused
  (fail closed).
- Book 1's own leftover still stops Book 1 until it is committed. The root rule stays: every writer commits what it
  writes.

**Verdict: PASS** for bf4863e. After the merge I check `main` and CI.

## Addendum 8 (merge check, e6484cc)

**MET.**
- e6484cc has parents 7712e80 (`main`) and bf4863e (the passed tip), and it equals my recomputed merge.
- The only other code on `main` since my last check is the S1 merge (judge 85 addendum 2).
- CI on e6484cc (run 38547211119) was in progress when I wrote this; I confirm it at my next check.

**Confirmed:** CI is green on e6484cc (run 38547211119).
