# Judge 108: NP8 material-first reads (code), round 1 at e6aac2a: FAIL (tests only)

**Lane 1, two judges; this is judge #1.** Branch `story/NP8-material-first-reads`, frozen SHA e6aac2a. I reviewed `git diff origin/main...e6aac2a`, which touches:
- `news/pin.py`;
- in `reads/`: `order.py`, `queue.py`, `plan.py`, `pass_note.py`, `links.py`, and the changes to `run.py`, `report.py` and `wiring.py`;
- `materiality/` and the cluster grouping (re-pointed to `pin.py`);
- the workflow, and contract rows M1 to M17.

## Gates (strong evidence)
In a venv installed from `requirements.lock`:
- 2001 passed;
- ruff check and format are clean, and check_imports is clean;
- the largest file is `run.py` at 193 lines; the test file has 334 lines, under 350.

## B1 (required, tests only; strong evidence, plants survived the FULL suite): the pass-note manifest guard is not pinned
The new manifest `read-passes.csv` is guarded in `ReadPass._ready` exactly like `reads.csv`, but the two guard lines are untested. Each plant below passes all 2001 tests:
- removing `skipped += self.notes.skipped_rows`, so a skipped row of the note manifest no longer stops the pass;
- removing `self.notes.check_ready()`, so a pass with `apply` writes a note into a manifest whose last line is torn.

These are the write-once manifest guards every other Record writer has pinned. Fix: two tests (a skipped row, and a broken note manifest, each giving `manifest_row_skipped` / `manifest_broken` with nothing read or written), plus these two plants as contract rows.

## My other plants (each one undone; all fail tests, strong evidence)

| Plant | Result |
|---|---|
| a file used before and now gone treated as green | 1 failed |
| a never-configured file treated as red | 1 failed |
| the pin not applied in the read pass | 2 failed |
| the score cap off by one (`>`) | 1 failed |
| the resolve cap off by one (`>`) | 1 failed |
| tiers swapped | 2 failed |
| the pin read from the oldest note | 1 failed |
| a note written on a probe | 1 failed |
| the `material` count forced to 0 | 2 failed |
| the note's `asked` forced to 0 | 1 failed |
| the note holding the materiality SHA as the company SHA | 4 failed |
| a damaged note ignored (pin skipped) | 1 failed |

## What holds
**Plan conformance (strong evidence, read).**
- *Not configured* is green and newest first. *Used before and now gone*, rolled back, edited in place, damaged, or the store unreadable all degrade the same way: newest first, red, no note.
- A damaged last note degrades with `pass_note_unreadable`.
- Both files are always tried, so every problem found is reported.
- One budget of 300 article reads plus 100 resolution reads. `resolve_reads_exhausted` is its own count.
- `NewestFirst` keeps the old code path. The existing read tests pass unchanged.

**Pin.**
- `pin.py` is the NP7b rule, moved and not copied.
- The cluster grouping now calls it. I traced the behaviour as unchanged: `last_version == 0` returns "", as the old `not previous.companies_version` guard did.
- Z17 and Z18 are re-pointed and `ok`.

**Write-once and receipts.**
- The note goes through `WriteOnceWriter` into `news/read-passes/1/<stamp>.json`.
- The workflow adds `EXTRA_MANIFESTS` and `receipts/raw/news/read-passes` (M13).
- The read step keeps `continue-on-error`, so a red degraded pass still commits its read receipts.
- Same-second notes are a write-once conflict, not an overwrite. The `news-record` concurrency group makes that case rare.

**Privacy.**
- The note holds counts, two versions and two SHA-256s in a fixed key set; `parse_note` refuses anything else (M12).
- The SHAs are of private files and sit only in the private Drive file. The public receipt is the hash of the note's bytes.

