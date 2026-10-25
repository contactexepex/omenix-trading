# Judge 531: MS-SIM-e2, `school practice run --archive`

**Scope:** story/ms-sim-e2 at f9e61b93 (code 99101322; later commits are Claims text only; builder
session_01W2JE3W9xYftEDWTysHkdVC). The diff from main covers:
- `fno/school/simulator/archive/{archive,files,inputs,outcome,run,session,wiring}.py`, `command.py` and
  `practice/{render,dashcam,fleet}.py`;
- the publisher's move to `fno/storage/receipt_publisher.py`;
- the tests.

Story 7.8 and the SIM-e2 Claims. Lane 1 (Drive and git, records). Round 1 of 2. Judge H
(session_01KNkZVoWvXMkoihKrrXk5Xa).

**Verdict: FAIL**, with 1 should-fix and 4 minors. The archive logic is right. Its composition root is untested.

## Checked
| Item | Result | Evidence |
|---|---|---|
| `archived` only when every file, report.txt last, has a pushed receipt and a verified read-back | MET | `run.py` stops at the first error. `archived` is `len(files) == total > 0`. `publish` raises `SealNotPushed` unless the receipt is on `origin/main`. Plants caught: verify removed, report dropped, report first, `archived` true on any file |
| Exit 1 and "local only, not archived" with the reason | MET | Plant (exit 0) caught |
| The default run archives nothing | MET | Plant (archive always) caught |
| Minors (a)-(d) of judge 526 | MET | Plants caught: `..`/empty/`.` check off, record decode off, the UTF-8 error unwrapped. The collision test covers the instructor folder and the opportunity and marks paths |
| Only dashcam record files and the report | MET | Plant (glob over the whole scenario home) caught |
| Uncommitted code refused before the run | MET for tracked files | See minor (b) |
| Publisher move is pure | MET | 96% similar; only the import paths changed. The pilot's dashcam and instructor tests pass unchanged |
| Exact-path receipt commit | **NOT TESTED** | See finding 1. The code itself is right: `receipts/data/school-practice/<run>/` matches `ReceiptFolder.file_for("data/school-practice/...")` (`DATA_AREA = "data"`) |
| Gates | MET | pytest -n 6: 14,387 passed, 16 xfailed (matches the Claims). ruff check/format and check_imports are clean |

## Findings
1. **Should-fix: `build_practice_archive` is never built by a test, so the exact-path commit rests on reading only.**
   - Every session test swaps in `World.archive` with a `FakePublisher`.
   - Two plants in `archive/wiring.py` survived:
     - the recorder widened to `REPOSITORY / "receipts"`: a practice commit would then carry any pending receipt of
       any writer, which is exactly what 7.8 and the Claims say cannot happen;
     - the read-back reader replaced by the data store.
   - Expected: one test that builds it with a fake env, Drive and git, and asserts:
     - the recorder's folder is exactly `receipts/data/school-practice/<run id>`;
     - `git add` and `git commit` get only that pathspec;
     - the reader is the verified Drive reader over `DATA_AREA`.

**Minor:**
- (a) **A zero-byte record file is accepted.** `gzip.decompress(b"")` is `b""`, so `check_labelled` takes a
  `.jsonl.gz` that isn't gzip at all (my run). The fleet writes an empty *gzip* member. Accept only that (decompress
  must see the gzip header), not zero bytes.
- (b) **The untracked-file check is untested.** My plant dropping `--untracked-files=all` from `code_commit` survived.
  A new untracked module under `fno/` would then not block a run id that claims a clean commit. Add an untracked file
  to the real-git test.
- (c) **The Claims say "a refused push is retried once by the recorder".** `PUSH_ATTEMPTS = 3` gives three tries.
  That is A16's shared code, not this story's, so correct the Claims line or ask the orchestrator whether its "retry
  once" ruling needs a practice-only count.
- (d) **The archived `report.txt` omits the "recorded captures were left out of the spread model" lines.** The command
  prints them after `render()`. They describe the spread model the run id hashes, so the archived text should carry
  them too.

## Plants
15 planted:
- 10 caught;
- 3 survived (finding 1 twice, minor b);
- 2 equivalent (`> 0` dropped, since a run always has the report; an `if data` guard on an already-empty
  decompress), not counted.

Two plant strings first failed to apply. I re-planted them with the exact text, and both were caught.

## Addendum 1

**Round 2 of 2:** story/ms-sim-e2 at 00d2180f (main merged in). Against main, the branch holds only e2's files.
**Verdict: PASS.** Lane 1.

**Gates (my run):** pytest -n 6 gave 14,542 passed, 1 skipped, 16 xfailed and 1 failed. ruff check/format and
check_imports are clean.
- **The failure** is `tests/timetable/test_first_timely_decision.py::test_the_decisions_step_lists_the_other_runs_in_the_run_log`.
- It isn't this branch's code: `fno/timetable` and `tests/timetable` aren't in the diff.
- It passed alone and in three parallel reruns of `tests/timetable` (112 passed each time). That makes it a load flake
  in another story's git-commit-time test, so it doesn't hold this verdict. The orchestrator should watch it.
- **The skip** is growwapi not installed (environment only).

**Should-fix 1: ACCEPTED.** `build_practice_archive` now takes `repository` and `git`. `test_wiring.py` (5 tests) builds
it for real over a fake env, store, cache and git. My plants caught:
- the recorder widened to `receipts/`;
- the reader swapped for the store;
- the reader's area changed.

A plant dropping the publisher's own `run=git` survived. In production `git` defaults to `subprocess.run`, so that plant
is equivalent there. It's not a finding.

**Minors:**
- (a) **ACCEPTED.** Zero bytes are refused and an empty gzip member is still accepted. Plant caught.
- (b) **ACCEPTED.** The real-git test adds `fno/newpkg/b.py`. Plant (`--untracked-files=all` dropped) caught.
- (c) **ACCEPTED.** The Claims say PUSH_ATTEMPTS = 3, per the orchestrator's ruling.
- (d) **ACCEPTED.** One `left_out_lines` serves both the printed and the archived report. Plant caught.

**Plants:** 8 this round, 7 caught, 1 equivalent. Round 1's verify plant was re-run here and is still caught.
