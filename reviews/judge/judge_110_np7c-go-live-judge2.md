# Judge 110: NP7c news go-live checklist (judge #2, document)

**Subject:** `story/NP7c-go-live-checklist` at `8eeeab8`. The only file changed against main is `docs/NEWS_GO_LIVE.md`
(73 lines, a new document).
- It describes the workflows, the schedules and the owner's private files, so it takes lane 1, the lane of what it
  describes, with one judge.
- Scope is in bounds: it covers only turning on fetch, derive and store; nothing for a consumer.

**Gates (text only):**
- The doc-reading tests: 79 passed.
- `check_numbers`: clean.

## What I checked against main (`f829626`), all *strong evidence*

- **No schedules:** every `news-*.yml` workflow and `staging-cleanup.yml` has no `schedule:`, and all are dispatch only.
- **No Groww:** no news workflow mentions Groww. `staging-cleanup.yml` mentions it only in the comment "no Groww".
- **Workflow inputs match the doc:**
  - `news-probe-outlets` takes `include_refusing`;
  - `news-resolve` and `news-read-pages` take `apply` and `limit`;
  - `news-cluster` takes `algorithm`;
  - `news-promote` takes `from_date`;
  - `staging-cleanup` takes `apply`;
  - every workflow takes `dry_run`.
- **Private file folders:**
  - `feeds` (`feeds.py:21`);
  - `discovery` (`planning/discovery.py:18`);
  - `companies` (`companies/private_file.py:17`);
  - `materiality` (`materiality/file.py:15`).
- **Commands:** `seed-companies` and `plan-feeds` exist.
- **NP7b is on main** (`7d496ae` is an ancestor), so "algorithm 2 may be dispatched" is true.
- **Codes:** `resolver_failing`, `reader_failing`, `cluster_conflict`, `resolution_conflict` and `read_conflict` exist on
  main.

## Blocking

1. **B1: the document describes NP8 behaviour that is not on main and is FAILed** (judge 109, round 1).
   - These lines describe NP8:
     - section 1, "read order" as a user of the company list and of the materiality file;
     - section 4, `company_list_*`, where "The read pass DEGRADES ... no pass note";
     - section 4, the whole materiality row;
     - section 4, `pass_note_unreadable`;
     - section 7, "ranking up to 300 articles, then at most 100 resolution reads".
   - On main, `PASS_NOTE_UNREADABLE` and `MATERIALITY_UNAVAILABLE` do not exist, and the read pass never reads either
     private file. Merged now, the owner's one owning go-live document would describe codes and behaviour that the
     runs cannot produce.
   - **Fix, either of:**
     - merge this document only after NP8 merges, and say so in the story;
     - mark each NP8 line "(after NP8 merges)" and remove the marks in NP8's merge.
2. **B2: the `company_list_missing` row is wrong for cluster version 2.**
   - The row puts `company_list_missing` under "**Cluster v2 STOPS**". On main, a list that was NEVER used gives
     version 0 and a green run (`grouping.py`, `_company_list`). Only a list that was used before and is now missing
     stops the run.
   - The footnote ("never configured is not an error") speaks only of the read pass.
   - **Fix:** make the footnote cover both runs, e.g. "A file never configured is not an error: cluster v2 records
     version 0, the read pass is green and newest first. A file used before and now gone is red."

## Notes (not blocking)

- **Section 6, the git-history note:** it names no pattern or company, so it is correct. That history is from my
  judge 78, which I disclosed at the time.
- **Section 8:** it states plainly that the unreceipted walk is not built and not a gate. That is honest and needs no
  change.

**Verdict: FAIL** (round 1, `8eeeab8`).
- B1 is a merge-order or marking choice.
- B2 is one sentence.

## Addendum 1

**Round 2 re-review at `7fc5dd8`.** Against main, only `docs/NEWS_GO_LIVE.md` changed (75 lines).

**Gates (text only):**
- The doc-reading tests: 79 passed.
- `check_numbers`: clean.

**B1: fixed by sequencing.**
- The page now opens: "This page describes `main` **after NP8** ... it is merged after NP8".
- NP8 passed my round 2 at `770cf76` (judge 109 Addendum 1), but it is **not yet on main** (`770cf76` is not an ancestor
  of `origin/main` at this review).
- **Condition:** merge this page only after NP8 is on main. Whoever merges it checks that `770cf76`, or NP8's merged
  head, is an ancestor.

**B2: fixed.**
- The company-list and materiality rows now name `*_missing` only for a file used before.
- The footnote covers both runs: never configured is green, with cluster v2 at version 0 and the read pass newest
  first; used and then gone is red.
- One nit, not blocking: "red in both (`company_list_missing`, `materiality_missing`): cluster v2 stops" can read as if
  cluster v2 used the materiality file. It does not; only the company list stops it. Fix it in the next edit of the
  page.

**Verdict: PASS** (round 2, `7fc5dd8`), on the condition that it merges after NP8.
