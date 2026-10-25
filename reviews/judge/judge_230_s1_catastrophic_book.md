# Judge 230: S1 item 13, `catastrophic_loss_book` with the owner's per-book figures (judge A, lane 1)

**Checked:** `story/s1-catastrophic-book` at `9643838ec1993db50fe93f5f0ca5e1f2e172a86b` (the R2/G7 builder). The
diff is 2 files: the one S1 item in `research/evaluation/PROTOCOL.md`, and a new
`tests/evaluation/test_catastrophic_book_figures.py`.

**Verdict: PASS.** No blocking or should-fix findings.

## The figures against the cited rows and `config.yaml`

| Item text | DESK_DECISIONS (main) | `config.yaml` `risk.profiles.books` |
|---|---|---|
| Brake: closed equity Rs 1,20,000 below its high, no new trade | Line 105, "Risk buckets and caps accepted": "closed equity Rs 1.2 lakh below its high stops new trades until the owner restarts in writing" | `drawdown_brake_rs: 120000` |
| One bucket at most Rs 30,000 | Line 105: "Rs 30,000 a bucket" | `bucket_cap_rs: 30000` |
| Open maximum losses at most Rs 1,50,000 | Line 105: "open positions' maximum losses sum to at most Rs 1.5 lakh … a cap on open risk, not a stop" | `open_risk_cap_rs: 150000` |
| New maximum loss at most Rs 50,000 a session | Line 105: "new risk Rs 50,000 a day" | `new_risk_per_day_rs: 50000` |
| No flat open-trade limit | Line 131, "Books drop the flat '3 open trades' limit" (paper books only; the Manual account keeps its own) | `max_open_trades` absent from `rules` |
| Per book | Line 189, "Risk caps and the drawdown brake apply per book" | one `books` profile for each Rs 20 lakh book |
| The brake never closes a trade; only the owner restarts | Lines 13 and 105 | the brake rule's comment |

- All seven match.
- The Reason names the three rows by their titles, and it says they replace the 12 Oct Rs 30,000 brake and the 3
  open trades (lines 12-13). That is right.
- The status stays "proposal, owner decides", which is also right: the owner decided the numbers, but this S1 item
  still needs its own decision.

## Nothing else in S1 changed

- The diff touches only `catastrophic_loss_book`'s Value and Reason.
- `python -m fno evaluation check` on the trial merge prints S1 and the gate complete.

## The test

- `test_the_catastrophic_rule_states_the_books_config_figures` checks that each of the four config figures appears in
  the item, in Indian grouping. It also checks that `max_open_trades` is gone and that the old "Rs 30,000 or more
  below" is not in the text.
- My plant (`bucket_cap_rs` 30000 → 40000 in `config.yaml`) fails 1 test.
- `test_rupees_groups_the_indian_way` pins 30,000, 1,20,000, 1,50,000 and 20,00,000.

## Note (one line, no fix asked)

- The item does not name the books' Rs 10,000 per-trade maximum loss (`max_loss_per_trade_rs`). That cap is C2's,
  and the item is about catastrophic loss, so leaving it out is consistent. The owner may want it stated beside the
  others for one complete picture.

## Gates

- On the trial merge with origin/main 78e7daa2 (tree 0b0f9bb, clean), `-n auto`: pytest 6932 passed.
- `ruff check` is clean, `ruff format --check` shows 1226 files formatted, and `check_imports` is clean.
