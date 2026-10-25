# Judge 48: story A11, revisions of NSE files

**Verdict: PASS.** All 4 criteria are MET.
- **Both real versions are verified against NSE myself:** the archived first version's SHA-256 equals A10's record,
  and NSE's current file equals the archived revision, with Last-Modified 23:20:10 IST.
- **The builder's correction is true:** NSE added 21 indices, not 2, and changed none. NIFTY 50 (22,363.35) and India
  VIX (15.25) are the same in both versions.
- **My 2 point-in-time plants are caught,** including the one-second boundary.

**What I judged**
- **Repository:** trading at 7080f6f.
- **Claims:** `reviews/claude/response_54_2026-10-13-a11-revisions.md`.
- **Story:** `docs/stories/A-data-foundation.md`, A11.

## Checks run by the judge

```
$ python -m pytest -q tests -k "revision or versioned or sweep"        32 passed
$ (full suite at 46fe709: 1215 passed; ruff and imports clean)
$ sha256sum tests/fixtures/nse/revisions/*
  fc847998…7f25  ind_close_all_12102026.first.csv        (= warmup_closes.csv's index_sha256 for 12 Oct, recorded by A10)
  e8e8f6ec…e621  ind_close_all_12102026.rewritten.csv
$ curl NSE …/ind_close_all_12102026.csv                 sha256 e8e8f6ec…, Last-Modified Mon 12 Oct 2026 17:50:10 GMT (23:20:10 IST)
```

**My comparison of the two versions:** 146 rows, then 167 rows: **21 added, 0 removed, 0 changed**.

**Plants (each reverted; `git status` clean):**

| Plant | Result |
|---|---|
| The point-in-time reader ignores `as_of` (always the newest) | **caught** (1 failing) |
| `<=` changed to `<` at `available_from` (the exact second of the rewrite) | **caught** (1 failing) |

## Criteria

| # | Criterion | Judge's evidence | Result |
|---|---|---|---|
| 1 | A later version is stored under `revisions/` with the same path, a time and its SHA-256; raw is never overwritten | The committed index row is the path, `e8e8f6ec…`, 17,552 bytes, available from 23:20:10+05:30. The test checks the raw bytes are unchanged and that a repeat capture adds nothing. | MET |
| 2 | Point-in-time and latest readers, tested on the real 12 Oct case | Both real files are fixtures with SHAs I verified. The readers are tested at 15:30, 23:20:00, 23:20:10 and 13 Oct 09:00, and for latest. Plants caught. | MET |
| 3 | A8's sweep stores what it finds as revisions | `RevisionCapturingSource` decorates the sweep's source and `LastWriteSweep` is unchanged. The wired test uses only a fake NSE. The builder's real run (178 moved, 0 new revisions) agrees with my reading of the code: a moved Last-Modified with the same bytes is not a revision. | MET |
| 4 | Coverage reports revisions per dataset; size, lint, imports, tests | `coverage.py` counts revised days, with a test. Files are 157, 57 and 41 lines. Lint and imports are clean. | MET |

## Notes

- **`available_from` uses NSE's Last-Modified for the bytes, or else the time found.** That is right and
  conservative. If NSE later touches Last-Modified without changing bytes (the 178 participant-OI cases), no new
  revision is made, so nothing becomes available earlier than it was.
- **The reader takes the last index row that is available,** which relies on the append order. That is safe: NSE
  cannot serve an older version after a newer one, so the find order equals the availability order. An explicit sort
  by `available_from` would make this independent of the order (optional).
- **Consequence for other verdicts:** the 12 Oct rewrite changed no NIFTY 50 or VIX value. So no closes-based result
  (B3's discovery, G1's IV30 check, judge 44's warm-up check) is affected. My judge 44 note about 12 Oct's
  different SHA is now explained and archived.
