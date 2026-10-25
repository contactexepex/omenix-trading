# Judge 101: T1 daily trade card v1: `story/t1-daily-card` 3e705bf7ece247d31e4d1251c4ce10b7b30f0a98 (lane 1, response 101)

Fresh judge session for orchestrator session_01VG1RqxLFUVdvvPuMRYZtDH; no shared context with the builder.

**What I did:**
- read the story text at this SHA, design 04 sections 4.1 and 4.4, 6.5, REPLAN's T1 paragraph, response 101 and every
  new file under `fno/cards/`, plus the `fno/alerts/sender.py` and `fno/constants.py` diffs;
- ran the gates on the exact SHA and on a trial merge with `origin/main` (ecf66f4, which includes the quality rules);
- checked the live test post **read-only**: the Slack message, the Drive record and the committed delivery file;
- ran the real CLI in dry runs, and with `--post` with no token and no Drive, in a scratch worktree I never pushed;
- planted 16 code mutations and 8 data scenarios of my own;
- checked positive, negative, boundary and empty cases per criterion, as the owner's quality rule 5 asks.

## Gates

- **Exact SHA:** full history, Slack token unset: **3,253 passed**. `ruff check`, `ruff format --check` (730 files) and
  `check_imports` (740 files) are clean.
- **Trial merge with `origin/main` ecf66f4:** merges cleanly; 3,253 passed; ruff, format and imports clean.
- **Sizes:** the largest new file is `tests/cards/test_issue.py`, 224 lines; the largest module is about 120 lines.
- **Frozen files:** no frozen file changed. `fno/constants.py` is hashed only in experiment 1's finished freeze, which
  has changed since by design (judge 53).

## The live test post (criterion 16a), checked read-only

| Witness | My check |
|---|---|
| Slack | #fno-desk message at ts **1792025414.919329**, by the F&O bot, equals the stored `ts`. First line "TEST — PAPER ONLY: a one-off check of live delivery, not the day's card." |
| Card hash | I re-ran the e5dcf69 dry run for 15 Oct and prefixed the TEST banner. Its SHA-256 is **995fdaa6...86f73c7**, equal to the stored `card_sha256`, and the Slack text matches line for line |
| Drive | `cards/2026/10/2026-10-15_1792025414919329_test.json`: 7,323 bytes, `test: true`. The SHA-256 of its `text` equals `card_sha256`, and every fact equals the committed delivery file |
| Delivery file | `research/cards/deliveries/2026/2026-10-15-a1.json`: no card line (0 matches for PAPER ONLY, Status:, a question line), no token. GitHub clock `skew_seconds: null`, with no reason stored (the `line` key arrived after e5dcf69) |
| Point in time of that post | It used `scores/2026-10-15.json`, a same-day report. The builder discloses this; the code now uses the latest report dated before the day (my T2 mutation caught) |
| Half (b), GitHub's push receipt | Due at the merge check, as the criterion says |

## Per criterion

