# Judge 91: NP4b page reads (code), round 1 at 337f0ea: FAIL

**Lane 1 (page requests once dispatched, Record writes, a workflow); judge #1.** Branch `story/NP4b-page-reads`. The request named no frozen SHA, so I reviewed the branch tip, **337f0ea**. Reviewed `git diff origin/main...337f0ea`: `news/reads/*` (460 lines), `news-read-pages.yml`, rows Y1 to Y13.

## Gates (strong evidence)
- **Locked venv:** ruff is clean. 1794 passed and contract plants are all `ok`, **once selectolax is importable by the base interpreter** (see M1).
- **Without that:** 9 commit-guard tests fail, and plants X6 and X7 report "tests fail without the plant". The commit-guard test symlinks `python` to `sys.executable` from a temporary directory. A venv interpreter run through a symlink outside the venv falls back to the base interpreter, and `fno news ...` now imports selectolax when it loads.

## B1 (required; strong evidence, reproduced): one hostile JSON-LD block ends the whole read pass
- `extract.from_json_ld` catches only `ValueError` around `json.loads`. A JSON-LD script of 100,000 nested `[` (about 200 KB, well under the 1 MB `MAX_JSON_BYTES` and the 4 MB page cap) raises **`RecursionError`**. That escapes `extract()`.
- `ReadPass._read` (`run.py:122`) calls `extract(page.body)` with no handler. The error therefore stops `run()`, and the CLI reports `unexpected RecursionError` for the whole run.
- Reproduced: 5,000 levels give `None` (bounded), 100,000 give `RecursionError`.
- **The effect:**
  - one page from a listed outlet stops every remaining page of the run;
  - pages are taken newest first, so the same article would stop every run until it leaves the look-back.
- Page text is untrusted (the story's own premise), and this was one of the named attack points.
- **Fix:**
  - catch any exception per script in `from_json_ld` (or `RecursionError` with `ValueError`);
  - wrap `extract` per page in `_read`, counting `extract_failed` without stopping the run;
  - pin it with this input and a plant.

## What holds (strong evidence)
- **Plants (each one undone; all fail tests):**

| Plant | Result |
|---|---|
| no `may_fetch` pre-check | 1 failed |
| no 2,000-byte read-file cap | 1 failed |
| the probe writes | 2 failed |
| no JSON-LD size cap | 1 failed |

- **The read file** holds facts and the body's SHA-256 and length only: no body, no HTML, no key sentences (decision E1's default). Names are capped at 80 characters, with at most 5 authors.
- **Requests** go through NP4a's fetcher, so every hop is re-checked. The pass also pre-checks `may_fetch`, so an unlisted host is counted, never requested.
- **Run budget.** The 900 s budget (my NP4a forward note) is built: the clock is checked before every page, and pages left over are counted `budget_stopped` and alerted.
- **A blocked runner is red.** `reader_failing` is set when nothing is OK, or under half OK in a large batch; robots.txt refusals and host stops don't count as faults.
- **Depth.** `article_nodes` is bounded in depth and node count; a 3,000-deep `author` object does not hurt.

## Minor (requested)
- **M1.** Make the selectolax import lazy (inside `extract()` or `reads/cli`), as NP2b does for its library. Then `fno news check-manifest`, which the shared commit guard runs, never needs a parser package to load. Today any environment without selectolax breaks the commit guard of every news workflow.

## Hard lines
No order path, no secret, no Groww call. Nothing is requested until the owner dispatches, and only with `apply` is anything committed.

## Verdict: FAIL round 1 at 337f0ea. B1 required; M1 requested.

## Addendum 1: superseded by 346e78c: PASS

Reviewed `git diff 337f0ea 346e78c`, which also answers judge 89.

**Gates (locked venv).** 1806 passed; contract plants all `ok`, H1 to H17 and Y1 to Y18.

**B1 fixed (strong evidence, my reproduction re-run).**
- The 100,000-deep JSON-LD block is now skipped (`extract` catches `ValueError` and `RecursionError` per block), and the page falls back to its meta tags (`provider='X'`).
- `_read` also counts any other extractor failure as `extract_error` and goes on.
- Plants: `RecursionError` not caught → 1 failed; `_read` catching only `ValueError` → 1 failed.

**M1 fixed (strong evidence).**
- `import fno.ingestion.news.cli` no longer loads selectolax.
- I removed the selectolax I had installed for the base interpreter (my change to the environment, now undone). All 23 commit-guard tests then pass through the symlinked interpreter.

**The total deadline per fetch (judge 89 F2, and my judge 88 note) holds.**
- It covers the hops, robots.txt and the body; request timeouts are `min(limit, time left)`.
- The body is read with `raw.read1(65536, decode_content=True)`. I checked this against a **real** local server sending a gzip bomb (48 KB compressed, 50 MB of zeros): decoded chunks were at most 65,536 bytes, reading stopped at the 4 MB cap, and peak memory was 75 MB. So the decoded-byte cap still holds with `read1`.
- Plants: no deadline between drips → 4 failed; no deadline per hop → 1 failed.

**Verdict: PASS at 346e78c.**
