# Judge 123: story E5b text, one Book 1 decision a day and recovery after a failed commit (quality rule 1; judge C)

Date: 15 Oct 2026 (UTC). Branch `story/e5b-book1-commit-failure` at **aca525df523236008222adb99da0dd128ad04df4**
(text only: `docs/stories/E-paper-desk.md` E5b, response 123), based on E2b at 9aefbc0. Checked against:
- the orchestrator's decisions 46 and 57;
- judge 118 addenda 3, 7 and 8;
- the code at aca525d: `fno/books/book1.py`, `book1_wiring.py`, `book1_cli.py`, `fno/playbook/decision_store.py`,
  `fno/desk/committed_decisions.py` and `fno/desk/pending_commit.py`.

## Verdict: FAIL (text), 2 should-fix; 2 minor

**The design is right:**
- The CLI catches `CommitFailed`, sends one alert and exits 1.
- Recovery reuses E2b's `PendingCommitter` with Book 1's own marker, so the two commands never overwrite each other's
  marker.
- Nothing is regenerated, and a changed file stops the rerun.
- Most of all, the one-decision-a-day rule closes the look-ahead hole: a second run with fresher inputs would be read by
  E3 as the day's decision.

### The orchestrator's points

**(a) Is there another path that writes a Book 1 run? Not in code today.**
- `build_decision_run` (`fno/playbook/wiring.py:100`) has one caller, `book1_wiring.py:32`, which is used only by
  `Book1.decide` (`fno desk book1`).
- The other `DecisionStore` users only read (`committed_decisions.py`, `scoreboard/*`, `book1_records.py`) or write the
  no-decision marker file (`no_decision.py`).
- No D3 correction writer exists yet: `corrects` is always None (`decision_record.py:93`).

But a check in `Book1.decide` only covers the run of `Book1.decide` **in that checkout**. See should-fix 1.

**(b) Does criterion 0 cover the marker-only case? Yes**, in its words: "the same with the decision only recorded by the
marker". One unmarked state is not covered. See should-fix 2.

**(c) The builder's reason for leaving D3's store as it is: accepted.**
- The store serves every book and D3's corrections, so a per-book rule belongs to the book.
- The real point is the collector's "latest run before the deadline" (`committed_decisions.py:36-41`). It is correctly
  raised as a question for the orchestrator, not changed here.

**Rule 9: agreed, E5b is a money path.** It decides which decision trades, so it goes to ChatGPT after my code PASS.

## Should-fix

**1. "A decision run already on disk" must include what origin holds, or a second checkout can decide again.**
- **The gap.** `Book1.decide` builds the run before any pull: `DecisionRun.decide` writes it, and only then does
  `GitCommitter.commit` pull. So the one-a-day check sees only this checkout's files.
