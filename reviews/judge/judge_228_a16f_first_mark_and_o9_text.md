# Judge 228: A16f (first mark, push to main) and O9 story text: `story/a16f-first-mark-and-main` 4c6fb11 (lane 1)

**What I did:**
- read the whole diff against current `main` (six files);
- read `OwnedPathsCommitter`, which A16 uses, to see how the new refusal interacts with it;
- read the O9 story in full;
- searched `main` for frozen records and tools that read `research/data`;
- ran the gates on a trial merge.

## Gates

On a trial merge with current `origin/main` (clean): **6909 passed** (`-n auto`). `main` now needs `pytest-xdist`
because `pytest.ini` carries `--dist`, and it is in `requirements.txt`. Ruff, format (1223 files) and
`check_imports` are clean.

## A16f: criteria

| Criterion | Status | Evidence |
|---|---|---|
| (a) A run started at 08:53:17 with `--until 10:05` takes 09:15-10:00, all good | MET | `run()` no longer ends on `NO_MARK`; `_wait_for_next_mark` sleeps until the next mark is within `MAX_WAIT`, then `snapshot()` takes it. The test reproduces 16 Oct's start time and asserts four good marks |
| (b) `--until` before the first mark ends without waiting | MET | The loop still breaks when `_later_mark(until)` is false; tested |
| (c) A session branch absent from origin publishes to `main`; no branch is created on origin | MET | The pull now fetches and merges `origin main`, and the push is `HEAD:main`. The test checks out `claude/lucid-ptolemy-test` and asserts the row on `origin main` and no such branch on origin |
| (d) A branch carrying another change is refused, the path named, `main` untouched | MET | `pull()` lists `git diff --name-only origin/main...HEAD` and refuses any path the writer does not own. It uses `self.owns`, which `OwnedPathsCommitter` (A16) overrides, so A16's owned files pass and nothing else does. Tested with `code.py` on `story/x-unjudged` |
| (e) Existing recorder and committer tests pass | MET | Full suite above |

**Root cause (strong evidence):** both defects match the 16 Oct record in the story. The early-exit fix is the right
place: `snapshot()` keeps its 15-minute cap and `run()` owns the waiting. Pushing data to `main` from any branch is
safe only because of the refusal, which keeps unjudged code from riding along.

**A16f risks (follow-ups, not blocking):**
1. **A refused push is silent.** If the routine's agent commits anything else on the session branch before the recorder
   pushes, for example a conversation log, every mark prints `NOT committed: pull failed: ... carries changes ...`
   and the rows stay in the container. That is the 16 Oct failure in a new form. The output names the paths, but
   nothing alerts #fno-desk. The routine prompt must commit nothing else until the recorder ends. Better: an
   unpublished-row alert, the "nothing left unpushed" last step the story already names.
2. The same push-to-main now applies to every user of the committer (manifests, read-model inputs). That is intended
   and covered by (d).

**Verdict for A16f:** the code passes. It is urgent for Monday 19 Oct's 08:52 fire.

## O9 story text: one must-fix

The owner's decision is quoted with the question asked ("Hash receipt only"), and the design is sound:
- `RawFileStore` stays the seam;
- every record is written once;
- receipts carry only paths and hashes;
- readers sync to a SHA-checked cache;
- risks are stated: single point of failure, 0.41 MB/s, the token expiry around 20 Oct.

**Must-fix: the plan removes data from HEAD that frozen records and tools read.** On `main` these name
`research/data` files:
- `research/2026-10-12-experiment-1/FREEZE.md`;
- `research/forecasts/FREEZE.md`, `FREEZE_v2.md` and `FREEZE_v3.md`;
- the G6 v4 calibration tools that compute the **operative thresholds**: `tools/v4_size_study.py`,
  `v4_brier_regimes.py`, `v4_futility_study.py`, `v4_regime_stress.py` and `v4_vix_null.py`, which read
  `warmup_closes.csv`;
- 22 test files.

"Remove the files from HEAD in one commit per folder" would break those freeze checks and tests, and with them G8's
`operative_thresholds`. The story must list frozen and test inputs as their own class, and say how each stays valid.
Either they stay in the repository as frozen inputs, like the calendar, or the freeze record pins their SHA-256 and
the reader fetches exactly that file from Drive. It must also add a criterion: every freeze check and the full suite
pass after the removal.

**Should-fix (story level):** receipts appended to **one** file by two overlapping runs collide on merge, as two lines
at the end of the same file. The story's own race case (criterion 3) needs per-write receipt files or a union-merge
rule, stated now.

**Verdict for O9: FAIL** (story text, one must-fix).

