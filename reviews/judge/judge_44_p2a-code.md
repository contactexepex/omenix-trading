# Judge 44: P2a code (news fetch into Staging), judge #1

**SHA:** `8a3a45c5787ba39443a3c73be95dbc60bbc30c91` (`story/P2a-news-fetch`, base f0f20e3). Lane 1 (a new outside
source, Drive writes, the privacy rule).
**Verdict: FAIL, round 1 of 2.** The fetcher is well built and fails closed. Two privacy claims are not proven by the
test that claims them, and the story describes the feed-list read wrongly.

## Gates

- Suite: 617 passed, 2 runs out of 2.
- ruff, imports (412 files) and size: clean.
- `git diff f0f20e3 8a3a45c -- fno/shared` is empty, so NSE's and Yahoo's `PacedSession` are untouched.
- The two disclosed count bumps (pinned installs, cli) are new-file counts only.

## Confirmed (strong evidence: code read, plants run)

**Staging only.** `wiring.py` gives the fetcher `AreaStore(drive, STAGING_AREA)`. The feed id that forms the path is
validated as `feed-\d{2,3}`, so no path can climb out of `staging/`.

**File first.** The poll-log row is written only after `stage()` returned True. A plant that writes the row first is
caught.

**Session.** `RejectAllCookies` and `allow_redirects=False` are set in `NewsSession` only. A redirect, or a 200 with no
feed root, is `block_page`; 403/429 is `refused`. Both stop the host for the run, as does `host_paused`.

**Feed list.** Newest by number (`int(...)`), anti-rollback against the poll log, `https://` only, opaque ids, 1 to 50
feeds, and `FeedEntry.url` with `repr=False`. Every error is a fixed code.

**Workflow.** `workflow_dispatch` only, a fixed commit message with a date, and only the poll log is added, plus the
pause-log step.

**Plants, all caught:**

| Plant | Result |
|---|---|
| Log row written before staging | caught |
| Cookies accepted | caught |
| Redirects followed | caught |
| A non-feed 200 accepted | caught |
| No host stop | caught |
| No rollback check | caught |
| Exception text in the fetch code | caught |
| Exception text in the stage code | caught |
| `url` repr on | caught |
| `http://` allowed | caught |

## Required to PASS

### F1. The DEBUG part of the privacy test is vacuous: no real request runs through it

Strong evidence: experiment.

`test_no_marker_reaches_anything_committed_or_public_on_any_path` sets `caplog` to DEBUG but uses a fake `Session`. urllib3
never runs, so the surface R2-3 named is not exercised. I ran `NewsSession().get` against a local `http.server`:
- With default logging (production: no handler, urllib3 level 30), nothing is emitted.
- With the root at DEBUG and a handler attached, urllib3's log **contains the query** (`MARKQ`).

So the safety rests on nobody ever enabling DEBUG, and no test pins that.

Fix:
- The news command sets the `urllib3` logger to WARNING or higher itself.
- The privacy test's good-poll and error paths go through the real `NewsSession` against a local server, with
  DEBUG captured, and assert no marker.

A plant that removes the level pin must fail.

### F2. The story describes the feed-list read wrongly

Strong evidence: code read.

The story says the choice gives "one read path, **no unverified 'config' path**". The code reads the feed list
directly from Drive, `PrivateFeedLists(AreaStore(build_owner_drive(env), "config"))`, with no receipt and no verified
cache. Reading it unverified is a reasonable choice, because it avoids the `DAMAGED` stop I raised in judge_42.

But it means an in-place edit of `feeds-v3.json` is used silently, and the poll log's `feed_list_version` then no longer
identifies what was fetched.

Fix:
- Correct the text: the feed list is read directly, not through the cache.
- Recommended: add a short SHA-256 prefix of the list to the poll row, so an in-place edit is visible. It is a hash of a
  JSON of several URLs, so it cannot practically be reversed.

