# Judge 472: A9c, a second NSE archive host, code (story/oss1-second-host @ 5f9be1e6)

Judge F. Code round 1 of 2. Story text: judge 471 add. 1 PASS and its note (the provenance rows, met at d761d3c9).
Claims: response 320. The A20 builder (owner of `raw_source.py`) reviewed it first. Lane 1.

## Verdict: PASS. It may merge from 26 Oct (pull, full suite on the merged tree, `check_numbers.py`, then push). 1 minor.

Gates on 5f9be1e6: **9848 passed**, 16 xfailed; ruff, ruff format (1856), `check_imports.py` and the record scan
(7872) are clean.

Checked in the code:
- `FallbackSource` re-raises `RawFileRefused` and `RawSourceCoolingOff`, and asks the second host only on
  `RawSourceUnavailable`. A `None` stays `None`.
- A failure on both hosts keeps the second error's kind and names both hosts. All three error classes share
  `RawSourceUnavailable.__init__(message, status, tries)`, so `type(second)(...)` is safe.
- `last_written` is the primary's; `fetch_published` from the second host carries no write time.
- The secondary is built with `retry_waits=()` (one try) on its own host, so it gets its own pacer.
- Only `build_librarian` and `build_nse_library` use the fallback.
- The provenance log writes `second-host/<dataset>.csv` with the second host's URL.

## Plants (each reverted)

| # | Plant | Caught |
|---|---|---|
| 1 | a refusal falls back to the second host | yes, 2 failed |
| 2 | write times from the second host | yes, 1 failed |
| 3 | the second host given full retries | yes, 1 failed |
| 4 | no provenance row | yes, 4 failed |
| 5 | the fallback not wired (primary only) | yes, 2 failed |

## Minor

**The provenance row is written before the store accepts the file [code read].**
- `fetch` logs the row as soon as the second host answers. `RawFileLibrary.get` saves to the archive after that.
- If the archive then refuses the bytes (the content check, a write-once conflict, Drive down), a row in
  `second-host/` describes bytes the store does not hold.
- The SHA-256 join to the manifest shows it (no matching manifest row), so nothing is lost. But the docstring's
  "every file the second host serves" should read "every file the second host returned", or log the row after the
  store's put.

After the merge (quality rule 8): one live `data-hosts` day and the first librarian run, as the claims say.
