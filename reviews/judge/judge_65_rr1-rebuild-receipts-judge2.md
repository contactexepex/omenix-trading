# Judge 65: RR1 rebuild receipts (code, lane 1), judge #2

Frozen SHA `d636145` (branch `story/RR1-rebuild-receipts`). Reviewed `git diff origin/main d636145`:
- `storage/receipt_rebuild.py`;
- the `repair_cli.py` and `repair_wiring.py` edits;
- `.github/workflows/rebuild-receipts.yml`;
- `tests/ingestion/rebuild/`;
- the story;
- the two test edits.

For context I also read `google_drive.py` (`get`, `_listing`, `_child`).

**Gates (cleared `__pycache__`):** 1165 passed; ruff check and format clean; imports clean (488 files); code size
passed; contract plants all ok.

**My plants (6 of 6 killed):**

| Plant | Tests failed |
|---|---|
| a mismatching receipt not reported | 1 |
| a mismatching receipt replaced | 1 |
| dot-files receipted | 1 |
| no recursion into sub-folders | 8 |
| a failed commit exits 0 | 1 |
| an unreadable file not reported | 1 |

**Checked and correct:**
- It only adds: `receipts.write` keeps the first receipt and refuses a different digest.
- A mismatching receipt is reported and kept.
- Report-only is the default in the CLI and in the workflow.
- The workflow is dispatch-only and has `contents: write` only.
- Its concurrency group stops two rebuilds overlapping.
- Installs are hash-locked; the record scan is on.
- Nothing writes Drive; there is no Groww and no order code.
- The two test edits match the new workflow: 18 installs, and it reaches no paced host.

## Findings

1. **F1 (must fix): a partial or changed read becomes a permanent wrong receipt.** This answers your question (1):
   yes, it can write a wrong receipt.

   `_file` (`receipt_rebuild.py:71-81`) hashes whatever `drive.get` returned. It never compares that with the MD5
   Drive itself reported, although `_walk` already holds it (`self.drive.checksums(folder)` returns name to MD5, line
   62).

   Reproduced (strong evidence, my script). A store whose `get` returns the bytes less 3 at the end:
   - the rebuild writes the receipt of the short bytes, with no problem reported;
   - the verified cache then reports `DAMAGED` for the real file;
   - a second rebuild reports `differs_from_receipt` and, correctly, cannot replace it.

   So one bad read leaves that Record file red for good, with no legal way out, because the receipt is write-once.

   The same happens if the file is replaced in Drive between the listing and the download: Drive keeps one file ID
   and a new revision, and `get` follows the ID.

   Fix: pass the listing's MD5 into `_file`. When `hashlib.md5(data).hexdigest()` differs from it, or Drive gave no MD5,
   report a problem and write no receipt. Add a test and a plant.

   How likely: rare, since `requests`/`urllib3` usually raise on a short body when a Content-Length is present. But
   the check is one comparison against data already fetched, and the cost of a miss is permanent. That is in
   proportion.
2. **F2 (should fix): a doubled name crashes the walk.**
   - `_listing` raises `RawFileConflict` for two items with one name in a folder (`google_drive.py:131`). That is the
     DR1 race that `data-repair merge-folders` exists for.
   - `_walk` does not catch it, so the run ends in a traceback. Receipts already written earlier in that run stay
     uncommitted on the runner. That is harmless, but there is no report line.

   Reproduced with a listing that raises. Fix: catch it per folder, report a problem naming the folder that points
   to `data-repair merge-folders`, and go on with the other prefixes. Fail closed, as now, but readable.
3. **F3 (should fix, for the owner): better evidence may exist.**
   - The docstring (line 7) says this is for receipts "never moved into this repository". The story says only
     `data/vix` receipts exist *here*.
   - If the original receipts still exist in the old repository, importing them, with their digests checked against
     Drive, proves what the original run wrote, at its time.
   - The rebuild proves only the bytes as of today, and once written it blocks any later import of the originals:
     write-once refuses a different digest, and the same digest keeps the rebuild's writer and time.

   The story should say whether the old receipts exist and, if they do, why they are not imported first. This is
   a question for the owner, not a code defect (reasoning only). On your question (2): the rest of the caveat is
   stated honestly, including "a file already damaged is adopted and nothing can tell".

## Notes on the workflow (not blocking; your question 3)

- **Concurrency with other workflows:** the group covers only this workflow. Suppose a flows or circulars run saves a
  new file during a rebuild. The rebuild can then receipt it before that run commits its own receipt. Both write the
  same per-file path, so one push meets a merge conflict and ends red: fail closed. The story should say to run it
  with circulars paused (CP1 already) and outside the flows windows.
- **`$PREFIXES` is unquoted** (line 64), which is needed for word splitting. But a `*` in the input would be
  expanded against the checkout. Harmless for owner input.
- **`FNO_SLACK_BOT_TOKEN`** is in the job environment, and this command sends no alert. Drop it unless the committer
  alerts.

**Verdict: FAIL** (round 1, `d636145`). F1 is a one-comparison fix with a test.

## Addendum 1: round 2 on `678259c` (supersedes `1a34bd3`, which has the same code)

`git diff d636145 678259c -- fno .github docs/RUN_LOCATIONS.md`:
- `_walk` passes Drive's listed MD5 to `_file`;
- bytes that do not hash to it write no receipt and are reported;
- a listing error is caught per folder;
- the workflow has `set -f`, no Slack token, a run-window comment and the wider default `data/circulars`;
- the story records the owner question.

The `circulars.yml` pause in the range is CP1, already on main (judge 64); it is not part of this change.

**Gates (cleared `__pycache__`):** 1171 passed; ruff check and format clean; imports clean (489 files); code size passed;
contract plants all ok.

**My Addendum 0 reproductions, re-run:**
- **F1 fixed.** The short read now writes nothing and reports "not the ones Drive lists". The sync still says "no
  receipts", so nothing wrong is adopted. A re-run with a good read writes the receipt. The bad read is no longer
  permanent.
- **F2 fixed.** A listing error is a problem line naming the folder. My doubled-name store no longer raises.

**Plants (4 of 4 killed):**

| Plant | Tests failed |
|---|---|
| MD5 check off | 3 |
| an empty listed MD5 accepted | 1 |
| folder error silent | 1 |
| MD5 mismatch not a problem | 3 |

**F3:** recorded in the story as the owner's question, with the reasoning. The owner's answer, relayed by the
orchestrator, is "rebuild, no old-repo access". The apply is on hold until then, as the story says. Accepted.

**Workflow notes:** all three are folded in (`set -f`, token removed, run window stated).

**Verdict: PASS** (`678259c`).