| # | Criterion | Builder's claim | My own evidence (positive / negative / boundary / empty) | Result |
|---|---|---|---|---|
| 1 | PAPER ONLY first line; no order instruction | `render.py:11` | Real dry run, line 1 "PAPER ONLY. ... Information, no action.". My T8 (drop it) caught. No "order" anywhere on the card | MET |
| 2 | NO TRADE with reason codes | `status.py`, `card.py:78` | **Positive:** real repository, header-only registry: `no_approved_strategy`, "Paper trades so far: 0". **Negative:** a committed `paper` row gives `trade_fields_not_built` naming `nifty_condor-v1`, still NO TRADE. A bad status row gives `data_check_failed` naming `PlaybookError`. A removed account gives `data_check_failed`, "at least 0 (book2_hybrid unknown)". **Empty:** no registry gives `data_check_failed`. My T4 caught | MET |
| 3 | Weather "not yet scored", no colour word | `weather.py:10` | Present on every card I made; no GREEN, AMBER or RED | MET |
| 4 | House forecast per question, labelled fallback, back-fill vs live, point in time, missing named | `forecasts.py`, `track_record.py` | **Positive:** q1 0.59, bin 0.5-0.6 on 175 days, 57%, Brier 0.245 over 669; q5 0.69, 0.6-0.7 on 118 days, 84%, 0.217 over 630. I recomputed these from `scores/2026-10-13.json`'s `close_proxy` mode and the capture's `baseline_b_base_rate` rows: equal. **Point in time:** the report used is 2026-10-13 for a 15 Oct card (T2 caught), and a future capture or report is never used (T3 caught). **Late capture** named (19:27 IST). **Empty:** an empty capture names all five missing past-average rows; no capture gives "Forecasts: none on record yet". T11 (all forecasters as house) caught | MET |
| 5 | Committed records only; footer hashes = committed bytes | `committed.py` | All 7 footer hashes equal `git show HEAD:<path> \| sha256sum`. Appending to the capture and corrupting `registry.csv` in the working tree leaves the card byte-identical. **But my T12 mutation (read the index, `git show :<path>`, instead of `HEAD`) passes every test**, so a staged, uncommitted edit is not covered. See should-fix 3 | PARTLY |
| 6 | Slack `ts` is the issuance time; `card witness`; committer time never read | `posting.py`, `witness.py` | Live `ts` stored and equal to Slack's message. `witness.py` reads `first_commit_adding` and `PushReceipts`, never a commit date. The receipt half waits for the merge | MET (b at merge) |
| 7 | UTC stored, IST shown; host vs Slack and GitHub; > 5 s WARNING | `clock.py` | UTC with `+00:00` stored and IST shown: MET. Slack check live: 0.006 s. **GitHub: never succeeded live.** In my probe from this container, HEAD on `api.github.com` gives 400 and `/zen` 403, with no `Date` header, so it is "not checked (KeyError)", as the orchestrator found. Two defects (should-fixes 1 and 2): an error answer that carries a `Date` header (from a proxy) is taken as GitHub's time, and the 5-second boundary is untested | PARTLY |
| 8 | Owner-unavailable line, E8 absent stated | `card.py:16` | On every card I made | MET |
| 9 | Card records in Drive only; no card text in the repository | `record_store.py`, `issue.py` | Live record in Drive; the delivery file holds none of the card's lines (checked for the live file and for my no-token file) | MET |
| 10 | The card always arrives | `card.py` `_guarded` | **Empty**, with no calendar, registry, captures or score reports committed: a card still came out, with `data_check_failed`, "Forecasts: none on record yet", and Missing naming the calendar, registry, weather and capture | MET |
| 11 | Slack/Drive down: retry rules, printed, stored, next card names the miss | `posting.py`, `deliveries.py` | `--post` with no token and no Drive settings: "alert NOT sent: FNO_SLACK_BOT_TOKEN is not set", "card record NOT saved to Drive: ... (FNO_GDRIVE_*) are not set", delivery a2 written, exit 1. After committing a2, the 16 Oct card names both misses. Retry rules: my T9 (retry a maybe-posted) and B4 (two retries) caught | MET |
| 12 | Dry run by default, no network | `cli.py` | Dry run prints "nothing posted, saved or written" and writes no file (`git status` clean) | MET |
| 13 | Secrets never in files or logs | | No token in the diff (only `test-token-not-real`), none in either delivery file; errors are named by type | MET |
| 14 | Non-session and muhurat days: no card; unknown calendar still a card | `session.py` | 17 Oct (Saturday), 2 Oct (holiday) and 8 Nov 2026 (muhurat) print "not a trading day: no card". 5 Jan 2027 (beyond the calendar) gives a card naming "session calendar cannot answer". My T10 (muhurat gets a card) caught | MET |
| 15 | Interfaces, one root, sizes, constants | `wiring.py`, `CLAUDE.md` | Every source, store, poster and clock is chosen only in `fno/cards/wiring.py`, which is listed in `CLAUDE.md`. Constants are in `fno/constants.py` and at the top of modules | MET |
| 16 | Live delivery verified once | (a) on the branch, (b) at the merge | (a) checked above: MET. (b) at the merge check | (a) MET; (b) pending |

