# Judge 32: R1c code (Drive on the shared retry policy), judge #1

**SHA:** `1381a8eea6661a5c797df64e1e7fa8ee373c9b45` (branch `story/R1c-code`), lane 1 (the Record store's write path).
**Verdict: FAIL, round 1 of 2.** The design is built as the story says. Three gaps remain: the 5-try claim is not true
by construction, and two own-record writers named by the story have no test at the caller.

## Gates (run on the frozen SHA, own worktree)

- `python -m pytest -q -n auto`: 511 passed.
- `ruff check fno tests tools ops`: clean.
- `tools/check_imports.py`: clean (390 files).
- `tests/test_code_size.py`: 3 passed.
- `check_numbers` runs on `main` with this file.

## What I confirmed (strong evidence: code read, plants run)

- **Classification is unchanged.** Transient {429, 500, 502, 503, 504}, Google's 403 rate-limit reasons, and
  `ConnectionError` and `Timeout` are retried. Every other answer ends the call, and `accept` is checked as before.
  The 401 re-sign is inside the attempt: one extra send, no wait, never twice.
- **Behaviour change, in the safer direction.** A `ConnectionError` on the re-send after a 401 is now retried, where
  today it was raised at once. That means more tries, never fewer, and the story states it.
- **Retry-After.** It is clamped to `DRIVE_RETRY_AFTER_CAP_SECONDS = 120.0` in `_classify`, and the Drive ceiling is
  600 s, so `retry.py:98` never stops a Drive call. NSE and `nse_json` settings are unchanged: the `fno/shared` diff is
  the `drive` block only. There is no library edit.
- **No Drive breaker.** `settings_for("drive").breaker is None`, and nothing reads it. `raw_source.py:187` reads only
  `nse`. `test_guarded` now builds the counting breaker explicitly, so the library mechanism stays tested.
- **Plants caught (7 of mine, plus 1 write-order check):**

  | Plant | Result |
  |---|---|
  | Cap removed | caught |
  | Cap 119 s | caught |
  | Ceiling 100 s | caught |
  | Drive jitter 1.0 | caught |
  | 401 re-sign repeated | caught |
  | `ConnectionError` not retried | caught |
  | `Timeout` not retried | caught |
  | Receipt written before the Drive put (`data_store.py`) | caught |
  | Quote reader defaulting the flag to not-saved | caught |

- **One equivalent mutant, no action:** accepting an exhausted answer whose status is in `accept`. No caller passes a
  transient status in `accept` (only 409 is used).

## Required to PASS

### 1. The 900 s total limit can cut a Drive call below today's 5 tries

Strong evidence: probe run, plant survives.

The `drive` settings keep `max_total_seconds=900`. `RetryPolicy.run` counts the time the attempts themselves take
(`time.monotonic` from before the first try). The story's 780 s worst case assumes each attempt ends within 60 s. That
is false: `requests`' `timeout=60` limits each connect and each read gap, not the whole request. A multipart upload or
an `alt=media` download can legitimately run longer.

Probe (`DriveSession` with a fake clock, 503 with `Retry-After: 300` on every answer):

| Attempt length | Tries | Today |
|---|---|---|
| 60 s | 5 | 5 |
| 100 s | 5 | 5 |
| 110 s | 4 | 5 |
| 200 s | 3 | 5 |

Today has no total limit, so this is "fewer attempts at the Record store than today", which the story forbids.

Likelihood: it needs attempts of about 105 s or more, plus Retry-After headers. That is uncommon (reasoning only).

The plant `max_total_seconds` 900 → 500 **survives**: the "Retry-After 300 gives 5 tries" test models attempts as
taking no time, so it does not pin the 780 s budget at all.

Fix:
- Set Drive's total limit so the 5-try count is the only stop. A value such as 3600 s is above any 5-try worst case
  short of hour-long attempts.
- Or state and accept a lower bound in the story, with the owner's agreement.
- Either way, add a test with timed attempts. Each attempt advances the fake clock by at least the 60 s timeout, and
  the test asserts 5 tries.

### 2. A failed quote CSV save must not produce a canonical marker: no test

Strong evidence: plant survives.

Plant `recorder.py:263`: `complete` ignores the `raw_file_error` failure, so a failed save can be canonical.
**511 passed.** This rule is what keeps the second sidecar reader safe (`quotes/compare.py:40`, judge_30 Addendum 4).
It also protects `indices.py:85`. The story text at this SHA still says "exactly one reader".

Fix:
- The story correction from Addendum 4.
- A test: a CSV save that fails every try leaves `complete` false and writes no canonical marker.

### 3. Intraday snapshots: the ledger half of "snapshot files and ledger" is untested

Strong evidence: plant survives.

The new test checks only that `SnapshotFiles.save` raises. The own-record writer is the caller,
`intraday/recorder.py:_take` (`:209-212`), which turns a failed save into a `DRIVE_WRITE` failure, so `settle` writes a
`failed` row, never a `taken` one.

Plant: swallow the save exception and return a taken tuple with `path=None`. **511 passed.** A "taken" ledger row with
no Drive file would ship unnoticed.

Fix: a test that drives `_take` (or the slot run) over a Drive that fails every try. It asserts the result is the
`DRIVE_WRITE` failure and that the ledger gets no `taken` row for the mark.

## Hard lines

- No orders.
- No secrets in the diff or in this file.
- No Groww call: plants and probes used fakes only.
- The record scan ran on this commit.
- Write-once is untouched: no store's put or conflict logic changed. Only the session's retry loop changed.