## Verdict on the SHA

**FAIL for 4c6fb1179029a096701aa243eec6d149c24749ed as a whole, only because O9's text rides in the same commit.**

The **A16f part passes**. To merge it before Monday: push a commit that removes `docs/stories/O9-data-to-drive.md`
from this branch, or moves it to its own branch, with the A16f files byte-identical. I will PASS that SHA after
checking only that diff.

## Addendum 1 (16 Oct 2026): f4bedbeb (4c6fb11..f4bedbeb)

- `git diff --stat 4c6fb11 f4bedbeb`: only `docs/stories/O9-data-to-drive.md` is deleted (106 lines). Every A16f file
  is byte-identical to what I judged at 4c6fb11. Against the merge base the branch now carries only A16f's five files.
- The gates of judge 228 stand: the code is unchanged, and the only change is a deleted file that nothing reads. The
  trial merge with `main` was clean, with 6909 passed.
- The builder accepted O9's must-fix and should-fix, and checked the same freeze files, tools and tests. O9 returns on
  its own branch.
- Follow-up 1 is partly covered: the routine prompt now starts with `git checkout -B main origin/main`. The
  "commit nothing else" line and an unpublished-row alert go to the next A16 story.

**Verdict: PASS for f4bedbeb (A16f).** Merge before Monday 19 Oct's 08:52 fire. After the merge I check the merge and
CI, and Monday's run log for 09:15 taken as good and the rows on `main`.

## Addendum 2 (16 Oct 2026): merge check, A16f merged to main as 4a83ce6

- **Merge is exact.** 4a83ce6's parents are c77868af (main) and f4bedbeb (the passed tip). Recomputing the merge with
  `git merge-tree --write-tree` gives a tree identical to 4a83ce6's (empty diff).
- **A16f files are identical on main.** `git diff f4bedbeb 4a83ce6` on all five A16f files is empty, and nothing
  under `fno/intraday`, `fno/storage` or their tests changed between 4a83ce6 and the current head 78e7daa.
- **CI.** The parent is green. The run on 78e7daa, which contains the merge, was in progress; I confirm it in my
  report.
- **Monday 19 Oct:** I check the 08:52 run's log for 09:15 taken as good and the rows on `main`.

**Verdict: merge check PASS** (CI on the merge to be confirmed).

## Addendum 3 (16 Oct 2026): O9 v2 story text at 35dfd5ec (`story/o9-data-to-drive`, text only)

The branch changes four files, all documentation: `docs/stories/O9-data-to-drive.md` (179 lines), response 238 (the
read-only inventories, 419 lines), and one row each in the claude README and the work register. No code or tests.

**Judge 228's points:**

| Item | Status | Evidence |
|---|---|---|
| Must-fix: frozen and test inputs | MET in substance, with one flaw (below) | Section 4 sorts them into three classes: freeze-checked, recorded but not checked, and tests that read real data (about 45, more than my 22). Criterion 5 requires every freeze check and the full suite to pass after removal |
| Should-fix: receipt collisions | MET | Rule 3: one receipt file per Drive write (`receipts/<drive path>.sha256`), so a merge cannot conflict |

**The design is sound and evidence-based:**
- The owner's words are quoted.
- Write-once is enforced by the existing `RawFileConflict`.
- Appended tables become parts, and mutable state becomes versioned snapshots.
- Readers read through a SHA-checked cache, and only the data root changes.
- Section 5 maps every mechanism that relies on git history to its receipt.
- A16's one-taker claim rests on the measured 16 Oct 429 evidence.
- Each step gets its own judge round, and a step switches only when its readers work.

## Must-fix

**1. Section 4.1 changes a frozen file.** "The check reads the bytes from the Drive cache instead of the working
tree" means editing `fno/forecast/freeze.py`, but `freeze.py` and `freeze_v2.py` are themselves listed with their
SHA-256 in `research/forecasts/FREEZE.md` (line 27) and `FREEZE_v2.md` (lines 41-42). Changing them breaks the v1
and v2 freezes, which would need a new forecast version. Fix (wording): leave the frozen check code unchanged.
- Before a freeze check, the cache sync writes each freeze-checked file back to its **original repository path**,
  git-ignored, with the same bytes.
- `changed_files(root, freeze)` then compares the same hashes, untouched.
- Rule 5's commit refusal still holds, because those files are ignored and never committed.

## Notes (not blocking)

- **4.2 is simpler than written.** History is not rewritten (section 7), so `git show <commit>:<path>` keeps working
  for experiment 1 and for the recorded freeze versions. The upload is a useful second copy, but the test does not
  need to change.
