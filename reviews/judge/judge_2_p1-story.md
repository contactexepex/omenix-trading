# Judge 2: P1 story text (staging / record split), branch `story/P1-staging-record-split`, SHA af1fc7d

**FAIL (round 1 of 2), lane 1, judge 1 of 2.** Story text only; no code on the branch (diff: the story and a 2-line
`docs/PIPELINE_DESIGN.md` date and link fix).

## Criteria

| Criterion | Verdict | Evidence |
|---|---|---|
| Fail-closed identity default per dataset | MET (as text) | participant-oi, participant-volume and fii-stats checks already take the claimed day (`content_checks.py:51-60`); fo/cm get a new check; index-close and delivery are excluded |
| No numeric window by default; a swappable seam | MET (as text) | `FreshnessCheck` wired only when `promotion.max_lag_days` is set; must ship unset, with a config test |
| Only the gate writes the Record | PARTLY | true in code only; see finding 2 (credentials) and finding 3 (revisions) |
| Gap list covers every design requirement of Phase 1 | NOT MET | finding 2 is in neither list |
| Live collection unchanged | MET (as text) | adds a dispatch-only workflow; no edits to existing ones |

## Findings

1. **Should fix: claim 1 overstates.** "Fetchers write only Staging" is false after Phase 1: all live workflows keep
   writing the Record directly (the gap list's third item). Reword it as "the new `stage` command writes only Staging".
2. **Blocking: credential separation is missing from the gap list.** Staging would be an `AreaStore` on the same owner
   Drive (`build_owner_drive_store`, `storage/wiring.py`), so any job holding that credential can still write `raw/`.
   The design's Security section says an abused fetcher "can at worst drop garbage in Staging". Phase 1 gives only
   code-level separation. Either add it to the gap list (what is missing: a separate credential or Drive folder
   permission for Record writes) or deliver it.
3. **Should fix: the revision branch is ambiguous.** "Reported as a revision (existing revision path), never written."
   The existing path (`revisions.py`, `RevisionArchive`) writes the bytes to the `revisions` area plus an index row.
   Say which one the gate does. If it writes, the static-test allow-list and the `staging/` path spy test must account
   for it.
4. **Should fix: a failing copy is re-reported forever.** Failing copies stay in Staging with no retention rule
   (gap list), and claim 5 exits 1 and alerts on every non-promoted file. Every later `promote` run would then fail
   and alert again for the same file. Define which days or copies a run examines, and when a failed copy stops being
   reported (for example, once the Record holds the path or a later copy passes). When an older passing copy is
   promoted over a failing newer one, say that the failure is still reported.
5. **Minor: cm-bhavcopy "every row".** `read_equity_bhavcopy` (`nse_files.py:33-49`) keeps only EQ and BE rows. The
   new check must read `TradDt` on all rows, not through that filtered reader. State this.
6. **Minor: the index-close reason is inaccurate.** The repo's fixture (`tests/shared/test_fo_bhavcopy.py:37`) has an
   `Index Date` column (dd-mm-yyyy). The honest reason is "not confirmed against a real archived file". Excluding it
   is accepted: a wrong date-format guess would reject every real file.
7. **Minor: fetch-time format.** Give the zone and format of `<fetch time>` (IST, sortable, like `REVISION_NAME` in
   `revisions.py:26`). Choosing the newest copy depends on its order.

## Plants

None: story text only, no code. Plants come with the code review.

## Notes

- Process: the implementer pushed a code draft (`story/P1-staging-promotion`, 46307f09) before the story was judged,
  which deviates from JUDGE.md quality rule 1 without authorisation. The orchestrator says story-first holds from now
  on. That draft is superseded and was not reviewed.
- The implementer's flag is correct: `CLAUDE.md` says the schedules are commented out, but `.github/workflows/`
  has active `schedule:` crons (for example `circulars.yml:9`, `flow-history.yml:10`). Two jobs are `if: false`
  (`participant-oi-release.yml:95`, `participant-oi-sweep.yml:71`). This is a rule-document fix for the orchestrator,
  not this story.
- The pipeline design is still a DRAFT with open owner decisions. Phase 1 as scoped needs none of them.

## Addendum 1: story + code, SHA 759153c (interim, not counted as a round)

**FAIL, lane 1, judge 1 of 2.** Reviewed because the implementer asked for it explicitly. The orchestrator then
said 759153c was interim and that round 2 is the implementer's next "round-2 artifact" SHA; these findings are
early feedback for that SHA. Gates rerun by me: 206 passed; ruff, check_imports, check_numbers and code size are
clean. `check_records` refuses LICENSE e-mails and `ruff format` flags `tests/ingestion/test_paths.py`; both fail the
same way on `main`, so neither comes from this branch. Only one workflow was added (`pipeline-staging.yml`, dispatch
only, pins match the other 13).

Round-1 findings: 1 OPEN (claim 1 unchanged). 2 OPEN (no credential gap; staging uses `build_owner_drive`, the same
credential as the Record, `promotion/wiring.py:32-36`). 3 PARTLY (code only reports `DIFFERS_FROM_RECORD`; story claim
3 still says "existing revision path"). 4 OPEN (REJECTED and DIFFERS re-alert and exit 1 on every later run). 5 OPEN
(`equity_content_days` uses the EQ/BE-filtered reader, `datasets.py:33-34`). 6 OPEN. 7 FIXED (UTC `%Y%m%dT%H%M%SZ`).

New findings:

8. **Blocking: staging lookups grow quadratically.** There is one stamp folder per staged file (`staging.py:51`; the
   clock is read per file, `runs.py:73`). `copies()` does one `get` per stamp folder (`staging.py:57-61`), and each
   Drive `get` walks the whole folder chain (`google_drive.py:96-102`). `stage()` scans every stamp for a file not
   staged before. Measured with a counting store: staging 250 files cost 31,125 gets and 1,000 files cost 499,500
   gets (n(n-1)/2); each later lookup costs n gets. The gap list's "one Drive folder listing per staged file" is
   wrong. Fix the layout, not the cost: `<source>/<archive path>/<stamp>` (as `Revision.revision_path` does), so one
   listing of one folder finds every copy of a path.
9. **Should fix: test gaps (my plants, 29 in all, 4 survived).** (a) `PromotionRun` with the sourced-exception skip
   removed: 206 pass. (b) `cmd_promote` with the config window ignored (`max_lag_days` forced to None): 206 pass, so
   the owner-decision seam is untested end to end. (c) Minor: `ALERT_LINES` 5 changed to 50: 206 pass. (d) Minor:
   `stamp_of` without `astimezone(UTC)`: 206 pass.
10. **Should fix: documents.** `PIPELINE_DESIGN.md`'s new "Phase 1 as built" section repeats the story (one
    functionality, one owning document). It also marks build-plan item 1 "(built)" although "move existing fetchers to
    write Staging" is not done. Story lines 3-5 still say "no code". The workflow header says "the freshness and schema
    checks", but freshness is off.
