# Judge 572: REH1g, DRY2's rehearsal gaps G1, G2, G4, code (story/reh1g-record-gaps @ f9562dfe1), judge B

**FAIL (round 1 of 2; 1 should-fix, 4 minor). Lane 1** (the rehearsal's no-look-ahead reads of the real Drive record).

## Criteria

| # | Criterion | Result | My evidence |
|---|---|---|---|
| C1 | 3 pm record lists sidecars and markers from the repository; raw file read by name, hash-checked | MET | `record_store.py:34-38`; real-builder test passes; plants Pf (listing `{}`) and Pl (A4b's store back) caught; my run lists the Claims' 9 names for 23 Oct |
| C2a | a row counts from the committer time of its first first-parent commit on `origin/main` | PARTLY | right for A9 and cue rows (Pa, Pg caught; 16 Oct close 22:40:15 UTC and KOSPI 03:23:35 UTC reproduced); wrong for every revised file (finding 1); Pj survives (minor 1) |
| C2b | an A9 file is its dataset's (day, URL) row | MET | my script: 12,582 rows of the 20 RAW_SOURCES manifests map back through `path_for` and `_a9_key`; the fo_secban 22/23 Oct test passes |
| C2c | a `path` row (cues, candles) matches only that path in the raw area | NOT MET | `_index` takes `path` rows from every manifest under `manifests/`, so `revisions/*.csv` and `filings/outside-layout.csv` count too, and win over the A9 row (finding 1) |
| C2d | the rehearsal's Drive is wired with the rows | MET | `drive_wiring.py:23`; test passes; Pn (receipt branch off) caught |
| C3a | scheduled reads: 60 s before to 10 min after | MET | `serving.py:26-27`; Ph (`<` at +10 min) caught |
| C3b | paced reads: nearest within 60 s, never twice, never back in time, waits | MET | Pd (`>=`), Pi (lower bound dropped), Pe (pre-open wait) and Pm (cue wait) caught |
| QR2-6 | gap list, self-review, broken-code proof, cases, real sample | MET | sample reproduced on my trial merge; rejections checked below |
| Gates | trial merge with origin/main 404452481 | MET | ruff, format (2,442 files), imports, record scan (8,992 files) clean; 15,143 passed, 15 xfailed; new files 46-153 lines |

## Findings

1. **Should fix: revision-index rows date the raw file, later than its A9 row.** `manifests/revisions/index-close.csv`
   and `span-bod.csv` have a `path` column: the raw path whose later NSE version was found. `_index`
   (`manifest_rows.py:59-66`) indexes them as path rows and `seen_at` (`:40-41`) prefers them to the A9 row. My
   read-only run on the trial merge: `raw/nse/derivatives/span-bod/2026/10/nsccl.20261021.i1.zip` is seen at 24 Oct
   00:34:09 UTC (the revision row), though its A9 row reached main on 20 Oct 02:23 UTC; `ind_close_all_23102026.csv`
   at 19:36:03 UTC instead of 17:01:15; the 12 and 21 Oct closes likewise. A rehearsal between the two times says
   NOT_RECORDED for a file the day held: G2's own "visibility fault", growing with each revision sweep [strong]. It
   errs late, never early (no look-ahead); no test has a revision row. Fix: index `path` rows only from the manifests
   whose `path` names a raw file (global cues, Groww candles), never `revisions/` or `filings/outside-layout.csv`
   (deleted trial files), or take the earliest of both kinds; test a revision row committed after the A9 row.

## Minor

1. **Pj survives:** `committer-time` read as `author-time` passes all 98 rehearsal tests (the tests set both dates
   equal). Add one row whose author date is earlier than its committer date.
2. **Pc survives:** `_a9_key` without the trailing `/` passes; it changes no row today (my script), but
   `fii-dii-cash`/`-by-session` and `fpi-daily`/`-by-session` are prefix pairs. One test pins it.
3. `announcements`, `board-meetings` and `india-vix-history` have no RAW_SOURCES entry, so their files are never
   visible. No routine of the four reads them (my grep); say so under Limits.
4. Limit 2 says manifest rows "are not written this way today", but the routines' `pull --no-rebase` then `push
   HEAD:main` puts earlier main commits on the second-parent side: hence the 16 Oct close dated 3 h 38 min after its
   commit (the Claims' own sample). Late only; reword it.

## Self-review rejections (my check)

- #5 holds: only `build_job` and `build_preopen` build the cue session (`global_cues/wiring.py:191,284`); of the four
  routines only `rehearse preopen` runs one (`rehearsal/routines.py`). #8 (no git) holds: the checkout runs `git
  rev-list` on `origin/main` before any step (`checkout.py:50`). #10 (partly) holds: behaviour tests catch Pd, Pe, Pi, Pm.

## Plants

16 planted, one at a time, each restored and `__pycache__` cleared: 10 caught (Pa look-ahead, Pd, Pe, Pf, Pg, Ph, Pi,
Pl, Pm, Pn). Survived: Pj, Pc (minors 1, 2); Pb (keep the later of two equal keys) and Pk (`top_level` dropped) are
equivalent on today's data.

## Notes

- Hunted: no write path (`ListedQuoteRecord.put` reaches `RecordReader.put`, which raises; raw reads use
  `record_view()`); no new post; holidays and empty days end NOT_RECORDED; every time compared is tz-aware.
- REH1g was finished by session_01Mt6dcBU5kp2htdPN2KmiZH, which launched this judge (no shared context); builders never merge.

## Addendum 1

**REH1g code, round 2 (story/reh1g-record-gaps @ f1f37f3a5), judge B: PASS (1 minor). Lane 1.** Round 2's code:
`manifest_rows.py` (+29/-8) and three test files (`git diff f9562dfe1 f1f37f3a5 -- fno tests`).

| Round-1 item | Outcome | My evidence |
|---|---|---|
| SF1 revision rows date a raw file | **Accepted** | `_index` now reads `path` rows only from the top-level files of `global-cues/` and `groww-candles/` (`_path_logs`, from the writers' own constants), and A9 rows only from the 20 `RAW_SOURCES` manifests. I ran `seen_at` read-only on my trial merge with full history: span-bod 21 Oct 20 Oct 02:23:12, 23 Oct close 17:01:15, 12 Oct close 13 Oct 01:54:09, 16 Oct close 16 Oct 22:40:15, KOSPI 03:23:35 (all UTC); a made-up file None. `global-cues/attempts/` has no `path` column, so `glob` loses nothing |
| m1 Pj committer time | **Accepted** | new test with author 03:20:00, committer 03:23:35; my Q3 (`author-time`) caught |
| m2 Pc trailing `/` | **Accepted** | both source orders tested; my Q6 caught |
| m3 three manifests never visible | **Accepted** | gap-list row added; `rehearsal/routines.py` runs none of them |
| m4 limit 2 wording | **Accepted** | reworded: late through a routine's merge, early only for a branch commit pushed as `HEAD:main` (seconds). Note below |

**Gates** (trial merge of f1f37f3a5 with origin/main d5ee18d02, full history): ruff clean; format 2,443 files;
imports clean (2,572 files); record scan clean (9,007 files); **15,150 passed, 1 skipped, 15 xfailed**. The skip is
`tests/intraday/test_feed_tls.py:190`: `growwapi` is not installed in my container. It is unrelated to this change.

**Plants** (9, each run alone on `tests/rehearsal`, file restored, `__pycache__` cleared): 8 caught.
- Q1 `revisions` and `filings` added to the logs (2 failed); Q2 `rglob`; Q3 author time; Q4 `_keep` keeps the later
  commit; Q6 no `/`; Q7 the closes serve the latest answer; Q8 no `--first-parent`; Q9 blame of `HEAD` (each 1 failed).
- Survived: Q5, `groww-candles` dropped from `_path_logs` (105 passed).

## Minor (round 2)

1. Q5 survives: no test has a candle `path` row. The candle source itself does not depend on it, because
   `RecordedCandles` reads its manifest directly (`candle_wiring.py:24`). But a candle file read through the rehearsed
   Drive would then be NOT_RECORDED. That is late, never early. Add one candle row to a `seen_at` test.

## Notes

- A shallow clone dates every row to its oldest fetched commit. My first run, before `--unshallow`, put every file at
  24 Oct 06:20:57 UTC. The checkout already unshallows the source before it starts (`checkout.py:48-49`), so this is
  late only and covered.
- Limit 2's early case is real but bounded: a commit's time is not its push time. Rows come from routines that push
  within seconds, as the Claims say. No fix is asked; git has no push time to use.
