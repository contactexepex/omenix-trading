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

## Addendum 1: SHA 1909b90 (round 2 of 2)

**FAIL, round 2. Two rounds are used, so the owner decides (JUDGE.md "Rounds").** The substantive change since
5e6e127 is one new residual-risk bullet in Security: full scope, mergers and admins, a compromised dependency,
limited recovery. That bullet is correct and settles my minor "recovery" note. My two should-fix findings are not
addressed:
- **Finding 1, OPEN.** `PIPELINE_DESIGN.md:111` still says branch protection "is recommended but was not confirmed
  on". GitHub reports `main` as `protected: true`, while direct pushes are accepted.
- **Finding 2, OPEN.** `:104` still says "every workflow uses the same owner Drive credential". It is 13 of 14.

New, and blocking: the doc now contradicts itself.
- **3.** The new bullet says "a compromised dependency installed in any job can use it", yet `:17` and `:108` still
  say "**outsiders cannot write Drive at all**". A dependency's publisher is an outsider. Verified: every
  `requirements.txt` entry except `xlrd` is an open `>=` range, and no workflow uses `--require-hashes` (grep: 0).
  Narrow the claim to "not through this repository's pull requests or forks".
- **4.** `:68-69` still reads "**Garbage cannot become a record** — this is the security property". With one shared
  credential any job can write `raw/` past the gate, and a well-formed forged file passes every check (the gate checks
  format and date, not authenticity). Make it a data-quality statement about the gate only.
- **Should fix 5.** `:48` "Each writes **only to Staging**" and `:51` "fully public-repo-safe" are still written as
  present fact. Mark the first as the target and reduce the second to "needs no broker key".

Transparency: findings 3-5 are things I missed in round 1. I re-read the full document at 1909b90 after the branch's
merge of `main` showed me judge #2's verdict (`judge_9_*`) inside the diff. I checked each finding myself, by grep
and by reading the lines cited, and I accept them on that evidence, not on judge #2's word.

## Addendum 2: SHA 3b766c8 (re-check after round 2; the orchestrator or owner rules on the count)

**PASS, lane 1, judge 1.** Every open finding is fixed:
- **1** Branch protection: `:116-117` now reads "GitHub reports `main` as protected, but direct pushes are accepted
  ... process, not a technical block; the rule's exact settings are not readable from here."
- **2** The count: "13 of the 14 workflow files that write Drive ... `participant-oi-watch.yml` holds none" (`:106`),
  and the same in the P1 gap list.
- **3** Outsiders: narrowed to "no outsider writes Drive through a fork or a pull request" (`:17`, `:110`). Supply
  chain is named as an open path, with no `--require-hashes` and hash-pinning not done (`:111-113`).
- **4** "Garbage cannot become a record" is now "a **data-quality** property ... **not authenticity**", with the
  direct-write path named (`:68-71`). The residual list adds forged staged files and deletion of the genuine copy.
- **5** `:49` "In the new path ... (code level; the live workflows still write the Record directly)". "Fully
  public-repo-safe" is removed, and it is reduced to "needs no broker key".
- The minor points (detection on read, recovery limits, lane wording) are taken.

Gates (text only): doc-reading tests 53 passed; record scan clean on both files; `check_numbers` clean.

Minor, not a finding: the zones table (`:27`) still lists the Record writer as "the promotion gate only". The paragraph
under it calls that the core rule, enforced in code only, so it reads as the target. Optional: add "(target)".
