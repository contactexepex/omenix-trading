# Judge 445: A22b, GIFT Nifty in its own early file for the 08:50 morning edition (story/a22b-gift-early @ 5308856b)

Judge F (independent). The change is A22 story amendment 1, its code and one sentence in CLAUDE.md. Claims:
`reviews/claude/response_308_a22b-gift-early.md`. Base main 37203a6a. Lane 1 (Drive, O9 receipts, a forecast
report's input). Labels: **strong**, **some**, **reasoning only**.

## Verdict: PASS. A22b may merge (pull, full suite on the merged tree, `check_numbers.py`, then push). 2 minors.

What it does: when the GIFT part ends, it saves the day row's GIFT cells (a value only when `ok` or `late`) as a
write-once file under `data/preopen/gift/` in Drive. It then pushes the receipts at once through O9's receipt
committer, at about 08:41, or about 08:45 when GIFT stays stale. The day row is unchanged.

This follows the owner's "Both" (e70525ee4):
- GIFT is context for the 08:50 edition;
- N0 goes in FL1's 09:12 post.

The value stays in Drive. The repository and the printed lines get only the receipt and the commit's one-line
outcome.

## Gates (exact head, growwapi absent as in CI)

| Gate | Result |
|---|---|
| pytest `-n auto` (no Slack token) | **9118 passed**, 16 xfailed, 365 s |
| `ruff check`, `ruff format --check` | clean, 1705 files formatted |
| `tools/check_imports.py`, `tools/check_records.py` | clean (1795 files); record scan clean (7413 files) |

## Checks

- **The push cannot crash the morning run.** `_save_early` runs inside the part's callback in `PreopenRun`, so an
  exception there would lose the pre-open capture. `ManifestRecorder.commit` is built never to raise and returns
  one line (`manifest_commit.py:34-35, 65-79`). Save errors are caught as `SAVE_ERRORS` and `RawFileConflict`
  [strong].
- **No clash with A17e part B.** Part B waits until 08:50 to read and commit, after this push at about 08:41-08:46
  [some: real push duration not yet measured].

## My plants (each reverted)

| # | Plant | Caught |
|---|---|---|
| 1 | a taken file not reported (the push still runs) | yes, 1 failed |
| 2 | a failed early push not reported | yes, 1 failed |
| 3 | no early file at all | yes, 4 failed |
| 4 | a stale GIFT not written (only `ok`/`late` kept) | yes, 1 failed |

## Minor

1. **A failed early file or push is alerted only at the run's end (about 09:11), after the 08:50 edition.** That is
   A22's one-alert rule, and fine. But the 08:50 edition must then say "GIFT: missing" itself when the receipt is
   absent, and no O8 witness judges the 08:50 deadline. State in the amendment that FL1's morning edition owns the
   missing-GIFT line (FL1's code), or add an O8 row for the GIFT receipt against 08:50.
2. **Gap list.** Add the amendment's rows to A22's gap list: the owner's e70525ee4, the 08:50 consumer, and O9's
   write-once rule for the new file.

After the merge (quality rule 8): the first live morning's GIFT receipt push time against 08:50.
