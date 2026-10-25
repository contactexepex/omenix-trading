# Judge 536: O9's DriveCache.sync on a single file (story/o9-sync-file @ 494d97df)

Judge F. Round 1 of 2. Lane 1 (O9's verified store, read by forecast and score records). Labels: **strong**, **some**,
**reasoning only**.

## Verdict: PASS. It may merge before FL1's branch, on the orchestrator's go. 1 minor.

Gates on 494d97df: **14579 passed, 0 failed**, 1 skipped, 16 xfailed; ruff, ruff format (2333), `check_imports.py`
and the record scan (8812) are clean.

What changes:
- `ReceiptFolder.under(prefix)` returns the one receipt when `prefix` names a receipted file.
- `sync` reports "no receipts under it" when nothing matches, instead of an empty success. That empty success was
  the root cause of FL1's broken evening check on 23 Oct.
- A receipt-backed series with nothing written yet still reads as empty.

**The new problem line could break any caller whose prefix has no receipt yet.** So I listed every `sync` caller in
`fno/` (13) and counted the receipts under each computed prefix on this tree [strong]:
- price_distribution 21; premium_ranges own 2; itm_chance own 1; price_ranges 17 (live 4, scores 3, backfill 4,
  closes 2); circulars 5; flows 2 and 2.
- Every prefix a caller treats as must-succeed has receipts today.
- The dashcam reader and the v4 pack filter problems by their own file path, or check the receipt first, so they are
  unaffected.

## Plants (each reverted)

| # | Plant | Caught |
|---|---|---|
| 1 | the empty success back (no "no receipts" problem) | yes, 1 failed |
| 2 | `under` ignores a single receipted file | yes, 1 failed |
| 3 | an empty receipt-backed series treated as unreadable | yes, 6 failed |

## Minor (for the next dataset, not now)

`circulars/wiring.py` and `flow_history/wiring.py` call `cache.sync` directly and raise on any problem. A **new**
dataset read the same way, before its first receipt, will now stop instead of reading as empty. Each new
dataset's first run should either write first, or read through `ReceiptedRowLog` (which checks receipts first). Say
so in O9b's per-step gap list [reasoning only].
