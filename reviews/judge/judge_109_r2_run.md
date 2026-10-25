# Judge 109: R2 run, part 1: pre-run amendment 1: `story/r2-run` 291760c (lane 1, story-text check, quality rule 1)

Judge D. Scope: `AMENDMENT_1.md` (new), `FREEZE.md` (its hash), `README.md` (one line), on parent `main` 32262d4. No
code, no data. The question: does anything in A-D change a registered rule or threshold, or choose anything with
outcome knowledge, and is D's data route acceptable.

**What I did:**
- read the diff and `AMENDMENT_1.md` in full against the frozen `PROTOCOL.md`, judge 97's follow-ups,
  `FACTORY_RULES.md`, `DATA_SPEND.md` and the owner's decision rows;
- checked the hashes, the freeze commit's ancestry and every data claim in D against the repository (manifests'
  headers and date ranges, `fno/filings/`, `fno/fo_bhavcopy.py`, a NIFTY index-future row of the 2 Jan 2024 fixtures
  for units). I read **no study data**: no stock row, results date, filing time or event move;
- re-derived the power arithmetic.

## Gates

- `PROTOCOL.md` SHA-256 at 291760c: `89947b4c...e40a6b`, unchanged. `AMENDMENT_1.md`: `8b36416b...1da47d`, equal to
  `FREEZE.md`'s new row. 93a19c3 (the freeze) is an ancestor of 291760c.
- `tests/research` (ledger guard included): 22 passed, Slack token unset. Record scan clean (1,275 files).
  `git merge-tree origin/main 291760c` merges cleanly. Files: 88, 25, 190, 6 lines.
- Docs only, so the full suite is not needed for this part; it runs on the `study.py` commit.
- Environment note: `requirements-groww.txt` does not install here (`clint`/`args` wheels fail, as the file itself
  warns). It does not affect a docs-only change; I record it for the code part.

## Claims vs reality

| Claim | Status | Evidence |
|---|---|---|
| A. Annualisation of criterion 3 | MET | Protocol §8.3: "at least 130 clusters a year (count of section 7) with an event meeting 1 and 2"; §7 does not say how a year is measured (judge 97 follow-up 2). A fixes it: clusters (Industry x ISO year-week of R) with at least one decision-window event that fits, is liquid and has EN > 0, divided by window days / 365.25. Reading criteria 1-2 per event is the stricter of the two readings (it can only remove clusters). The window holds 8 full results seasons plus the start of Oct-Nov 2026 in about 2.04 years, so the rate is biased slightly down, as stated. Chosen blind: it needs no data. |
| B. Depth descriptive only | MET | Per bucket: legs, median and p25 best quantities in lots, share with a lot on both sides; "no decision role"; raw quantities stay in Drive (owner row "Raw Groww quotes go to Drive only", 665c835) |
| C. 130 decides; 297 shown | MET | (1.645 x 0.60 / 0.05)^2 = 389.7, so 390 units, 130 a year; ((1.645 + 0.842) x 12)^2 = 890.7, so 891, 297 a year: both recomputed. 130 "alone decides"; a YES between 130 and 297 is labelled; changing to 297 "would be a new trial". No rule changes |
| D. Data details fixed before reading; none changes a threshold | MET for "no threshold changed, nothing chosen with outcomes"; **two should-fixes on the data route** (below) | No D item touches 25%, 50/100 contracts, Rs 10,000, e = 5%, T = 2%, 130, 80% or 10%. Items D5-D7 and D9 resolve ambiguities of the protocol mechanically (step arithmetic, session counting, stock-quarter definition, ANOVA n0 = (N - sum n_c^2/N)/(k - 1): correct; seeded cluster bootstrap) |
| D1. A12 has no board-meeting lists for 2019-26 | TRUE | `research/data/manifests/board-meetings.csv`: 1,020 rows, dates 2005-01-01 to 2007-10-17. A12's `day-lists` job (`fno/filings/sources.py:58`, daily files `board-meetings_YYYYMMDD.json`, run by `filings-archive.yml`) is walking forward from 2005 |
| D2. `filed_at` from `results-xbrl.csv` | TRUE as a source | Header `symbol,period_end,consolidation,filed_at,first_seen,...`, 15,995 rows (rows not read) |
| D3. Corporate-actions file covers about 400 days | TRUE | One file, `from_date=07-09-2025&to_date=12-10-2026`. So Oct 2024 - Sep 2025 of the decision window rests on bhavcopy detection alone, which the amendment states |
| D4. OI in shares in both formats; contracts = `TtlTradgVol` / `CONTRACTS` | TRUE | `fo_bhavcopy.py:37` maps them; NIFTY Jan-2024 future on 2 Jan 2024: 167,847 contracts x 50 x 21,756.75 = Rs 1.826e11 = `TtlTrfVal`, and OI 11,836,050 in both files (shares) |
| Exposure while testing reachability is harmless | ACCEPTED (some evidence: rests on the builder's attestation, as every freeze does) | Two November 2026 meetings of companies: future events, outside the decision window; the snapshot's stock list is mechanical (every F&O stock with a meeting in the next 10 sessions), so knowing two names steers nothing. Column names of one Jan 2025 answer: schema only. Results dates are event timing, not outcomes. No rule in A-D uses either |
| D1 is "an amendment, not a rule change" | ACCEPTED in substance | Protocol §3 names "A12 archive in Drive: NSE board meetings"; the amendment reads the same NSE list (the API A12 archives). Same data, same rule, different fetch path; §11 lets the script differ from the text only with the difference reported. Not a new trial. But see should-fix 1 on how it is fetched |

## Should-fix

**1. The study would be its own downloader of an NSE list that A12 already archives, against the owner's 13 Oct rule
and with an unproven request shape.**
- Owner, 13 Oct 2026: "One scheduled downloader fetches it and stores the raw files in Google Drive; every consumer
  ... reads only from Drive, never from third-party servers". D1 has the study script call NSE's
  `corporate-board-meetings` API itself, one month per request, writing its own files.
- That makes a second archive of the same list in a second layout (monthly files beside A12's daily
  `board-meetings_YYYYMMDD.json`), with its own manifest (`inputs.csv`) instead of A12's.
- A month-range request is not the shape A12 uses or has validated (one day per request, with `check_day_list`). Whether
  NSE returns a full month in one answer, or caps or pages it, is not known. A silently truncated month would lower
  results-date coverage and the event count, unseen.
- Fix (any one): (a) fill 2019-01-01 to the run day through A12's own `filings day-lists` (it already takes `--to`; a
  start day is a small lane-1 change to A12, judged on its own), then the study reads A12's Drive files and manifest; or
  (b) keep the study's fetch but write exactly A12's daily layout, file names and manifest through A12's classes, one
  day per request; or (c) get the owner's written exception for a one-off study fetch, and add a completeness check
  (each month's rows against the sum of the same days' daily answers on a sample). Whichever is chosen goes in the
  amendment before any data is read, and `DATA_SPEND.md`'s "Company results dates (A12)" row names the real source.

