# Judge 620: REC1 recommender story text, story/rec1-recommender-text at c0c6980dc (judge J, round 1 of 2)

**FAIL** (text), lane 1: 3 should-fix, 1 minor. Diff: only `docs/stories/REC1-recommender.md` (+190). Doc-reading
tests with `FNO_SLACK_BOT_TOKEN` set: 922 passed, 14 xfailed.

## What holds (my evidence)
- **The owner's decision:** quoted correctly (DESK_DECISIONS line 343 (4): "built in full ... with no proven edge it
  says NO TRADE").
- **Real money:** a closed two-member enum with no "buy" value (criterion 1's plant), matching response 327 item 9
  (`response_327_market-school-agreed.md:51`: "never buy").
- **Rungs:** backtests, the simulator, rehearsals and uncounted days count 0, each with a plant (criterion 3); day
  conditions only lower a rung (criterion 4).
- **One record:** Drive write-once with the receipt pushed before any post, read by the card, the editions and the
  contract.
- **The assumptions:** A1-A4 are each marked with a recommended answer.

## Findings
**S1 (should fix) "Proven" means one counted session, so the paper answer can recommend an unproven version.**
- Section 1 makes `PAPER_TRADE` the paper answer for "a version at evidence rung 1 or higher". `no_proven_version`
  is defined as "no version above rung 0". Rung 1 is 1 to 29 valid sessions.
- So after one forward session the card would say "Paper: PAPER_TRADE <version>" with the reason line of a
  recommendation. Section 6 says "no proven version means ... paper `NO_TRADE` or measurement only".
- Response 327 calls nothing proven before a one-sided 95% lower bound above zero (item 4, line 38). Rung 2 "may
  include zero" and P2 is "descriptive, no licence" (line 66).
- Fix: "proven" is rung 3 only, and the reason code names what it tests (e.g. `no_established_version`). A paper trade
  of a rung 0-2 version is shown as "paper, not a recommendation: <rung and numbers>". `PAPER_TRADE` as a
  recommendation exists only at rung 3. One test per rung (0, 1, 2, 3) with a planted promotion of rung 1.

**S2 (should fix) The point-in-time rule for the rung's inputs is not stated.**
- The rung is "from frozen forward records", but no criterion says which sessions it may count at 15:20 on day d.
  The day's own trades and outcomes are unresolved then.
- Fix: a rung counts only sessions whose outcome record's receipt time is before `made_at` (never day d), and the
  record carries that cutoff. One planted record of day d that must not count.

**S3 (should fix) The evening check of `NO_TRADE` can be chosen with hindsight.**
- It reports what "the day's candidates and the matched controls made", but the 15:20 record does not fix which
  candidates. An evening choice (the best, or only the closed ones) would flatter or punish abstaining.
- Fix: the recommendation names its candidate set at decision time (version, decision path, SHA-256). The check
  reports all of them, each and as a total, never a subset; "not known yet" until every one has closed. A planted
  test drops a losing candidate at check time and must fail.

**m1 (minor)** The acceptance header promises a planted failure for each criterion, but only criteria 1, 3 and 7
name one. Name the plant for 2, 4-6 and 8-11 as well (quality rule 4).

## Notes
- RM1x touches the real-money line, and the recommender "decides what a trade would be". Whether a second judge is
  needed (JUDGE.md, two judges for money pieces) is the orchestrator's call; the text's "one judge each" should name
  that ruling.

## Plants
0 (text round).

## Addendum 1: the delta to 94d532195 (still round 1, the orchestrator's re-point)
The verdict stays **FAIL** at 94d532195. One Markdown commit on c0c6980dc (+17 -11): release 1 (REC1a+b) the week of
26 Oct, new dates, A1 marked answered (DESK_DECISIONS line 343 (4) supports it).
- S1, S2 and m1 are untouched by the delta.
- **S3 now matters more.** Release 1 records verdicts from about 2 Nov, but the evening check is built later
  (release 2, about 9-13 Nov) "from the same records". A check written after the days it judges is fair only if each
  15:20 record already names its candidate set (version, decision path, SHA-256). So REC1a's record codec must carry
  that set from the first live day: name it in REC1a's scope and criterion 7, or the release-1 days cannot be checked
  without hindsight.

## Addendum 2: round 2 (the last), story/rec1-recommender-text at 0359a0e50
**PASS** (text), lane 1, 1 minor. Three Markdown commits on 94d532195 (f03ffdc09, 65a12e776, 0359a0e50; only the
story). Doc-reading tests with the token set: 922 passed, 14 xfailed.
- **S1 closed.** "Proven" is rung 3 only. `PAPER_TRADE` exists only at rung 3; rung 0-2 trades read "paper, not a
  recommendation" with their rung. `no_established_version` comes before the day's conditions, so while no version is
  at rung 3 only the first three codes can occur. The real-money answer also needs rung 3, and RM1 disagreeing with
  the rung gives `data_check_failed` with an alert. Criterion 4 has a planted rung-1 threshold.
- **S2 closed.** Only outcomes receipted strictly before `made_at` count, never day d; `evidence_cutoff` is in the
  record. Criterion 5's boundary is 1 s before, at, and day d.
- **S3 and 620.1 closed.** The record fixes the candidate set (version, path, SHA-256; empty written as empty) from
  REC1a's first live day; the codec refuses a record without it. The check reads only that set, reports each and the
  total, and gives `data_check_failed` (never a smaller total) for a missing or changed candidate. Criteria 11 and 12,
  with the dropped-loser plant.
- **m1 closed.** Criteria 1-14 each name a plant.
- **The card's mapping checks out** against the pinned contract (`fno-card.yaml` 2.14.0): `no_approved_strategy`,
  `data_check_failed`, `step_problems` and `weather_red` are in the enum. The three codes without a same-meaning entry
  are guarded to `data_check_failed` with an alert until a re-pin, and they cannot occur below rung 3.
- **Two judges for REC1b and RM1x:** the orchestrator's ruling is now written in.
- **m2 (minor)** S2's cutoff uses "the commit time of its receipt on `main`, read through git". A commit's time is
  set by whoever commits. The project's own rule for deadlines is GitHub's push receipt, never commit time
  (`fno/ai/receipts.py`; protocol v4 1.6). Use the push receipt for `evidence_cutoff` in REC1a's code, or state why
  commit time is enough here.
