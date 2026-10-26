# Judge reviews

Verdict files from the code judge and the lane-2 auditor (process: `docs/JUDGE.md`).

This index starts clean for **Omenix F&O (`exepex/omenix-ingestion`)**: the verdicts carried over from the parent
repository `exepex/trading` were for its forecasting, dashboard and desk stories and did not apply to this
data-ingestion repository, so they were removed in the migration clean-up. History is preserved in git.

New verdicts live here as `reviews/judge/judge_<n>_<story>.md`, numbered with
`python tools/claim_number.py judge-report <slug> --session <id>`, and are listed below as they are written.

| # | Story | Lane | Verdict | File |
|---|---|---|---|---|
| 1 | P1 staging / record split (story text, judge #2) | 1 | FAIL (round 1) | `judge_1_p1-staging-record-split-judge2.md` |