**2. The lot size must be the traded contract's, not the near-month future's.**
- D4 takes the lot from "the stock's near-month future on the entry session", and D3 detects an adjustment when "the
  stock's lot size differs between the entry session and R".
- But the options traded are those of the chosen expiry, which by §4 is often the next month: R plus at least 5
  sessions, with pushes to the second month counted. NSE's lot revisions apply to new or far-month contracts while
  the near month keeps its old lot. So near-month and next-month lots can differ, and the decision window includes
  such transitions (reasoning only for which exact dates; I did not read the data).
- Two effects. Fit and EN would be computed on the wrong lot: a smaller old lot makes the cap look easier to meet,
  which overstates feasibility. And the near-month future rolling between entry and R can show a "lot change" that is
  not a corporate action, so events are wrongly excluded.
- Fix: the lot of the chosen expiry's own contracts (the options' `NewBrdLotQty`, or the same-expiry future) on the
  entry session, and the adjustment test on that same contract on R. Legacy rows (descriptive only) are derived on the
  same-expiry future.

## Minor

1. **Legacy lot "at R" reads exit-session prices.** For legacy rows (to Jul 2024, which covers 2022-24 events), a
   lot on R can only be derived from R's `SETTLE_PR` and `VAL_INLAKH`. Protocol §2 says exit-session data is read only
   for contracts traded, and 2022-26 moves stay unread. The value is internal and rounded, so the harm is nil, but the
   statement should stay literally true. On legacy rows, detect adjustments by the K0-listing test on R and the
   corporate-actions file only (split and bonus adjustments rescale strikes, so K0 disappears).
2. **Report `filed_at` coverage.** A12's XBRL backfill is not complete for every symbol (judge 51). Missing
   `filed_at` falls back to the conservative R rule, and "filing before entry" exclusions cannot be seen. Report the
   share of decision-window events with a matched `filed_at`, descriptively.

## Project rules

Lane 1 (a hand edit under `research/`, a freeze record). No code, no secrets, no model names; files under 350 lines;
labels present. The amendment is append-only beside an unchanged protocol, as judge 97 asked.

**Verdict: FAIL for 291760c60ecfb1739995e163b07b3c89d8c518b1**, on should-fixes 1 and 2. A, B and C pass. D changes
no threshold and uses no outcome, and the exposure is harmless. A re-check needs only `AMENDMENT_1.md` (D1, D3, D4),
its new hash in `FREEZE.md` and, if the source changes, `DATA_SPEND.md`. Nothing may read study data until this
amendment and the `study.py` commit both pass.

## Addendum 1 (15 Oct 2026): amendment 1 revision 1 at 425b69336676083ddb06643820fb9cf2d93c1f50 (a4fbc53..425b693)

