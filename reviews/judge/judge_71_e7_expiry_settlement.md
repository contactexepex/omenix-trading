# Judge 71: story E7, expiry settlement (branch `story/e7-expiry-settlement` aa788df, before merge), with the E3 condition from judge 68

Date: 14 Oct 2026. Claims: `reviews/claude/response_73_e7-expiry-settlement.md` (renumbered from 72; D2 keeps 72).

## Verdict: PASS. The builder may merge. Two minor notes

## Gates (branch tip, separate worktree)

- `tests/desk` and `tests/risk`: 150 passed.
- Full suite: 2,168 passed. Ruff and imports are clean.

## Settlement price

- **Source:** NSE's UDiFF F&O file of the expiry day only, which is point in time. Every expiring NIFTY row (the future
  and every option) must carry the same `SttlmPric`, or the settlement is refused (`SettlementError`), never guessed.
- **Against data:** the fixture's 25 Jan 2024 price 21,352.60 equals NIFTY 50's official close that day in our closes
  file (`warmup_closes.csv`: 21352.6). NSE's final settlement price for index options is the index's closing value, so
  the two agree.
- **Intrinsic value:** reuses research's `Leg.intrinsic`, calls `max(S-K, 0)` and puts `max(K-S, 0)`, so the desk
  and the research agree.

**Plants:**

| Plant | Result |
|---|---|
| Expiring rows allowed to disagree on the price | caught (1 failed) |
| Exercise STT charged on the short (assigned) side too | caught (2 failed) |
| The "traded on the expiry day" row check removed | **not caught** (150 passed). Minor: the file is read by the expiry date's path, so its rows carry that date anyway; a fixture row with another `TradDt` would test it |

## Exercise STT rate, checked against primary sources (orchestrator's request)

- **NSE circular NSE/FATAX/73524, Circular Ref. 02/2026, 31 March 2026** (I read the PDF from `nsearchives`): "The
  Finance Act, 2026, which received the Presidential assent on March 30, 2026, has revised the following rates of levy
  of STT with effect from 1st day of April, 2026", including "(b) Sale of an option in securities, where option is
  exercised, has been revised to 0.15% (upto March 31, 2026 – 0.125%)". The same circular's table names the
  **purchaser** as the payer.
- **The Income-tax Act's section 98 table** (incometaxindia.gov.in) lists 0.15%, payable by the purchaser. The NSE
  product page states the value is the intrinsic value (settlement price minus strike) and applies only if in the
  money.

**C1's `stt_exercise_pct: 0.15` on the in-the-money long (the closing side "sell" of a bought leg) is correct**, with
the primary source now known. The builder's secondary citations should be replaced by NSE/FATAX/73524 in the config
comment and the response (minor).

**Same circular, checked for the rest of C1:**
- option sale STT: 0.15% from 0.10%. C1's `stt_sell_pct` is already 0.15;
- futures: 0.05% from 0.02%. This matters only if C1 ever prices futures.

Note: C1 applies today's rates to every date, which is conservative for history before 1 April 2026. That is already
a stated C1 limit.

## The E3 condition (judge 68) is met on this branch

- `RiskDecision` now carries `entry_cash_rs`, computed by C2 itself (`TradeCosts.entry_cash_flow`) together with the
  exact proposal it approved.
- E4's entry check refuses an order whose decision does not carry this exact proposal and its entry cash, then limits
  the entry by `order.risk.entry_cash_rs`. The caller can no longer supply its own limit.
- My plant, dropping the "same proposal" comparison, fails 1 test.

## Other points

- The settlement charges are reasonable and conservative: no exchange, SEBI, IPFT or stamp charges on a cash
  settlement; brokerage plus GST on each in-the-money leg as if it were an order; a worthless leg pays nothing.
- `settlement_needed` still blocks new risk until the expiry-day file is in Drive.

## Process

Followed the rule: reviewed on the branch before the merge.

## Addendum 1 (merge check, f655612; the trade-date test)

**MET.** f655612 merges b2dfa90, which is the passed tip aa788df plus three changes, none in `fno/`:
- `config.yaml`: the exercise STT comment now cites NSE circular NSE/FATAX/73524 (value unchanged at 0.15);
- the claims file;
- one new test, `test_rows_of_another_trade_date_under_the_expiry_day_s_name_are_refused`.

**The minor gap is closed.** The test sets every row's TradDt to the day before and expects a refusal. My plant,
removing the `TradDt != expiry` check from `fno/desk/settlement.py`, is now caught (1 failed, 9 passed).

My recomputed merge of 7ed140e and b2dfa90 equals f655612 exactly. CI `checks` on f655612 (run 38496795370) is green.

**No other code on main.** Main from a2fcb2e (my last merge check) to e1ec07e equals a2fcb2e plus the D2 and E7 tips,
with no other change under `fno`, `tests`, `tools`, `db`, `.github`, `config.yaml` or the requirements files.
