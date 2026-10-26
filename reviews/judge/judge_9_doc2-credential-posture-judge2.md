# Judge 9: DOC2 credential posture, docs (judge #2)

Branch `story/DOC2-credential-posture`, SHA `5e6e127ba9e560386371ed6dbd360a338cb8cdf0`; Markdown only
(`docs/PIPELINE_DESIGN.md`, `docs/stories/P1-staging-record-split.md`). **FAIL** (round 1), lane 1 (a hard-line
area: write-once data). The accepted owner decision is recorded honestly, but two statements still over-claim, and
removing exactly that kind of claim is this change's purpose.

## Criteria

| Item | Verdict | Evidence |
|---|---|---|
| Owner decision recorded (shared folder and credential, code-only separation) | MET | Security section; P1 gap-list line reworded |
| "A fetcher's credential can write or delete the Record" said plainly | MET | `PIPELINE_DESIGN.md` Security, first new bullet |
| No `pull_request` trigger | MET | `grep -l pull_request .github/workflows/*.yml`: none |
| Branch protection stated as unconfirmed | MET | stated |
| Receipt-based tamper detection, with its limit | MET | "a change that also rewrites the receipt would not be caught" |
| No remaining wording implies protection that does not exist | **NOT MET** | findings 1-3 |

Gates (text only, per CLAUDE.md): doc-reading tests 53 passed; `check_numbers` clean; record scan clean on both files.

## Findings

1. **Blocking: "outsiders cannot write Drive at all" is false.** It appears at `PIPELINE_DESIGN.md:17` and in the
   Security bullet. Every job runs `pip install -r requirements.txt` while it holds the full-scope token, and the
   requirements are unpinned ranges with no hashes (`requests>=2.31`, `PyYAML>=6.0`, `google-auth>=2.35`,
   `cryptography>=42`, plus their transitive dependencies; only `xlrd` is pinned; no `--require-hashes` in any
   workflow). A malicious new release of any of them is an outsider's code running with write access to the whole
   Drive. Fix: limit the claim to "not through this repository's pull requests or forks", and name the dependency
   supply chain as a remaining outsider path. Pinning with hashes is a mitigation the owner may choose; say that it
   is not done.
2. **Blocking: `PIPELINE_DESIGN.md:68-69` still reads "Garbage cannot become a record — this is the security
   property".** Two things make that false:
   - With one shared credential, any job can write `raw/` directly, past the gate.
   - Even through the gate, a well-formed forged file (right layout and date, false numbers) passes every check: the
     gate checks format, not authenticity.

   Fix: make it a data-quality property only ("a malformed file is not promoted by the gate"), and say the gate does
   not detect forged but well-formed data. The cross-source agreement planned for Phase 4 is the planned check.
3. **Should fix: two "target" statements are still written as present fact.**
   - `PIPELINE_DESIGN.md:47-48`: "Each [fetcher] writes **only to Staging**". The 13 live workflows write the Record
     directly.
   - `:50-51`: the gate "is fully public-repo-safe". It holds the full-scope token.

   Fix: mark the first as the target. Reduce the second to "needs no broker key".

## Notes

1. My H1 verdict (judge 7) is withdrawn with H1 (owner decision); it is marked so in the README.
2. Wording suggestion for finding 2, since the owner accepted the shared credential: "The gate keeps malformed files
   out of the Record on the stage-then-promote path. It does not protect against a job that writes `raw/` directly,
   or against forged but well-formed files."