425b693 (parent a4fbc53, a merge of `main`) changes only `AMENDMENT_1.md`, `FREEZE.md` and `research/DATA_SPEND.md`.
`PROTOCOL.md` still hashes to `89947b4c...e40a6b`. `AMENDMENT_1.md` hashes to `3b84ecae...35d1e6`, equal to `FREEZE.md`,
and the first version's hash is kept beside it. No `fno/` or `tools/` file changes from 32262d4 to 425b693.
- 9bfa0ad (an unfrozen script) is not judged here. It must not run on study data before the script check.

| Item | Status | Evidence |
|---|---|---|
| Should-fix 1: one downloader, A12's layout | MET | D1 now fills the lists through `build_day_list_librarian("board-meetings")` (`fno/filings/wiring.py:73`): A12's `NseBoardMeetingsSource` (one day per request, `board-meetings_YYYYMMDD.json`), the shared `PacedSession`, `check_day_list`, a `FingerprintingStore` writing A12's manifest rows, and `RawDataLibrarian.fill(start, end)`, which takes an explicit start (`librarian.py:58`), so no code change is needed. The scheduled job's `first_unarchived_day` (`runs_cli.py:179`) walks to the first day without a row from 2005, so the 2007-2018 backlog is still filled later. Pre-filled days are found present, and no gap is hidden. Completeness: a manifest row for every calendar day, no damaged, rejected or unpublished day, or the stage-0 answer is "cannot answer" |
| `DATA_SPEND.md` names the real source | MET | The "Company results dates (A12)" row names A12's daily lists from 1 Dec 2018 and `results-xbrl.csv` |
| Should-fix 2: the traded contract's lot | MET | D4: `NewBrdLotQty` of the chosen expiry's K0 call (else put) on the entry session. Legacy rows use the derivation on the same-expiry future, and the 98% validation uses the same rule. D3: the lot test is on that expiry's K0 options, current format only |
| Minor 1: no R prices on legacy rows | MET | Legacy rows use the K0-listing test and the corporate-actions file only. The current-format test reads R's lot column, not a price |
| Minor 2: `filed_at` coverage | MET | D10, descriptive |
| Builder's additions | ACCEPTED | D5: sessions after the archive's last file are counted from the A7 calendar. This is needed when an expiry lies after the last archived session, and it uses no data. D1: reschedule chains (each fewer than 30 days after the one before) form one group, and the latest meeting with a matched filing is kept. This is a mechanical rule chosen blind; neither addition changes a threshold |
| Data touched since the first version | ACCEPTED (attestation) | Raw F&O and index-close files copied to a local cache with SHA-256 checks; nothing parsed; no list fetched. Copying bytes is not reading |

**On the orchestrator's decision to run the A12 fill alongside the script check:** no reason it is unsafe for the
study. It is archiving only, and the lists hold event dates, not outcomes. Three conditions:
1. **Manifest commits.** The scheduled `filings-archive.yml` (every 6 hours) appends board-meetings rows to the same
   CSV. That file has no `merge=union` in `.gitattributes`, so pulls can conflict at the end of the file. Resolve by
   keeping both sides' rows, never dropping or rewriting one.
2. **Who commits the rows.** A hand-run fill's manifest rows are A12 output, but not a scheduled job's commit
   (refinement 3). Commit them with the fill report, which gives the day counts and the damaged, rejected and
   unpublished lists. My script check will verify a row for every day from 1 Dec 2018 to the last F&O session, and a
   sample of Drive files against their rows.
3. **Nothing parses the lists before the script passes.** This covers the work-in-progress `study.py` too.

**Verdict: PASS for 425b69336676083ddb06643820fb9cf2d93c1f50** (amendment 1, revision 1). The study may not read study
data until the `study.py` and snapshot-script commit passes, with its hash in `FREEZE.md`.

## Addendum 2 (15 Oct 2026): the script commit at adccf53f335c361fbace52dfa6b6a22fc99fce66 (425b693..adccf53)

Range: 1643f32 (code, `AMENDMENT_2.md`, tests, response 109) and adccf53 (script hashes in `FREEZE.md`). 9bfa0ad, the
work-in-progress commit, is inside this range's history; I judge the files as they stand at adccf53.

**What I did:**
- read all 22 `r2study/*.py` files, `study.py`, `snapshot.py`, `AMENDMENT_2.md` and response 109 in full, against
  `PROTOCOL.md` and amendment 1;
- checked every hash in `FREEZE.md`;
- ran the gates;
- planted 30 mutations of my own, one at a time, against `tests/research`, without bytecode.

I read no study data.

## Gates

- `FREEZE.md`: all 27 hashes match the files at adccf53. The protocol is still `89947b4c...`, amendment 1 still
  `3b84ecae...`.
- Full suite at adccf53: **3,272 passed** (Slack token unset). `ruff check` and `ruff format --check` are clean,
  including the study folder. `check_imports` is clean.
- `git merge-tree origin/main adccf53` merges cleanly. The full suite on the trial merge is in my report.
- Largest file: `snapshot_capture.py`, 165 lines.

## No order path, secrets, raw quotes

