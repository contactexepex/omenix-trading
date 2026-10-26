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
