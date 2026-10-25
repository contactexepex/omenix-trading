# Judge 629: REC1a recommender contracts, code, story/rec1a-contracts at 12f84eabd (judge J, round 1 of 2)

**FAIL**, lane 1: 1 should-fix, 0 minor. Trial merge with main e2d8e0de8 (fb82e9a36): 16,666 passed, 1 skipped,
14 xfailed; ruff, format, check_imports (2,770 files), check_records (9,281) and check_numbers all clean.
`fno/recommend/` is 339 lines, and every file is under 98 lines except contracts.py (130).

## Criteria (the orchestrator's four checks and the story's "REC1a Claims")
| Item | Verdict | My evidence |
|---|---|---|
| Rung 3 is tied to the record's evidence, never a candidate's own claim | NOT MET | S1: a candidate's rung must equal its version's rung (Q14 caught), but the version's rung is not tied to its own numbers |
| Point in time: push receipt before made_at, never commit time; ReceiptUnknown fails closed | MET | `rungs.py:96-98` counts only receipt_at < made_at, session < day, receipt_at not None. Q1 (<=), Q2 (session <= day) and Q5 (None counts) were caught. evidence_cutoff == made_at in UTC (`contracts.py:78`, Q13 caught). REC1b produces receipt_at; REC1a holds it as data |
| Only forward, counted outcomes count | MET | Q3 (any source) and Q4 (uncounted) were caught |
| Rung ladder 0-3 and day conditions | MET | `rung_for` gives 0, 1 (<30 or no review), 2, 3 (test passed). Q6 (watching at 29), Q7 (established without the test) and Q8 (a condition raising a rung) were caught. `lowered()` never goes up and never below 0 |
| The codec reads exact canonical bytes only | MET | decode refuses missing fields, unknown fields and non-canonical bytes by re-encoding and comparing. Q9 (skipping the compare) was caught. Reordered keys and added whitespace are refused (my probe) |
| The candidate set is in the record from day one | MET | `candidates` is a required field: decoding a record without it fails. It must be sorted and unique |
| Real money and paper need rung 3; the reasons while unproven | MET | `contracts.py:95,99-105`. Q10 (paper below rung 3), Q11 (real money without rung 3) and Q12 (weather_red while unproven) were caught |
| Pinned rung rule | MET | sha256 of `research/recommend/RUNG_RULE.md` = ba2f079a...b7e5 = `RUNG_RULE_SHA256` (`rungs.py:16`) |
| Good, bad, boundary and empty cases | MET | 102 tests. Boundaries at 29 and 30 sessions and receipt == made_at. The empty case: no outcomes gives UNPROVEN and NO_ESTABLISHED_VERSION |

## Findings
**S1 (should fix): a version's rung is not tied to its own evidence, so rung 3 can be written by hand.**
- `VersionEvidence.__post_init__` (`rungs.py:61-63`) checks only the types. `_problems` never compares `rung` with
  `counted_sessions`, `first_session` or `last_session`.
- My probe built a Recommendation whose version has VersionEvidence(rung=ESTABLISHED, counted_sessions=0,
  first=None, last=None), with one traded rung-3 candidate. It encodes, decodes and is accepted with paper=PAPER_TRADE.
  The same holds with counted_sessions=5.
- The record says "proven" while showing it has no evidence. A reader cannot recount rung 3 from the record, even
  though the class docstring promises "so a reader can recount it". Rung 3 also cites none of the three frozen reports
  that `EstablishedTest` stands for (sample plan, lower bound, second window).
- The fix needs two checks:
  - (a) VersionEvidence refuses a rung above what its count allows: 0 sessions gives rung 0 only; fewer than 30 gives
    at most rung 1. first and last are None exactly when the count is 0, with first <= last. This stays consistent with
    `lowered()`, which only lowers.
  - (b) A rung-3 version carries a RecordRef (path, SHA-256) for each of its three reports. The record is refused
    without them.