- **Groww calls.** Every Groww call is a read: `GrowwProvider.expiries` (`get_expiries`), `.chain`
  (`get_option_chain`), `snapshot.py:58-60` `get_quote`, and the sign-in. A grep of the folder finds no other API use.
- **Secrets.** Credentials come only from the environment, through `GrowwProvider`. Nothing prints or stores them.
- **Raw data stays out of the repository.** The raw snapshot goes to Drive's `raw/groww/derivatives/stock-option-quotes/`
  and to a local `.cache/`, which the folder's `.gitignore` excludes. The repository gets only `results.json` and
  `results.md`, which hold bucket statistics, counts and the study's numbers.
- **Exit-session reads.** Only contracts traded, listed strikes and the current-format lot column of R are read
  (`markets.py`, `evaluate.py`). Moves are read only for 2019-2021 (`moves.py` refuses other years; the builder's test
  and my M15 plant both bite).

## The code against the protocol (read line by line)

Correct as written:
- **Strikes and prices.** K0 is the nearest listed strike to the near-month future's close, ties to the higher, steps
  to the listed neighbours, ±2 steps as 2 x step (amendment 1 D6).
- **Untradable legs and prices:** close 0 or no trades; a debit at least its width; a condor credit at least its wider
  wing; a price not positive.
- **Maximum loss:** the debit, or the wider wing less the credit, plus costs.
- **Costs:** C1 charges on entry and exit at the entry price; a pad per leg per side of h x entry price x lot; EN =
  0.05 x P x lot - C - T, with T = 2% of the condor's maximum loss.
- **Liquidity:** 50 contracts on entry and on exit, and 100 contracts of open interest (OI in shares divided by the
  lot).
- **Buckets:** terciles from the quoted legs' previous-session contracts; the merge toward the more liquid neighbour;
  more than 20% one-sided (crossed counted as one-sided, an exact count ratio) makes a bucket untradable, and its
  history legs are not liquid; the 75th-percentile half-spread.
- **Timing:** R from the filing time (09:15-15:30 inclusive, before 09:15 the same session, otherwise the next; no
  `filed_at` gives the session after D); a filing at or before the entry close is excluded; the expiry is at least 5
  sessions after R, counted with calendar sessions after the archive (D5).
- **Reschedules:** a chain is one group, keeping the latest meeting with a filing.
- **Stages:** stages 1-4, and the decision rule with criterion 2 on the fitting events, are as the protocol and
  amendment 1 say.
- **Clusters:** clusters per event with fit, liquidity and EN > 0, divided by window days / 365.25.
- **The YES label** below the 80%-power need of 297.
- **Stage 0's two thresholds.**
- **Statistics:** the ICC by one-way ANOVA with n0 as in D9; a seeded cluster bootstrap; Kish on the ICC of |m|.
- **The once-only guard:** `check_frozen` plus "results exist" refuses.

**`AMENDMENT_2.md` (new, not judged before): ACCEPTED.**
- Items 1-12 resolve open details blind.
- None changes a threshold.
- Where they touch the share's denominator (items 2-4), untradable structures stay in it as not fitting. That is the
  conservative choice, and the new exclusions (no future close, no expiry, options or K0 not listed on R, lot missing on
  R) do not look at prices or moves.
- Kish on |m| (item 9) is the protocol's own section 7.