11. **Minor: one unpublished day blocks every promotion in the workflow.** `stage` exits 1 when any day in the range
    is not published, and the `promote` step then never runs. State this or decide otherwise.

Plants: 29 planted, 25 caught, 4 survived (9a-d).

Notes: Process: code was pushed on top of a story that had FAILED, with its round-1 findings not addressed. This is
the second departure from quality rule 1. Rounds: per the orchestrator, round 2 (the last) is the next artifact SHA.

## Addendum 2: story + code, SHA 1dd32d9 (round 2 of 2, final)

**FAIL, lane 1, judge 1 of 2. Two rounds are used, so the owner decides (JUDGE.md "Rounds").** My gates: 219 passed;
ruff, check_imports, check_numbers and code size are clean. The only `ruff format` finding is the pre-existing
`tests/ingestion/test_paths.py`. Only one workflow was added, dispatch only, and no existing workflow is touched.

Round-1 findings: 1 FIXED (claim 1 now covers `stage` only, story:56-59). 2 FIXED: credential sharing is disclosed
honestly in the gap list (story:73-76) and in the design, and the AST test is presented as code-level enforcement
only, not a security boundary. 3 FIXED (first copy wins and later versions go to the A11 sink; my plants caught all).
4 FIXED (problem vs note rule, `--from` required, tested). 5 FIXED (all rows, caught). 6 FIXED. 7 FIXED (UTC, stated).

