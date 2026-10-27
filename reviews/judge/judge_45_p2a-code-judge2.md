# Judge 45: P2a news fetch into Staging, code (judge #2)

Branch `story/P2a-news-fetch`, SHA `8a3a45c5787ba39443a3c73be95dbc60bbc30c91`, lane 1. **FAIL** (round 1) on 2
should-fix, both tests only. The code meets the design. Two guarantees the orchestrator listed are not pinned by
any test.

## Gates (`__pycache__` cleared)

617 passed; ruff check and format clean; imports clean; code size passed (the largest news module is 79 lines).

## The orchestrator's checks

| Check | Finding |
|---|---|
| 1. Privacy | The master test runs the marker URL, query, host and headline through a request error that quotes the URL, a block page that quotes the headline and URL, and a good poll. Logging is captured at DEBUG. It asserts that no marker appears in the poll log, the output, the alerts, the logs or the staging names, and that the headline **is** in the Drive raw bytes. A tree scan rejects `news.google.com`, `rss/search` and `q=` in `fno/`, `config.yaml` and `.github/`. My plants N6 (print the exception), N6c (log the URL), N9 (host in the staging path) and N10 (re-raise a Drive error) all fail it. N6b (log the whole `FeedEntry`) leaks nothing because `url` has `repr=False`, which is the protection working. **Gap: S2.** |
| 2. Staging only | The poll-log row is written only after `stage` returns True: N5 (a row for an unchanged poll) fails 1 test, N11 (row before staging) fails 3. **But N8, the wiring's store moved to the Record area (`AreaStore(drive, "raw")`), survives: S1.** |
| 3. Cookies, redirects | `NewsSession` sets a reject-all policy and forces `allow_redirects=False`; NSE's and Yahoo's sessions are unchanged. The cookie test uses a real local HTTP server, and its control is valid: an ordinary `requests.Session` on the same server does send `consent=yes`, which `server.seen[1]` checks, so the test can see a cookie. N1 (`set_ok` True) and N2 (redirects followed) each fail 1. |
| 4. Feed list | Write-once versions, the newest by number; an older-than-used version stops the run (N7: 2 failed); the version is read back from the poll log (N12: 2 failed). See note 1. |
| 5. The surviving plant | **Equivalent, confirmed.** `return_ok` True with `set_ok` False sends nothing. requests builds the `Cookie` header from a merged jar (`merge_cookies(RequestsCookieJar(), self.cookies)`, default policy), so the session jar's `return_ok` is not consulted when sending. Only `set_ok` decides, and it stores nothing. Nothing in the code sets a cookie by hand. |

Other plants: N3 (no feed-root check) 3 failed; N4 (no host stop) 1; N13 (a cron added) 1. **N14 (the workflow's
`git add "$POLLS"` changed to `git add -A`) survives**, which is low risk (note 3).

## Findings

1. **S1 (should fix, tests only): "the fetcher cannot reach the Record" is not pinned.** `news/wiring.py` builds
   `StagingArea(AreaStore(drive, STAGING_AREA))`. Replacing `STAGING_AREA` with `"raw"` (the Record) leaves all 617
   tests green. That would put raw polls into the write-once Record with no gate. Fix: a wiring test that the
   fetcher's store is the `staging` area, as the P1 tests pin their own wiring, or a check that nothing in
   `fno/ingestion/news/` names the Record area.
2. **S2 (should fix, tests only): the master test does not cover the pause log or the breaker's alert, and it never
   uses the real pacer.** In production every news request goes through `PacedSession` and `SHARED_PACER`. When a
   host opens, the breaker writes `paced:<host>` to the committed pause log (`ops/commit_pause_log.sh`) and alerts
   with the host name. The test treats the host as private (`MARK_HOST`), but its fake `Session` never touches the
   pacer.
   - Today this path is not reached: the fetcher stops a host after its first refusal (`HOST_STOPS`), and the paced
     breaker opens only at 2 (`settings.py:34`). That is some evidence, from reading the code, not a test.
   - It rests on two settings in two files. Pin it: a test with a real `NewsSession` on an `NsePacer` with a
     `TransitionLog` on a temp file, two feeds on the marker host each answering 429. Assert no marker in the
     transition rows and the breaker alerts.
   - Or, if feed hosts are to be public (they reveal which publishers the owner reads, not the queries), the design
     should say so and the marker should drop the host.

## Notes (not blocking)

1. **A damaged newest feed list stops the run; it does not fall back.** An invalid newest version raises
   `feed_list_invalid` and the run stops. The story says "a bad version leaves the previous one in place", meaning
   the file is not replaced, not that it is used.
   - The orchestrator mentions a locked rule "damaged newest -> last-good + alert, never halt". I find no such rule
     in the repository (`git grep -i "last-good\|last good"` on `main`, in docs, reviews and conversations: nothing).
     If it was agreed, it is not written down.
   - My view, reasoning only: use the newest valid version that is not older than the highest used, plus an alert.
     That keeps fetching (no gap in the news) and keeps the anti-rollback rule, since an invalid version is never
     "used". Halting is the more cautious choice while there is no cron. This is for the orchestrator or the owner.
2. **The anti-rollback guard has a hole:** the version used is recorded only on a `fetched` poll row. A run whose polls
   were all `unchanged` or blocked leaves no record that it used version N, so a later rollback to N-1 passes. Either
   record the version per run, or accept it in writing.
3. **The workflow's add scope is not pinned (N14).** `git add -A` would also commit `fetch.log` (counts only) and any
   stray file. Add a workflow test that the commit step adds only `$POLLS`.

**Verdict: FAIL** (round 1). S1 and S2 are tests only; the code is sound.