**Disclosure ruling: harmless (some evidence; it rests on the builder's statement).**
- `snapshot.py --ready` parsed the 14 Oct file into futures and option-symbol sets in memory, and NSE's event calendar.
  It printed only "72 F&O stocks with results in the next 10 sessions".
- That number is a count of scheduled meetings, public calendar information. No price, volume, lot, spread or move was
  shown.
- Every rule was frozen before it, and the snapshot's stock list is mechanical, so the count can steer nothing. 14 Oct
  being the decision window's last session does not change that: no outcome of any event was shown.
- Note: `AMENDMENT_2.md`'s opening line ("written before any data of this study was parsed") should mention this one
  parse, or `FREEZE.md` should. See minor 4.

## My mutations: 22 of 30 caught, 8 survived

| Plant | Result | What it would break |
|---|---|---|
| M3: clusters count events with EN <= 0 (per-event EN > 0 dropped) | **SURVIVED** | Amendment 1 A, the rule criterion 3 rests on: more clusters, a looser YES |
| M30: decision-window filter removed (2019 - Sep 2024 events decide) | **SURVIVED** | Protocol §3: earlier events "never decide" |
| M17: condor width = narrower wing | **SURVIVED** | §5: maximum loss from the wider wing. Steps differ above and below K0 at strike-grid changes, so the loss would be understated and the fit overstated |
| M18: cap with pads `<` instead of `<=` | **SURVIVED** | §5 "at most Rs 10,000" on the criterion-1 path (the no-pads boundary is tested; the with-pads one is not) |
| M23: stage 0 lot-unknown `>=` 10% | **SURVIVED** | §9 "more than 10%" |
| M24: stage 0 coverage `>` 80% | **SURVIVED** | §9 "fewer than 80%" |
| M10: condor tail on the loss without costs | **SURVIVED** | §6.1 T = 2% of the maximum loss (costs included), so EN on S7 |
| M16: Kish on the signed ICC | survived (descriptive) | §7 Kish uses `rho_abs` |
| Caught | M1, M2, M4-M9, M11-M15, M19-M22, M25-M29 | window +1 day, mean EN, exit contracts, OI per lot, the 5-session expiry, the 15:30 filing, the entry-close exclusion, the reschedule pick, two pad sides, the merge direction, the 20% boundary, the K0 tie, the 2022 refusal, the traded contract's lot, the lot change on R, the K0-on-R test, the 120-day filing period, the no-filing R, the 15:00 snapshot cut, crossed quotes, debit = width, p75 |

The code is right on all eight; I read each line. But the run happens once and cannot be repeated (protocol §11), and
quality rule 5 asks for every boundary. So untested decisive rules are should-fixes. The builder's "57 of 57" is true
for its own plants, not for these.

## Should-fix

**1. Tests for the seven decision-relevant survivors: M3, M30, M17, M18, M23, M24 and M10.**
- M3: an end-to-end case where an event fits and is liquid but has EN <= 0 and adds no cluster.
- M30: a pre-window event that would flip the decision if counted.
- M17: a condor with unequal steps.
- M18: the with-pads cap at exactly Rs 10,000.00 and 10,000.01.
- M23/M24: lot-unknown share at exactly 10% and coverage at exactly 80%.
- M10: the S7 tail on the costed loss.
- Tests are not frozen, so adding them changes no hash. If code changes too (should-fixes 2-3), its new hashes go
  into `FREEZE.md` in the fix commit.

**2. The snapshot's 20% "no previous-session row" rule is not enforced by the run, and cannot be.**
- Amendment 2 item 10 says the capture "is not used" above 20%. `snapshot.py` prints STOP and exits 2, but it has
  already written the legs file and uploaded the raw file. `study.py --run --snapshot <legs>` uses any legs file.
- Each leg's `previous_contracts` is 0.0 both for "no row" and for "a row with 0 contracts"
  (`snapshot_capture.py`: `old.contracts if old else 0.0`). So the run cannot tell them apart.
- Fix (study side; `snapshot.py` can stay as frozen): the run rebuilds the legs from the raw Drive file (every payload,
  strike, kind, expiry and lot is in it) and the previous session's F&O file. It applies the 20% rule itself, and above
  it treats the snapshot as absent ("cannot answer yet: no spread evidence").

**3. The results do not say which snapshot they used.** Nothing ties `results.json` to the snapshot: no legs-file
SHA-256, no raw Drive path or SHA-256. A legs file could be replaced or edited unseen. Fix: with should-fix 2, the run
reads the raw file by its Drive path, checks it against the SHA-256 that `snapshot.py` printed (recorded in the
conversation log or a small committed record of counts, path and hash, with no quotes), and writes the path and hash
into `results.json`.

## Minor

1. `check_frozen` checks the hashes of the script files only. `PROTOCOL.md` and the amendments are covered only by
   "the folder is clean". Add their hashes to the check, as `FREEZE.md`'s `sha256sum -c` line intends.
2. A filing in market hours on a muhurat day (the session list keeps muhurat days, amendment 2 item 7) sets R to that
   day, although the market was not open at that hour. This is rare. Count such events, or treat a muhurat day as
   after-hours for R.
3. The default cache is inside the checkout (`.cache/`, ignored by git) and holds the raw snapshot. A default outside
   the repository, or the A4b record-scan rule extended to it, would remove the risk of a `git add -f`.
4. Note the `--ready` parse in `AMENDMENT_2.md` or `FREEZE.md` (see the disclosure ruling).

## The snapshot today

I found nothing in `snapshot.py` or `snapshot_capture.py` that must change:
- read-only calls;
- window 14:00-15:00, with nothing asked or kept at or after 15:00;
- the stock list, expiry, lot, K0 and ±3 strikes per amendments 1-2;
- per-leg and per-stock failures counted;
- the raw file to Drive with every payload.

Should-fixes 2-3 are fixed in the study, from that raw file. So the snapshot may be taken today with exactly adccf53's
`snapshot.py` and `r2study/` files: check them with the `FREEZE.md` hashes before running, and record the printed raw
SHA-256 and Drive path. Taking it reads no outcome. If a later fix had to change the snapshot itself, protocol §9 lets
it be retaken next season under the same protocol.

**Verdict: FAIL for adccf53f335c361fbace52dfa6b6a22fc99fce66** (the analysis run), on should-fixes 1-3. The code
matches the protocol everywhere I read it. `AMENDMENT_2.md` is accepted, and the disclosure is harmless. The
snapshot may be taken today as stated above. `study.py --run` may not run before a PASS on the fix commit.

## Addendum 3 (15 Oct 2026): the fix commit at e634a36bb83d8b2f85d35fdccc437134230d14a8 (adccf53..e634a36)

Changes: `snapshot_legs.py` (new), `analysis.py`, `sessions.py`, `wiring.py`, `study.py`, `FREEZE.md` (revision-1
table), tests, `mutations.json`, response 109. Two commits beside it on the branch, 1738748 and 3ee3ab7, add only
A12 board-meeting manifest rows: 494 appended, every status 200, 2018-12-01 to 2020-04-07 so far, none removed. The
completeness check comes with the final fill commit.

## Gates

- `snapshot.py`, `r2study/snapshot_capture.py`, `PROTOCOL.md` and both amendments are byte-identical to adccf53.
- All 28 rows of the revision-1 table match. Every `r2study/*.py` is listed.
- Full suite at e634a36: **3,283 passed** (Slack token unset). `ruff check`, `ruff format --check` and `check_imports`
  are clean. It merges cleanly with `origin/main`.

## Findings of addendum 2

| Item | Status | Evidence |
|---|---|---|
| SF1: my 8 surviving mutations | MET | Re-run on e634a36: M3, M10, M16, M17, M18, M23, M24 and M30 are all caught now |
| SF2: the run rebuilds the legs and applies the 20% rule | MET | `snapshot_legs.rebuild` reads every quoted payload from the raw file and the previous session's option rows. It is the same lookup as the capture: chosen expiry, (strike, kind), `abs(steps)`, the stock's lot. "No row" (`row is None`) is now counted apart from "0 contracts". `usable` means at most 20% without a row. `analysis.py` uses the snapshot only when usable, else the answer is "cannot answer yet: no spread evidence". My plants N3 (no-row not counted), N4 (an unusable snapshot used) and N6 (signed steps) are caught |
| SF3: the results name the snapshot | MET | `--snapshot PATH SHA256`. The raw Drive file must hash to the printed SHA-256 (`SnapshotMismatch`; plant N2 caught). `results.json["snapshot"]` records the path, SHA-256, start time, stocks, skipped stocks, legs, legs without a row, the share and whether it was used |
| Minor 1: `check_frozen` hashes the protocol and amendments | MET in code; untested | `FROZEN` lists them. My plant N7 (dropping `PROTOCOL.md` from the list) survives; see minor A |
| Minor 2: muhurat filing | MET | `Sessions.irregular` (days with a file that the calendar does not call sessions). A filing on such a day goes to the next session. Plant N5 is caught |
| Minor 3: the cache outside the checkout | MET | `~/.cache/r2-study` |
| Minor 4: the `--ready` parse disclosed | MET | In the revision-1 section of `FREEZE.md` |

## New should-fix

**1. The 20% boundary of the snapshot rule is untested.** Amendment 2 item 10 says "more than 20%" without a
previous-session row, and the capture is then not used. The code (`no_row_share <= 0.20`) is right. But my plant N1
(`<` instead of `<=`) passes all 110 research tests, so at exactly 20% (for example 200 of 1,000 legs) a wrong
comparison would turn a usable snapshot into "cannot answer". This is the same class of rule as the 20% one-sided
boundary, where the builder's own mutation found a real bug. Fix: a test at exactly 20% (usable) and just over it (not
used). Tests are not frozen, so no hash changes.

