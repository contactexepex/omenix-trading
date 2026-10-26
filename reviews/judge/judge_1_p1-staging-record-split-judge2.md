# Judge 1: P1 staging / record split, story text (judge #2 of two)

Branch `story/P1-staging-record-split`, SHA `af1fc7d97017100f209d6ad64ec3f6ae04d5860f` (story only, no code).
**FAIL** (round 1), lane 1. Text-only round: judged by reading it against `main` (`c7a84f8`).

## Criteria (story text vs. design and owner decisions)

| Item | Verdict | Evidence |
|---|---|---|
| No invented numeric freshness window (owner decision 1 open) | MET | default = identity rule; `max_lag_days` ships `null` |
| Identity-rule table matches today's code | MET | `content_checks.py:50-60`: P-OI, P-volume, FII stats pass `day_for(filename)`, title checked; `read_fo_file` / `read_equity_bhavcopy` read `TradDt`, no day compare; legacy `TIMESTAMP` → `TradDt` at `fo_bhavcopy.py:152`; 8 `DATED_SOURCES` = 7 datasets (FO legacy+UDiFF) |
| Gap list covers every Phase-1 design line | PARTLY | finding 3 |
| "Promotes nothing today would not archive" | NOT MET | finding 1 |
| Write-once first-copy semantics kept | NOT MET | finding 2 |
| Claim 1 states the property truthfully | NOT MET | finding 4 |
| Design-doc date fix | MET | diff shows 27 → 26 Oct |
| Schedule disclosure | MET (confirmed) | `index-closes.yml:15-18`, `circulars.yml:9`, `fo-masters.yml:8` and others have live `schedule:` crons; CLAUDE.md's "commented out" is stale (note 1) |

## Findings

1. **Blocking: the gate drops the librarian's calendar and exceptions rules.** `librarian.py:61` archives only
   `calendar.is_session(day)` days and `:81` skips `(dataset, day)` in `build_file_exceptions()` (A1 never-published,
   A23 refused content). The story's checks are "content check + identity rule" only. So a staged file for a
   non-session day, or a refused-content day, would be promoted where today it is not. Fix: Claim 4 adds both rules
   (same calendar, same exceptions file) as checks, each with a bad-case test.
2. **Blocking: unclear which of several passing staged copies is promoted.** Today a session keeps its first copy, and
   later NSE versions go to the revisions area (A11; `revisions.py:3`; `flows-download.yml:3-4`). Claim 3 says only
   "older passing copy used when the newest fails", which implies the newest passing copy wins. Fix: state that the
   **earliest-fetched** passing copy is promoted. Later differing passing copies go to the revisions area through the
   existing path, and are also reported (say which). "Reported as a revision, never written" must also say whether
   the bytes reach the revisions area. If they only reach a report, a version is lost.
3. **Should fix: the design's Phase 1 says "move existing fetchers to write Staging" (`PIPELINE_DESIGN.md`, build plan
   item 1).** The story defers that, which I accept, since live collection stays unchanged. But the owning document
   still promises it for Phase 1. Fix: update build plan item 1 in place to match, so the two documents don't disagree.
4. **Should fix: Claim 1 over-claims.** "Fetchers write only Staging" is false after Phase 1: all 13 live workflows
   still write the Record directly with the same Drive credentials. The design's security property ("an abused
   workflow can at worst drop garbage in Staging") is not met in Phase 1, and the code-level separation is not an
   access boundary. Fix: reword to "the new `stage` command writes only Staging", and add to the gap list: "the Record
   is not credential-separated from fetchers; live workflows still write it".
5. **Minor: the static test is weak.** An AST check for `.put(` calls misses aliasing (`w = store.put`) and any other
   module that imports the Record store. Fix: assert on attribute access `.put` (not just calls), plus a test that
   `Stager` cannot be built with a Record store (type or wiring check).
6. **Minor: the fetch-time format and zone in the staging path are unstated.** Fix: name them (UTC ISO, or IST) so
   ordering in finding 2 is well-defined.

## Plants

