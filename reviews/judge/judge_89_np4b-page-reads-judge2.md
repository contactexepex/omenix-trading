# Judge 89: NP4b page reads (code, lane 1), judge #2

Frozen SHA `337f0ea` (branch `story/NP4b-page-reads`, from main `04cf28d`). Reviewed `git diff $(merge-base) 337f0ea`:
- `news/reads/{extract,read_file,run,report,cli,wiring}.py`;
- `news-read-pages.yml`;
- the tests, rows Y1-Y13 and their plants.

**Gates:** ruff clean; imports clean (585 files); code size passed.

The full suite in my venv gives 1785 passed and 9 failed. All 9 are `test_commit_guard.py` real-git tests, and they are
an **artefact of my venv**, not of this change:
- the test symlinks `python` to `sys.executable`;
- a symlink to a venv's interpreter, placed outside the venv, loses the venv, so the subprocess finds no `selectolax`;
- the same tests pass on main (23 passed), and CI installs the lock system-wide.

I counted those 9 as the baseline for my plants.

**My plants (5 of 6 killed):**

| Plant | Tests failed (above the baseline) |
|---|---|
| unlisted host allowed | 2 |
| budget check off | 2 |
| read-file cap off | 2 |
| probe writes | 3 |
| failing-reader check off | 3 |
| no JSON-LD depth limit | **survived** (should-fix 3) |

## Your questions

- **(a) A request to an unlisted host:** none found. `_page_url` checks `may_fetch` before asking, and the fetcher
  checks again at every hop (NP4a).
- **(b) A hostile page:** two defects, F1 below and should-fix 1. Control characters are removed, names are capped at
  80 characters and 5 authors, and the body is measured and dropped.
- **(c) The budget:** yes, a run can exceed it, without limit. See F2.
- **(d) The failing-reader rule:** `robots_disallowed`, `host_stopped` and `host_not_allowed` are not faults; every
  other fetcher code is. Red at 3 or more faults with nothing OK, or at 10 or more with under half OK. Plant killed.
  Reasonable. Note that a 404 counts as a fault, so a run that meets several deleted articles turns red: loud by
  design.
- **(e) Write-once and order:** the same `WriteOnceWriter` as NP2c: file, then receipt, then row; a conflict, never an
  overwrite; the torn check runs before writing with `--apply`.
- **(f)** `NOT_PACED` gains `news-read-pages.yml`: correct, since it uses the fetcher's own spacer. 22 to 23 installs:
  correct.

## Findings

1. **F1 (must fix): one hostile page stops the whole pass, run after run.**
   - `from_json_ld` catches only `ValueError`. A deeply nested JSON-LD array, `[` 200,000 times inside the 1 MB cap,
     makes `json.loads` raise **`RecursionError`**. Reproduced: it escapes `extract`.
   - It is not caught in `_read` or `run`. The CLI turns it into `stopped: unexpected RecursionError` and **no
     further page is read**.
   - The pass goes newest first and writes nothing for that article, so the same page comes up first again on every
     run for 3 days: the reader is dead for 3 days, with an alert each time.
   - Fix: treat any failure to parse a script, `RecursionError` included, as "no facts from this script". Also catch per
     page in `_read`, so that one page's parse failure counts as `no_facts`, or as a fault, and the pass goes on. Add a
     test and a plant.
2. **F2 (must fix): "a slow or silent outlet can never run the job past its limit" is not true.**
   - `requests`' `timeout=20` limits each wait for the connection or for the next bytes, not the whole download.
     Reproduced locally: with `timeout=1.0`, a server dripping 12 bytes at one every 0.5 s took **6.0 s** and
     completed.
   - Inside the 4 MB cap, an outlet sending a byte every 19 s holds one fetch for days, and so does a slow robots.txt.
     The budget is checked only *between* pages (`run.py:253`), so one fetch runs until the job's 45-minute timeout
     kills it.
   - Then nothing is committed. Files already written to Drive are re-rowed by the next run, so it fails closed, but
     the stated guarantee is false.
   - Fix: give `HttpsPageFetcher` a total deadline per fetch, covering every hop, robots.txt and the body loop, and
     have the pass pass in what is left of its budget. Add a test with a dripping fake response.