- Plants for round 2:
  - rung 3 with 0 sessions;
  - rung 2 with 29 sessions;
  - first after last;
  - rung 3 with one report ref missing.

## Plants (mine, 14 of 14 caught)
Q1 receipt == made_at counts; Q2 day d counts; Q3 any source; Q4 uncounted; Q5 unknown receipt counts; Q6 watching
at 29; Q7 established without the test; Q8 a day condition raises a rung; Q9 the codec skips its compare; Q10 paper
below rung 3; Q11 real money without rung 3; Q12 weather_red while unproven; Q13 the cutoff is not made_at; Q14 a
candidate's rung is unchecked. I ran them with PYTHONDONTWRITEBYTECODE=1 in a separate worktree, never during the
suite.

## Notes
- FNO_SLACK_BOT_TOKEN was set for the suite (run window 1792882660-1792883123):
  - #fno-forecast and #fno-intraday: nothing.
  - #fno-desk: two "DRY RUN ... replay" posts, at 22:57:41 and 23:00:58 UTC (a 2026-10-19 rehearsal summary and a
    2026-10-23 card). No REC1a test posts to Slack: `fno/recommend` and `tests/recommend` hold no Slack client, so I
    take both posts to be the orchestrator's or a builder's rehearsals. The orchestrator should confirm.
- The deviation (no R1 card or D6 row, because the recommender is not a book and the rung rule tests no hypothesis)
  is accepted, as the orchestrator states. I see nothing in REC1a that decides a trade on its own today.

## Addendum 1: round 2 (the last), story/rec1a-contracts at 4988abbbe
**PASS**, lane 1: S1 is closed; 1 minor. Trial merge with main ccc56670c: 16,705 passed, 1 skipped, 14 xfailed;
ruff, format, check_imports (2,773 files), check_records (9,299) and check_numbers clean.
- **S1 closed.** `VersionEvidence.__post_init__` accepts only `rung_for(count, reports)`. Rung 3 needs four
  RecordRefs: review, sample plan, lower bound and second window. Each ref's SHA-256 joins `_hashes`.
  - My probe refuses: rung 3 with 0 or 5 sessions; rung 3 with no review; rung 2 written over full rung-3 evidence;
    first after last; dates with a count of 0; 30 sessions in 10 days.
  - Through the codec, these are refused too: a nulled lower bound, an unknown report field, a bad report SHA-256.
- **Lower labels and demotions (the orchestrator's question).** An exact tie breaks no legitimate path:
  - 30 sessions and no review gives rung 1, accepted.
  - A review only gives rung 2, accepted.
  - A report that stops passing is dropped from `reports`, so the rung falls by the same rule.
  - `lowered()` acts on the day's shown rung, which no record field stores. It is unchanged: 3 with 1 condition
    gives 2; 3 with 5 gives 0.
  - If REC1b ever records a shown rung, it needs its own field, never `VersionEvidence.rung`.
- **Plants: 11 of 12 caught.**
  - Caught: the tie removed; the tie as a ceiling only; the span check off; first after last; dates at count 0; second
    window or sample plan optional; rung 2 without review; watching at 29; report hashes unchecked; paper at rung 2.
  - Survived: `refs()` dropping the review (m1).
- **m1 (minor, test only):** `test_a_malformed_report_hash_is_refused` breaks only `lower_bound`. Parametrize it over
  all four references. The code is right: my probe refuses a bad review SHA-256.
- Note: a rung-0 version may carry report references it cannot use. They cannot raise its rung. A later story may
  refuse them.
- Slack, with the token set (1792886736-1792887288):
  - #fno-intraday: nothing.
  - #fno-desk and #fno-forecast: only "DRY RUN ... replay" posts. These are the REH1 rehearsals, as the orchestrator
    confirmed for 629. Nothing in `fno/recommend` or `tests/recommend` mentions Slack.
