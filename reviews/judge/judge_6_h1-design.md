# Judge 6: H1 credential isolation (design), branch `story/H1-credential-isolation`, SHA 0fb3312

**FAIL (round 1), lane 1, judge 1; nothing blocking, 3 should-fix.** Design only: the diff is the story (91 lines) and
one pointer line in `docs/PIPELINE_DESIGN.md`. The analysis is sound and the D1 + E-B direction follows from it. The
gaps are the factual count, one missing setup step, and an incomplete residual-risk list.

## Criteria

| Claim | Verdict | Evidence |
|---|---|---|
| 1 Measured problem | PARTLY | The full Drive scope is right (`ops/gdrive_oauth_setup.py:20`, `DRIVE_FULL_SCOPE`). The count is not: finding 1 |
| 2 Owner setup and limits per option | PARTLY | D1's setup omits how the gate reads Staging: finding 2 |
| 3 Unverified items labelled | MET | `drive.file` behaviour, GitHub settings and consent mode are all labelled; the gap list repeats them |
| 4 Recommendation labelled, residual stated | PARTLY | Labelled "reasoning only"; the residual list is incomplete: finding 3 |

## Findings

1. **Should fix: the count.** "All 13 workflows put the same owner Drive OAuth refresh token ... including
   `pipeline-staging.yml`" is wrong. There are 14 workflow files, and 13 of them name the token: 12 of the 13 live
   workflows plus `pipeline-staging.yml`. `participant-oi-watch.yml` does not (`grep -L`). State it exactly.
2. **Should fix: D1's read path has an unlisted credential.** The build section says the gate reads Staging with "the
   existing `DRIVE_READ_SCOPE` service account", and constraint 2 says "it already does". But no workflow holds
   `FNO_GDRIVE_SERVICE_ACCOUNT_JSON` (`grep` over `.github/workflows`: 0); it is used by sessions and readers
   (`storage/README.md:83`). D1's owner setup must add that secret to the `record-writer` environment. The simpler
   alternative is that S shares the staging folder read-only with account R, and the gate reads with R's token. Pick
   one and list its setup.
3. **Should fix: the residual risk after D1 + E-B is incomplete.** Add:
   (a) Until the P-series switch moves them, the 12 live fetchers still need R's full-scope token to write the Record.
   So "a compromised fetcher job holds only S's token" holds only after that migration. Say what protects the Record
   until then (nothing new).
   (b) The gate job itself runs every `requirements.txt` dependency with R's token. A compromised dependency there
   reaches the Record; the problem section names this threat, but the residual list drops it.
   (c) R's token is full-scope over the owner's whole Drive, not just `raw/`, so a leak exposes the owner's other
   files too.
   (d) Detection and recovery: the SHA-256 receipts in GitHub detect a changed Record file. Drive trash and version
   history allow only limited recovery, and there is no backup. Name these as the remaining safety net, or as an
   option.

## Plants

None: this is a design document; I judged it by checking each factual claim against the repository.

## Notes

The D1 reasoning (Google permissions, not convention) and the E-B caveat (protection is a setting; anyone who can
merge to `main` or is an admin can still reach R's token) are correct and honestly labelled. E-A is fairly costed.
