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

## Addendum 2: 65a99c0 and e25ab90, reviewed together: FAIL, two of four findings still open

I was sent `65a99c0b421ee8f7caac15f6ef29b1d981114db1`, but `story/R1c-code-r2` already carried
`e25ab90a68938b500de6d7a0ce42ff7ebf5464f1` on top of it. I reviewed both. `fno/` is byte-identical to 1381a8e
(`git diff --quiet 1381a8e e25ab90 -- fno`), so only tests and the story changed.

Gates on e25ab90:
- ruff and imports are clean.
- The suite passed 517 of 517 in 9 runs after clearing `__pycache__`.
- The first run, right after the checkout, showed `1 failed, 516 passed`. I could not reproduce it and did not capture
  the test's name (some evidence that it was stale bytecode from the switch; not proven).

| # | Finding | Status | Evidence |
|---|---|---|---|
| 1 | Drive's 900 s total limit can cut a call below 5 tries | **open** | `fno` unchanged; my probe at e25ab90 still gives 4 tries at 110 s attempts and 3 at 200 s (Retry-After 300) |
| 2 | Failed quote save must not be complete or canonical | **closed** | A real `_attempt` over the sample provider, plus a control run. The plant (`complete` ignores `raw_file_error`) is now caught. The story names both readers. |
| 3 | Failed intraday save must give no `taken` ledger row | **open, not addressed** | The plant on `intraday/recorder.py:_take` (swallow the save error, return a taken tuple with `path=None`) still passes all 517 tests |
| 4 | Retried re-send after a 401 must be pinned | **closed** | The plant (re-send's `ConnectionError` not retried) is now caught. The per-call re-sign test is good. |

**On finding 1, the new `test_the_worst_retry_after_case_stays_inside_the_policys_total_limit`:** it assumes the very
thing the finding disputes, that each request lasts at most `TIMEOUT_SECONDS` (60 s). `requests`' timeout limits
each connect and each read, not the whole request (strong evidence: the documented behaviour of `requests`). So a slow
multipart upload or an `alt=media` download can run longer. The test also sets 780 s against 900 s as arithmetic only;
it never runs the policy with timed attempts.

It does catch a plant lowering the limit to 780 s, but only because it asserts `== 900.0`. That pins the number, not the
behaviour.

The fix stays as in Addendum 1:
- Either raise Drive's `max_total_seconds`, so the 5-try count is the only stop, and add a test that runs
  `DriveSession` with attempts of 110 s or more and asserts 5 tries.
- Or the owner accepts, in writing, a time bound below today's. Today has no time bound.

**Minor (no action required):** the comparison test asserts `AttributeError` from `None.decode()`. That pins a crash's
type, not a designed refusal. It is loud, which is the point, but a later tidy-up of `compare` could turn it into a
silent `None`. This is acceptable for now because the writer-side test is now the main protection.

## Addendum 3: code round 2, c05a1d7: PASS

Reviewed `c05a1d7d022d7dd88770ff1287f47b9460367015` (`story/R1c-code-r2`), the SHA routed as decisive. The branch moved
on to `60ab2d8` after routing. I reviewed that delta too (below).

**Gates on c05a1d7:**
- Suite: 522 passed, 3 runs out of 3, `__pycache__` cleared.
- ruff, imports (390 files) and size (3 passed): clean.

The production diff from 1381a8e is one line: Drive's `max_total_seconds=float("inf")` (`settings.py:56`).

**Finding 1, closed.** My probe at c05a1d7 now gives 5 tries at 60, 100, 110 and 200 s attempts with Retry-After 300,
and 5 tries with no header.
- (a) Only `drive` changed. A plant giving NSE an infinite total is caught. At 60ab2d8, `nse_json`'s 60 s is pinned too.
- (b) It is `inf`, not a finite number. Plants of 900 and of 1e6 are both caught.
- (c) A fake-clock test with 1000 s attempts asserts 5 tries and four waits of 120 s.
- (d) The 780 s test no longer pins a limit; it now asserts the limit is `inf`.

**Finding 2, still closed.** The plant (`complete` ignores the save error) is caught. Judge #2's S3 plant (the
`RAW_FILE_SAVED=False` line made `pass`) is caught too.

**Finding 3, closed.** The new test runs the real `IntradayRecorder._take` over a Drive that drops after the create, then
`Settlement.settle`. The result is a `DRIVE_WRITE` failure and one `failed` row naming no Drive copy. My plant (swallow
the error, return taken with `path=None`) is caught.

**Finding 4, still closed.** The plant (re-send `ConnectionError` not retried) is caught.

**Earlier plants, all caught:** the 401 re-sign repeated, the cap removed, the ceiling 100, and the receipt written
before the Drive put. That is 11 of 11 plants at this SHA.

**Story text (one functionality, one document):** the two-readers chain is right in substance. At c05a1d7 its line
references are off by one or two:

| Cited | Actual |
|---|---|
| `recorder.py:258-259` (the raw-save error is a failure) | `260-262` |
| `recorder.py:261-263` (`complete`) | `263` |
| `drive_only_store.py:48-62` | `49-63` |

60ab2d8 corrects the first two and gives `49-62`; the method's last line is 63, so that is a nit. Not blocking: every
citation lands on or next to the code it names, and the reasoning it states is true (I traced it).

**60ab2d8 delta (reviewed):** story text, plus one test assertion (`nse_json` limit 60 s). `fno/` is identical, and 522
tests pass. Either SHA is acceptable to me; the orchestrator picks the one that merges. Pushing after a SHA is routed
breaks the freeze rule; the orchestrator should note that, but it changes no verdict here.

**Hard lines:**
- No orders.
- No secrets in the diff.
- No Groww call: every plant and probe used fakes.
- Write-once is untouched: no put or conflict logic changed.
- NSE retry numbers are unchanged.

**Verdict: PASS (strong evidence: gates run, probe re-run, 11 plants caught).**

## Addendum 4: 60ab2d8, the routed round-2 SHA: PASS

The orchestrator corrected the routed SHA to `60ab2d8b989763d2c6a86c067299fd2d29de1126`. `fno/` is byte-identical to
c05a1d7 (`git diff --quiet`), so the code review, gates and 11 plants of Addendum 3 carry over. At 60ab2d8: 522 passed.
The delta is the story's line numbers plus one test assertion pinning `nse_json`'s 60 s limit.

I checked each corrected citation against the code at 60ab2d8:

| Citation | Code at that line | Result |
|---|---|---|
| `recorder.py:260-262` | the save, then `failures.append(raw_file_error)` | right |
| `recorder.py:263` | `complete = ... not failures ...` | right |
| `recorder.py:273-274` | `meta[RAW_FILE_SAVED] = False` | right |
| `recorder.py:284-286` and `:285-286` | the sidecar put, then the marker put only if `complete` | right |
| `compare.py:40` | the direct sidecar read | right |
| `drive_session.py:49` | the per-call `signed_in_again` flag | right |
| `drive_session.py:54/56/57` | the re-sign check, the flag set, the re-send | right |

Nits, not blocking:
- `drive_only_store.py:49-62` stops one line short of the method's `return data` at `:63`.
- `recorder.py:185` names the `if` whose marker put is at `:186`.
- The worst-case section's `drive_session.py:41-62` is an approximate span of `request`.

Each lands on or next to the code it names, and the reasoning it supports is true.

**Verdict on 60ab2d8: PASS (strong evidence).**
