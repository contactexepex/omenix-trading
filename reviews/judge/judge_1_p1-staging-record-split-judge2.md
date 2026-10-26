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
