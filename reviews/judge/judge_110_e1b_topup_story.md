# Judge 110: story E1b text, the capital top-up to Rs 20 lakh (quality rule 1; judge C)

Date: 15 Oct 2026 (UTC). Branch `story/e1-topup` at **d309de619c799035ce0b5f7486a5166d44437703** (text only:
`docs/stories/E-paper-desk.md` E1b, response 110). Checked against:
- the owner's "2 B" (15 Oct), "Paper account Rs 20 lakh" (14 Oct) and the orchestrator's "brake per book" (owner to
  confirm);
- judge 105 minor 4;
- the code it changes (E1 `fno/books/`, C2 `fno/risk/book_view.py` and `caps.py`, C4
  `fno/checks/validity_account.py`, P10 `home_inputs.py`, S2 `reconcile.py`).

## Verdict: FAIL (text), 1 should-fix; 3 minor

The design is right:
- **History stays as written.** A new ledger kind is appended; nothing earlier changes.
- **The amount is computed**, never typed.
- **The brake is unaffected by algebra.** Capital is constant across the closed-equity series, so a top-up shifts the
  whole series and never makes a new high. Drawdown is measured on profit and loss only.
- **Refusals cover the risky states:** an open position, already at size or above it, not started, no lock.
- **C4 reads the ledger independently.**

I checked the reader list against the code. `grep` for `starting_cash`, `LEDGER_OPENING` and `opening_row` outside E1
finds exactly the readers it names: C2 `caps.py:100` and `book_view.py`, C4 `validity_account.py`, S2
`reconcile.py:30`, P10 `home_inputs.py:52`.

## Should-fix

**1. A top-up must carry its time, and count only from that instant.**
- **The gap.** The story dates a top-up by day: "capital ... dated on or before a day"; C2 uses "capital (as of the
  decision day)". C4's own ledger read (`_filled_by`, `validity_account.py:61-63`) treats a row with no time zone as
  filled by the cutoff for the **whole day**.