- **Section 6's claim rule:** the losing run's push is rejected and its pull meets an add/add conflict on the claim
  file. The committer settles it with `-X theirs` (A16's option). The A16 step's acceptance must test exactly this
  race: two clones, one claim, the loser sees the winner's file and waits.
- **Drive token:** the first text named the token expiring about 20 Oct 2026. O9 makes every run depend on that
  token, so re-issuing it from the published app belongs before step 2.
- Response 238 is 419 lines. It is a review file, which the size test does not cover, as with earlier long
  responses.

**Verdict: FAIL for 35dfd5ec** (story text), on must-fix 1 only: one sentence in 4.1 plus the restore-to-path
step. Everything else is ready for the owner and for market-brief's own approval.

## Addendum 4 (16 Oct 2026): O9 v2 story text at 1664d638 (35dfd5ec..1664d638)

The diff touches one file, `docs/stories/O9-data-to-drive.md` (+13/-7).

| Item | Status | Evidence |
|---|---|---|
| Must-fix 1: frozen check code | MET | 4.1 now leaves `freeze.py` and `freeze_v2.py` untouched and cites their pins (FREEZE.md line 27, FREEZE_v2.md lines 41-42). The cache sync writes each freeze-checked file back to its original path (git-ignored, same bytes, checked against its receipt), and `changed_files` compares the same hashes. Rule 5 still holds |
| Note: 4.2 | Taken | `git show` stays and experiment 1's test is unchanged; the byte-exact upload is kept as a second copy |
| Note: claim race | Taken | Criterion 3 names the exact test: two clones of one bare origin, add/add conflict settled by `-X theirs`, the loser takes no snapshot and waits |
| Note: Drive token | Answered | The owner says the app is published and the refresh token was re-issued after that. The builder will verify a live Drive write before step 2. I accept that, and the step 2 judge round will ask for the evidence |

**Verdict: PASS for 1664d638** (O9 v2 story text). Each build step in section 8 is its own lane-1 judge round.
Section M also needs market-brief's own approval: both AIs and the owner. The owner's two open questions (rewriting
history, a Slack line on good runs) stay with the owner.

## Addendum 5 (16 Oct 2026): merge check, O9 v2 text merged to main as 431f37d0

- **Merge is correct.** 431f37d0's parents are e10b38ab (main) and 1664d638 (the passed tip). Against its main parent
  it changes exactly the branch's four files: the story, response 238, the work-register row and one index row.
  `git diff 1664d638 431f37d0` on the story, response 238 and the register is empty.
- **The one conflict was resolved by hand.** In `reviews/claude/README.md` both index rows (238 and 239) were kept;
  the only difference from the recomputed merge is the removed conflict markers. No other file was touched.
- **CI.** The parent is green. The run on 16a0a62, which contains the merge, was in progress; this is a docs-only
  merge, and I confirm the run in my report.

**Verdict: merge check PASS.**

**CI confirmed (07:50 UTC):** checks run 38868747841 on 16a0a62 (this push contains 431f37d0) finished green.

## Addendum 6 (19 Oct 2026): Monday's A16 run on main, with O9 step 2a live

Every mark due by the time of the check (05:30 UTC) is on main and **good**: 09:15, 09:30, 09:45 and 10:00 as required, plus 10:15, 10:30, 10:45 and 11:00.

- **Contracts.** Each mark recorded all of its contracts: 220 of 220, and 224 of 224 at 11:00.
- **Ledger rows reached main, not a session branch.** Each one landed about 1.5 minutes after its claim. For example, the 10:00 claim is bbbce338 at 04:29:15Z and its row is 10688ace at 04:30:54Z.
- **The heartbeat on main** shows the 11:00 mark as good, with `clock_ok` and a skew of 0.0.
- **One taker per mark.**
  - Every mark has exactly one claim file in `receipts/intraday/claims/2026-10-19/`.
  - Each claim was made at mark minus 45 seconds (09:14:15, 09:29:15, and so on).
  - Four runs took the marks in turn: 09:15-10:00, then 10:15-10:30, then 10:45, then 11:00.
  - Git does not show runs that lost a claim, because a loser commits nothing, so this does not prove an overlap happened. It does show that no mark was taken twice and none was missed.
- **The retry worked.** At 09:45 one quote failed and was retried (`quotes_retried:1`). The mark still recorded 220 of 220 contracts and is good.
- **No Groww rate-limit (429) losses.** On 16 Oct, overlapping runs lost 74-87 quotes per mark. Today no mark lost any.

**Verdict: the A16f and O9 step 2a behaviour holds in production for this session.**
