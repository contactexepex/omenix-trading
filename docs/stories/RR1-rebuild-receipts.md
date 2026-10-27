# RR1: receipts rebuilt from Drive

**Lane 1, one judge (it writes the proofs of Record files).** Owner decision, 27 Oct 2026 (relayed by the orchestrator): "rebuild from Drive
files". Companion decision: the circulars cron is paused (CP1) until this has run.

## Why
Only `data/vix` receipts exist in this repository. The flow-history table steps (`data/flows/history/*`) and the circulars job (`data/circulars/list`)
stop at once on every run with "no receipts under it", failing closed before they write. Loosening that check is wrong: the table parts are write-once,
so a tolerant first build would write a second copy of history next to the real one. The right fix is to ADD the missing receipts.

## What it does
`python -m fno data-repair rebuild-receipts <prefix>... [--apply]` (`storage/receipt_rebuild.py`): walks each Drive prefix, hashes every file's CURRENT bytes
and writes the per-file receipt (strategy A) for each file that has none; commits `receipts/` like the other repair commands. It reads Drive and changes
nothing in it. Report only unless `--apply`.
- A file whose receipt exists and matches: counted `already_receipted`. One whose receipt exists but does NOT match the Drive bytes: a PROBLEM (exit 1),
  never replaced, never "fixed".
- A file that cannot be read: a problem, no receipt. Dot-files (partial writes) are skipped.
- Counts are printed; a problem names a path (a Drive path, no content).
- `.github/workflows/rebuild-receipts.yml`: dispatch only, `apply` off by default, inputs the prefixes (default `data/circulars/list data/flows/history`).

## What a rebuilt receipt proves (the owner's accepted caveat)
The file's bytes AS OF THE REBUILD: from now on a changed file is detected by the verified cache. It does NOT prove the file is what the original run
wrote, and its time is the rebuild's (the receipt's writer is `rebuild-receipts`, so a rebuilt receipt is recognisable). If a file was already damaged
before the rebuild, the rebuild adopts the damaged bytes as its baseline and nothing can tell. The module docstring says so.

## Tests (`tests/ingestion/rebuild/`, offline) and plants
Without receipts a sync of `data/circulars/list` and of both flow tables fails with "no receipts"; after the rebuild all three pass (the owner's
acceptance test). Every rebuilt receipt equals the digest, size, writer and injected time. Report-only writes nothing. A matching receipt is left alone, a
mismatching one is reported and kept. Twice is a no-op. Unreadable and dot-files. The command commits only with `--apply` and a failed commit is red.
Plants that each fail a test: a digest not of the file's bytes, a wrong size, report-only that writes, a mismatching receipt called fine, dot-files
receipted, the rebuild not visible in the receipt, an unreadable file not reported.

## Not done / for the owner
- It has not been run against the real Drive (that needs the workflow, or the owner's session). The first run should be `apply` off.
- `data/circulars/` files other than the list (the saved circulars themselves) also lack receipts; `capture.py` asks `receipts.read` before saving, so they
  would be re-saved (same bytes, a no-op in Drive) and receipted at the next run. Add `data/circulars` to the prefixes to avoid that.
- After the rebuild: sync both prefixes, dispatch circulars once by hand, then restore its cron (see the comment in `circulars.yml`).
