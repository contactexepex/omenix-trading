# Judge 40: R1d4 locking tests and the no-refactor finding, a lane-2 check (judge #2)

Branch `story/R1d4-refactor`, SHA `8d2968e3c90527e979ef38104672c8bbeaaf7d1b`, tests only
(`tests/characterization/test_yahoo_pacing_wiring.py`, 6 tests; no `fno/` change). **PASS**, one nit. This stands in
for the orchestrator's lane-2 check.

## Gates

565 passed across the suite (`__pycache__` cleared); ruff check and format clean; imports clean. The new file passes
alone and in file order. The suite's autouse fixture (`tests/conftest.py:97-105`) clears `SHARED_PACER` hosts and
detaches the pause log after every test, so opening the Yahoo host in one test cannot leak into the next, and no
test writes the repository's pause log.

## Do the tests lock today's behaviour?

| Test | Code it locks | Match |
|---|---|---|
| (a) every cue session and the pre-open NSE parts on `SHARED_PACER` | `global_cues/wiring.py:280-283` `PacedSession()`; `preopen/wiring.py:63` one `PacedSession` for `NseGiftNifty` and `NsePreopenList`. `[:2]` is right: parts 3 onward are Groww candle sources, which do not use the session | yes |
| (b) two Yahoo 429s open the host, the third index is never sent | `http_pacing.py` `observe(host, status)`; `nse_pacer.py:30` `REFUSAL_STATUS_CODES = (403, 429)`; the breaker refuses with `SourceCoolingOff` before the GET | yes |
| (c) one 429, then a good answer: host closed | `observe`: any non-refusal calls `record_other`, which resets the run | yes |
| (d) 19 and 20 minutes live, 21 stale | `preopen.py:39` `STALE_AFTER = 20 min`; `:75` `>` (strictly over) | yes |

**Plants (mine; each restored):**

| Plant | Failed |
|---|---|
| Y1 a private `NsePacer` in the cue session | 3 |
| Y2 pre-open on a plain `requests.Session` | 1 |
| Y3 stale window 30 min / Y3c `>` changed to `>=` | 1 / 1 |
| Y4 `PacedSession` not calling `observe` | 2 |
| Y5 429 no longer a refusal | 6 |
| **Y3b stale window 20 min 59 s** | **0: survives** (nit) |

## The no-refactor finding: confirmed

I read `fno/ingestion/global_cues/` and `fno/ingestion/preopen/` for every sleep, loop and retry.
- Yahoo, global cues and the pre-open reader make one GET each, with no retry: the A17e block rule
  (`yahoo_source.py`, `preopen.py:147`, `collector.py:83-88`). Pacing and the host pause are already
  `SHARED_PACER` (R1b1).
- `preopen_cli.py:84-88` sleeps until the window opens: a window wait.
- `preopen/run.py` reads each part every 30 s (`RETRY_EVERY`) inside its window until it is complete. That is a retry
  in form, but it is scheduled by the clock and bounded by the window, not by a count, the same kind as the index
  recording loop the R1d plan keeps. `RetryPolicy` (attempts and waits) would not express it without a window mode.
  It stays.
- `preopen/label_read.py:14` is a bounded thread join (600 s) so the run always ends, not a retry.
- `open_check.py:87` and `reading.py:91` are look-back loops over days, not waits.
- `global_cues/attempt_log.py` is already a committed day ledger; reformatting it would change a record.

So R1d4 has no wait or retry to move, and tests only is right. I see no lane-1 code here: nothing changes an outside
service call or a record.

## Nit (not blocking)

The 19/20/21-minute pair pins whole minutes. A level's age is not whole minutes: the seen time has seconds. So a
window widened by up to 59 s (plant Y3b) passes. A 20 min 1 s case (stale) would pin the exact edge; one more
parametrize row.

**Verdict: PASS** (lane-2 check, judge #2).