## Should fix (not blocking)

1. **Long non-ASCII names overflow the 2,000-byte cap.** With `ensure_ascii=True`, each Devanagari character costs 6
   bytes. Five 80-character names plus an 80-character provider gives `ValueError`, then `READ_WRITE_FAILED`, a red
   run, and a retry every run. Reproduced. Realistic bylines are shorter (reasoning only). Cap by encoded size, or fall
   back to fewer authors, rather than refusing the file.
2. **`python -m fno` now imports `selectolax` at startup.** `news/cli.py` imports `reads/cli.py`, which imports
   `reads/run.py` for `PAGES`, which imports `extract.py`, which imports `selectolax`. So every news subcommand,
   `check-manifest` in the commit guard included, now needs the library. Every workflow installs the full lock, so
   nothing breaks today. NP2b kept its library import lazy on purpose; keep `PAGES` in a module without the import.
3. **The JSON-LD depth limit has no test.** Removing `depth < MAX_DEPTH` survives the suite.

**Verdict: FAIL** (round 1, `337f0ea`). F1 is a small catch; F2 is a deadline in the fetcher.

## Addendum 1: round 2 on `346e78c` (with `9a12caf`'s unbuffered probe job)

`git diff 337f0ea 346e78c -- fno`:
- `from_json_ld` skips a block that raises `ValueError` or `RecursionError`, and `_read` counts any extract failure as
  `extract_error` and goes on;
- `fetch(url, seconds)` has a total deadline (at most 60 s) over hops, robots.txt and the body;
- requests' connect and read timeouts are cut to the time left, and the body is read with `raw.read1`, so the deadline
  is checked between drips;
- a timeout stops the host;
- the pass gives each fetch what is left of its budget;
- the read file is UTF-8 with a 4,000-byte cap;
- `PAGES` and the other limits moved to `reads/limits.py`.

**Gates** (in the locked venv): **1806 passed**. My earlier 9 commit-guard failures are gone too: `python -m fno` no
longer imports `selectolax` (I confirmed `import fno.ingestion.news.cli` leaves it unloaded). ruff clean; imports clean
(586 files); code size passed; contract plants all ok.

**My round-1 reproductions:**
- **F1 fixed:** the 200,000-deep JSON-LD page gives `None`, no exception.
- **Should-fix 1 fixed:** five 80-character Devanagari names plus the provider come to 1,789 bytes, under the cap.
- **Should-fix 2 fixed:** the CLI import no longer loads `selectolax`.

**F2 fixed, checked in urllib3 2.8.0 (locked):** `read1(decode_content=True)` keeps reading until it has decoded data or
reaches the end of the stream. So the loop never ends early on an empty chunk in the middle of a gzip body, and a drip
returns what has arrived, so the deadline is checked between drips.

The bound is now: a run takes at most `BUDGET_SECONDS`, plus one fetch of at most `max(1, what is left)`, and never more
than 60 s per fetch. The name lookup is outside it, and that is stated.

**Plants (5 of 5 killed):**

| Plant | Tests failed |
|---|---|
| no deadline check in the body loop | 5 |
| no deadline check per hop | 1 |
| the pass not passing its budget | 2 |
| extract failure not caught | 1 |
| `RecursionError` not caught | 2 |

**Verdict: PASS** (`346e78c`). Both must-fixes and all three should-fixes are done.

## Addendum 2: `98ad64a` (= `346e78c` plus one test)

`git diff 346e78c 98ad64a` changes no code. It adds one test (`test_cli_wiring_workflow.py`, +10 lines: a subprocess
check that importing the CLI does not load the parser), row Y19 and its plant. That matches my Addendum 1 check
(`selectolax` stays unloaded) and judge #1's M1.

**Verdict: PASS** (`98ad64a`).
