# Judge 647: REH1p, earlier days' Groww raw quote files visible to a rehearsal, story and code (story/reh1p-quote-visibility @ 678be37b4)

**PASS (1 minor), judge F (judge B the other; not read). Lane 1.** Own session (session_01A8XfbTUVgeeEpqatHaWbtP).
Labels: strong, some, reasoning only.

## Criteria

| Check | Result | My evidence |
|---|---|---|
| The rule | MET | `QuoteSidecars.seen_at` (`rehearsal/quote_sidecars.py`): only Groww quote CSVs (`GROWW` prefix, `QUOTE_FILE`); the sidecar's adding commit from `git log --first-parent --no-renames --diff-filter=A` on the record's `main`; the sidecar read with `git show <commit>:<path>`; visible at `max(finished_at, commit time)`; `Visibility` then compares with the replay clock |
| No look-ahead (a same-day file before its time stays invisible) | MET | both times must be reached: plants dropping either one caught (5 and 1 tests); plant ignoring the clock caught (7); the later of the two can only delay |
| `raw_file_saved` false stays invisible | MET | `seen_at` returns None; plant caught |
| No live record touched | MET | reads only (git log and show on the record checkout); used only inside `rehearsed_drive`, which is under the mode; real runs build no `QuoteSidecars` |
| Only `main` and first-parent | MET | plants "record HEAD instead of main", "not first-parent" and "sidecar from the working tree" caught; "any dataset counts" caught |
| gates | MET | trial merge with main 4295944c8 (clean): **16,602 passed, 1 skipped, 13 xfailed** (token kept); ruff, format (2,636 files), `check_imports`, `check_records` (9,301 files) clean |

## Minor

1. Two choices are untested, though stated in the docstring. `--no-renames` (a renamed sidecar counts from its rename)
   and keeping the oldest of several adds both survive my plants. Neither can cause look-ahead: without
   `--no-renames` a renamed sidecar never counts, and the newest add is later, so the plants only make files visible
   later or never. Neither case exists today: `main` has 0 renamed and 0 deleted sidecars under `research/data/quotes`
   (my `git log --diff-filter=R/D`). Add a test for each when convenient.

## Plants

10 planted on 678be37b4: **8 caught, 2 survived** (minor 1, both in the no-look-ahead direction). Caught: finish only;
commit only; `raw_file_saved` false visible; not first-parent; any dataset; record HEAD; the clock ignored; the sidecar
from the working tree.