Interim findings (759153c):

8. **Blocking, still open: staging lookups are quadratic.** The layout and code are unchanged (`staging.py:51,63-69`).
   I re-measured on 1dd32d9 and got the same numbers: staging 250 files costs 31,125 gets and 1,000 files cost
   499,500; each lookup costs n gets, and each Drive `get` walks the folder chain. The gap list (story:83) still says
   "one Drive folder listing per file", which the code contradicts. Fix the layout to `<source>/<archive path>/<stamp>`.
   If the owner instead accepts the cost for dispatch-only use, the gap line must state the measured cost, and this
   becomes a should-fix before any back-fill or schedule.
9. **Should fix, partly open.** My second plant run: 27 plants, 21 caught, 6 survived.
   (a) `cmd_promote` with the config window forced to None: 219 pass. This survived both of my reviews, so the
   owner-decision seam is still untested end to end.
   (b) NEW: wiring a no-op revision sink in `build_promotion_run`: 219 pass, so a wiring slip would silently lose every
   later NSE version.
   (c) NEW: removing `notes()` from `PromotionReport.lines`: 219 pass, so claim 5's "printed in the log" is untested.
   (d) Minor: `ALERT_LINES` 5 changed to 50, and `stamp_of` without UTC conversion, both survive.
   (e) Minor: removing the layout call in `equity_content_days` survives, because `SchemaCheck` already runs the
   same reader. The call is a duplicate: drop it or say why it stays.
10. **Should fix, partly open.** Build-plan item 1 is fixed. The design's "Phase 1 as built" section still repeats
    the story (one functionality, one owning document; keep one line and the link). The workflow header
    (`pipeline-staging.yml:4`) still says "freshness and schema checks", but freshness is off by default.
11. **Minor, open.** One unpublished day makes `stage` exit 1, and then the workflow's `promote` step never runs.

Plants: 27 planted on 1dd32d9, 21 caught, 6 survived (9a-e).

Notes: Confirmed against the code: the gate applies the librarian's session, archive-range and exception rules
(planted and caught), and `RevisionArchive.capture(found_at=None)` keeps its default behaviour. For the owner: the core
safety properties hold (fail-closed identity, no default window, first copy wins, never overwrite, credential gap
disclosed). The FAIL rests on finding 8 (measured, and wrongly described in the gap list) and on three untested
wiring paths.

## Addendum 3: story + code, SHA f6120cc (round 3, authorised by the owner after the two-round limit)

**FAIL on two should-fix findings, no blocking finding left; lane 1, judge 1 of 2.** The owner authorised this full re-review
after round 2 (1dd32d9, Addendum 2), as the orchestrator relayed. My gates: 229 passed; ruff, check_imports, check_numbers and code size are clean, and the
only `ruff format` finding is the pre-existing `test_paths.py`. Only `pipeline-staging.yml` changed under `.github/`.

Earlier findings:
- #8 FIXED. The layout is `<source>/<archive path>/<stamp>` (`staging.py:73-76`). My counting store, re-run: 1,000
  files staged, 0 extra reads while staging, and 1 read per lookup (before: 499,500). The old layout planted back
  makes 54 tests fail.
- #9a, #9d and the `ALERT_LINES` plant: FIXED (all caught now).
- #10 FIXED. The design keeps a pointer plus 3 facts, Security says "not met yet", and the workflow header is
  corrected.
- #11 FIXED. Staging uses `continue-on-error`, `promote` always runs, and a final step fails the run.
- Round 1, 1-7: still fixed.
- Pushback accepted: alerts are not deduplicated across runs. The rule is defined (story, "What a run examines"), the
  workflow is dispatch-only, and the ledger is in the gap list.