- **How a second decision happens.** A second checkout (a scheduled session fired twice, or a retry in a fresh container
  while the first container's push is still on its way) has no run and no marker for the day, so it decides again.
  - If both runs are named `-r1` with different content, the pull conflicts. That fails closed.
  - If the first checkout already had `-r1` (an earlier "no approved" day file, or a stale checkout), the run IDs differ
    and both can reach origin.
  - E3's collector then takes the later one, exactly the hole decision 57 closes.
- **Expected text fix.** Do the one-a-day check after bringing the checkout up to date with origin (a pull, or a fetch
  plus a look at `origin/<branch>`'s decision folder for the day). Also check it again just before the commit: refuse to
  commit a new Book 1 run if the pulled tree already holds one for the day.
- **Test.** Two checkouts of one bare origin each run `fno desk book1` for the same day. Origin ends with one decision
  run for Book 1, and the second run alerts or reports "already decided".
- **Alternative root fix.** E3's collector takes the *first* Book 1 run committed before the deadline, not the latest. It
  closes every path, including hand-made runs, but it changes E3/D3 semantics (corrections), so it is the
  orchestrator's call. Either way, state which.

**2. A run on disk that is neither committed nor in the marker must not be reported as "already decided".**
- **The gap.** The story says a run on disk means "it recovers the pending commit, or reports already decided".
- **When it happens.** A run can sit on disk with no marker: the process stops after `DecisionRun.decide` writes the run
  and before `PendingCommitter` writes its marker (the marker is written inside `commit`).
- **Consequence.** The rerun then says "already decided" with no alert, and the decision is never published. E3 then
  finds no decision, and the book is "late" with nothing saying why.
- **Expected text fix.** Name this third state:
  - a run in the day folder,
  - not in `HEAD`,
  - and not in the marker.

  It gives one alert naming the run and the hand fix (commit it as recorded, or remove it before the deadline). Never a
  quiet "already decided", and never a new decision. Add it to criterion 0.

## Minor

1. **Criterion 0's "one alert naming the changed input file"** should say which comparison is used: the day's
   recomputed inputs against the run's `inputs.json`, byte for byte. It should also name the file when the run holds
   more than one input file.
2. **E3's collector on a correction run before the deadline** (the Out question) should go to the owner together with
   should-fix 1's alternative, since both are about which Book 1 run counts.

## Project rules

- Lane 1: it decides which decision is acted on.
- Depends on E2b merging first (`CommitFailed`, `PendingCommitter`).
- `PendingCommitter` gains a marker-name argument: one new constructor argument, no second class. That is right (DRY).

**Verdict: FAIL for aca525df523236008222adb99da0dd128ad04df4** (story text) on should-fixes 1-2. A re-check needs only
the scope lines for the one-a-day check and criterion 0.

## Addendum 1 (15 Oct 2026): b94f4db233167613ffedf41240056ed3738c4b2a

Text only (`git diff aca525d b94f4db`: the E5b section and response 123), following the orchestrator's decision 59.

| Item | Status | Evidence |
|---|---|---|
| sf 1, origin | MET | `Book1.decide` fetches and looks in three places: origin's day folder, `HEAD` and disk. Book 1's committer re-checks the pulled tree after its pull and before its commit, refusing through `CommitFailed` (one alert). Criterion 0 adds two checkouts of one bare origin, in sequence and with the second pulling only after the first decided: origin ends with exactly one run. Decision 59 (b) puts the guarantee in D3b (the collector takes the *first* non-correction run before the deadline), so a run that slips past is never the decision. Prevention plus guarantee is the right pair |
| sf 2, on disk only | MET | It is named as the third state: one alert, the hand fix, never a quiet "already decided" and never a new decision. `--commit-run <run_id>` refuses a run that `DecisionStore.edited` finds edited and never runs D2. It is in criterion 0 and in the judge's plant list |
| Minor 1, input comparison | MET | Byte for byte against each recorded input file, naming each file and the top-level fields |
| Minor 2, correction runs | MET | Decided by decision 59 (b), carried by D3b |

### The orchestrator's question: can `--commit-run` publish a run decided after the deadline as timely? No.

From the code at this SHA:
- **Timeliness comes from commit time.** E3 judges a run by the committer time of the commit that adds its
  `records.sha256` (`committed_decisions.py:50-55`, `committed_at < deadline`). A commit made by `--commit-run` gets the
  local time when it runs. It cannot be earlier than the decision it holds, so a run decided after the deadline is
  always committed after it.
- **Timeliness also comes from visibility.** The collector pulls once at the deadline (`collect_decisions`,
  `observe()`) and records the run and commit it saw. A restart after the deadline plus grace makes every book late
  (`daily_steps.py:91-94`). A run pushed after the collection is never read for that day.

So `--commit-run` adds no timeliness of its own. Only someone forging the committer date and pushing before the deadline
could cheat, and that is a hand forgery outside this tool.

## Minor (text, for the code)

1. **Say that `--commit-run` passes the same pre-commit check as a decision** (no other Book 1 run of the day in the
   pulled tree). Also say it accepts only a run in the on-disk-only state: not in `HEAD`, not on origin, not in the
   marker. Otherwise it could publish a second run beside a committed one, which D3b would then ignore but the record
   would still hold.
2. **Say that `--commit-run` never sets or changes a commit date** (no `GIT_COMMITTER_DATE`), and that timeliness stays
   with E3's collector by commit time and visibility at the deadline. That is the answer above, written down where the
   code author will read it.

Rule 9 stands: E5b is a money path, so it goes to ChatGPT after my code PASS.

**Verdict: PASS for b94f4db233167613ffedf41240056ed3738c4b2a** (story text). Code may start once E2b is on `main`
(`CommitFailed`, `PendingCommitter`). Minors 1-2 go into the story or the code's docstrings; I check them in the code.

## Note (15 Oct 2026): the owner's "keep the design simple" rule

Under `docs/DESK_DECISIONS.md`, 15 Oct row "Keep the design simple":
- **Addendum 1 minor 1 (`--commit-run` refusing a second run) is now a note only.** It needs a person to apply the hand
  fix wrongly.
- **Minor 2 stands.** It is one sentence: never set commit dates.
- **The two-checkout pre-commit re-check (should-fix 1) is flagged to the orchestrator.** It may count as unlikely while
  no routine runs `fno desk book1`. The check against origin before deciding is cheap and covers a real fresh-container
  rerun.
