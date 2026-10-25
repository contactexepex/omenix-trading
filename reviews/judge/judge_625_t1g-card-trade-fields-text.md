# Judge 625: T1g story text, the card shows TRADE and WATCH with the trade's fields (story/t1g-card-trade-fields at 6a503b37e)

**FAIL, lane 1.** Round 1 of 2. Judge I, own session (session_01CHtddAzFcEdQh4HFiz3mqU), 25 Oct 2026. Text only
(`T-cards.md`, T1g). Judged by reading, against REC1 on `main` and the pinned contract 2.14.0.

## Checks asked for

| Check | Verdict | My evidence |
|---|---|---|
| TRADE only for REC1's `PAPER_TRADE` at rung 3 | MET | Scope "TRADE" and decision 1; REC1 (`REC1-recommender.md:199`) gives `PAPER_TRADE` only at rung 3 |
| Fail closed when a core field cannot be verified | MET | Scope and decision 2: `NO TRADE` with `data_check_failed` and a line naming the trade; never a TRADE without a verified maximum loss; criterion 2, P2, P3 |
| "Entry range (paper fill rule)" wording | MET | Scope, decision 3, the boundary test, P10 |
| WATCH only for a rung 1-2 trade; rung 0 never | MET | Scope "WATCH", criterion 4, P9 |
| The card never computes a number | MET | Scope ("prints each value as recorded"), criterion 7 (no calculator import; byte-for-byte), P4 |
| No trade field in the repository | MET | Scope "Privacy", criterion 6 with planted distinctive values, P5 |
| Reason within the pinned contract | MET for the code | `null` is in the enum (`fno-card.yaml:39`); NO TRADE codes follow REC1's mapping (`REC1-recommender.md:99-108`) |

## Findings

1. **Should-fix: criterion 5 cannot pass as written. The contract requires a `trade` object on TRADE and WATCH, while
   criterion 6 keeps every trade field out of the delivery.**
   - `FnoCard` lists `trade` as required (`fno-card.yaml`, `required`). Its `allOf` gives every status but NO TRADE
     `reason: null`, `trade: {type: object}` and `price_of_staying_out: null`.
   - `card_from_delivery` (`tests/market_read_models/test_p1_t1_card.py:35-50`) fills every field the delivery does
     not hold from the `getFnoCard_india_none` example, whose `trade` is `null`. So a TRADE or WATCH delivery fails
     `trade: object`, and criterion 5's "validates against the pinned contract" is red, by design of the privacy rule.
   - Fix expected: state how the public card meets the contract on TRADE and WATCH days without a trade field in the
     repository. For example, the check takes `trade` (and `price_of_staying_out: null`) from the contract's own
     `getFnoCard_india_trade` and `getFnoCard_india_watch` examples, so it checks the fields the delivery holds; or name
     the dashboard's owner-only path as Out, with the check limited to the delivery's fields. Then add the test case
     and a plant.

## Notes (not findings)

- "NO TRADE with T1's reason" on a failed would-be WATCH day: after REC1b the reason comes from
  `RecommendationStatus` (mapped, for example `no_established_version` -> `no_approved_strategy`). Say "the status's
  reason" so it does not read as T1's old `RegistryStatus`.
- A failed TRADE gives `data_check_failed`, but a failed WATCH keeps the status's reason. That is defensible (a shadow
  trade is not the card's decision), and T1e's warning still shows. Say why in the text.
- The rung-0 rule narrows design 4.1's literal "anything earlier is WATCH". The orchestrator's brief confirms it; record
  it as the orchestrator's decision, not only "sent to the orchestrator".

## Gates

Doc-reading tests at 6a503b37e, with `FNO_SLACK_BOT_TOKEN` kept: 922 passed, 14 xfailed; record scan clean.

## Addendum 1: round 2 at 99d766e45 (diff 6a503b37e..99d766e45)

**PASS, lane 1** (Judge I, own session). The diff changes only `T-cards.md` (T1g).

| Item | Verdict | My evidence |
|---|---|---|
| 625.1 should-fix | FIXED | I reproduced the builder's claim with the pinned validator: `getFnoCard_india_none` with the status set to TRADE or WATCH is refused on exactly `evidence/rung`, `price_of_staying_out` and `trade`, while `india_trade` and `india_watch` validate. Criterion 5 now splits in two. (a) The delivery file's own fields, through `card_from_delivery` starting from the example for its status; the example's trade part is labelled and never read as the day's trade. This is P1's test file, agreed by the orchestrator in its owner's place. (b) The Drive record's `trade` and `evidence` against the pinned `FnoCardTrade` and `evidence` schemas, with a missing `max_loss` refused. The publish path is Out. Plants P6b and P6c |
| Note: "the status's reason" | FIXED | criterion 4 |
| Note: a failed WATCH | FIXED | now `data_check_failed` too, with the reason stated (T1 criterion 2, one rule for both statuses). Stricter than my note asked, and correct |
| Note: the rung-0 rule | FIXED | recorded as the builder's decision, open to the orchestrator or the owner |

Doc-reading tests at 99d766e45, with `FNO_SLACK_BOT_TOKEN` kept: 922 passed, 14 xfailed.
