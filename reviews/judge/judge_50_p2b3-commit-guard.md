# Judge 50: P2b3 (the news-promote commit guard), judge #1 of two

**SHA:** `e41cd1e48e26cec38fda673a5c4a808ce52dbdf0` (`story/P2b3-commit-guard`, base 960ff08). Lane 1: a workflow
that writes to `main`.
**Verdict: FAIL, round 1 of 2.** The guard is the right design and is mostly well pinned. Two small gaps remain.

## Gates

- Suite: 767 passed, 2 runs out of 2.
- ruff and imports (441 files): clean.
- Size: 3 passed.

## My acceptance criteria (a)-(e)

| | Status | Evidence |
|---|---|---|
| (a) Same rule, in Python | met | `news check-manifest` calls `NewsManifest.well_formed()`, which is `check_appendable` plus "no row skipped by `_whole`". It prints only `whole` or `manifest_broken`. There is no shell re-implementation. |
| (b) Nothing broken reaches `main`; receipts stated | met | The else-branch skips committing both the manifest and the receipts. The next run starts from a clean checkout of `main`, so its missing-row repair re-adds receipts and rows from the bytes held in Drive. The story states that healing is range-bound. Plant "guard bypassed (`if true`)" is caught. |
| (c) A rejection still commits good rows | met | The guard is keyed on the file. Plant "guard keyed on promote's exit code" is caught. |
| (d) Red, *with an alert* | **not met** | See G2. |
| (e) A test drives a torn manifest through the guard | partly met | See G1. |

Other plants caught: "`check-manifest` always exits 0", and "`well_formed` ignores skipped rows".

## Required to PASS

### G1. The trailing-newline half of `well_formed` is untested (plant survives), and it is load-bearing

Plant: `well_formed()` returns `not self.skipped` only, so `check_appendable` is dropped. **767 passed.** The torn-line
tests all tear inside a field that `_whole` rejects, so the newline check never decides alone.

But it does decide alone for a line torn inside the size field. Reproduced: after a good row, append
`2026-10-27,<64 hex>,recorded,<64 hex>,12`, a torn `123` with no newline. Then:
- `skipped` is 0: the row passes `_whole`, because `12` is a number;
- the loader **accepts** it as recorded, with the wrong size;
- only `check_appendable` makes `well_formed()` False.

With the plant, that corrupt row would be committed to `main`.

Fix: a test with a whole-looking final row and no newline, asserting `check-manifest` exits 1. The plant must then fail.

### G2. A killed promote gives a red run but no #fno-desk alert

You asked me to rule on this. The torn line only arises when the promote process dies mid-write (OOM or SIGKILL). In
exactly that case the Python command cannot send its alert, and the guard's else-branch only `echo`s. The final
`exit 1` makes the run red, but the owner is told through #fno-desk (CLAUDE.md), not by watching the Actions tab.

Meanwhile the run's Drive files have no receipt on `main`, and the workflow is dispatch-only, so nothing reruns the
range unless someone is told. It is a silent drift between Drive and GitHub, which is exactly what (d) was meant to
prevent.

The repository already has the fix as a standard: **13 of the 16 workflows** end with an "Alert #fno-desk when the job
failed" step, `if: failure()`, posting through `build_alert_sender()` (for example `data-checks.yml:61-64`, whose
comment reads "O10's watcher sees an alert step on every failure"). `news-promote.yml` and `news-fetch.yml` lack it.

Fix:
- Add that standard step to `news-promote.yml`, with fixed text such as "news promote failed (run red); if the commit
  was skipped, re-run --from over the same range".
- Make the guard's else-branch exit non-zero after its echo, so `failure()` fires even if promote itself had exited
  cleanly.
- Add a test that pins the alert step.
- `news-fetch.yml` has the same gap. It is out of this story's scope, so I recommend it as a follow-up.

## Hard lines

No orders and no secrets: the alert text is fixed. Write-once is untouched, and nothing is truncated or rewritten.