## Claims vs reality

| Builder's claim (response 101) | Reality |
|---|---|
| "43 of 43 planted breaks are caught" | Plausible; I did not rerun the builder's script. My own: 16 planted, **12 caught**. Survivors: T12 (index instead of HEAD), B1 (limit raised to 9.9 s), B2 (resolution ignored on the early side), T6 (next card's clock-warning line) |
| "prints correctly from the real repository" | True: hashes and numbers checked |
| "Each clock check now stores its line, e.g. 'not checked (ConnectionError)'" | True, but the line says only `KeyError`, not "HTTP 400, no Date header", and a non-2xx answer with a `Date` header is accepted (should-fix 1) |
| "The likely cause ... the routine's network blocks a plain HEAD to api.github.com" | Confirmed from this container: 400 with no `Date`. It is the proxy, as the orchestrator says |
| "A muhurat-only day gets no card, as A4 does" | True. See the orchestrator's question 4 below |
| "the house forecast ... changes no scoring" | True: nothing under `fno/forecast*` or `research/forecasts/` changed; the card only reads |
| "Missing items and previous misses are copied into the public metadata ... harmless" | True for v1: the strings are paths and error types, plus a source failure's message cut to 160 characters (`card.py` `_failed`). See minor 2 |
| "A retry after a lost Slack answer can post the card twice" | True and disclosed. `requests.ConnectionError` also covers a connection dropped after the request was sent, and that error is retried. Minor 3 |

## Findings

### Should-fix

1. **The GitHub clock check trusts any answer that has a `Date` header.** `HttpDateClock.now` (`clock.py:43-49`) never
   checks the status code. My plant: a fake HEAD answering **403 with the current `Date`** (what a proxy typically adds)
   gives "clock: host vs GitHub within 0.0 s", stored as `skew_seconds 0.0, warning false`. That is a missing witness
   read as "within skew", the exact case the orchestrator asked about. Today this proxy sends no `Date`, so the check
   fails safe, but only by accident. Fix: accept only a 2xx (or 3xx) answer from GitHub. Store the reason in plain
   words, for example "not checked (HTTP 400, no Date header)" rather than "KeyError". Add tests for a 403 with `Date`
   and a 400 without one.
2. **The 5-second boundary is untested.** Owner's rule 5 asks for tests at, just under and just over every limit. My
   B1 (limit raised to 9.9 s) and B2 (the 1-second resolution ignored on the early side) pass all tests; only 10 s and
   30 s skews are tested. Fix: at 5.0 s no WARNING, at 5.1 s (beyond resolution) a WARNING, on both sides.
3. **"Never an uncommitted file" is not pinned against the index.** My T12 (`git show :<path>`) passes the real-git
   test, because that test only edits the working tree. A staged, uncommitted edit would then reach a card, against
   criterion 5's "an uncommitted ... file is never read". Fix: in the real-git test, also `git add` an edited file and
   assert the card is unchanged.
4. **Criterion 7's GitHub half has never worked live, and nothing says so.** The routine's network answers 400 with no
   `Date`. So every real card will store GitHub "not checked", and the next card never names it (`misses` reads only
   `warning`). Fix: the next card names a server clock that was not checked, as it does a WARNING (also covers T6,
   which survived). The story's known limits must say that from this host the GitHub clock is never available until a
   route that returns GitHub's `Date` is found. This is a fact to report, not a code change in GitHub.

### Minor

1. **`--on` with `--post` can issue a card for another day from today's records.** Registry and accounts come from
   `HEAD` now, not as of that day. The delivery file then counts as that day's card in `misses`. Refuse `--post` unless
   `--on` is today (IST).
