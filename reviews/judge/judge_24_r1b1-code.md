# Judge 24: R1b1 NSE layer (code), branch `story/R1b1-nse-layer`, SHA 9034093

**PASS, lane 1, judge 1.** 14 files: the new `fno/shared/nse_pacer.py`; `http_pacing.py` now re-exports it and keeps
`PacedSession`; `raw_source.py` runs on `RetryPolicy`; `public.py` too; the library edit (`RetrySettings.jitter`
only); tests; the story. This is code the live workflows run, judged against the passed story (ab5bba8).

| Check | Verdict | Evidence (my own runs) |
|---|---|---|
| Gates | MET | 431 passed; ruff, check_imports, check_numbers, code size and format clean |
| Characterization adaptations are only the named ones | MET | The diff of `tests/characterization/` changes only constructors, imports, a zero-jitter `RetryPolicy` injection, and drops `assert COOL_OFF_SECONDS == 900`. The 900 s is still pinned by behaviour (the 899 s and 901 s steps in the same test). No assertion on behaviour changed |
| Behaviour parity, read line by line | MET | Old vs new `_response`: 404 returns `None`; 403 and other refusals give `RawFileRefused`; a second consecutive 429 gives `RawSourceCoolingOff`; `SourceCoolingOff` gives `RawSourceCoolingOff(tries - 1)`; unbuildable requests are not sent; `Retry-After` over 120 s gives `RawSourceUnavailable`; message texts are identical. The new 900 s total-time limit can never bind (waits up to 81 s, or 3 x 120 s, plus 4 x 60 s timeouts, is at most 600 s). `nse_json` keeps 3 tries, the warm-up, every wait including the last, and the 0.4 s pause |
| Per host, one shared pacer | MET | `_host()` keys `RateLimit` and `CircuitBreaker` by host; `SHARED_PACER = NsePacer()` |
| Library edit is only `jitter` | MET | `git diff -- fno/shared/resilience`: `retry.py` and `settings.py` only; no `record_unanswered`; `RequestPacer` and the NSE `RETRY_WAITS` are gone from `fno/` (Drive's is R1c) |
| Probe and wait, real threads | MET | My own check, outside the suite. After a pause, the probe goes alone. Answered **200**: all three callers complete, with released waiters 0.2 s apart (the spacing set). Answered **403**: the two waiters get `SourceCoolingOff`, one request in all |
| Tests catch breakage | MET | 28 plants, all detected. 26 fail a test: one host for both, no spacing, half-open raising, no release on observe, unanswered re-opening, 5xx counted, the message text, no release on a session exception, an unshared pacer, 404, the cooling `tries`, the second 429, the 5xx reset, a 403 retried, unbuildable retried, `Retry-After` dropped, the message text, BLOCK becoming unavailable, `nse_json`'s last wait, 4 tries, no warm-up, no pause, NSE jitter 1.0, the `nse_json` waits, jitter ignored, negative jitter. 2 make the suite **hang** instead of failing: waiters not waiting for the probe, and an expired wait that does not close |
| Claim 7 (static `sleep(` allowlist) deferred to R1c/R1d | ACCEPTED | Recorded in the story (`R1b-nse-source.md:186`). The NSE loops it would guard are already gone |

## Notes (not findings)

- **Hang-mode detection:** two concurrency plants are caught only by the suite hanging. On CI that is a job stuck until
  its timeout, not a clear failure. Bound the threaded tests' joins or waits (for example `join(timeout=...)` plus an
  assert), so that a regression fails in seconds. This can ride with R1b2.
- After the merge, the story's active log comparison of the first scheduled runs applies (`R1b-nse-source.md`,
  "Verification").