- The new manifest re-put is checked as safe: Drive `put` of the same bytes is a no-op
  (`google_drive_upload.py:37-41`), and `ManifestFolder.record` ignores the same row and refuses a different SHA
  (`manifest_folder.py:72-83`), which the gate maps to `CONFLICT`.

Findings:

12. **Should fix: a conflict on a write-once record does not have to be reported.** With `CONFLICT` added to `RECORDED`
    (`runs.py:81`), all 229 tests pass: a record-or-manifest mismatch would then exit 0 with no alert. The code is
    right today (`CONFLICT` is not in `RECORDED`); the test is missing. Add a `PromotionReport` or CLI test: a conflict
    gives exit 1 and an alert.
13. **Should fix: the revision sink's wiring is untested (flagged in Addendum 2, 9b).** A no-op sink in
    `build_promotion_run` (`wiring.py:77-78`) still passes all 229 tests, so a wiring slip would lose every later NSE
    version silently. `test_wired_pipeline.py` should stage two passing versions and assert that one lands in the
    revisions area with an index row.

Minor, not blocking: `notes()` removed from the report lines survives, so the "printed in the log" claim is
untested; re-putting the held file without a passing copy survives, but is harmless (same bytes); the duplicate
layout call in `equity_content_days` is kept.

Plants: 27 planted on f6120cc, 23 caught, 4 survived (12, 13, the two minor ones above). A plant dropping
`path_parts(source)` in `_name` also survived, but the store's own path check still refuses bad tags, so it is no
finding.

Notes: For the owner (strong evidence: measured and planted): no blocking finding remains. The safety properties hold,
the cost problem is fixed, and the credential gap is disclosed. What is left is two missing tests that guard lane-1
behaviour; the code itself is correct. That is 2 small tests to a PASS.

## Addendum 4: delta check f6120cc..056a0e6 (final SHA, inside the round 3 the owner authorised)

**PASS, lane 1, judge 1 of 2.** Delta: tests plus one reader change in `datasets.py`. No layout, gate, wiring or
workflow code changed. My gates on 056a0e6: 234 passed; ruff, check_imports, check_numbers and code size are clean
(the only `ruff format` finding is the pre-existing `test_paths.py`). Lookup cost re-measured: 1 read per lookup with
1,000 files staged.

| Finding | Verdict | Evidence (my own plant on 056a0e6) |
|---|---|---|
| 12 CONFLICT counted as recorded | FIXED | `CONFLICT` added to `RECORDED`: 1 failed |
| 13 no-op revision sink in the wiring | FIXED | no-op sink in `build_promotion_run`: 1 failed |
| Minor: notes in the log | FIXED | `notes()` dropped from `lines()`: 1 failed |
| Minor: re-put without a proving copy | FIXED | `if True:` re-put: 1 failed |
| Minor: duplicate layout call | FIXED | removed; `SchemaCheck` keeps the layout check |
| Reader change (missing or empty `TradDt`) | SAFE | `fromisoformat("")` raises `ValueError`, and `ContentDayCheck` turns that into a rejection reason. Plants "skip rows without a date" and "EQ/BE rows only" fail 1 and 2 tests |

Full regression set (27 plants from Addendum 3) re-run on 056a0e6: all caught except the redundant `path_parts(source)`
plant (the store's own path check still refuses bad tags; no finding).

Note (not a finding): the story's Evidence line says 232 tests; 234 pass on 056a0e6.

## Addendum 5: final SHA be69c3a (supersedes 056a0e6)

**PASS, lane 1, judge 1 of 2.** 056a0e6..be69c3a adds one test in `tests/ingestion/promotion/test_gate.py` (+13 lines,
judge #2's S5 case) and changes no production code. My gates on be69c3a: 235 passed; ruff, check_imports,
check_numbers and code size are clean. My 7 targeted plants re-run on be69c3a: all caught (#12 conflict counted as
recorded, #13 no-op sink, notes hidden, re-put without a proving copy, conflict swallowed, and both reader plants).
The Addendum 4 verdict carries over to be69c3a.
