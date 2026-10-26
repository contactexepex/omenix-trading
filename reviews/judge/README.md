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
| 7 | H1 credential isolation, design (judge #2) | 1 | WITHDRAWN (H1 dropped by the owner; was FAIL round 1) | `judge_7_h1-credential-isolation-judge2.md` |
| 8 | DOC2 credential posture (design doc, P1 gap list) | 1 | PASS (3b766c8, re-check after round 2) | `judge_8_doc2-credential-posture.md` |
| 9 | DOC2 credential posture, docs (judge #2) | 1 | PASS (3b766c8; third pass, see file) | `judge_9_doc2-credential-posture-judge2.md` |
| 10 | P1c stage-only labels | 1 | PASS (ebfafca) | `judge_10_p1c-labels.md` |
| 11 | P1c stage-only labels (judge #2) | 1 | PASS (round 2, ebfafca) | `judge_11_p1c-stage-only-labels-judge2.md` |
| 12 | SEC1 hash-pinned requirements, story (judge #2) | 1 | PASS (story a8efd5b; final build be23751) | `judge_12_sec1-hash-pinning-judge2.md` |
| 13 | SEC1 hash-pinned requirements (story text) | 1 | PASS (story a8efd5b, final be23751) | `judge_13_sec1-hash-pinning.md` |
| 14 | SEC1b minors (relock pin, pipx, portable header) | 1 | PASS (e01d717) | `judge_14_sec1b-minors.md` |
| 15 | SEC1b minors (judge #2) | 1 | PASS (e01d717) | `judge_15_sec1b-minors-judge2.md` |
| 16 | P1d first stage-only runbook (judge #2) | 1 | PASS (7e7c035) | `judge_16_p1d-runbook-judge2.md` |
| 17 | R1 resilience layer, story (judge #2) | 1 | PASS (story 163011b, delta after round 2) | `judge_17_r1-resilience-judge2.md` |
| 18 | R1 resilience layer (story text) | 1 | PASS (story, 163011b delta check after round 2) | `judge_18_r1-resilience.md` |
| 19 | R1a resilience library | 1 | PASS (37bfa45, thread-safe) | `judge_19_r1a-library.md` |
| 20 | R1a resilience library (judge #2) | 1 | PASS (round 2, 37bfa45) | `judge_20_r1a-library-judge2.md` |
| 21 | R1b NSE source (story text) | 1 | PASS (story, final ab5bba8) | `judge_21_r1b-story.md` |
| 22 | R1b NSE source, story (judge #2) | 1 | PASS (final story ab5bba8) | `judge_22_r1b-nse-source-judge2.md` |
| 23 | R1b2 persisted pause (story text) | 1 | PASS (story, round 2, c705ef5) | `judge_23_r1b2-story.md` |
| 24 | R1b1 NSE layer (code) | 1 | PASS (round 2, 0c0af47) | `judge_24_r1b1-code.md` |
| 25 | R1b1 NSE layer, code (judge #2) | 1 | PASS (round 2, 0c0af47) | `judge_25_r1b1-nse-layer-judge2.md` |
| 26 | R1b2 persisted pause, story (judge #2) | 1 | PASS (round 2, 3ff3358) | `judge_26_r1b2-persisted-pause-judge2.md` |
| 27 | R1b2 persisted pause, code (judge #2) | 1 | PASS (round 2, 53c6478) | `judge_27_r1b2-code-judge2.md` |
| 28 | R1b2 persisted pause (code) | 1 | PASS (round 2, 53c6478) | `judge_28_r1b2-code.md` |
| 29 | R1c Drive session, story (judge #2) | 1 | PASS (round 1, d68df6e) | `judge_29_r1c-drive-judge2.md` |
| 30 | R1c Drive session (story text) | 1 | PASS (story, d68df6e) | `judge_30_r1c-story.md` |