2. `_failed` puts a source exception's message (up to 160 characters) into the public delivery file. In v1 every source
   reads public committed files. Name by type only, as the stores do, before slice B adds trade fields.
3. Retrying `ConnectionError` can double-post when the connection drops after sending. Disclosed; harmless in v1.
4. The test post's file has no `line` in its clock entries (pre-fix code). It is append-only and correct as a record of
   that code; noted only.

## The orchestrator's questions

1. **GitHub clock.** The failure is named per check, but as "KeyError". A missing witness can read as "within skew"
   when the error answer carries a `Date`: should-fix 1. The unchecked state is never surfaced to the owner:
   should-fix 4.
2. **Point in time.** MET: the latest report dated before the card's day (T2 caught), never a later capture or report
   (T3 caught). The live test post itself used the same-day report (disclosed; pre-fix code).
3. **House forecast label.** On the card: "House forecast (baseline_b_base_rate): no primary named in G1; past average
   shown (orchestrator's fallback rule)". It changes no scoring (no scoring file touched). The figures equal G4's
   report.
4. **Muhurat: a justified choice, not a gap.** The forecast capture already skips muhurat (`fno/forecast/capture.py:87`),
   so the card would have no forecast to issue. There is no 15:00 market: even the 2025 session (13:45-14:45) closed
   before 15:00. A4 does the same. Design 04's "a card exists every trading day" reads best as every session with a
   15:00 market. Record that reading as a one-line design note, so the text and the code agree.
5. **Drive-only records.** MET: `research/cards/deliveries/` holds hashes, outcomes, missing items and clock facts, and
   no card line, strike or token (minor 2 is for later).
6. **PAPER ONLY and NO TRADE with a reason, incl. my own empty case.** MET. With the calendar, registry, captures and
   score reports all removed: "PAPER ONLY ...", `NO TRADE (data_check_failed)` with its reason, and every missing item
   named.

## Project rules

- Lane 1 is right: it touches Slack, Drive, an outside clock and the shared sender.
- `slack_post` is a behaviour-preserving extraction. `tests/test_alert_sender.py` passes, and it adds the non-dict
  guard (an `AttributeError` before).
- No orders; no Slack post by me (read only); no secrets.
- The quality rules (now on `main`) are met: the gap list, self-review, broken-code proof and a real NO TRADE sample.
  Rule 5's boundary cases are not (should-fix 2).

## Verdict: FAIL for 3e705bf7ece247d31e4d1251c4ce10b7b30f0a98

Four should-fixes, all in the clock contract and test coverage:
- the GitHub check trusts any `Date`;
- the 5-second boundary is untested;
- the staged-file case is untested;
- an unchecked GitHub clock is silent.

The card itself is honest and correct: every number traced to G4's report, the hashes equal the committed bytes, the
live post was verified in Slack and Drive, and the failure paths behave as claimed. A re-check needs `clock.py`,
`deliveries.py` `misses`, the tests named above and the story's known limits. Criterion 16(b) is checked at the merge.

## Addendum 1 (15 Oct 2026): 44fa45da5c5ac3d17d67c18408f307e4e16b7d62 (3e705bf..44fa45d: 9f540e9 and 44fa45d)

### Gates

- **Exact SHA:** full history, Slack token unset: **3,265 passed**. `ruff check`, `ruff format --check` (730 files)
  and `check_imports` (740 files) are clean.
- **Trial merge with `origin/main` e45c91e:** 3,265 passed; ruff, format and imports clean.
  - **Merge note:** `reviews/claude/README.md` conflicts (both sides add rows). Keep both.
- My mutations ran in a separate worktree, never in the one under test.

### Should-fixes re-checked

| Judge 101 finding | Status | My evidence |
|---|---|---|
| 1. GitHub clock trusts any `Date` | **MET** | `HttpDateClock.now` accepts only 2xx or 3xx with a readable `Date`. My C1 (status check off) is caught. Real probe from this container: the API root gives "clock NOT CHECKED: host vs GitHub (HTTP 400 from GitHub, no Date header: an error answer's time is not trusted)", stored `checked: false` |
| 2. 5-second boundary untested | **MET** | My B1 (limit 9.9 s), B2 (resolution ignored on the early side) and new B5 (`>=` at the limit) are all caught |
| 3. Staged-file case untested | **MET** | My T12 (read the index instead of `HEAD`) is caught |
| 4. GitHub clock never available; unchecked never surfaced | **MET; pushback ACCEPTED** | The builder's evidence holds. Through the proxy, `HEAD https://api.github.com/repos/exepex/trading` answers **200 with GitHub's `Date`**, and my real `check_server` gives "within 0.0 s, checked: true". So the limit applied to the root path only, and `GITHUB_TIME_URL` now uses the repository path (my C8, root URL back, caught). An unchecked clock on a sent card is now named on the next card (my C2 caught) |

### Minors re-checked

| Minor | Status | Evidence |
|---|---|---|
| 1. `--post` for another day | MET | Real run: `--on 2026-10-14 --post` prints "--post issues only today's card ... nothing done", exit 2. My C3 caught |
| 2. Exception message in the public record | MET | Type only now. My C7 (message back) caught |
| 3. `ConnectionError` retried | Fixed in code, **untested** | Moved to "may have posted" and never retried. My C4 (move it back into the retried set) passes all 112 tests in `tests/cards`, `tests/ai` and the alert sender |
| 4. Test post's clock entries lack `line` | Unchanged, as agreed | The file is append-only |

### `fno/ai/receipts.py` (9f540e9), as the orchestrator asked

- **Not frozen.** No freeze record lists it: `research/forecasts/FREEZE*.md`, `research/evaluation/`, experiment 1 and
  the other study freezes were searched.
- **It still fails closed.** `ReceiptAccessDenied` subclasses `ReceiptUnknown`. The only other consumer,
  `fno/ai/submissions.py:56`, catches `ReceiptUnknown`, so a 401 or 403 still gives `Published(..., None, reason)` and
  is never a receipt. My C6 (403 not marked access-denied) is caught.
- **Paging is correct on real data.** I ran `GitHubActivityReceipts` against GitHub through this proxy with `per_page`
  forced to 3 (10 pages). Page 2 is requested as `/repos/exepex/trading/activity` with GitHub's `after` cursor, and the
  receipts of my own pushes came back: 7963b8f at 00:47:53 UTC and e45c91e at 01:50:36 UTC. My C5 (follow the numeric
  next link) is caught.
- **The paging test is stricter, not looser.** It now requires page 2 by owner/name, with `after` and `ref` carried.
  The 403 case is asserted as `ReceiptAccessDenied`, and a 500 is asserted as `ReceiptUnknown` but **not**
  access-denied. Nothing was removed.
- **G5's collector results cannot change** for any answer that worked before:
  - the same pushes are read, from the same activity log, in the same order;
  - only the URL form of pages 2 and later changed;
  - a page refused before (HTTP 403 on the numeric path) now succeeds, so a receipt that read "unknown" can now be
    found. That is a correction, not a change of the rule.

### Muhurat note and the owner's rows

- **Story design note:** "a card every session with a 15:00 market" is recorded, matching the owner's "3 A". Small
  slip: it says "one evening hour", but the 21 Oct 2025 muhurat ran 13:45-14:45. It is still no 15:00 market, so the
  rule holds.
- **Criterion 16(a)** stays MET on the one post that exists. The owner's row 133 ("1 B") records that the orchestrator
  ran it on the builder's behalf, which the owner does not accept for the future.
- **Owner's "4 A" (missing weather blocks new trades):** **not yet on the card.** The weather lines still say only "not
  yet scored ... no colour until M1 scores one". In v1 this misleads no one, since no trade can be shown and the
  status is NO TRADE. But the card should say "no new trades while the weather reading is missing (owner rule)" before
  slice B. Minor; it carries to the next T1 change.

### Mutations this round

13 planted and **11 caught**. Survivors, both minor:
- **T6:** the next card's line naming a clock WARNING; the code is right but untested.
- **C4:** `ConnectionError` not retried.

### Minor (open, non-blocking)

1. Add tests for T6 (a WARNING named on the next card) and C4 (a `ConnectionError` is never retried).
2. Add the owner's "4 A" wording to the weather lines, with a test.
3. In the design note, write "one-hour Diwali session" instead of "one evening hour".

**Verdict: PASS for 44fa45da5c5ac3d17d67c18408f307e4e16b7d62.** All four should-fixes are met. The SF4 pushback is
accepted on my own probe. The receipts change is sound and fails closed. Three minors remain.
- **Merge:** as a merge commit, keeping both rows in `reviews/claude/README.md`.
- **At the merge check:** criterion 16(b), GitHub's push receipt of the test delivery file
  (`research/cards/deliveries/2026/2026-10-15-a1.json`) once it reaches `main`, plus the recomputed merge, the branch
  files equal to 44fa45d, and CI.

## Addendum 2 (15 Oct 2026): merge check, T1 merged to main as f0c47ae; criterion 16(b)

- **Parents.** f0c47ae's parents are 215fc26 (main) and 44fa45d (the passed tip).
- **The merge matches my recomputation, apart from resolved conflicts.** `git merge-tree --write-tree` conflicts in
  `fno/cli.py` and `reviews/claude/README.md`. f0c47ae's tree differs from the recomputed tree only by those files'
  conflict-marker lines.
  - `fno/cli.py` keeps both sides: the `vix-history` import and parser line (A15) and the `card` ones (T1).
  - The README keeps both rows.
- **Branch files arrived unchanged.** Every file T1 changed equals 44fa45d, except where `main`'s own additions from A15
  share the file: `CLAUDE.md`, `fno/cli.py`, `fno/constants.py`, `fno/storage/README.md` and
  `reviews/claude/README.md`. In each of those, T1's lines are present unchanged.
- **Criterion 16(b), GitHub's push receipt:** **MET.** `python -m fno card witness --on 2026-10-15` on main prints:
  `research/cards/deliveries/2026/2026-10-15-a1.json: Slack 2026-10-15 06:20:14 IST (ts 1792025414.919329); GitHub push
  receipt 2026-10-15 07:44:39 IST (commit cc441095a4)`.
  - cc44109 is in main's history.
  - The receipt is the push that brought the merge to `main` (02:14:39 UTC). So for this test post it witnesses the
    merge, not when the file was written. The file sat on the story branch from 00:50:24 UTC, and branch pushes are
    not in main's activity log.
  - For daily cards committed straight to `main` by the scheduled run, the two witnesses will be minutes apart.
- **No unjudged change since.** From f0c47ae to aa2f4c3 only `reviews/`, conversation and decision files changed.
- **CI.** The first push carrying f0c47ae is aa2f4c3: run 38669953437 (`checks`) **completed, success**.
- **End-to-end run (rule 8).** The orchestrator records the dry run on the merged tree printing the PAPER ONLY NO TRADE
  card with nothing written. My own dry runs at 3e705bf and 44fa45d agree.

**Merge check: PASS. T1 criterion 16 is now MET in full.**

## Addendum 3 (15 Oct 2026): follow-up 9d5310b177da959a1bd46ce3d8231841f5783e13 (owner "4 A" weather wording)

One commit on top of 44fa45d. It changes `fno/cards/weather.py`, one test, the story's criterion 3 and response 101.

- **The card now carries the owner's rule.** The weather section reads "Weather: not yet scored (M1 pending)", then
  **"No new trades while the weather reading is missing (owner rule)."**, then the M1 line. That is the owner's "4 A"
  (row 136: missing weather fails closed, like RED).
  - Nothing on the card implies a trade would be allowed.
  - The colour test still passes: "reading" is not the word RED.
- **The test bites.** My mutation removing the line from the section fails 1 test (`tests/cards` 60 of 61 pass).
  `tests/cards` passes 61 of 61 at 9d5310b.
- **Gates.**
  - At 9d5310b: `ruff check`, `ruff format --check` (730 files) and `check_imports` are clean.
  - On a trial merge with `origin/main` 6c473ea, which already holds T1 and A15: **3,539 passed**; ruff, format and
    imports clean.
- Minors 1 and 3 of addendum 1 go to the builder's next follow-up, as the orchestrator says. I check them when sent.

**Verdict: PASS for 9d5310b177da959a1bd46ce3d8231841f5783e13.** Merge it; I check the merge afterwards.

## Addendum 4 (15 Oct 2026): follow-up a84f92db66056cc7f8b154e17da3ebf327f70d0c (minors 1 and 3)

a84f92d = 9d5310b + 8c3ab1b + one commit.
- **8c3ab1b** is a merge of `main`. It equals my recomputed `git merge-tree` exactly.
- **The one commit** adds two tests and changes muhurat wording in the story, `session.py`, `constants.py` and a test
  comment. No logic changes.

| Item | Status | Evidence |
|---|---|---|
| Minor 1a: the next card names a clock WARNING | MET | `test_the_next_card_names_a_clock_warning`. My T6 (the WARNING line removed) now fails 1 test |
| Minor 1b: `ConnectionError` never retried | MET | `test_a_connection_error_is_never_retried_even_when_a_retry_would_succeed` queues a success behind the error and asserts one call. My first C4 mutation was a no-op: it added `ConnectionError` to the retried set, but the "may have posted" check runs first. A real mutation (moved from "may have posted" to "retried") fails 2 tests. Correction of my addendum 1: the old code was already right; only the test was missing, and it is now there |
| Minor 3: muhurat wording | MET | "the one-hour Diwali session; 21 Oct 2025 ran 13:45-14:45" in the story; `session.py` and `constants.py` say "one-hour Diwali session" |
| Gates | MET | At a84f92d (clean rerun, since my first run overlapped a mutation): 3,541 passed; ruff, format (762 files) and imports clean. Trial merge with `origin/main` c8ac9fd: 3,541 passed; ruff, format and imports clean |

**Style nit (not blocking).** `ruff format` moved two trailing comments after a closing parenthesis:
`CARD_SESSION_KINDS = (...)  # ...` and the muhurat test's `assert (...)  # ...`. They read oddly; put the comment
above the statement next time.

**Merge check of 16a904a (9d5310b), done here.**
- Its parents are b933d65 and 9d5310b, and it equals my recomputed merge exactly.
- `fno/cards`, `tests/cards` and the story equal 9d5310b.
- CI run 38671984351 on 16a904a: completed, success.

**Verdict: PASS for a84f92db66056cc7f8b154e17da3ebf327f70d0c.** Every T1 minor is closed. Merge it; I check the merge.

## Addendum 5 (15 Oct 2026): merge check, a84f92d merged to main as 860030c

- **Parents.** 860030c's parents are 26f020e (main) and a84f92d (the passed tip).
- **The merge matches my recomputation exactly** (empty diff; no conflicts).
- **Branch files arrived unchanged.** `fno/cards`, `tests/cards`, the T1 story and `fno/constants.py` equal a84f92d.
- **No unjudged code since.** From 860030c to c0978bd only review, log, decision and scheduled-job data files changed;
  none under `fno/`, `tests/`, `tools/` or `.github/`.
- **CI.** Run 38674600675 (`checks`) on c0978bd, the first push carrying the merge: **completed, success**.
- **End-to-end run (rule 8).** The orchestrator records the dry-run card printing on the merged tree, with the tree
  clean.

**Merge check: PASS. T1 is done:** every criterion is met, every minor is closed, and both merges are checked.
