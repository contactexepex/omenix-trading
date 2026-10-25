# Judge 575: REH1h story text, files a routine archives during its own run (story/reh1h-archive-serving @ 19ed7aa7a)

**FAIL (round 1 of 2, text; 1 should-fix, 3 minor). Lane 1** (serves the record's files into a rehearsal: a wrong
rule is a look-ahead). Judge E. Text-only (one `.md` file, 76 added lines on top of REH1g's f9562dfe1): judged by
reading, no suite. Labels: strong, some, reasoning only.

## Criteria (rule 1: the text against G2b, the owner's decisions and REH1's frame)

| # | Check | Result | My evidence |
|---|---|---|---|
| T1 | Covers G2b as written | MET | G2b's two sentences are REH1g's own first text (`b5ab43ef6`, story lines 625-630); both mapped (H1/H2, H5) |
| T2 | The "why" is true | MET | My read of `manifest_rows` on origin/main: fo-bhavcopy 23 Oct 19:55:20, participant-oi 19:55:29, fii-dii-cash-by-session 19:55:39 IST; 22 Oct index-close 01:06:53 on 23 Oct, all as written |
| T3 | No look-ahead | MET | H2: served only at or after the row's commit, which is after the day's Drive write; the upper bound 10 min, boundaries exact |
| T4 | No real Drive write; dryrun only | MET | H6: real Drive only read (`RecordFiles`), writes via `DryrunDrive` under `dryrun/<run_id>/`, a test on the real `build_librarian` composition |
| T5 | One new class behind an existing seam | MET | `nse_wiring.rehearsed_session` is the one seam (`storage/wiring.py:162-164`); it extends `NotRecordedSession` |
| T6 | Criteria testable, with good/bad/boundary/empty | PARTLY | H1-H6 each testable; H2's lower-bound rule rests on a false premise for one of H1's three targets (SF1) |
| T7 | Gap list complete; out-of-scope reasons true | MET | 404s: every row of the 23 top-level manifests has status 200 (none recorded); filings and by-symbol: no routine command in `routines.py` reads them; release-check reason matches `forecast_lab/release.py:36` (`fetch_published`, no store) |

## Findings

1. **Should fix: H2's "more than 60 s before now is not served ... the library already reads that file from the
   stores through REH1g's G2" is false for the FII/DII snapshot, one of H1's three targets.** `data-snapshot
   fii-dii-cash-by-session` is a `SessionFiledTaker` (`storage/wiring.py:234-239`, `COVERED_SESSION` in
   `content_checks.py:90-94`), and `SessionFiledTaker.take` fetches first, always: the path depends on the session read
   from the copy (`session_filed_taker.py:43-49`). No store is read before the request. So a rehearsal whose
   by-session step reaches the request more than 60 s after 19:55:39 (a slow step before it, a late start) gets
   NOT_RECORDED, though the record holds the copy and G2 already shows its file. The same applies to the fo-ban-list
   and the NSDL by-session report [strong: code read]. Fix: give the session-filed (fetch-first) takers their own
   rule in the text, for example the latest row for that URL committed on or before now on the replay day; or keep
   the 60 s and say the limit plainly, with its effect on e5. Add the case (a by-session read at commit + 61 s) to H2's
   boundary tests.

## Minor

1. H1's condition on the FII/DII request can be settled now: `FiiDiiCashSource.url_for` returns the one API URL
   (`snapshot_source.py:80-85`) and `_response` sends one GET with no warm-up page (`raw_source.py:144-147`).
2. The wait's clock is not named. The evening's waits run on the replay clock, but the text should say whether they
   use the skipping waiter or a real sleep (G3 was decided as real speed for the pre-open only).
3. A repeat request for the same URL in one run (a retry, a second step) gets the same copy again. That differs from
   REH1g's paced `ServedOnce` rule. Right for a scheduled read, but say so in H4.

## Plants

None (text round). The eight planned plants cover the wait, the window, the SHA-256 check, the `url_for` round trip,
nearest vs first, the ambiguity refusal, the old session wired back and HEAD.

## Notes

- H2 inherits REH1g's finding SF1 (judge 574): a file with an A11 revision row is shown by G2 only from the revision's
  commit (e.g. span-bod 21 Oct from 24 Oct 06:04 IST, though its row reached main on 20 Oct). In that gap neither the
  store nor this session answers. Fixed in REH1g, H2 holds as written.
- The guard's entry is named in Design but not in a criterion. H6's test should include the guard listing the new class.

## Addendum 1

**REH1h story text, round 2 of 2 (story/reh1h-archive-serving @ e8c2f9de4): PASS. Lane 1.** Judge E, own session
(session_01Sp5rJyPberRttZaJ4WwW26; DESK_DECISIONS 24 Oct, own sessions). Text only: `git diff --stat f1f37f3a5
e8c2f9de4` is one file, `docs/stories/REH1-rehearsal-mode.md` (+158); judged by reading, no suite.

| Round-1 item | Outcome | My evidence |
|---|---|---|
| SF1: fetch-first takers NOT_RECORDED 60 s after the commit | **Accepted, fixed** | Candidates are the replay day's rows up to `NEAREST` ahead; a future row is waited for, else the latest row committed at or before now that day. I confirmed the premise: `SessionFiledTaker.take` calls `source.fetch` before any store read (`session_filed_taker.py:42-47`); H2 now has commit + 61 s and + 1 h |
| m1: H1 conditional for FII/DII | Accepted, fixed | `FiiDiiCashSource.url_for` returns the one `API` (`snapshot_source.py:80-85`); `_response` sends one `get` per try, no warm-up (`raw_source.py:144-148`) |
| m2: the wait's clock | Accepted, fixed | `ReplayClock` is wall + offset (`clock.py`); `jump_to` is used only through `SkippingWaiter` in `fno/daily/wiring.py:89`, none of the evening steps: a real sleep moves the replay clock by the same amount |
| m3: a repeat request | Accepted, fixed | H4 says it and why it differs from `ServedOnce` |
| 573 SF1 (judge B): quotes not in the repository | Checked, fixed | Handover line 99 and `b5ab43ef6` story lines 625-630 match the quotes word for word |

**The new rule: nothing served before its commit on the replay clock.** Holds as written. A future candidate (commit
after now, at most 10 min) is served only after the sleep to its commit time; a past candidate has commit <= now by
definition. The served time is never before the first-parent commit that REH1g's C2a dates, so no read sees a file
before `main` held it [strong: the rule read against `clock.py` and REH1g's index]. The one early case is REH1g's own
stated limit 2 (a branch commit pushed as `HEAD:main` keeps its commit time, seconds before the push); inherited, said.

## Findings

None blocking, none should-fix.

## Minor (for the code round)

1. REH1g's A9 index keeps only `(manifest, day, URL) -> commit time` (`manifest_rows.py:72`). H3's SHA-256 check and
   H4's same-time ambiguity need each row's `sha256` and dataset: the code must extend that index (one reading), not
   read the manifests again, as the Design says.
2. A future row is preferred to a past one: a read at 20:00 with one row of the URL at 19:55:39 and another at 20:05
   waits 5 min for the later (hypothetical: the record has no run-dated `fii-dii-cash` row after 20 Oct). No
   look-ahead, but a test should pin which one is served.
3. A morning fetch-first read (the ban list, published the evening before) has no same-day row and stays NOT_RECORDED.
   No rehearsed routine runs it in the morning today; say so under H5.

## Plants

None (text round). The ten planned plants cover the new rule (the at-or-before branch dropped, the replay-day bound
dropped, the wait removed); I add one: the past branch serving the earliest row of the day instead of the latest.
