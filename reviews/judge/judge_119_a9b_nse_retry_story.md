# Judge 119: A9b story text, NSE downloads: one retry policy and a named failure everywhere: `story/a9b-nse-retry` ad0c9aee768b29ebc210fd24365ca1ec6a9ccd56 (quality rule 1, text only)

**Number note.** A9b has no response file yet, so I used 119, the next free judge number. The orchestrator may
renumber it if 119 is reserved.

**What I checked:**
- the A9b section, the only change;
- the inventory against the code on `main` today: every `NseArchiveSource` subclass, every NSE fetcher outside it,
  every place that catches `HTTPError`;
- the pacer (`fno/http_pacing.py`), `PublicData` (`fno/providers/public.py`) and its callers, and the filings
  librarian;
- the five questions the orchestrator asked.

## The orchestrator's questions

**(a) Is the 22-class inventory complete? Yes.**
- **Subclasses.** An AST walk over `fno/`, `research/` and `tools/` finds exactly **22 transitive subclasses** of
  `NseArchiveSource`, in four files: `fno/filings/sources.py` 4, `fno/storage/raw_source.py` 7,
  `fno/storage/snapshot_source.py` 10, and `fno/vix_history/source.py` 1. NSDL's `NsdlFpiDailySource` and
  `NsdlFpiDailyBySessionSource` are among the 10.
- **NSE fetchers outside the class.** Only `fno/providers/public.py` (PublicData, out of scope) and
  `tools/nse_raw_download` (out). `fno/http_pacing.py` holds only host names.
- **A14** reads its SPAN files from Drive (`nse_margins/wiring.py:33`), so its NSE path is `data-librarian`, which the
  table already covers.
- **`HTTPError` catches** around an NSE fetch exist only at `fno/filings/librarian.py:128` and `:151`. The table's
  `filings archive` row covers both. The other catches (`drive_check.py`, `drive_session.py`) are Drive's.

**(b) The `check-once` alert: proof that it fires, and no live post in tests?**
- **That it fires: yes.** Criterion 3 requires "`participant-oi check-once` sends its UNREACHABLE alert on a 503", and
  rule 4 (in criterion 6) requires a broken-code proof per criterion. So a test must fail when the alert is not sent.
- **No live post: not stated.** In practice it cannot happen. The suite-wide fixture of judge 86 deletes
  `FNO_SLACK_BOT_TOKEN` and the other credentials for every test, with a guard against a silent sender.
- Minor 1 asks for the guarantee to be written into the criterion.

**(c) A reason for the 120 s Retry-After cap? Partly.**
- The text gives the purpose: "rather than block a run; the next scheduled run tries again".
- It gives no reason for the number 120 and no evidence label.
- Minor 2.

**(d) Does excluding PublicData leave a traceback? None that I found today.**
- **What `PublicData.nse_json` can raise:** `requests.RequestException`, including `SourceCoolingOff` (`session.get`
  is outside any try); `HTTPError` (`raise_for_status`); or `RuntimeError` (an empty answer).
- **Its two callers both catch these:**
  - The quotes recorder's `NseLevelSource` catches `Exception` per field and records it (`fno/quotes/market_levels.py`
    lines 82 and 86).
  - The A12 filing indexes are caught by the librarian's `LIST_ERRORS` (`requests.RequestException`, `RuntimeError`,
    `ValueError`, `KeyError`, `TypeError`, `librarian.py:38`).
- So the exclusion is safe today, but only because those callers catch broadly. Minor 3 asks the story to say so,
  naming the two callers, so a later caller of `PublicData` is not assumed covered by A9b.

**(e) The README correction as a criterion? Yes.**
- Criterion 5: "the participant-OI README line corrected".
- Scope 4 names the file and line (`research/data/participant_oi/README.md:54`).

## The policy itself (checked against the pacer)

