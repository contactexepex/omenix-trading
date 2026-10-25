# Judge 63: W9-F&O (dashboard), Home and the frame read the F&O tool's blocks

Date: 13 Oct 2026 (UTC). Repository: exepex/omenix-dashboard (e44bb21, dca854d; read-only clone).
Claims: that repository's `reviews/claude/response_29_w9-fno.md`. Criteria: the four the builder proposed for
`docs/stories/X-cross-repository.md` (not yet added there).

## Verdict: FAIL end to end (page keys disagree with P10); the dashboard's own logic is sound

## Per criterion

| # | Criterion | My check | Result |
|---|---|---|---|
| 1 | Each F&O part shows P10's page, or its reason when missing (never an example) | Logic correct: my plant keeping the example index levels when the page is missing was caught. **But against what P10 actually publishes it shows only reasons:** it reads `today`, `risk`, `session`, `indices`, `events`; P10 publishes `fno_picks` and `fno_books` and does not publish the other three (judge 61) | **NOT MET** end to end; logic MET |
| 2 | Stock and F&O never combined; each stock figure beside real F&O labelled Example | Events merge: my plant showing the stock list's expiry rows beside the F&O ones was caught (2 failed). The Example labels are not in any test or harness case (builder says so: build and typecheck only) | PARTLY (labels unverified) |
| 3 | The US shows no F&O element | Tested (`frameData` strips F&O fields; no F&O read for the US) | MET |
| 4 | Without a published session, NSE's calendar at regular hours, said as such | Tested (session day, Saturday, Dussehra, after IST midnight). Muhurat and special sessions show regular hours (builder says so) | MET |

`npm test`: 427 pass, 0 fail, 0 skipped (my run). `tsc --noEmit`: clean. I did not re-run the UI harness (cost).

## Claims vs reality

| Claim | Reality |
|---|---|
| "Page keys are W10's own" | Partly. `today` for picks is W10's. `risk` for books is half of W10's "risk and scoreboard_b". `session` and `indices` are W10's keys **in the stock tool's store** (`rm.blocks`, `x-publisher: stock`), not in `fno.pages_history` |
| "The owner's decision now has P10 publish session and indices" | The decision (DESK_DECISIONS, 13 Oct) does list the India band. P10's builder stopped it because the contract says stock. The two builders read the same decision differently; the contract owner must move the India band to `fno` or the owner must withdraw that part. Blocked by owner/contract owner, not this story's fault |
| Freshness uses the morning publication window | Correct concern raised by the builder: if books and picks ever publish from a 3 pm run, the rule is wrong. P7's `fno.run_status` now exists for this |
| Index source label "the stock tool's daily close" with a note added | True; a contract source value for NSE's close is the proper fix (contract owner) |

## What must happen (one decision, then a small change on one side)

1. The contract owner fixes the page keys for FnoPicks and FnoBooks (`today` vs `fno_picks`, `risk` vs `fno_books`) and
   says which store holds India's session and indices. Then P10 or W9-F&O changes its keys to match.
2. A test on each side naming the agreed keys from the contract (not from either builder's memory), so this cannot
   drift again.

## Project rules

No model names or internal ids seen in the changed components; files within size limits (builder's check passed). No
connection to Azure by me.
