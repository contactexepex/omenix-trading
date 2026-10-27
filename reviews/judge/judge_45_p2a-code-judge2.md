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

## Addendum 1: the corrected SHA 9f794fe (still FAIL, round 1: S1 and S2 open)

The orchestrator replaced `8a3a45c` with `9f794fe6...` (branch `story/P2a-news-fetch-r2`). It adds detection of a
feed-list version edited in place: each poll row now records the SHA-256 of the feed-list file used. On the next run,
a used version whose hash changed is skipped, the next older good one is used, `feed_list_damaged` is counted and
alerted, and if every version is damaged the run stops.

**Gates** (`__pycache__` cleared): 621 passed; ruff, format, imports and size clean.

**The new field is safe for privacy.** `feed_list_sha256` is `sha256(file bytes)`, a 64-character hex digest of the
whole JSON file, so it cannot carry the query or the URL. Inverting it would mean guessing the file byte for byte
(key order, spacing, every id and URL), which is out of reach for any real list. At most, a one-feed list in a
predictable format could be confirmed by a guess, the same class as the accepted article-id residual (reasoning
only). Plant H1 (the file's text written in place of the digest) fails 2 tests, the privacy test among them, so the
master test still catches a marker with the field present.

**New plants:** H2 (the edit-in-place check removed) 3 failed; H3 (a damaged version not counted, so the run reads
clean) 2 failed.

**Still open:**
- **S1:** N8, the wiring's store moved to `AreaStore(drive, "raw")`, still passes all 621.
- **S2:** no test through the real pacer and pause log.

**Notes on the new logic (not blocking):**
1. **The note-2 hole now covers both guarantees.** A version's hash, like its number, is recorded only on a `fetched`
   row. A version used only in runs where every poll was unchanged or blocked has no row, so it can later be edited
   in place, or rolled back below, without detection. Record the version and hash once per run (for example a run
   row), or accept this in writing.
2. **The fallback can go below the highest version used.** If the newest used version is edited in place, the code
   falls back to an older one, even below `lowest_version`. That is a rollback the guard otherwise refuses. It is
   alerted and not clean, and it seems intended ("the next older good one"). Say it in the story.
3. **Asymmetry:** a used version edited in place falls back to the last good version, but a new, never-used invalid
   version still **halts** the run (`parse_feed_list` raises). If the agreed rule is "damaged newest -> last good +
   alert", it should cover an invalid new version too. My judge 45 note 1 recommends it (reasoning only).

**Verdict: FAIL** (round 1, on 9f794fe): S1 and S2, tests only.

## Addendum 2: where else the privacy test rests on fakes (9f794fe), and S3

The orchestrator asked whether the master test is vacuous anywhere beyond judge #1's F1 (DEBUG capture with a fake
session) and F3 (the pause log, which is my S2). The fakes in `test_privacy.py`:

| Fake | What it hides | Matters? |
|---|---|---|
| `Session` (scripted) | urllib3, the real `NewsSession` and the real pacer | yes: F1 and S2 |
| `LocalFolderStore` for Drive | the real Drive client's errors | no for the fetcher (`_stage` catches all and keeps a code); `PrivateFeedLists.latest` does not catch Drive errors, but those name Drive file names and ids, not feed content |
| the alert sender | the real Slack sender | no: the alert text is the counts line |
| the commit message | built by the workflow (fixed text and a date), not by the code | no; it is pinned by the workflow file |

**S3 (should fix, code plus test): one bad feed entry crashes the whole run, and the crash path is unguarded.** The
feed-list check accepts any `https://` URL with a host. `https://a..b/rss?q=...` passes it (`hostname` is `a..b`). On
`9f794fe`, run through the real `NewsSession`, the fetcher then raises `UnicodeEncodeError` (from IDNA encoding),
which is not a `requests.RequestException`, so it escapes `_poll` and `cmd_news_fetch`. Reproduced, with a scratch
script (not committed):
- the remaining feeds are not fetched;
- no #fno-desk alert is sent (the command catches only `FeedListError`);
- a traceback goes to the public Actions log.

This message held no query ("label empty"), but nothing guarantees that for every error a library may raise. Fix:
- `_poll` keeps a code for any exception (class name only), as the close read does;
- `cmd_news_fetch` catches everything else, prints a fixed line and alerts;
- the feed-list check rejects a host that will not IDNA-encode.

Test it with a feed whose request raises a non-`RequestException` carrying the marker URL.

**Verdict unchanged: FAIL** (round 1, 9f794fe), with S1, S2 and now S3.

## Addendum 3: decisive round 2, f5a656b (PASS)

Branch `story/P2a-news-fetch-r3`, SHA `f5a656ba9e26d3037796f7aa9ddf2172df08413f`.

**Gates** (`__pycache__` cleared): 637 passed; ruff check and format clean; imports clean; code size passed. Six more
full parallel runs: 637 passed every time.

**My findings, each with its plant on f5a656b:**

| Item | Fix | Plant | Failed |
|---|---|---|---|
| S1 the fetcher cannot reach the Record | wiring test: every write under `staging/news/` | the store moved to `"raw"` | 1 |
| S2 / judge #1 F3 the host in the pause log | `NEWS_PACER`, the news session's own pacer, never attached to the pause log or the alerts; real-session tests; a control shows the shared pacer **does** write the host and alert, so the test is not vacuous | the news session back on the shared pacer | 2 |
| judge #1 F1 urllib3 at DEBUG | `urllib3` held at WARNING; a real-session test at DEBUG | the level line removed | 1 |
| S3 a non-request error escapes | `_poll` keeps a code for any exception; the command catches everything with a fixed line and an alert; hosts must IDNA-encode | narrow `except` / the command's catch narrowed / the message printed / no IDNA check | 1 / 1 / 1 / 1 |
| The salt | at least 16 characters, required, in the private list; the committed hash depends on it; tests that it is stable and in no committed file | a fixed salt / the URLs written into the committed log | 4 / 4 |
| Note 2 version and hash per run | `feed_lists.csv`, one row per version, written before the first request | the per-run row removed | 6 |
| Earlier plants | cookies, redirects, workflow add scope, row after staging | `set_ok` True / redirects / `git add -A` / row first | 1 / 1 / 1 / 2 |

The `return_ok` survivor stays equivalent, for the reason in the first report.

**The three timing tests made deterministic: I checked they are not weaker.** These are
`test_rate_limit.py::test_spacing_holds_across_threads` (the shared library) and two characterization tests (the
intraday `RatePacer`, and `NsePacer` spacing). Each now freezes the clock and asserts the waits the limiter hands
out, instead of timing threads after they wake.
- **Spacing removed** (`max(now, self._last)`): all three fail.
- **Lock removed** in `RateLimit.acquire`: the shared-library test fails in 3 of 3 runs. It keeps its `slow_decide`
  hook, which forces threads to interleave. The two characterization tests pass.
- I ran the **old** versions (on `9f794fe`) against the same lock-removed plant 5 times. The NSE characterization test
  caught it once in 5, and the shared-library test 5 in 5. So the old characterization tests caught a missing lock
  only by chance. The new ones lose nothing real, and the shared-library test pins the lock every time.
- Optional: give the two characterization tests the same `slow_decide` hook so each pins the lock too.

**Verdict: PASS** (lane 1, code round 2, judge #2).
