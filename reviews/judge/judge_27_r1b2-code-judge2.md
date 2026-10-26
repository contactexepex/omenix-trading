# Judge 27: R1b2 the pause remembered between runs, code (judge #2)

Branch `story/R1b2-code`, SHA `c3b50d8`, 29 files. **FAIL** (round 1), lane 1, on 1 should-fix (tests only). The design
is built as judged and the receipts-safety fix is proven by real git tests. One wiring line has no test: removing it
silently turns the whole of R1b2 off.

Gates: 484 passed; the new files' tests (50) pass; `ruff check`, `check_imports`, `test_code_size` clean; changed
files formatted. The record scan passes on a sample pause-log row (`paced:www.nseindia.com,opened,900.0`).

## Criteria

| Item | Verdict | Evidence |
|---|---|---|
| No tracked file dirty mid-run (my B1) | MET | `LayeredLog` writes only `.run/paced-hosts.csv` (git-ignored). `test_commit_pause_log.py:98-109`: two clones; another workflow pushes the log; a manifest committer's `pull --no-rebase` still succeeds. `:111-124` reproduces the old design's refused pull. Plant Q1 (writing the committed file) fails 2 tests |
| The commit step | MET | the last step in 13 workflows, `always() && !inputs.dry_run`, `continue-on-error`. `ops/commit_pause_log.sh` sets `core.hooksPath` and the identity, pulls before appending, removes duplicate rows by exact line, keeps the header once, keeps the rows on a failed pull. Plants: not last, no `always()`, no `continue-on-error`, no hooks path, a second header, no duplicate removal: each fails 1-2 tests |
| UTC restore | MET | production `_wall = now_utc` (the derived clock only when a test injects `clock`); restored message from the remaining cool-down. Plant Q2 (monotonic) fails 3 tests |
| `force_probe` (R1a edit), once per host per process | MET | plants: forced on non-live commands (4 fail); forced repeatedly (1 fails). The race on `state.forced` is harmless: the breaker's lock admits one probe |
| `LIVE_WINDOW_COMMANDS` (8, pinned) | MET | plant: `fo-masters` removed (3 fail); live detection disabled (1 fails) |
| Restore reads the committed log | MET | plant: committed rows ignored (5 fail) |
| Alerts per transition | MET | plant: no sender (1 fails) |
| Loosened timing assertion (0.04 to 0.03 s with 0.05 s spacing) | acceptable | it still fails an unlocked pacer (0.0 s gaps) and spacing cut to half (0.025 s); it gives up only the band 0.03-0.04 s, which no plausible regression lands in |

## Finding

1. **S1 (should fix; tests only): `cli.main`'s call to `attach_pause_memory` is untested.** Plant Q14 replaces
   `attach_pause_memory(sys.argv[1:] if argv is None else argv)` with nothing, and all 484 tests pass. Then no run
   remembers a pause, no alert is sent, and the live-window rule never applies. Every workflow still goes green, so
   the post-merge comparison would see nothing unusual either. `test_pause_memory_wiring.py` tests `attach_pause_memory`
   directly, not that `main` calls it. Fix: a test that runs `cli.main([...])` with a stub command (or a live and a
   non-live real command with their work patched out) and asserts `SHARED_PACER.log` is a `LayeredLog` on the repo's
   two paths and `live_window` matches the command.

## Plants

19 planted in the real files, 18 caught. Survivor: Q14 (S1).

## Note

Sessions outside the workflows (routines, the owner's PC) append to their own ignored `.run/` file and never commit it.
A later command in the same checkout restores from it, so a pause seen there persists locally until the file is
deleted. That is harmless and never weaker; it is worth one line in the story.
