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
| 29 | R1c Drive session, story (judge #2) | 1 | PASS (round 1, ddbcf60) | `judge_29_r1c-drive-judge2.md` |
| 30 | R1c Drive session (story text) | 1 | PASS b057f5a; FAIL ddbcf60 (text, Addendum 4) | `judge_30_r1c-story.md` |
| 31 | R1c Drive session, code (judge #2) | 1 | PASS (round 2, 60ab2d8) | `judge_31_r1c-code-judge2.md` |
| 32 | R1c Drive session (code) | 1 | PASS (round 2, 60ab2d8; code = c05a1d7) | `judge_32_r1c-code.md` |
| 33 | R1d4 characterization, lane-2 check (judge #2) | 2 | PASS (e5ea34d) | `judge_33_r1d4-characterization-check.md` |
| 34 | R1d plan (Groww and the rest) | 1 | PASS (round 3, 1508163; 2 conditions carried to R1d1 code) | `judge_34_r1d-plan.md` |
| 35 | R1d plan, Groww pacing (judge #2) | 1 | PASS (round 2, 1508163) | `judge_35_r1d-plan-judge2.md` |
| 36 | R1d1 Groww consolidation, code (judge #2) | 1 | PASS (round 2, b1bebc4) | `judge_36_r1d1-code-judge2.md` |
| 37 | R1d1 Groww reads on the shared primitives (code) | 1 | PASS (round 2, b1bebc4) | `judge_37_r1d1-code.md` |
| 38 | R1d3 close read and NSDL waits (code) | 1 | PASS (round 1, b4f1fc6) | `judge_38_r1d3-code.md` |
| 39 | R1d3 close read and NSDL waits, code (judge #2) | 1 | PASS (round 1, b4f1fc6) | `judge_39_r1d3-code-judge2.md` |
| 40 | R1d4 locking tests and no-refactor, lane-2 check (judge #2) | 2 | PASS (8d2968e) | `judge_40_r1d4-refactor-check.md` |
| 41 | RUN_LOCATIONS map, lane-2 check | 2 | PASS (round 2, 5f4fd8e) | `judge_41_run-locations.md` |
| 42 | P2 news and dedup plan (design) | 1 | PASS (round 3, 06e3467; 3 items carried to P2a/P2c) | `judge_42_p2-news-plan.md` |
| 43 | P2 news and dedup, design (judge #2) | 1 | PASS (round 3, 06e3467) | `judge_43_p2-news-plan-judge2.md` |
| 44 | P2a news fetch into Staging (code) | 1 | PASS (round 2, f5a656b) | `judge_44_p2a-code.md` |
| 45 | P2a news fetch into Staging, code (judge #2) | 1 | PASS (round 2, f5a656b) | `judge_45_p2a-code-judge2.md` |
| 46 | P2b1 pure article functions (code) | 1 | PASS (bounded re-verify, ff08a7a; code = be857dc) | `judge_46_p2b1-pure.md` |
| 47 | P2b2 news Record writer (code) | 1 | PASS (007ff9c) | `judge_47_p2b2-writer.md` |
| 48 | P2b2 news Record writer, code (judge #2) | 1 | PASS (round 2, 007ff9c) | `judge_48_p2b2-writer-judge2.md` |
| 49 | P2b3 news manifest commit guard, code (judge #2) | 1 | PASS (08a55f5) | `judge_49_p2b3-guard-judge2.md` |
| 50 | P2b3 news-promote commit guard (code) | 1 | PASS (60d3f1b; carries to 08a55f5) | `judge_50_p2b3-commit-guard.md` |
| 51 | P2a2 news-fetch failure alert (workflow) | 1 | PASS (11b25db) | `judge_51_p2a2-fetch-alert.md` |
| 52 | P2c news clustering (code) | 1 | PASS (round 2, d5af65f) | `judge_52_p2c-clustering.md` |
| 53 | P2d news cluster record (code) | 1 | PASS (round 2, 5aa0af3; bounded re-check 2f2355e) | `judge_53_p2d-cluster-record.md` |
| 54 | P2d cluster record and shared commit guard, code (judge #2) | 1 | PASS (round 2, 2f2355e) | `judge_54_p2d-cluster-judge2.md` |
| 55 | CF1 commit-failure signalling, code (judge #2) | 1 | PASS (round 2, a34b886) | `judge_55_cf1-commit-failure-judge2.md` |
| 56 | P5 Record contract (doc + tests) | 1 | PASS (round 2, 31796d7) | `judge_56_p5-record-contract.md` |
| 57 | P5b contract follow-ups, code (judge #2) | 1 | PASS (round 2, f7740e2) | `judge_57_p5b-followups-judge2.md` |
| 58 | F1 filings non-list answer (code) | 1 | FAIL (round 1, 39f38e5); PASS (round 2, fbca4e2; N2 follow-up) | `judge_58_f1-filings-non-list.md` |
| 59 | F2 filings non-text row fields (code) | 1 | PASS (round 1, 5f00329) | `judge_59_f2-filings-field-text.md` |
| 60 | T1 test reliability and filings field messages, code (judge #2) | 1 | PASS (147d15c) | `judge_60_t1-test-reliability-judge2.md` |
| 61 | R2 news batch receipts, code (judge #2) | 2 | PASS (d7f7c3a, e919a29; FAIL 498151a, e9b98b2) | `judge_61_r2-batch-receipts-judge2.md` |
| 62 | R2 news batch receipts (code, judge #1 of 2) | 1 | FAIL (round 1, e9b98b2); PASS (round 2, 498151a; superseded by e919a29, PASS; doc sentence to correct) | `judge_62_r2-news-batch-receipts.md` |
| 63 | G1 Groww cutover plan, text (judge #2) | 2 | PASS (15e1dad; FAIL af42b79) | `judge_63_g1-groww-cutover-judge2.md` |
| 64 | CP1 pause circulars cron (code) | 1 | PASS (round 1, 8297459) | `judge_64_cp1-pause-circulars.md` |
| 65 | RR1 rebuild receipts, code (judge #2) | 2 | PASS (678259c; FAIL d636145) | `judge_65_rr1-rebuild-receipts-judge2.md` |
| 66 | S1 staging cleanup (code, judge #1 of 2) | 1 | FAIL (round 1, f41b1df); PASS (round 2, d88f82c then c909933; spy test to fix) | `judge_66_s1-staging-cleanup.md` |
| 67 | S1 staging cleanup, code (judge #2 of 2) | 2 | PASS (c909933, d88f82c; FAIL f41b1df) | `judge_67_s1-staging-cleanup-judge2.md` |
| 68 | S1b loud proof errors, code (judge #2, sole) | 1 | PASS (cead192) | `judge_68_s1b-loud-proof-errors-judge2.md` |
| 69 | CP2 re-enable the circulars cron (judge #2, sole) | 1 | PASS (c07e721) | `judge_69_cp2-circulars-cron-on-judge2.md` |
| 70 | NP0 news port plan (plan doc) | 1 | FAIL (round 1, 0e9401a); PASS (round 2, 6439195) | `judge_70_np0-news-port-plan.md` |
| 71 | NP1 news source rules (code, judge #1 of 2) | 1 | FAIL (round 1, 1d1bfed); PASS (round 2, final d6f28e4; held for owner decision H) | `judge_71_np1-source-rules.md` |
| 72 | NP1 news source rules, code (judge #2 of 2) | 2 | PASS (d6f28e4, df3fe62; FAIL 1d1bfed) | `judge_72_np1-source-rules-judge2.md` |
| 73 | NP2a article format 2 (code, judge #1 of 2) | 1 | FAIL (round 1, 20c8c32); PASS (round 2, a72a037) | `judge_73_np2a-article-format-2.md` |
| 74 | NP2a article format 2, code (judge #2 of 2) | 2 | PASS (a72a037; FAIL 20c8c32) | `judge_74_np2a-article-format-2-judge2.md` |
| 75 | NP2b link resolver, code (judge #2 of 2) | 2 | PASS (3f2fbb1, 356b149; FAIL 3cc0c62) | `judge_75_np2b-link-resolver-judge2.md` |
| 76 | NP2b link resolver (code, judge #1 of 2) | 1 | FAIL (round 1, 3cc0c62); PASS (round 2, 356b149) | `judge_76_np2b-link-resolver.md` |
| 77 | NP3 company list and feed plan, plan doc (judge #2) | 2 | PASS (ec3b34f; FAIL 8459517, eb05a7b) | `judge_77_np3-plan-judge2.md` |
| 78 | NP3a company list, code (judge #2) | 2 | PASS (0ffad12, 1a1e5d6, c5aeb93; FAIL 6504962) | `judge_78_np3a-company-list-judge2.md` |
| 79 | NP3a company list (code, judge #1) | 1 | FAIL (round 1, 6504962); PASS (round 2, 1a1e5d6; allow-list grammar) | `judge_79_np3a-company-list.md` |
| 80 | NP3b feed plan, code (judge #2) | 1 | PASS (4fa33b2, 0d6adbe) | `judge_80_np3b-feed-plan-judge2.md` |
| 81 | NP3b feed planner (code, judge #1) | 1 | PASS (0d6adbe, then 4fa33b2) | `judge_81_np3b-feed-planner.md` |
| 82 | NP2c resolve pass (code, judge #1) | 1 | FAIL (round 1, feb5fa9); PASS (round 2, b1917e7) | `judge_82_np2c-resolve-pass.md` |
| 83 | NP2c resolve pass, code + workflow (judge #2) | 2 | PASS (b1917e7, feb5fa9) | `judge_83_np2c-resolve-pass-judge2.md` |
| 84 | NP4 page-reads plan, plan doc (judge #2) | 2 | PASS (a12cae7; FAIL c886e5a) | `judge_84_np4-plan-judge2.md` |
| 85 | NP2d wrapper index, code (judge #2) | 2 | PASS (2ac29df; FAIL dbb4905) | `judge_85_np2d-wrapper-index-judge2.md` |
| 86 | NP2d wrapper index (code, judge #1) | 1 | PASS (round 1, dbb4905; round 2, 2ac29df; wiring pin to add) | `judge_86_np2d-wrapper-index.md` |
| 87 | NP4a page fetcher and outlet probe, code (judge #2) | 1 | PASS (40faf61, 3f56dbc) | `judge_87_np4a-page-fetcher-judge2.md` |
| 88 | NP4a page fetcher (code, judge #1) | 1 | PASS (round 1, 3f56dbc) | `judge_88_np4a-page-fetcher.md` |
| 89 | NP4b page reads, code (judge #2) | 2 | PASS (98ad64a, 346e78c; FAIL 337f0ea) | `judge_89_np4b-page-reads-judge2.md` |
| 90 | NP5 tagger and origins plan, plan doc (judge #2) | 2 | PASS (36623b1; FAIL 4a322e9) | `judge_90_np5-plan-judge2.md` |
| 91 | NP4b page reads (code, judge #1) | 1 | FAIL (round 1, 337f0ea); PASS (346e78c, 98ad64a) | `judge_91_np4b-page-reads.md` |
| 92 | NP5a tagger, code (judge #2) | 1 | FAIL (round 1, 29d19cf) | `judge_92_np5a-tagger-judge2.md` |
