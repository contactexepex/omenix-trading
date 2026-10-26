# Judge 8: DOC2 credential posture, branch `story/DOC2-credential-posture`, SHA 5e6e127

**FAIL (round 1), lane 1 (it describes what protects write-once data), judge 1; 2 should-fix.** Text only:
`docs/PIPELINE_DESIGN.md` and `docs/stories/P1-staging-record-split.md`. Removing the "cannot poison the Record"
claim is right, and the new wording is mostly true. Two statements are wrong.

## Criteria

| Check | Verdict | Evidence |
|---|---|---|
| The "abused workflow cannot poison the Record" claim is removed | MET | Why item 3, the zones paragraph, Security and the P1 gap list are all reworded |
| "Outsiders cannot write Drive" | MET | No workflow has a `pull_request` trigger (grep); `data-checks.yml` has `push: branches: [main]`, which needs write access |
| Staging is a subfolder of the shared folder | MET | `promotion/wiring.py`: `AreaStore(build_owner_drive(env), "staging")` |
| Branch-protection statement | NOT MET | Finding 1 |
| "Every workflow uses the same credential" | NOT MET | Finding 2 |

## Findings

1. **Should fix: branch protection is on, but it does not block direct pushes.** GitHub's branch list (MCP
   `list_branches`, 26 Oct, about 21:20 UTC) reports `main` as `protected: true`. Yet every session and 13 workflows
   (`contents: write`) push straight to `main`, and this judge's own pushes succeed. So a protection rule exists, but
   it does not require a reviewed pull request for these pushers. Replace "recommended but was not confirmed on" with
   that fact: "`main` has a protection rule, but direct pushes are accepted, so the judge review is process, not a
   technical block". The rule's exact settings are not readable from here; say that too.
2. **Should fix: "every workflow uses the same owner Drive credential".** 13 of the 14 workflow files name
   `FNO_GDRIVE_OAUTH_REFRESH_TOKEN`; `participant-oi-watch.yml` does not. Say "every workflow that writes Drive" or
   give the count.

Minor (optional):
- **Detection** is stronger than the text says: the verified Drive cache checks each file against its receipt's
  SHA-256 on every read (`storage/drive_cache.py:3,17`).
- **Recovery** is not stated: only Drive's trash and version history, with no independent backup. One line belongs in
  Security.
- **"The required judge review":** lane 2 changes take the orchestrator's check, not a judge. Say "the lane review
  (`docs/JUDGE.md`)".

## Plants

None: a text-only change, judged by checking each statement against the repository and GitHub.

## Notes

H1 (`judge_6_h1-design.md`) is withdrawn by the owner's decision. My verdict there stays as written, unused.