**Scope (the owner's ingestion-only rule, 27 Oct 2026, as relayed).** In scope: this is fetch prioritisation.

## Notes (not blocking)
- **N1, wording.** `pass_note.py` says "a red or degraded pass never moves the pin". A pass that is material first but red for another reason, such as `reader_failing` or a read write failure, does write its note, and correctly so: the versions it used were valid. Say "a degraded pass" (the story's own wording), not "a red pass".
- **N2, style.** `PrivateMaterialityFile.terms` sets `terms.sha256` after construction, while the company list uses `replace` on a frozen dataclass. Pass it to the constructor for one idiom.

## Hard lines
No order path, no Groww call, no secret. No title, term, symbol or URL is in a note, a log or git. The degrade never stops collection.

## Verdict: FAIL round 1 at e6aac2a. B1 (pin the note-manifest guards) required; N1 and N2 requested.

## Addendum 1: round 2 at 18f9111: PASS

I reviewed `git diff 3d9ad45 18f9111`. 3d9ad45 was e6aac2a plus `main`, with no NP8 change. The diff covers:
- `materiality/file.py` and `terms.py` (N2);
- the `pass_note.py` docstring (N1);
- two tests, and plants M18 and M19.

**Gates (locked venv, strong evidence).**
- 2018 passed.
- ruff check and format are clean; check_imports is clean.

**B1 fixed (strong evidence, replanted against the full suite).**

| Plant | e6aac2a / 3d9ad45 | 18f9111 |
|---|---|---|
| `skipped += self.notes.skipped_rows` removed | 2001 passed | 2 failed |
| `self.notes.check_ready()` removed | 2001 passed | 2 failed |

**N1 fixed.** The docstring now says only a *degraded* pass never moves the pin, and that a pass red for another reason still writes its note.

**N2 fixed.** `parse_terms` takes the digest, and `MaterialTerms` gets it in its constructor.

**Verdict: PASS round 2 at 18f9111.**

## Addendum 2: correction: Addendum 1's PASS is withdrawn; FAIL at 18f9111 (my miss)

**What I missed.** In both rounds I ran pytest, ruff, check_imports and my own plants, but **not** the full contract-plant runner, `tools/contract_plants.py`. Judge #2 found it red, and the orchestrator told me.

**I re-ran it at 18f9111 in the locked venv (strong evidence).** 272 rows are `ok` and one is not:
- `Y4: the plant went unnoticed: the claim is no longer pinned`.
- Y4's plant replaces `min(pages, PAGES)` with `pages` in `reads/run.py`. Its only test, `test_at_most_eighty_pages_are_fetched_whatever_limit_is_asked`, drives the newest-first path.
- NP8 added a second `min(pages, PAGES)` for the material-first queue, so the 80-page cap on that new path is not pinned by any test.
- The cap limits outside requests to news outlets, so this is lane 1 politeness, not style.

**Verdict: FAIL at 18f9111.** Required:
- a test that a material-first pass fetches at most 80 pages whatever limit is asked;
- Y4, or a new row, planting the material-first cap;
- the runner all green.

**My process change.** From now on, an all-green `tools/contract_plants.py` run at the frozen SHA is a condition of every PASS I give, and I record its count in the verdict.

## Addendum 3: re-review at 770cf76: PASS

I reviewed `git diff 18f9111 770cf76`. It changes one line in `reads/run.py`: the cap is now computed once, as `limit = min(pages, PAGES)`, and both paths use it. It also adds tests (the material-first page cap; M20, production wires `ReadPlanner` and `PassNotes`; M21, the outlet name reaches the tagger) and plant rows.

**Gates (locked venv, strong evidence).**
- 2020 passed.
- ruff check and format are clean; check_imports is clean.
- **Plant runner: 275 of 275 `ok`** at 770cf76, in one run, with nothing unnoticed.

**Addendum 2's items are fixed (strong evidence, my own plants).** Each was undone after its run.

| Plant | Result |
|---|---|
| the queue path given `pages` uncapped | 1 failed |
| the queue's page loop off by one (`>`) | 2 failed |
| the outlet name dropped before the tagger | 2 failed |
| the outlet name dropped before the weight | 1 failed |

**Verdict: PASS at 770cf76.**