### F3. The pause log can commit a feed's host publicly; the test claims host coverage but skips that path

Strong evidence: code read.

`attach_pause_memory` (`cli.py:177`) attaches the committed pause log to `SHARED_PACER` for every command, news
included. `TransitionLog.FIELDS` includes `source`, which is the host. `news-fetch.yml` ends with
`ops/commit_pause_log.sh`. So a 403 or 429 from a feed host writes that host to
`research/data/resilience/paced-hosts.csv` and commits it.

The privacy test plants a host marker (`third-host-zz46.example`) but, through the fake session, never reaches the
pacer. For Google News the host is already public (the design names it). For publisher feeds later, the committed log
would show which publishers the owner reads.

Fix, one of:
- The design states that hosts are not private, and the host is dropped from the marker list.
- Or news hosts are kept out of the committed pause log, tested with a 403 through the real pacer.

This is the owner's choice. It must not be left implicit.

## For the orchestrator: the feed-list fallback

The code **stops** on a missing, invalid or rolled-back newest version (`job.py` raises `FeedListError`; the CLI alerts
and exits 1). The agreed behaviour was "fall back to the last good version and alert". With the direct read (F2) an
"edited, damaged" file does not arise, but an *invalid* new version stops all news until it is fixed.

The story's "a bad version leaves the previous one in place" reads as a fallback; the code does not do that. Both are
fail-closed and safe.

My recommendation: fall back to the newest **valid** version at or above the highest one used, and alert with
`feed_list_invalid`. That keeps data flowing, is about 5 lines plus a test, and matches what was agreed. Whichever you
choose, the story must say it exactly and a test must pin it.

## Hard lines

No orders. No secrets: the Drive sign-in is through the existing owner settings and nothing is printed. No live call:
everything is offline (a local server only in my probe). Nothing reaches the Record. The poll log is the only
committed file.

## Addendum 1: SHA corrected to 9f794fe: FAIL stands; the feed-list behaviour is now right

The orchestrator corrected the SHA to `9f794fe27475aeb5967417aff147bb4254b58bad` (`story/P2a-news-fetch-r2`), which is
8a3a45c plus one commit. Gates: 621 passed.

**The agreed edit-in-place behaviour now holds (strong evidence: code read, plants).**
- Each poll row logs the SHA-256 of the feed-list file it used.
- On a later run, a used version whose file hash differs is skipped. The next older good version is used, and the
  report counts `feed_list_damaged`, so the run is not clean and is alerted, never silent.
- If every version is damaged, the run stops before any request.

| Plant | Result |
|---|---|
| Damaged check off | caught |
| Damaged not reported | caught |
| List hash not logged | caught |

Two edges, not blocking:
- A version used only in runs that fetched nothing (all unchanged or failed) has no row. A later edit of it is not
  detected.
- A *new, malformed* version still stops all news (`feed_list_invalid`): only *edited* versions fall back. That matches
  the orchestrator's locked rule, which covered edited versions only. My earlier recommendation to fall back for an
  invalid new version too is the orchestrator's call.

**New, introduced by this commit (privacy, small): the full list hash can confirm a guess.**

`feed_list_sha256` is the SHA-256 of the whole JSON file, committed in every poll row. I said in F2 that such a hash
"cannot practically be reversed". That holds only when the file holds enough that cannot be guessed. A one-feed list
in standard `json.dumps` form, such as `{"feeds": [{"id": "feed-01", "url": "https://news.google.com/rss/search?q=NIFTY"}]}`,
can be confirmed by anyone who hashes candidate queries. That reveals the research intent invariant 1 protects. I
correct my earlier statement.

Fix (about 3 lines plus a test): the list format carries a required random `salt` field (at least 16 characters),
and `parse_feed_list` rejects a list without one, so the hash cannot be guessed. Alternatively, log an HMAC keyed by a
value stored only in Drive.