## Minor

A. A test that `check_frozen` refuses a changed `PROTOCOL.md` or amendment (plant N7).

B. Operator note: `snapshot.py` prints `Drive: raw/<path>`, while `--snapshot` wants the path under `raw/`, without
the prefix. A wrong path stops the run loudly, so nothing is at risk, but say it in the run instructions.

**Verdict: FAIL for e634a36bb83d8b2f85d35fdccc437134230d14a8**, on the one new should-fix (a boundary test). Everything
else in addendum 2 is fixed and verified. A re-check needs only the new test or tests at the next SHA. The frozen
files must stay as at e634a36. The snapshot plan of addendum 2 is unchanged.

## Addendum 4 (15 Oct 2026): the test commit at 02e84d029a4a94bc6122792f1f441fab91165899 (e634a36..02e84d0)

Changes: two tests in `tests/research/test_r2_snapshot_sources.py`, `mutations.json`, the folder's `README.md`, and
fill-progress manifest rows (f2a5749, 3ee3ab7). No frozen file changed: all 28 rows of `FREEZE.md`'s revision-1
table match at 02e84d0, and every `r2study/*.py` is listed.

| Item | Status | Evidence |
|---|---|---|
| Should-fix: exact-20% boundary | MET | 2 of 10 legs without a row is usable, 3 of 10 is not, no legs is not. My plant N1 (`<=` to `<`) is now caught |
| Minor A: `check_frozen` and the protocol | MET | The test changes `PROTOCOL.md` and each amendment in a copy and expects `NotFrozen` naming the file. My plant N7 is now caught |
| Minor B: run instructions | MET | `README.md` step 3: the printed Drive path **without** `raw/`, and the printed SHA-256, and the run refuses a different file |

