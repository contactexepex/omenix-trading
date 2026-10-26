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