None (no code). Code plants follow in the code round.

## Notes

1. CLAUDE.md "Ingestion workflows" says schedules are commented out; `main` has active `schedule:` crons in all 13
   files (`data-checks.yml` also runs on push). This is a lane-2 doc fix for the orchestrator, not this story's.
2. JUDGE.md quality rule 1 was broken once: code `46307f09` on `story/P1-staging-promotion` was pushed before the
   story review. It was disclosed and superseded; I did not judge it.

## Addendum 1: advisory, interim story + code at `759153c6be16cd2a16595e43786fe8c2e7e5a3ea`

**Relabelled advisory** (orchestrator ruling, 26 Oct 2026, 20:52 UTC: 759153c was an interim build. The implementer had
sent it to me as "ready for review", so I judged it). This does not count as a round. The formal round 2 is the
implementer's declared round-2 SHA, judged in Addendum 2 against these findings. Advisory verdict: **FAIL**. Gates re-run by me: 206 passed;
`ruff check`, `check_imports`, `check_numbers`, `test_code_size` clean. `check_records` (LICENSE) and `ruff format
--check` (`tests/ingestion/test_paths.py`) fail identically on `main`, so they predate this branch.

### Round-1 findings

| # | Verdict | Evidence |
|---|---|---|
| 1 calendar + exceptions | ACCEPTED (code) | `runs.py:19-23` sessions only; exceptions skipped in `Stager.stage` and `PromotionRun.promote`. Story claim 4 text not updated (S4) |
| 2 which copy wins | NOT FIXED | `gate.py`: newest-first loop, first passing copy promoted; `PIPELINE_DESIGN.md` "Phase 1 as built" now codifies "newest" (B1) |
| 3 build-plan item 1 | PARTLY | marked "(built)" but still says "move existing fetchers to write Staging" (S3) |
| 4 Claim 1 over-claims | NOT FIXED | claim text unchanged; gap list has no credential-separation line (S2) |
| 5 AST aliasing | NOT FIXED | `test_design_rules.py` counts `ast.Call` only; Stager check is by parameter name (m1) |
| 6 stamp format | ACCEPTED | `staging.py:19` `%Y%m%dT%H%M%SZ`, UTC |

### Findings

- **B1 (blocking): the newest passing copy becomes the record, where today the first copy does.** Scenario: Monday's
  copy A is staged, the promote fails (Drive sign-in, or a push refused), NSE then republishes, and B is staged. Next
  promote writes **B**. Today's librarian keeps A and A11 files B as a revision. That is a different record from
  today's, against the agreed "promotes nothing today would not". Untested: plant M3 (`reversed(copies)`) survives.
  Fix: promote the earliest passing copy, report later differing passing copies as revisions, and add a test with
  two passing, differing copies and an empty record.
