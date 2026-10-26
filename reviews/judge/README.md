# Judge reviews

Verdict files from the code judge and the lane-2 auditor (process: `docs/JUDGE.md`).

This index starts clean for **Omenix F&O (`exepex/omenix-ingestion`)**: the verdicts carried over from the parent
repository `exepex/trading` were for its forecasting, dashboard and desk stories and did not apply to this
data-ingestion repository, so they were removed in the migration clean-up. History is preserved in git.

New verdicts live here as `reviews/judge/judge_<n>_<story>.md`, numbered with
`python tools/claim_number.py judge-report <slug> --session <id>`, and are listed below as they are written.

| # | Story | Lane | Verdict | File |
|---|---|---|---|---|
| 1 | P1 staging / record split (story text, judge #2) | 1 | PASS (final be69c3a; judge #2 only) | `judge_1_p1-staging-record-split-judge2.md` |
| 2 | P1 staging / record split (story + code, judge #1) | 1 | PASS (be69c3a; round 3 authorised by the owner) | `judge_2_p1-story.md` |
| 3 | DOC1 schedule status (CLAUDE.md, README) | 1 | PASS (round 2, 01dae73) | `judge_3_doc1-schedule-status.md` |
| 4 | P1b stage-only input (pipeline-staging.yml) | 1 | PASS (64faaa1) | `judge_4_p1b-stage-only.md` |
| 5 | P1b stage-only input (judge #2) | 1 | PASS | `judge_5_p1b-stage-only-input-judge2.md` |
| 6 | H1 credential isolation (design) | 1 | WITHDRAWN (owner decision; FAIL round 1 was given) | `judge_6_h1-design.md` |
| 7 | H1 credential isolation, design (judge #2) | 1 | FAIL (round 1) | `judge_7_h1-credential-isolation-judge2.md` |
| 8 | DOC2 credential posture (design doc, P1 gap list) | 1 | FAIL (round 1, 2 should-fix) | `judge_8_doc2-credential-posture.md` |
