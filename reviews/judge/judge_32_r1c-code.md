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

## Addendum 1: the 401 behaviour change, and every finding in one list (same round)

The orchestrator asked two questions: whether the change to the re-send after a 401 is acceptable, and whether a
persistent 401 can loop.

**The re-sign cannot loop (strong evidence: code read and tests).** `signed_in_again` is a `nonlocal` flag of the whole
call, not of one attempt. So the re-sign happens at most once per call, which is stricter than once per attempt and the
same as today. A second 401 is classified `OK`. Its status is not in `accept`, so `_raise_with_reason` raises it at once.
Two characterization tests pin this:
- `test_a_second_401_is_raised_and_the_token_is_asked_only_twice`;
- the test at `test_drive_behaviour.py:149`: 401, then 503, then 401, which raises with no third sign-in.

**The behaviour change is accepted (strong evidence on its bounds, reasoning on its value).** Today a `ConnectionError`
on the re-send after a 401 is raised at once. It is now retried, within the same five tries and waits, so there are
more tries, never more than five, and no new loop. A retried create is safe because it reuses its reserved ID: a
repeat answers 409, which `accept` takes. Keeping today's quirk would need a special case for one rare path, and that
gains nothing. I do not think a refactor must keep it.

**But nothing pins it (strong evidence: plant survives).** Plant: the re-send's `ConnectionError` is turned into a
non-retried error. **511 passed.** A test must pin the new behaviour: 401, then a dropped connection on the re-send, then
200, ends OK after one wait. That gives the orchestrator's condition "pinned by a test" a real test.

**On the "780 s < 900 s margin test": it does not fix finding 1.** A test whose attempts last 60 s passes at 900 s.
Finding 1 is about attempts longer than 60 s: `requests`' timeout limits each read, not the whole request. Two fixes
are acceptable:
- raise Drive's `max_total_seconds`, so the 5-try count is the only stop;
- or ask the owner to accept a time bound below today's.

The test must use attempts longer than 105 s and still assert 5 tries.

**Every finding for the superseding SHA:**
1. Drive's total time limit can cut a call to fewer than 5 tries (round-1 finding 1).
2. No test that a failed quote save writes no canonical marker, and the story text says "exactly one reader"
   (finding 2, judge_30 Addendum 4).
3. No test that a failed intraday save writes no `taken` ledger row: the plant on `intraday/recorder.py:_take`
   survives (finding 3).
4. No test pins the retried `ConnectionError` on the re-send after a 401 (this addendum).

**On a stopgap for the writer-side test (finding 2):** a reader-level test in `compare` plus a written argument from the
code is not enough on its own. The thing to pin is the writer's rule: `complete` stays false when the save failed. The
harness can be small. `_save_quote_file` already runs alone in the new tests, and `complete` is one expression
(`recorder.py:263`). If building the harness really is out of proportion, pulling that expression into a small pure
function that is tested directly is enough for me. A comment or a written argument is not.

There are no other findings. I re-read the whole diff for this addendum.