- **S1 (should fix, new; receipts): a Record file with no manifest row is never given one.** `gate.py` returns
  ALREADY_RECORDED before any `put`. `librarian.py:76-78` re-puts in that case ("saved by a run stopped before its
  manifest commit"), so the row gets written. If `promote`'s manifest commit fails, the file stays in Drive with no
  receipt until a live librarian happens to pass that day. Fix: mirror that branch, and add a test.
- **S2: Claim 1 and the design's "only the gate writes the Record, by construction" still over-claim.** The 13 live
  workflows write the same `raw` area with the same OAuth secrets (`pipeline-staging.yml` env = theirs). Fix: reword
  it, and add the gap-list line.
- **S3: in `PIPELINE_DESIGN.md`, build-plan item 1 contradicts "Phase 1 as built".** Fix item 1 in place. "Phase 1 as
  built" also restates the story: keep one owner (CLAUDE.md "one functionality, one owning document").
- **S4: the story's claims 3 and 4 don't describe the calendar and exceptions rules.** The promote-side exceptions
  skip is untested: plant M5 survives. Fix: update the text, and add a test that a staged copy on an exception day is
  not promoted.
- **m1:** the AST check should also catch the `.put` attribute (not only calls).
- **m2:** the story table says fo-bhavcopy covers the legacy `TIMESTAMP`, but only `fo-bhavcopy` (UDiFF) is
  promotable. `fo-bhavcopy-legacy` is in neither list.
- **m3:** "identical bytes not staged twice" compares with the newest copy only (A, B, A stages A twice). Fix the
  wording.
- **m4:** `gate.put` doesn't catch `RawFileConflict` / `StoredCopyDamaged`. A race with a live librarian aborts the
  rest of the range (the record stays safe). Plant M19 (the gate's source tag in the wiring) survives too.
- **m5:** the comment in `pipeline-staging.yml` says "freshness and schema checks", but there is no freshness check
  by default.

### Plants

19 planted, 16 caught. Survivors: M3 (copy order, B1), M5 (promote-side exceptions skip, S4), M19 (gate tag in the
wiring, m4).

### Notes

Confirmed: no numeric window (`config.yaml` `null`; plant M15 caught); no existing workflow changed (diff stat); the
new workflow is dispatch-only, with the same pinned SHAs as the other 13 and secrets only via `env`; staging cannot
reach `raw` (plant M13 caught).

## Addendum 2 (superseded by Addendum 3: the SHA was replaced as the round-2 artifact), story + code at `1dd32d949cd4341548687b7dc71a4e33f0dbc3a2`

**FAIL**: one blocking finding (B2, added after first publication; see the note under it) and one should-fix (S1).
After two rounds the owner decides (JUDGE.md).
Gates re-run by me: 219 passed; `ruff check`, `check_imports`, `check_numbers`, `test_code_size` clean; new files
formatted. The diff outside `promotion/` is `pipeline-staging.yml` (new), `config.py` (+1 key) and `revisions.py`
(optional `found_at`, default unchanged). No existing workflow is touched.

### Earlier findings

| # | Verdict | Evidence |
|---|---|---|
| R1-1 calendar + exceptions | MET | `checks.SessionCheck`, `ExceptionCheck`, always wired (`wiring.checks_for`); plants R5-R9 caught |
| R1-2 / B1 first copy wins | MET | `staging.copies` gives earliest first; `gate.py` records `passing[0]`; later passing copies go to the A11 archive with their fetch time; plants R1, R2, R3, R4, R11, R12, R18 caught |
| R1-3 / S3 build-plan item 1 | MET | rewritten in place to the deferral |
| R1-4 / S2 over-claim | MET | Claim 1 reworded; credential-separation gap stated in the story and the design |
| R1-5 / m1 AST + Stager | MET | counts `.put` attributes (plant R14 caught); `TypeError` guard (plant R13 caught) |
| R1-6 stamp | MET | UTC `YYYYMMDDTHHMMSSZ` |
| S4 story text / exceptions test | MET | Principle and Claim 3 list the rules; plant R15 caught |
| **S1 missing receipt** | **NOT MET** | below |
| m2-m5 | open (minor) | below |

### Findings

- **B2 (blocking; Drive load grows without bound): the staging layout makes every promote cost quadratic.**
  `Stager._stage_day` stamps each file with its own `clock()` (`runs.py:75`), so each staged file is a new
  `nse/<stamp>/` folder. `StagingArea.copies` (`staging.py`) lists every stamp folder under the source, then does a
  `get` for the path in each one. All 5 datasets share `nse/`. Measured with a counting store, one stage per day:
  50 days -> 2,500 gets to promote them, 100 -> 10,000, 200 -> 40,000 (n^2). Each real `get` is at least one Drive
  lookup. After about 1 year of 5 datasets (about 1,250 folders), each daily 7-day promote costs about 8,750 lookups
  and keeps growing; a back-fill is in the millions. The gap list's "one Drive folder listing per file" understates
  this. Fix: key Staging by archive path first (`<archive path>/<source>/<stamp>`, or a per-path folder), so copies of
  one path are a single listing, and add a test that bounds `get` calls per promoted path.
  *Disclosure:* I missed this in my first pass. The orchestrator's message (20:53 UTC) mentioned a "measured
  quadratic-layout blocker" with no details. The analysis and numbers above are my own (counting-store script).
- **S1 (should fix; receipts): the gate never repairs a Record file that has no manifest row.**
  `librarian.py:76-78` re-puts the same bytes when the file is stored but not in the manifest. `gate.py` returns
  ALREADY_RECORDED without any `put`. The story's Principle says the gate applies the librarian's rules, so this
  claim is not yet true. I reproduced it with `FingerprintingStore` + `ManifestFolder` over local folders:
  - Run 1: PROMOTED, 1 row.
  - The manifest commit is lost: `cmd_promote` still exits 0 on a failed commit (the same as the librarian, which is
    why the librarian repairs on its next run). I simulated this by deleting the uncommitted row.
  - Run 2: ALREADY_RECORDED, 0 rows, Drive file present. The file now has no receipt for as long as only the gate
    touches that day.

  Fix: when `held` is not None and the filename is missing from the dataset's fingerprints, re-put `held`. The store
  keeps its copy and writes the row. Add a test with a fingerprinting record store.
- **m2:** the table says fo-bhavcopy covers the legacy `TIMESTAMP`, but only UDiFF `fo-bhavcopy` is promotable, and
  `fo-bhavcopy-legacy` is in neither list.
- **m4:** plant R17 survives: the gate's source tag in `wiring.py` is untested. A wrong tag gives "not staged" on every
  day, so it fails loudly (exit 1 and an alert), not silently.
- **m5:** `pipeline-staging.yml:4` still says "freshness and schema checks", but there is no freshness check by
  default.
- **m6:** "Phase 1 as built" in `PIPELINE_DESIGN.md` restates the story (one functionality, one owning document).

### Plants

18 planted on this SHA, 17 caught. Survivor: R17 (m4).

### Note for the owner (reasoning only)

B2 needs a layout change in `staging.py` (small, but it is the Staging contract) and S1 about 4 lines. The rest of
Phase 1 meets every criterion I set. If the owner allows a
scoped re-check, I would verify B2 and S1 alone: each fix, its test, and a plant of it.

## Addendum 3: round 2 (formal; the orchestrator's designated artifact), story + code at `f6120cc132d1fb80edc70036e0d7e4a0695a5dbb`

**PASS**, lane 1, judge #2 of two. Round record, stated openly:
- `af1fc7d`: round 1.
- `759153c`: advisory (interim).
- `1dd32d9`: Addendum 2; the implementer declared it round 2, then the orchestrator and implementer superseded it
  with this SHA.
- `f6120cc`: the formal round 2.

Addendum 2's findings are the checklist below. Gates re-run by me: 229 passed; `ruff check`, `check_imports`,
`check_numbers`, `test_code_size` clean; new files formatted. Outside `promotion/`, only `pipeline-staging.yml`
(new), `config.py` (+1 key) and `revisions.py` (optional `found_at`) change. No existing workflow is touched.

| Finding | Verdict | Evidence |
|---|---|---|
| B2 quadratic staging reads | MET | layout is now `<source>/<archive path>/<stamp>`, one listing per path; my counting script: 50/100/200 days -> 50/100/200 gets (was 2,500/10,000/40,000) |
| S1 missing receipt | MET | `gate.py` re-puts `held` when a passing copy equals it; my repro: run 2 ALREADY_RECORDED with 1 row (was 0); plant F1 caught |
| B1 first copy wins | MET | plants F4, F5 caught |
| calendar, exceptions, identity, schema | MET | plants F9, F10, F13, F16 caught |
| m1, m3 | MET | `.put` attribute AST check; wording "equal to the newest staged copy" |
| m2 fo legacy | MET | gap list: pre-2024 `NseLegacyFoSource` not promotable |
| m4 conflict / gate tag | MET | `RawFileConflict` becomes a CONFLICT verdict (plant F3 caught); wired end-to-end test (plant F8 caught) |
| m5 workflow comment | MET | names the real checks; no window unless configured |
| m6 design duplication | MET | "Phase 1 as built" is a pointer plus facts; the target and not-met lines are explicit |

### Minor (not blocking; for a follow-up)

1. Plant F14 survives: counting CONFLICT as recorded (exit 0, no alert) breaks no test. The code is right today
   (CONFLICT is not in `RECORDED`, so it alerts). Add a test that a CONFLICT day is a problem.
2. Plant F2 survives: re-putting `held` with no matching passing copy breaks no test. Harmless, since the bytes are
   the same and the row describes held bytes, but the guard is unpinned.
3. `pipeline-staging.yml`: the stage step has `continue-on-error: true` and a closing `exit 1`. Correct (promote
   still runs, and the run still fails), but the first real dispatch should confirm the run turns red.

### Plants

16 planted on this SHA, 14 caught. Survivors: F2 and F14 (minor 1-2).

### Merge conditions (JUDGE.md)

Run the gates on the merged tree. The first real run is `pipeline-staging.yml` by hand, dry-run first, then one
dataset over 7 days; record the result in the merge follow-up. The two-judge rule still applies: this PASS is mine
only.

## Addendum 4: owner-authorized full fresh re-review of `f6120cc132d1fb80edc70036e0d7e4a0695a5dbb`

**FAIL** on one should-fix, which is tests only (S5). There is no code defect and no blocking finding. **This
changes my Addendum 3 PASS on the same SHA.** Re-done from scratch, the review found three surviving plants in one
new branch. Under JUDGE.md quality rule 4 (every criterion needs a test that fails when its code is broken), that is
not a minor.

Re-verified from scratch:
- 229 tests pass, and every gate is clean.
- Every changed file, story and workflow re-read in full.
- The quadratic cost is gone. `Stager` stages into `<source>/<archive path>/<stamp>`, and `copies()` is one
  `checksums` listing of that path's folder plus one read per copy. My counting script: 50/100/200 days give
  50/100/200 gets. `test_staging::...one_listing_and_one_read_per_copy` pins it (plants F12 and N5 caught).
- First copy wins, the librarian's rules apply, S1 repair is in, and identity is checked. Plants F1, F4, F5, F9,
  F10, F13, F16, N2, N3 and N6 caught.
- The wording is honest: Claim 1 is code-level only, and the gap list and design doc say plainly that credential
  separation is not met.
- No existing workflow is touched; `revisions.py` gets an optional argument with the default unchanged.

### Finding

- **S5 (should fix; tests only): the new re-put and conflict branch in `gate.py` is only partly pinned.** 23 plants
  in total on this SHA; three survive. I checked by script that the code is correct for each:
  - **F14:** counting CONFLICT as recorded. Claim 5 says a conflict is a "problem" (alert, exit 1), and today
    `PromotionReport.problems()` lists it. A regression would silently hide a Record/manifest disagreement.
  - **N1:** re-putting `passing[0]` instead of `held`. Scenario: the live path recorded X, and Staging holds Y (fetched
    first), then X. The code gives ALREADY_RECORDED, keeps X, and files Y as a revision (verified). With N1 it would
    report a false CONFLICT.
  - **F2:** re-putting `held` with no passing copy equal to it. The guard is unpinned.

  Fix: three tests. (1) A CONFLICT day is in `problems()`, alerts, and exits 1. (2) The X / Y-then-X case above.
  (3) A held file with no equal passing copy is not re-put, so `record.saved` stays empty.

### Notes (not findings)

1. A damaged held copy is not re-validated by the gate. The librarian reports it as `damaged`; the gate gives
   ALREADY_RECORDED and files passing copies as revisions. The daily coverage check (`data-checks.yml`) still
   catches the damage.
2. A staged copy on a day whose exception was filed after staging is a problem, not "excepted". The stager skips
   exception days, so this only happens in that window. It is reported, not lost.
3. `pipeline-staging.yml` checks `DAYS` in the stage step only. The promote step uses it quoted from `env`, so
   there is no injection; a bad value only fails the step.

### Plants

23 planted on this SHA (Addendum 3's 16 plus N1-N7), 20 caught. Survivors: F2, F14 and N1 (S5).