**Gates on a clean worktree at 02e84d0** (the builder's run collided with the live fill writing `board-meetings.csv`):
- **3,285 passed** (Slack token unset).
- `ruff check`, `ruff format --check` and `check_imports` are clean.
- It merges cleanly with `origin/main`.

**A12 fill so far.** At 1763c63: 1,000 rows appended since adccf53, every status 200, 2018-12-01 to 2021-08-26, none
removed or edited.

**Verdict: PASS for 02e84d029a4a94bc6122792f1f441fab91165899** (the analysis script, revision 1, with its tests). Before
`study.py --run`:
1. The A12 fill finishes and its final commit carries the fill report. I check a manifest row for every calendar day
   from 2018-12-01 to the last F&O session, and a sample of Drive files against their rows. The run itself also
   refuses on a missing day (`MissingResultsDates`).
2. The snapshot is taken with adccf53's `snapshot.py` and `r2study/snapshot_capture.py`, which are byte-identical at
   02e84d0. Its printed SHA-256 and Drive path are logged.
3. The run is made from a commit whose study folder equals 02e84d0's (`check_frozen` enforces it), and it runs once.
After the run: `results.json`, `results.md`, the `DATA_SPEND.md` rows updated to what was read, and my check of the
results against the protocol.

## Addendum 5 (15 Oct 2026): A12 fill completeness at f296e25484860650b253a5143e7ad85530bd1617

Since 02e84d0, the range touches only `research/data/manifests/board-meetings.csv` and response 109. The study folder is
byte-identical to 02e84d0 (`git diff --quiet`).

| Check | Result |
|---|---|
| A row for every calendar day 2018-12-01 to 2026-10-14 (the last F&O session) | MET: 2,875 days, 0 missing, 0 duplicated; every row in the file has status 200 (3,895 rows including 2005-2007); none after 14 Oct |
| Append-only | MET: 0 rows removed or changed since adccf53 |
| Drive files equal their rows | MET: 10 days drawn with seed 20261015 across 2019-2025, each Drive file (`NseBoardMeetingsSource.path_for`) read through the service-account reader, with SHA-256 and size equal to the row: 10 of 10. Bytes hashed only, never parsed |
| Fill report | In the commit message: 2,875 uploaded, 0 damaged, rejected or unpublished, result "complete" |

**Verdict: the fill condition of addendum 4 is MET.** The run may go ahead in this order:
1. Take the snapshot today, 14:00-15:00 IST, with adccf53's snapshot files (byte-identical at 02e84d0). Log its printed
   SHA-256 and Drive path.
2. Make one `study.py --run --snapshot <path without raw/> <sha256>` from a commit whose study folder equals 02e84d0's.
3. Commit the results and the `DATA_SPEND.md` rows updated to what was read. Then I check the results.

## Addendum 6 (15 Oct 2026): results check at ca8e5d5d6baf6b66e1a08a8d1a732e0f2ee83c08

**Verdict: PASS.** The registered answer "NO, stopped at stage 3 (cost wall), trial 53 of 53" follows the frozen rules. There are no blocking or should-fix findings and two notes.

**One run and the snapshot binding (my own checks).**
- **Study folder unchanged.** `git diff 02e84d0 f296e25` and `git diff 02e84d0 ca8e5d5` over the study folder show only the two new files, `results.json` and `results.md`.
- **Freeze hashes.** At ca8e5d5, the 28 revision-1 rows of `FREEZE.md` all hash OK (`sha256sum -c`), covering `PROTOCOL.md`, both amendments, `study.py` and every `r2study/` file. The original table's four superseded script rows differ, as expected.
- **Single results commit.** `results.json` has exactly one commit in all of history, ca8e5d5. `run_commit` reads f296e25, and `trial` reads "trial 53 of 53", the ledger's last row.
- **Snapshot.** I read the raw file from Drive read-only: `groww/derivatives/stock-option-quotes/2026/10/15/r2-snapshot_20261015_140024.json`, 1,543,104 bytes. Its SHA-256 is `b83836e32d8bdfadd5c45f0b001587c9b1086f7e95f7c6d6b794afed42bb6c3f`, equal to `results.json` `snapshot.sha256`.
  - Its own fields: started 14:00:31, finished 14:19:18 IST (inside 14:00-15:00), 0 after the window, 0 errors, 2 legs with no previous row, 3 legs not listed, 1 stock skipped, 73 stock entries. These match the results.
  - `results.json` has `used: true` and a no-row share of 0.2%, under the 20% rule.

**The cost wall follows the frozen rules.**
- **Code matches the protocol.** `evaluate.py`/`structures.py` compute EN = 5% x P x lot - C - T, with:
  - C = C1 charges on entry and exit (exit at the entry price) plus one pad per leg per side (bucket p75 half-spread x leg price x lot);
  - T = 2% of the costed maximum loss for S7 only;
  - e\* = (C + T) / (P x lot).
  This matches PROTOCOL 6.1.
- **Stage logic.** Stage 3's test is criteria 1 and 2: S5, S6 and S7 pass criterion 1 with pads (50.8%, 44.3%, 48.3%, all at least 25%) and fail criterion 2 (median and mean EN below 0). So no structure passes, and section 9 says "NO, stopped at stage 3". Stages 1 and 2 pass on S5-S7 (89.3%/63.4%, 86.4%/55.2%, 79.3%/49.7%), so the stop is at stage 3, not earlier.
- **Recomputed from `results.json`.** Since gross/cost = e/e\* for every event, the median gross/cost must equal 0.05 / median e\*.
  - S5: 0.05/1.012106 = 0.049402. S6: 0.051876. S7: 0.101367. S1: 0.360836. S2: 0.359906. Each equals the reported `median_gross_to_cost` to 6 decimals, so EN, e\* and the cost all come from one consistent cost figure.
  - The implied median S5 debit is about Rs 3,300 a lot (EN / (e - e\*)). That fits a one-step spread at the reported Rs 6.2 lakh median lot value and 1.3% median strike step.
- **Rough hand check (my assumptions: ATM call about 3.4% of the underlying for one month, liquid buckets).** Pads are 2 x (0.065 x Rs 21,000 + 0.023 x Rs 17,700), about Rs 3,540, against a gross of about Rs 165. EN is about Rs -3,500 before charges, the same order as the reported Rs -3,177.
- **Robustness.** e\* of 49-101% against 5% means even halving every pad leaves e\* around 25-50%. The NO does not hinge on the p75 pad choice or the 5% hurdle.
- **Clusters.** 602 clusters / (744 days / 365.25) = 295.5 a year, as reported. Clusters a year are 0.0 for S5-S7 because amendment 1 counts only events with EN > 0.

**The builder's three flaws and the decision window: none touches it.**
1. **Legacy lot derivation, 13% exact.** Legacy rows exist only before July 2024. In the decision window (1 Oct 2024 on), lot unknown is 0.0%, all from the current format's `NewBrdLotQty`. It empties only the descriptive 2019 - Sep 2024 table (536 events), which never decides. The 2019-2021 correlation is reported, not deciding.
2. **"First failed" reads "none" in the descriptive table.** A display flaw in a non-deciding table. The decision table names cap, cap, cap, cap, cost wall, cost wall, cost wall.
3. **Duplicate meetings collapsed (32,858).** Decision-window coverage is 1,617 of 1,626 stock-quarters (99.4%), so no quarter's results date was lost. Even a few percent more or fewer events could not move medians of Rs -2,700 to -3,200 above 0.

**Bookkeeping.**
- `DATA_SPEND.md` now marks as `exposed`: the bhavcopy fields read, the 2019-2021 moves, the snapshot with its hash, and A12's dates.
- 2022-2026 moves stay `fresh` (no exit price was read).
- The ledger row is NO at stage 3, and the idea card is updated.
- `tests/research` at ca8e5d5: 112 passed.

**Notes (not findings).**
1. **"Exactly one run" rests on the builder's statement** plus there being a single results commit. I cannot list every run made in another container. Some evidence.
2. **Merge.** A trial merge with `origin/main` conflicts in three files: `conversations/2026-10-15.md`, `reviews/claude/README.md` and `research/data/manifests/board-meetings.csv`.
   - Main's A12 job has filled 2005-2011 board-meeting rows since the branch point.
   - I compared both sides: 1,020 days appear on both, all with identical SHA-256, and no day has two rows.
   - So the manifest resolves as the union of both sides, sorted by date, never one side only. That needs a full suite on the merged tree before the push, as usual.

## Addendum 7 (15 Oct 2026): merge check, R2 merged to `main` as 72ffc31

**Verdict: merge check complete, matching the PASS.**

- **Parents and history.** `72ffc31` has parents `d72af56` (main) and `ca8e5d5`, the SHA I passed, and it is on `origin/main`. The freeze commit `93a19c3` is in its history: a real merge, not a squash, so B4's ledger guard holds.
- **Branch content intact.** Every file the branch changed that main did not touch is byte-identical to ca8e5d5. That covers the study folder, results, ledger, idea card and `DATA_SPEND.md`. The 28 revision-1 `FREEZE.md` hashes still check OK on the merged tree.
- **The three conflicts, checked line by line.**
  - `research/data/manifests/board-meetings.csv`: same header; 5,125 rows, exactly the union of both parents' rows (set equality), sorted by date, no date twice.
  - `conversations/2026-10-15.md` and `reviews/claude/README.md`: no line of either parent was lost, and there are no conflict markers.
- **Gates on 72ffc31, run by me.** 4,953 passed with `FNO_SLACK_BOT_TOKEN` unset; ruff and check_imports clean.
- **Rule 8.** The protocol allows one run only, so the run of addendum 6 is the record. A second run would break the registration. Noted in `conversations/2026-10-15.md`.

No findings. R2 is closed: NO at stage 3, ledger status `screened_out`.