**Still open from round 1, unchanged at 9f794fe:**
- **F1:** the privacy test still uses the fake session, so urllib3 never runs. There is no `urllib3` level pin in
  `fno/ingestion/news`. My local-server probe still shows the query in urllib3's DEBUG log.
- **F2 (text):** story line 186 still says "no unverified 'config' path". The feed list is read directly from Drive.
  The added hash check makes that direct read safe, so say so.
- **F3:** a news host can still be committed through the pause log (`TransitionLog` `source`, and `commit_pause_log.sh`
  in `news-fetch.yml`). The owner's choice is still pending.

**Verdict at 9f794fe: FAIL.** F1, F2 and F3 remain, plus the salt item. The orchestrator rules on round counting.

## Addendum 2: round 2 (decisive), f5a656b: PASS

Reviewed `f5a656ba9e26d3037796f7aa9ddf2172df08413f` (`story/P2a-news-fetch-r3`). That is the whole delta from 9f794fe:
- the `fno/ingestion/news/` changes in b0a8549, f7b87b1, 70ae53e and 7541d3b;
- e22b1bf and f5a656b, which change tests only.

`git diff f0f20e3 f5a656b -- fno/shared` is still empty.

**Gates:**
- Suite: 637 passed, 5 runs out of 5, no flake.
- ruff and imports (414 files): clean.
- Size: 3 passed.

**Round-1 items, each closed (strong evidence: code read and a plant per item):**

| Item | How it is closed | Plant |
|---|---|---|
| F1 | `NewsSession` pins `urllib3` at WARNING, and `test_real_session.py` runs the real session on a local server. | Removing the pin is caught. |
| F2 | The story now says the list is "read directly from Drive with no receipt", and integrity comes from the hash logged at first use. | n/a (text) |
| F3 | `NEWS_PACER = NsePacer()` is never attached to the committed log or alerts. An unknown host still gets 1.0 s spacing and the NSE breaker, so it is as strict as NSE. | Using the shared pacer is caught by the real-pacer host test. |
| Salt | `salt` is required, at least 16 characters, and is in the private file only. | Not requiring it is caught. |
| Version per run | `note_feed_list` writes a version row before the first request, so a run with no new bytes still records the version. | Removing it is caught (4 tests). |
| Catch-all | The command prints the class name only, never a traceback. | Narrowing the catch-all is caught. |

Judge #2's S1, S2 and S3 are in the same commits.

**The thread tests for the merged resilience layer** (`test_groww_and_close_read_behaviour.py`,
`test_pacer_and_public_behaviour.py`, `test_rate_limit.py`): the edit is sound, and it weakens no behaviour coverage.

- **(1) Faithful.** On a frozen clock each caller reserves `max(now, last + spacing)` and sleeps the difference. N callers
  must therefore ask for N−1 distinct waits of 0.05, 0.10, and so on: the first goes free and none share a slot. That is
  the same property the old test approximated with wall-clock gaps, now without scheduler jitter.
- **(2) It still bites:**

  | Plant | Result |
  |---|---|
  | `RateLimit` lock removed | caught (the `slow_decide` test) |
  | `RateLimit` sleep removed | caught (3) |
  | Spacing ignored | caught (3) |
  | The `NsePacer` per-host creation race | caught by the frozen-clock `NsePacer` test |

  The race plant has the lock off plus a 20 ms gap, which gives two limiters for one host.
- **(3) No retroactive weakening.** Only the timing source changed, and each assertion is stricter: exact waits instead
  of a gap of at least 0.04 s or 0.03 s. One honest limit: without `slow_decide`, the two characterization tests do not
  force a lock race on their own. The old wall-clock versions only caught it by chance too, and the shared-library test
  forces it deterministically, so nothing is lost.

**Verdict: PASS (strong evidence: gates, the delta read, 13 plants all caught).** Two non-blocking notes carry over
from Addendum 1:
- a new malformed version stops the run, by ruling;
- the salt's randomness is the owner's to keep, because the code checks only its length.