- **403 and 429 together.** The pacer counts both as refusals (`REFUSAL_STATUS_CODES = (403, 429)`) and pauses a host
  after 2 in a row for 15 minutes. So the story's "a 429 gets one retry in practice" is right: the second 429 pauses
  the host, and the next try meets `SourceCoolingOff`.
- **403 raised at once as `RawFileRefused`** is right. The pacer's comment says NSE "can refuse once until its cookies
  are set", so a single 403 on one file must not stop a whole archive run. A12 goes on to the next company, and a
  second 403 pauses the host and stops the run politely.
- **`SourceCoolingOff`.** Not retrying it is right: today `_response` retries it, which sleeps 65 s into a paused host
  for nothing.
- **Successful paths unchanged** (criterion 4: one request, same bytes and `Last-Modified`, plus one real download
  against its manifest SHA-256).
- **No partial raw file:** kept and stated.

## Minor (text, non-blocking)

1. **Criterion 3, `check-once`:** add "with a fake alert sender; no test posts to Slack (judge 86's fixture)". Then the
   alert proof and the no-live-post guarantee are both in the criterion.
2. **The 120 s cap:** add a reason and label. For example: "reasoning only: a wait longer than 2 minutes is a block,
   not a hiccup. The pacer's own pause is 15 minutes, and the next scheduled run is the right retry". Also say that the
   worst case, 3 x 120 s per file, matters for long runs (A12's deadline-bound backfill).
3. **The `PublicData` out-of-scope line:** say why it is safe today. Its two callers, the quotes recorder's
   `NseLevelSource` and the A12 filing indexes, catch every exception it can raise. Say also that any new `PublicData`
   caller must do the same until `PublicData` is brought under this policy.
4. **A8's measured release time** (owner decision: "the time our 5-minute check first sees the file"). With retries, a
   check that sees a 503 and then a 200 sees the file up to 65 s after it started. Say which time `check-once` records:
   the start of the check, or the time of the successful answer. That keeps the measured release times consistent
   before and after A9b.

## Verdict: PASS for ad0c9aee768b29ebc210fd24365ca1ec6a9ccd56 (story text)

- The inventory is complete by my own search.
- The policy is consistent with the pacer and the owner's politeness rule.
- The caller table covers every NSE path I could find.
- The criteria carry the cases rule 5 asks for: `Retry-After` 120/121, the fourth try, the second 429, the empty 200.

Code may start. Fold the four minors into the code round; I check them there.

## Addendum 1 (15 Oct 2026): A9b code at f90e18bdc2e9251bd274d9a90f36b036800f4444 (merge-base fa58953; claims: `reviews/claude/response_119_a9b-nse-retry.md`)

**Gates, run myself:**
- **Exact SHA:** `env -u FNO_SLACK_BOT_TOKEN python -m pytest -q` 4355 passed; `ruff check fno tests tools` clean;
  `ruff format --check` clean (835 files); `python tools/check_imports.py` clean.
- **Trial merge with origin/main a0b2915:** no conflict; 4604 passed; ruff clean; imports clean.
  - `ruff format --check .` flags one file, `reviews/chatgpt/review_2_...md:98`. It is already flagged on `main` and is
    not in this branch.
- **Network:** a socket-blocking plugin over the 742 NSE-related tests: all passed, no real connection.

**Real download (criterion 4):**
- 9 Oct index close through the new code: SHA-256 equals the manifest (7b2b7c2e…).
- 13 Oct participant-OI `Last-Modified` revision: 875c9cf4…, the recorded A11 revision, the same as the old code.
- So the successful path is unchanged.

**Planted mutations (separate worktree, 11; all caught):**

| # | Mutation | Result |
|---|---|---|
| R1 | 429 refused, not retried | 9 failed |
| R2 | 599 not retried | 1 failed |
| R3 | `Retry-After` 120 stops (cap off by one) | 1 failed |
| R4 | `SourceCoolingOff` retried | 26 failed |
| R5 | a third 429 tried | 1 failed |
| R6 | `Retry-After` ignored | 3 failed |
| R7 | `checked_at` = start of check | 1 failed |
| R8 | legacy log not read | 2 failed |
| R9 | unanswered revision re-read ignored by `market daily` | 1 failed |
| R10 | any failure, not only `RawFileRefused`, kept per company in A12 | 1 failed |
| R11 | 410 treated as not published | 22 failed |

### The orchestrator's points

**(a) A8 v2 log: readers MET, writers PARTLY (should-fix 1).**
- **Readers.** Every reader goes through `ReleaseLog.checks()`, which reads the legacy file, then v2. No frozen file
  names `release_checks.csv` (searched every tracked file outside tests).
- **Writers.**
  - `ReleaseLog` refuses the legacy name for writing.
  - `.gitattributes` has union lines for both v2 files.
  - `participant-oi-watch.yml` `LOG` is v2 and `git add "$LOG"`.
  - O6's `participant-oi-release.yml` adds the whole `actions/` folder.
- **Not covered:** the A8 Claude routine "participant-OI release times". Its prompt as recorded
  (`response_40_...:199`) says: "Commit `research/data/participant_oi/release_checks.csv` and push". O6 runs it side by
  side "until the owner switches" (`participant-oi-release.yml:1-2`).
  - After this merge, that routine writes its rows to `release_checks_v2.csv`.
  - If it still commits only the legacy path, its rows die with the container every evening: lost A8 evidence and no
    error.
  - Neither the story, the response nor the gap list mentions the routine. I cannot read or change scheduled tasks, so I
    cannot verify it either way. Under JUDGE.md, NOT MET.

**(b) `market daily` stops when a revision re-read is unanswered: CONSISTENT with judge 49 and judge 79.**
- "A bad file still stops": an unread re-read is now a named problem (ARCHIVE_INCOMPLETE). R9 is caught.
- Documented in the story and `DATA_SOURCES.md`. The cost is accepted: one NSE hiccup at that step holds that day's
  publication until a re-run.

**(c) The code-reading test can be dodged: YES (minor 1).** It matches exception names written directly in the
`except` of a function that directly calls `fetch`, `fetch_published` or `last_written`. These dodges passed it:
- an alias (`E = requests.HTTPError`);
- a tuple constant (the librarian's own `LIST_ERRORS` pattern);
- a method alias for the read;
- `except Exception`;
- a catch one call up (the librarian's `run` catches `requests.RequestException` around `_company`, rightly for Drive,
  and the test cannot see it).

No offender exists today; my own search agrees. The behaviour itself is pinned by the source tests: R1, R4, R5 and R11
are caught. So the code-reading test is a backstop, not the proof. Minor: name its limits in its docstring, or resolve
module-level aliases and tuples.

**(d) Network in the command tests: MET.**
- The `nse` fixture patches both `wiring.build_nse_source` and `fno.composition.build_nse_source`. That fixes the
  earlier real fetch the builder disclosed.
- My socket-blocking run shows no connection.
- There is no permanent socket guard, so a future name import could leak again. Minor 2: a suite-wide guard like judge
  86's credential fixture.

**(e) Worst case: MET.**
- 65 s of waits, or 3 x 120 s, plus up to four 60 s timeouts per file. Twice that for A12's truncated second
  download.
- Stated in `retry_policy.py`, the story and `DATA_SOURCES.md`, with the reasoning-only label for the 120 s cap.

### Judge 119's text minors

| Minor | Status |
|---|---|
| 1 fake sender, no live post | MET: `FakeSender`; judge 86's fixture |
| 2 120 s reason and label | MET |
| 3 why `PublicData` is safe | MET (story and `DATA_SOURCES.md`) |
| 4 which time `check-once` records | MET: `checked_at` = answer, `started_at` = start; tested with 503 then 200 (19:00:00 / 19:00:05). R7 caught |

### Unclaimed-bug hunt

- **3xx is now `RawFileRefused`.** `session.head` does not follow redirects. Before A9b, a redirect's own
  `Last-Modified` would have been read as the file's (wrong). Now it is a named failure. No NSE redirect was seen in my
  probes. Note only, safer than before.
- **Ordering in the librarian's `run`:** `(SourceCoolingOff, RawSourceUnavailable)` is caught before
  `requests.RequestException`. So an NSE stop is never reported as a Drive stop. Checked.
- **Boundary and empty cases tested by the builder, re-read by me:**
  - `Retry-After` 120 / 121, past, empty, malformed, non-ASCII;
  - the fourth try; the second 429;
  - an empty 200;
  - a zero-byte v2 file;
  - the legacy name refused for writing.

### Findings

**Should-fix 1 (blocking the PASS): the A8 Claude routine's commit path.**
- **Evidence:** `response_40_...:199` (the prompt commits `release_checks.csv` by path) and
  `participant-oi-release.yml:1-2` (the routine still runs). The branch writes v2 only.
- **Expected:**
  - (A) the orchestrator updates the routine's prompt to commit `research/data/participant_oi/` (or
    `release_checks_v2.csv`), effective at the merge; or
  - (B) shows that the routine is retired or already commits the folder.
- **Either way,** record it in the story's gap list and the response, with the routine's prompt line quoted. A
  schedule change is lane 1 for the orchestrator, not for me.

**Minor 1:** the code-reading test's dodges, see (c).

**Minor 2:** no permanent socket guard, see (d).

### Verdict: FAIL for f90e18bdc2e9251bd274d9a90f36b036800f4444 (code)

- **Everything else is met:** the code, the tests, the mutations, the trial merge, the network check, and the real
  download.
- **One should-fix:** the routine. It needs the orchestrator's evidence, not new code.
- **A re-check needs:** the routine's prompt line (or its retirement) and the story or response row recording it. If the
  code is unchanged, I re-run nothing else.

## Addendum 2 (15 Oct 2026): A9b fix round at a19b5b3e8856571b7f6d5000bc878592febd0e45 (f90e18b..a19b5b3, main merged in)

**Gates, run myself:**
- **Exact SHA:** 4611 passed; `ruff check fno tests tools` clean; `ruff format --check fno tests tools` clean (877
  files); imports clean.
- **Trial merge with origin/main a511228 (187195b):** no conflict; 4611 passed; ruff and imports clean.

| Addendum 1 finding | Status | Check |
|---|---|---|
| Should-fix 1: the A8 routine commits the check log by path | **MET (by design, decision 49)** | `release_checks.csv` keeps its name and header (`LOG_FIELDS` unchanged), with `checked_at` = the answer time. Start times go to `release_check_starts.csv` beside it, so a by-path writer loses start times, never a check (`test_a_lost_start_log_loses_start_times_never_evidence`). The watch workflow adds `$LOG $STARTS $REREADS`; O6 adds its whole `actions/` folder. v2 is withdrawn: no `*_v2.csv` in the tree, and `release_checks.csv` is unchanged against main. The gap list records the routine, with an **owner item**: update its prompt or retire it |
| Minor 1: code-reading test dodges | MET | Module-level exception tuples are resolved (the `tuple.py` plant is found; `proper.py` and the source's own `RawSourceCoolingOff` pass). The docstring names what it still cannot see: an imported alias, a tuple built in a function, a method alias, `except Exception`, one call up |
| Minor 2: no permanent network guard | MET | `tests/conftest.py` `no_real_network` (autouse): `connect` and `connect_ex` allow loopback and Unix sockets only, block the proxy's own `(host, port)`, and remove the proxy settings. It raises `RealNetworkBlocked` (not an `OSError`, so nothing retries it). The subprocess limit is stated |

**The orchestrator's four questions:**

1. **Is the join on (day, checked_at) unique? YES in practice.**
   - `checked_at` is `now_ist()` with microseconds. The real rows confirm it: `2026-10-13T06:06:28.088401+05:30`.
   - Each side log has one writer: the root pair is the watch job's; `actions/` is O6's. The routine writes the root
     check log, but its start rows are never committed.
   - Two checks in one process are sequential, with an NSE call between them, so "same second" is not "same key".
   - The existing logs have 0 duplicate (day, checked_at) keys (root and `actions/`).
   - A clash would keep the last start row silently. That needs two identical microsecond times on one day: not
     reachable. Note only.
2. **Does every reader ignore a missing start row? YES.**
   - `checks()` uses `started.get(...)`, which gives `None`.
   - No code outside `release_times.py` reads the release log's `started_at` (searched `fno/`, `research/`, `tools/`).
     `first_seen_times`, `last_written_times` and the rule read `checked_at` only.
   - Tested: rows before A9b, and a deleted side log.
3. **Can the side log's union merge duplicate rows? NO harm either way.**
   - Tried myself on a scratch repository: both sides add the same row and one adds another → one copy of each.
   - Even an identical duplicate maps to the same start time.
   - Different rows from different checks cannot share a key (question 1).
4. **Does the guard block a legitimate local server? NO.**
   - `test_a_local_server_still_answers` binds 127.0.0.1:0.
   - The full suite passes with the guard on (4611), Postgres fixture included.
   - Only the proxy's exact `(host, port)` is blocked on loopback. A test server cannot hold that port while the proxy
     does.

**Planted mutations (separate worktree, 9 of 9 caught):**

| # | Mutation | Result |
|---|---|---|
| M1 | join key without `day` | 7 failed |
| M2 | start row never written | 8 failed |
| M3 | a missing start row raises | 6 failed |
| M4 | the proxy on loopback allowed | 1 failed |
| M5 | `connect_ex` unguarded | 2 failed |
| M5b | proxy settings kept | 1 failed |
| M6 | tuple constants ignored | 1 failed |
| M7 | workflow drops `$STARTS` | 1 failed |
| M9 | header check off on append | 1 failed |

My first M5b plant matched twice and was not applied, so I re-planted it with a unique context.

**Notes (non-blocking, nothing to fix now):**
1. The guard matches the proxy by the address it is set as. A proxy set as `localhost:port` would be reached as
   `127.0.0.1`, which is not matched. Today it is set as 127.0.0.1, and the settings are removed anyway, so no library
   routes through it.
2. `test_requests_to_nse_fail_loudly...` needs DNS: `requests` resolves the name before `connect`. Where DNS is down
   it would fail with a `ConnectionError`, not the guard's error. Both this container and GitHub Actions resolve. DNS
   lookups themselves are not blocked: a name leaks, but no connection is made.
3. The builder disclosed one raw TCP connect during a guard-off mutation run, which failed. It is expected for that
   run and not reproducible with the guard on.

### Verdict: PASS for a19b5b3e8856571b7f6d5000bc878592febd0e45

- No blocking or should-fix finding is left.
- The owner item (the routine's prompt or its retirement) is recorded in the story and is not needed for correctness:
  only the routine's start times are lost, never a check.
- Merge check to follow.

## Addendum 3 (15 Oct 2026): merge check, 16661ec9167ecc917ef0b165fb8b22ef457c2e7a

| Check | Result |
|---|---|
| Recomputed merge equals the merge commit | **MET**: `git merge-tree --write-tree cac5f13 a19b5b3` gives tree b29c21ec…, the same as 16661ec's tree. Parents cac5f13 and a19b5b3, the SHA I passed |
| Branch files identical | **MET**: `a19b5b3..16661ec` differs only in four review files changed on `main` after the branch (`response_113`, `judge_118`, `judge_119`, `reviews/judge/README.md`). No code, test, workflow or data file differs |
| CI on `main` | **MET**: `checks` run 38691471905 on 16661ec, success. The later runs on d89947f and 6320f0b also succeeded |
| Rule 8 | Recorded by the orchestrator in `conversations/2026-10-15.md`: `data-fingerprints index-close` 14 Oct, "identical" to Drive, exit 0. My own real-download check is in addendum 1 |

**A9b is done.** The owner item stays open: update the A8 routine's prompt, or retire it.
