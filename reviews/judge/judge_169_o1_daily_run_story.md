# Judge 169: O1 story text (one daily run), rule 1

**Verdict on a38dee6f1b402385d61752df8a5a80d20dcee869 (`story/o1-daily-run`, text `docs/stories/O1-daily-run.md`,
claims response 165): FAIL.** There are two should-fix findings, both on real paths of the 3 pm routine. The four
points the orchestrator asked about are otherwise correct.

Applied: `docs/JUDGE.md` rule 1; the owner's rules "keep the design simple" and "one builder per function" (a
contradiction with another session's passed work is a FAIL).

## Should-fix 1: the quotes step contradicts A4c's passed routine and leaves out the NSE and index recorders' timing

- **What O1 says.** The `quotes` step runs "A4's `record_today` (with A4c and the NSE recorder when those land), then
  commits `research/data/quotes/` at once". O1 also replaces CLAUDE.md's "3 pm quote recorder" section with its own.
- **What is already decided or passed.**
  - The NSE recorder runs inside the 14:33 routine today, in parallel with Groww, pushed after Groww
    (`conversations/2026-10-15.md`; the owner's YES). So "when those land" is wrong for NSE.
  - A4c's text, passed in judge 151 addendum 2, rewrote that same CLAUDE.md section:
    - NIFTY and NSE run in parallel from the start;
    - `record-indices` starts right after NIFTY's push, in its own 15:01-15:13 window;
    - each part commits only its own paths, NIFTY first. The text says "never `git add research/data/quotes/` as a
      whole".
  - A4c's code passed in judge 160 and waits only for the 16 Oct check.
- **The real path.**
  - O1's single sequential command commits the whole quotes folder. That is the rule A4c's text forbids, and it can
    sweep up another part's half-written files.
  - It does not say where NSE (14:55-15:10) and the indices (15:01-15:13, after NIFTY's push) run relative to E3's
    steps. E3's `pack` waits for NIFTY's canonical and its snapshot is at about 15:15. If `record-indices` runs in
    line before E3's steps, E3 starts about 4 minutes later. If it runs after, the indices miss their window.
- **Expected fix (text).**
  - Adopt A4c's passed steps 2-3b inside O1: parallel NIFTY and NSE; indices after NIFTY's push; per-part commit
    paths, NIFTY first.
  - State which run in the background beside E3's steps.
  - Make the new CLAUDE.md section carry A4c's per-part `git add` lines word for word, so there is one prompt and no
    contradiction.
  - Criterion 4 should test the per-part paths, not a whole-folder commit.

## Should-fix 2: what happens to the card when E3's commit-failure stop fires is not stated

- **The conflict.** O1 keeps E3's rule: "a failed **commit** stops the run with one alert naming the missed exits
  (decision 44)". `DailyRun` then raises `RunStopped`: no later step, nothing more committed. But criterion 2 says
  "every later step still runs, `exits` and `card` included", and criterion 5 says the card "still posts naming any
  earlier step that failed".
- **Which one wins after E3's stop is undefined.** T1's `card daily --post` posts, saves to Drive and writes delivery
  metadata, so it is a commit in the same checkout that E3 has just stopped. A commit failure in E3 is a real,
  already-judged case (decision 44, E2b).
- **Expected fix (text).** Say whether the card runs after a `RunStopped`. For example: it posts a "desk stopped"
  card without committing, or it does not run and the stop alert stands alone. Add a criterion and a test for that
  case.

## The orchestrator's four points

1. **E3's commit-failure stop (decision 44): kept.** O1 does not change `DailyRun`'s steps, and criterion 2 keeps the
   unchanged test. Only the card after the stop is open (should-fix 2).
2. **Per-step `live_from` gates: sound.** `weather`, `forecasts_v4` and `card` are recorded `not_live` and call
   nothing before their date (criterion 6, with a fake proving no call). The dates are set by the owner or the freeze,
   not by O1. This keeps a first live weather record from ending M1's back-fill before the freeze.
3. **The O8 run-log contract (criterion 7): sound.**
   - The shape is E3's own.
   - One `DAILY_RUN_STEPS` tuple is the plan the run loops over, and O8 imports it, so no parallel copy exists.
   - The statuses are `ok`, `failed`, `refused` and `not_live`, with `not_live` neither missed nor a problem.
   - Whichever of O1 and O8 merges second deletes O8's private list and its source-parsing test.
   - The note on `fno/constants.py`'s size is right (split, never squeeze).
4. **No trade beyond E3: confirmed in the text.** O1 adds no decision and no fill. `versions` … `exits` are E3's
   `DailyRun` steps "untouched", and the data checks are E3's `DataGate`. Said plainly: O1 is what first makes those
   E3 steps run every day (today nothing calls `fno desk run`). That is the point of the story and the owner's
   decision, not a new trade rule.

## Other checks

- **The start.** The prompt is updated, never a new scheduled task; the owner pastes it; Groww, Drive and Slack stay in
  the routine's environment, with no broker key in GitHub. That matches the owner's "timed jobs on routines" row
  (eeac1897).
- **Times are read from their owners** (G10, the recorder's window, `terms`), never typed again. That is right.
- **The work register.** O1 owns the routine prompt per the orchestrator. Should-fix 1 is exactly the place where that
  ownership must take in A4c's passed lines rather than overwrite them.

## Addendum 1 (15 Oct 2026): revision 2 at 63c2dd1fa52306b44231a4140f74fc2cfac12ae3 (main merged in)

**Verdict: PASS.** Both should-fix findings are met. Two notes.

- **Should-fix 1: met.**
  - The `quotes` step now starts A4c's passed steps 2-3b as child processes beside E3's steps:
    - NIFTY (Groww) and NSE together at the start;
    - `record-indices` right after NIFTY's push, each in its own window (today's and G10's times);
    - each part commits only A4c's paths, word for word, NIFTY first, never the whole folder;
    - the paths are one constant, checked against CLAUDE.md by A4c's own test.
  - E3's steps run in the foreground. `pack` is released by NIFTY's push, as E3 already waits for the committed
    canonical.
  - A new `quotes_done` step after `exits` collects the parts' results. The CLAUDE.md section keeps A4c's steps 2-4
    word for word, so there is one prompt and no contradiction with judge 151 or 160.
  - Criterion 4 tests the per-part paths, NIFTY first, and that a part running to 15:13 moves neither `decisions` nor
    `snapshot`.
- **The single git lock (4a): accepted.** A part's commit and an E3 commit asked for at the same moment in one
  checkout would otherwise collide on git's `index.lock`. A collision inside E3 is a `CommitFailed`, which stops the
  desk (decision 44). That is a real path once the parts run beside E3, and the lock is the simplest fix.
- **Should-fix 2: met.** After E3's `RunStopped`:
  - the card does not run (T1's `--post` writes delivery metadata, and nothing more may be committed);
  - the running parts finish and commit their own paths under A4c's rule, alerting for themselves;
  - `quotes_done` and `card` are not recorded, so O8 shows them missed;
  - the last line adds "no card today";
  - the owner's loss that day is stated (the card's forecast block and Slack witness; the forecasts stay committed by
    their own job).

  Criteria 2 and 5 test it with a fake card that proves no call, post or write.

**Note 1 (one line under "Known limits").** E3's `GitCommitter` refuses any unpushed commit it did not make
(`_refuse_stray`, decision 51; `fno/desk/git_sync.py`).
- So a quote part whose push is rejected every time leaves a local commit that stops E3 at its next commit, with one
  alert and the desk's later steps missed.
- That is a single real failure, the same kind E3 lists for itself ("a push rejected every time"). The lock does not
  cover it.
- State it, and make the parts' commits go through the same committer as E3's (`GitCommitter`: the raw-quote guard,
  pull and three push attempts), not a second git path.

**Note 2 (code round).** After E3's stop, a refused E3 commit can leave E3's files staged. A part's commit must commit
by pathspec (`git commit -- <its paths>`, as the A16e committer does), so it never carries E3's staged files. Criterion
4's "each commit stages exactly that part's paths" should be tested with another writer's file staged.
