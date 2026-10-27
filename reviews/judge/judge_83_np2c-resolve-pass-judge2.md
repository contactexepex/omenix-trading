# Judge 83: NP2c resolve pass (code and workflow, lane 1), judge #2

Frozen SHA `feb5fa9` (branch `story/NP2c-resolve-pass`, from main `67470c7`). Reviewed `git diff origin/main feb5fa9`:
- `news/resolve/{run,resolution_file,report,cli,wiring}.py`;
- `news/write_once.py`, extracted from `ClusterWriter`;
- `.github/workflows/news-resolve.yml`;
- the two test-count edits, rows V1-V12 and their plants.

The judge_80 and judge_81 files that `git diff` shows as "deleted" come only from an older base.

**Gates** (in the venv from `requirements.lock`, `--require-hashes`): 1556 passed; ruff check and format clean; imports
clean (545 files); code size passed; contract plants all ok.

**My plants (7 of 9 killed):**

| Plant | Tests failed |
|---|---|
| cap ignored in the pass | 2 |
| cap ignored in the CLI | 1 |
| the probe writes | 3 |
| manifest row written before the Drive file | 1 |
| an overwrite allowed | 2 |
| `MAX_READS` off | 2 |
| one resolver call per link | 4 |
| `check_ready` removed | **survived** (should-fix 1) |
| workflow commit step also on a probe | **survived**, nearly equivalent (note) |

## The questions asked

- **(a) More than 80, or more than one resolver?**
  - The pass calls `resolver.resolve` exactly once with at most `min(cap, CAP)` links. The CLI clamps `--limit` to
    0..80.
  - `build_resolve_pass` builds one resolver per run, so its spacer and stop are never reset.
  - Note on wording: `CAP` counts **links**, not HTTP requests. The adapter makes one page request per link (up to 3
    hops each, on one host) plus one POST per ten. So 80 links is about 88 requests plus hops, each at least 1.5 s
    apart, and the whole run stops on the first refusal. The story should say "80 links", not "80 requests", wherever
    it does.
- **(b) Does the probe write?** No. `_record_answer` returns before the writer unless `apply`, `check_ready` runs only
  with `apply`, and the commit step only runs with `apply` (`news-resolve.yml:71`). The probe does make real, paced
  requests, as the story says.
- **(c) Private content and overwrites:**
  - The resolution file (URL, host, claimed domain, a flag, the resolver name) lives only in the private Record.
  - The committed `resolved.csv` holds day, key, status, SHA-256 and size, the same shape as `articles.csv`.
  - An existing file with other bytes is a `RawFileConflict`, never an overwrite (plant killed).
  - Note: the resolution bytes have no time in them, so their public SHA-256 confirms a guessed (key, URL) pair. That
    is the same exposure `articles.csv` already has for article bytes, not a new class.
- **(d) Order and the torn-manifest guard:** `WriteOnceWriter.write` puts the Drive file, then the receipt, then
  `manifest.add` (plant killed). The guard needs a test (should-fix 1 below).
- **(e) The workflow:**
  - dispatch-only, no schedule, `concurrency: news-record` (serial with promote and cluster);
  - `APPLY: ${{ inputs.apply && '--apply' || '' }}` is right for a boolean input;
  - the commit goes through `ops/commit_news_record.sh` (manifest check, `repair-batches`, pull or exit, push or exit);
  - the fail step comes after the commit; an alert step runs on `failure()`;
  - the installs are hash-locked; `contents: write` only.
- **(f) `NOT_PACED` for `news-resolve.yml`: correct.** The job never uses the shared NSE pacer or its committed pause
  log. Its only outside host goes through the resolver's own `RequestSpacer` and `PushbackStop` (NP2b), and Drive is
  not paced.
- **(g) 20 to 21 installs: correct.** The new workflow adds one locked install.

## Should fix (not blocking)

1. **The torn-manifest guard is not isolated by a test.**
   - `test_a_torn_resolved_manifest_stops_the_pass_before_anything_is_written` uses a torn *partial* row. The reader
     also counts that row as skipped (`MANIFEST_ROW_SKIPPED`), so the test passes with `check_ready` removed.
   - The case only `check_ready` catches is a whole last row missing its final line break. Without the guard, the pass
     would call the resolver live and write one Drive file before `manifest.add` refuses (`RESOLUTION_WRITE_FAILED`).
   - It fails closed (the next run adds the missing row), but the story's guarantee "before anything is written" is
     untested for that case. Add that file shape to the test.
2. **The commit step on a probe:** running it on a probe would only pull and push with nothing staged, so the plant is
   nearly equivalent. A test asserting `inputs.apply` in the step's `if` would pin it cheaply.

**Verdict: PASS** (`feb5fa9`), with the two should-fixes above.