- **The consequence.** Say a top-up is run at 17:00 IST on session day T, after that day's 15:00 decision:
  - live, at 15:00, the book had Rs 5 lakh and was refused by `paper_account`;
  - any later C4 or C2 recomputation of T (D3's replay, an audit) sees Rs 20 lakh and passes.

  The record and its replay then disagree, the point-in-time failure the project guards against everywhere else.
- **Fix.**
  - The `capital_top_up` row's `filled_at` is the write instant, time-zone aware in IST.
  - Capital is "the opening plus top-ups written at or before the decision cutoff", in E1, C2 and C4 alike. C2 takes the
    cutoff it already uses; C4 its `cutoff`. P10 can stay by day (end-of-day figures).
  - Test: a top-up at 17:00 on T is not capital for T's 15:00 decision, a replay of T still refuses, and the top-up
    counts from T+1 (or from a later same-day cutoff).
  - Alternatively, the command refuses on a session day between 14:50 and the end of that day's fills, and the
    timestamp rule still applies. Either way, say which.

## Minor

1. **Say what the amount is.** It restores **capital**, not cash or equity: amount = target − capital. A book with
   realised losses before the top-up keeps them. That is correct, and the text should say so in criterion 1, so nobody
   later "tops up to Rs 20 lakh of equity".
2. **Name the source of the target.** The command's target is `risk.profiles.books.paper_account_rs`, so a later config
   change would allow a second top-up. Raising that number is a lane-1 config change and an owner decision, and a second
   top-up should be named as such in its output line. One sentence.
3. **C4's opening check must accept top-up rows after the opening.** `account_facts` requires row 0 to be the opening
   and treats every other row as a fill (`_trades(rows[1:])`). The design says capital rows "never count as trades", so
   criterion 5 should include a C4 test with a top-up row between two fills (today that row would be parsed as a fill
   and fail on `trade_id`/`side`).

## Project rules

- Lane 1: E1 money records and the `journal/` data. The run on the real journal is by the orchestrator or the owner
  after the merge, never by the builder, and committed and judged as data.
- Order: built on `main` after C5 merges (orchestrator's decision), since it renames `starting_cash`, which C5's
  `PaperAccountSize` reads.

**Verdict: FAIL for d309de619c799035ce0b5f7486a5166d44437703** (story text) on should-fix 1. A re-check needs only the
capital definition, criteria 3-5 and the C4 design line.

## Addendum 1 (15 Oct 2026): revision 2 at d6b313c26cae77a5374a9d26660d35e970036480

Text only for E1b (`git diff d309de6 d6b313c -- docs/stories/E-paper-desk.md`; the other files in that range come
from `main`, merged cleanly).

| Item | Status | Evidence |
|---|---|---|
| sf 1, the write instant | MET | A top-up's `filled_at` is the IST write instant with its offset, never a bare date. Capital at an instant is the opening plus top-ups written at or before it, so a decision uses its cutoff in E1, C2 (`DESK_DECISION_TIME` on the decision day) and C4 (its cutoff, by the row's instant). Criteria 3 and 5 test a 17:00 top-up on T: it refuses T's 15:00 decision live and in replay, in both C2 and C4, and passes T+1's. A 10:00 top-up counts at 15:00 the same day |
| Minor 1, capital not equity | MET | Criterion 1: a book with Rs 10,000 of realised losses still gets Rs 15,00,000 and keeps the loss |
| Minor 2, a second top-up | MET | The output line names it "a further top-up"; raising the setting is a lane-1 config change and an owner decision |
| Minor 3, C4 reading order | MET | Trades are read only from fill and settlement rows; a top-up row between two fills is capital (criterion 5 test) |

### Who runs the real-journal top-up: the builder (orchestrator's decision 23). No objection, with three conditions

My "never by the builder" was reasoning only, not a recorded rule. On the risk itself:
- the command computes the amount;
- it refuses at size, above size, unstarted and open books;
- it writes under the book's lock;
- it is idempotent per day.

So the operator matters little, provided the merged code is what runs. The conditions:
1. **Run it from a clean checkout of `main` at or after the merge commit**, via `python -m fno account top-up`, never
   a branch build or a hand edit. Record the command's output lines (one per book) and the commit it ran at in the
   claims file.
2. **The data commit contains only the command's own writes**, for each of the three books:
   - one appended `capital_top_up` row in `cash_ledger.csv`;
   - the rebuilt `positions.json`;
   - that day's row in `equity_history.csv`.

   Nothing else under `journal/` or elsewhere. "Nothing else may be written" should list exactly these three files per
   book, since the command itself writes all three.
3. **Timing.** Run it outside 14:50-15:30 IST on a session day, so it never races the day's decision or fills under
   the account lock. The timestamp rule makes any time correct, but a lock clash with the desk would refuse one of the
   two writers.

**My merge check will verify:**
- each book's ledger is byte-for-byte its pre-merge content plus exactly one row;
- the amount is Rs 20,00,000 minus that book's capital (Rs 15,00,000 each);
- the instant is time-zone aware and after the merge commit's time;
- `positions.json` and `equity_history.csv` equal what the merged code rebuilds from the ledger;
- C2 and C4 then pass `paper_account` for the three books.

**Verdict: PASS for d6b313c26cae77a5374a9d26660d35e970036480** (story text). Code on `main` after C5 merges.

## Addendum 2 (15 Oct 2026): E1b code at ddcefcc8f969f42cb82e7ef706173d68234183c3

Code 725b249 plus `main` (C5 included). Judged on the real paths, under the owner's "keep the design simple" rule.
- Gates: 5,142 passed (the builder's figure); ruff, format and imports clean.
- `merge-tree` with `origin/main`: no conflict. With STR1b-1 (918c5ef): no conflict.

## Verdict: PASS (code)

| Real path | Status | Evidence |
|---|---|---|
| A top-up restores capital, not equity | MET | `AccountWriter.top_up` amount = target − `capital()` (opening plus earlier top-ups), so realised P&L stays. One `capital_top_up` row at the IST write instant, with an offset (`top_up_row` refuses a naive time) |
| A 17:00 top-up does not count at that day's 15:00, and counts at T+1 | MET | My probe on a real ledger (opening Rs 5 lakh on 14 Oct, a Rs 15 lakh top-up at 17:00 IST on 15 Oct). C2's `capital(at)`: Rs 5,00,000 at 15:00 and 16:59, Rs 20,00,000 at 17:00 and at 16 Oct 15:00. C4's `account_facts`: Rs 5,00,000 at the 15 Oct cutoff, Rs 20,00,000 at the 16 Oct cutoff. C2 takes the cutoff `DESK_DECISION_TIME` on the decision day (`book_view.py`), and C4 compares the row's instant |
| The brake is unchanged by a top-up | MET | The capital is the same at every point of the closed-equity series in C2 (`closed_equity_series`) and C4 (`equity = capital`), so the drawdown is P&L only, and the Rs 1.2 lakh boundary sits where it did before |
| A refusal writes nothing | MET | Not started, above the target or an open position each raise before any write. The lock is required first, and `AccountBusy` from the writer is caught. One line per book, exit 1 |
| Readers | MET | P10 `home_inputs` takes P&L as marked equity minus the capital in force that day; S2 `reconcile` subtracts `capital()`; C4's `paper_account` check uses the capital at the cutoff. `positions.json`'s key is renamed to `capital_rs`, and no other reader uses `starting_cash` (grep) |

The real-journal top-up keeps addendum 1's three conditions:
1. a clean `main` at or after the merge;
2. only the 3 files per book written;
3. outside 14:50-15:30 IST.

My merge check verifies them.

**Verdict: PASS for ddcefcc8f969f42cb82e7ef706173d68234183c3** (code). Rule 9: ChatGPT next.

## Addendum 3 (15 Oct 2026): dashboard contract change for E1b, `exepex/omenix-dashboard` at a046f00d64d894e8e1bc2104098a95743bd0ef3b

Branch `story/e1b-contract-capital`, parent dashboard `main` b9c41ec. I read it through a read-only git clone; I wrote
nothing to that repository.

**The change:**
- `api/schemas/fno-paper-trades.yaml:30`: `opening_value`'s `x-record` goes from `account_state:starting_cash` to
  `account_state:capital`. The description becomes "Opening balance plus top-ups in force, Rs 20 lakh a book".
- `api/catalog/fno-screens.md:378` is regenerated to match.
- The type, minimum, examples and version (2.7.0) are unchanged.

| Check | Status | Evidence |
|---|---|---|
| Semantics | MET | E1b (judge 110 addendum 2) renames `AccountState.starting_cash` to `capital` = the opening plus top-ups in force. After the real top-up that is Rs 20,00,000 a book, matching the description and the examples' `2000000`. Before the top-up it is the Rs 5 lakh actually held, which is correct, and the description's "Rs 20 lakh a book" becomes true when the top-up runs |
| Other readers of the field | none | `grep -rn` for `opening_value`, `openingValue` and `account_state:` over the whole dashboard repo finds only the schema, the catalog and `api/examples/fno-screens.json`. No `web/` code reads it |
| Gates | MET | `tools/api/check_contract.py`: "OpenAPI 3.1 valid; examples valid and current; catalog complete; screen rules hold; every planted break caught". `check_fno_screens.py`: "every rule holds", 28 of 28 planted breaks. `check_code_size.mjs`: ok. The web typecheck, tests and build were not rerun: no `web/` file changed, so the builder's 465/465 stands for them |

**Verdict: PASS for omenix-dashboard a046f00d64d894e8e1bc2104098a95743bd0ef3b.** It merges together with E1b in
trading, whose contract pin must name this commit's merged SHA.
