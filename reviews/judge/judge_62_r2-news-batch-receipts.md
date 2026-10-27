# Judge 62: R2 news batch receipts (code), round 1 at e9b98b2: FAIL

**Lane 1, two judges; this is judge #1.** Branch `story/R2-news-batch-receipts`, frozen SHA e9b98b2, base main c37a381. Reviewed `git diff c37a381 e9b98b2`. The content is 89a9ab7 and 3d1f8a0; the merge only brings in main's scheduled data commits (5 receipt and manifest lines, lane 3). Story: `docs/stories/R2-news-batch-receipts.md`.

## What holds (strong evidence unless marked)
- Gates: ruff, format, check_imports and code size are clean; 1127 passed; `tools/contract_plants.py` reports `ok` for every row, N6 to N8 included. Files are 94 and 83 lines.
- Design: the `ReceiptWriter` Protocol, `BatchReceiptWriter` as the second strategy, one line in each news wiring root, and `Receipt` moved out to break the import cycle. Every other source still writes per-file receipts.
- Write-once: the same digest keeps the first receipt; a different digest is refused against a batch or a per-file receipt.
- Your question (a), a crash between the Drive write and the receipt line: the next run saves the same held bytes again (writer.py:5), so the receipt is written then. This is the same as before. (Reasoning plus code read.)
- Your question (a), staleness of the index in one process: each news run builds one `ReceiptFolder` through `batch_receipt_writer()`, and the writer adds to that same index (plant "writer index not updated" → 2 failed).
- Your question (c), git: `ops/commit_news_record.sh` loops `for folder in $RECEIPTS` unquoted, so the two paths are each `git add`ed. Run ids are unique, so batch files never collide.
- My plants:

| Plant | Result |
|---|---|
| writer index not updated | 2 failed |
| sync hides batch problems | 1 failed |
| torn line read as a receipt | 2 failed |
| bad path accepted | 1 failed |
| batch line wins over a per-file receipt in `under` | **0 failed** (see M1) |

## B1 (required, blocker; strong evidence, reproduced end to end): one damaged news batch line breaks unrelated live readers

**What changed.** `ReceiptFolder.under()` now loads *every* batch file for *any* prefix, and `DriveCache.sync` now adds *all* batch problems to every report (`drive_cache.py:46`).

**Reproduction.** A per-file-receipted flows table `data/flows/fii`, plus one news run's batch file in the same `receipts/` tree:
- A torn last line in the news batch makes `DriveCache.sync("data/flows/fii")` incomplete: `complete = False`, with the batch problem listed.
- A malformed line in the news batch (a size that is not a number, or an invalid path) makes the same sync **crash**: `ValueError: invalid literal for int()` or `not a valid archive path`.
  - `BatchIndex._load` only checks the field count. `int(size)` and the path check in `under` run unguarded.
  - That breaks N8's own claim: "a torn, malformed or conflicting line is never read as a receipt", which should mean *reported*, not a crash.

**Callers that turn this into red live runs.**

| Caller | Location | On a problem |
|---|---|---|
| `entered_sessions` (flow_history) | `flow_history/wiring.py:60` | raises |
| `listed_circulars` | `circulars/wiring.py:37` | raises |
| `receipted_rows` (every receipted table) | `receipted_rows.py:43` | raises |
| preopen `check_files` | `preopen/check_files.py:35` | raises |
| `cache_cli` | `cache_cli.py:21` | exit 1 |

**Why it would last.** The code never edits or removes a batch line (write-once, by design). A torn or malformed news line would therefore keep these readers red forever, unless someone hand-edits a receipt file in git, which this design forbids.

**The coupling breaks the standard.** News damage must not make FII flows, circulars or preopen unreadable ("loose coupling"; "confirm the live workflows are not broken").

**Fix, the design is yours.** Required properties:
1. A bad batch line is never a crash; any parse failure becomes a MALFORMED problem.
2. A batch problem is reported only to a sync whose prefix the line's path falls under (or under the news area when the path cannot be read), never to unrelated prefixes.
3. A stated way out for a torn tail, so one crash does not leave news syncs red forever. For example: the torn line is reported once as a warning, and once the same path has a valid receipt (the next run's re-save) it no longer makes the sync incomplete. Say which, and pin it with a test.

## B2 (required, small; the code is strong evidence, the likelihood is reasoning only): a short write glues the next receipt line

- `os.write(descriptor, line)` ignores its return value. A short write (for example a disk filling up) leaves part of a line, and the *same run's* next receipt is appended right onto it.
- The result is one line with too many fields, MALFORMED. The next file's receipt is lost, while the in-memory index says it is receipted, so the manifest row is still written.
- That gives a Record file with **no findable receipt**: exactly your question (a). It is also the glued-line class the project already fixed for manifests (N4).
- Fix: raise when the bytes written are fewer than the line's length. Before appending, refuse a batch file that does not end in a line break (as `check_appendable` does). Pin both with a test.

## Minor (not blocking)
- **M1 (some evidence).** The precedence in `under()` (a per-file receipt wins over a batch line) is untested: my plant flipping it passes all tests. A per-file receipt and a batch line with different digests for the same path are also never reported (my probe: `problems: []`). The writer cannot create that state; a hand edit can. Add one test, or state it.
- **M2.** The story's design item 2 and item 6 say `BatchReceiptWriter(folder, run_id)`; the code is `BatchReceiptWriter(receipts)`, taking the run id from each receipt. The "Tests and plants" section says row W4 names both strategies; W4 is unchanged. Correct the doc.
- **M3 (already on main before R2).** The reader never checks the shape of a digest (a line with sha256 `zz` is accepted). With CRLF line endings, a `\r` stays in `run_id`.

## Hard lines
No order path, no secret, no Groww call, no change to a recorded Drive file. The workflow changes are the `RECEIPTS` value only.

## Verdict: FAIL round 1 at e9b98b2. B1 and B2 required; M1 and M2 requested.
