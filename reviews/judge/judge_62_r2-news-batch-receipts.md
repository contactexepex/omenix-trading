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

## Addendum 1: round 2 at 498151a: PASS, with one doc sentence to correct before merge

Reviewed `git diff e9b98b2 498151a`. That covers the round-1 fold f6d44cc (the orchestrator's sharding, the run-id check and `unreceipted`) and 6cba9da with 498151a (my findings and judge 61's).

**Gates (strong evidence).**
- ruff, format and check_imports are clean; 1151 passed; `tools/contract_plants.py` reports `ok` on every row.
- `batch_receipts.py` is 195 lines.
- `tests/ingestion/test_batch_receipts.py` is 363 lines. The size rule and `tests/test_code_size.py` cover `fno/` only, so this is not a violation. A split would still be welcome.

**B1 fixed (strong evidence, my round-1 reproduction re-run).**
- With a news batch damaged in four ways (torn, a size of NaN, `raw/../x`, a byte that is not UTF-8), `sync("data/flows/fii")` is complete and nothing crashes.
- A news sync reports a torn or malformed line that names its file as a problem. A line that names no file is a warning.
- The way out works: the next run's re-save of the same path settles it, and the news sync is complete again.

**B2 fixed (strong evidence).**
- I made `os.write` write 10 bytes and then raise ENOSPC. The run raised; the next append was refused with `BatchBroken` (not at a line end); the file kept its half line and nothing was glued onto it.
- 3-byte partial writes finish the whole line.
- In the news gate, `BatchBroken` is counted as `RECORD_FAILED`, and promote exits 1. The files left without a receipt are listed by `unreceipted`.

**M1 fixed.** My round-1 plant (a batch line wins in `under`) now fails a test, and a conflict between a per-file receipt and a batch line is reported.

**M2 fixed.** The constructor in the doc now matches the code.

**My plants this round** (11, every one fails a test):
- the line-end check before append removed;
- path-less problems shown to every prefix;
- path problems shown to every prefix;
- a torn line never settled;
- an unproved line dropped at once;
- the digest shape not checked;
- the size not checked;
- a byte that is not UTF-8 crashing the reader;
- the per-file conflict not reported;
- every batch problem demoted to a warning;
- a short write treated as whole.

### Required before merge: correct one doc sentence (text only, orchestrator may check)
- The story's "Fail closed" section says: "A torn last batch line names its file ... and the file is listed as unreceipted too."
- This holds only when the cut falls after the path's tab. My short-write probe left `raw/news/a`: no tab, so no file is named, only a warning, and **the default `data-cache sync raw/news` reports complete** while `z.json` and `w.json` have no receipt.
- Only `--unreceipted` finds them, and it did list both.
- The sentence must say the cut-in-the-path case gives only a warning and needs `--unreceipted`.

### Follow-ups (recommended; lane 1, the orchestrator's call)
- **F-a (some evidence).** Nothing runs `--unreceipted`. `data-checks.yml` runs plain `data-cache sync` over `$MOVED`, and no news workflow calls it.
  - Until a scheduled step runs `data-cache sync raw/news --unreceipted`, N9 is a tool, not a guarantee that runs.
  - This is the same gap the per-file layout always had (a lost receipt is invisible to a verifier that walks receipts), so it is not a regression; R2 is what makes closing it possible.
- **F-b (reasoning only).** One byte in a batch file that is not UTF-8 turns the whole file into a single warning, and every receipt in it drops out of verification. Decoding line by line would keep the damage to one line. F-a would catch it in any case.

**Hard lines.** No order path, no secret, no Groww call, and no change to a recorded Drive file. The workflow changes are the `RECEIPTS` value only.

**Verdict: PASS round 2 at 498151a, on condition of the one-sentence doc correction above. F-a and F-b are recommended follow-ups.**

## Addendum 2: round 2 superseded by e919a29: PASS, same condition, reworded

Reviewed `git diff 498151a e919a29`. The only change is the commit guard from judge 61's F1 part (ii): `cut_torn_tails`, `news repair-batches`, one line in `ops/commit_news_record.sh` (`|| broken=1`), contract row K4 and real-git tests. Everything in Addendum 1 still holds at e919a29.

**Gates (strong evidence).** ruff, format and check_imports are clean; 1155 passed; contract plants all `ok`.

**Plants** (each one undone):

| Plant | Result |
|---|---|
| the repair also cuts the last whole line | 2 failed |
| a file cut but the command exits 0 with no alert | 2 failed |
| the repair's red ignored in the script (`|| true`) | 1 failed |
| the repair removed from the script | 1 failed |
| the repair does nothing | 3 failed |

My first try at the "cuts a whole line" plant changed nothing in practice: it used `data[:-1].rfind`, which finds the same line break. I replanted it properly before counting it.

**Design (reasoning only).** Cutting the fragment edits a receipt file. It is acceptable: the fragment was never a receipt and was never read as one, every whole line stays byte for byte, git history keeps nothing of it (it was never committed), and the run is red with a fixed-text alert that names no path.
- One side effect: `cut_torn_tails` walks *every* batch file in the checkout, not only this run's. A committed file that ends in a fragment cannot arise through the code once this guard exists; it could only come from a hand edit. Such a file would also be cut and committed. That is acceptable, but limiting the walk to files git does not yet track would match "never edits a committed receipt" exactly. Optional.

**The condition, reworded (required before merge, text only).**
- With the repair, a torn line never reaches `main`. So on `main`, a file whose receipt line was cut has **no signal at all in a default sync**: the UNPROVED problem went with the fragment.
- What remains: that run's red status, the `batch_torn` alert, and `data-cache sync <prefix> --unreceipted`.
- The "Fail closed" sentence "A torn last batch line names its file ... and the file is listed as unreceipted too" must be replaced with that. The UNPROVED message now matters only inside the run that wrote the fragment, before the guard runs.

**F-a is now strongly recommended (some evidence).** After this guard, the only durable record that a Record file has lost its receipt is `--unreceipted`, and no workflow runs it. Schedule `data-cache sync raw/news --unreceipted`, for example in data-checks.

**Verdict: PASS at e919a29, on condition of the reworded doc sentence. F-a strongly recommended; F-b and the walk limited to untracked files optional.**
