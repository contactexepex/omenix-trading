# Judge 198: RM2 real-money test record, story text (judge A)

**Checked:** `story/rm2-real-money-record` at `9f964dc6`. That is the RM2 section of `docs/stories/RM-real-money.md`,
its claims file (response 186, to be renamed 189, text only) and the register row. I read them against:
- the frozen gate on main (`research/evaluation/REAL_MONEY_GATE.md`, RM1 merged 4777653e);
- E8's card-time section (`docs/stories/E8-owner-timing-fills.md:52-62`), which cites O1:88;
- C1's charges (`fno/costs.py`).

**Verdict: FAIL, 1 should-fix, no blocking.** It never places an order and makes no Groww call. The times and every
gate number check out. One pairing rule biases the binding pass test against real trades.

## Checked and sound

- **Gate numbers, item by item against the frozen gate:**
  - 1 lot; max(30, registered) trades and 6 months (gate line 158);
  - paired bound −Rs 500 (169);
  - the prediction floor;
  - Rs 1.50 per unit (175);
  - 10% unknown legs, left out and listed when 10% or fewer;
  - 90% of eligible cards (178);
  - stops (a) at or below −Rs 20,000, (a2) a Rs 20,000 fall from the peak, and (b) above Rs 2 per unit over 5
    trades (191-193);
  - valid quotes within 5 minutes, with the A16 fallback in the same 5 minutes (35).

  Criterion 7 pins `rules.py` to the gate text. Criterion 3's boundaries are right: −20,000 trips; a +6,000 high
  falling to −14,000 trips; 2.01 trips and 2.00 does not.
- **Times:** the card posts at 15:15 or later (O1:88, via E8:54). E8's R = 60 paper fill is the next session's 10:15
  mark (E8:60). The owner may place the order in the same session's last minutes or the next session, and pairing by
  card handles either.
- **"Next snapshot" is strictly after the fill:** right, because E8 fills on its due mark, so the mark at the fill
  time is the fill's own quote (gap 0). Criterion 6 pins 10:15 against 10:30. That is my RM1 note 2, answered.
- **Order-time quote:**
  - the screenshot comes first, and its time is typed from the image, because Drive's upload time cannot date it;
  - the file-name time is kept as a check, flagged when it differs by more than a minute;
  - the A16 fallback is the latest mark at or before the order, within 5 minutes, with age 0 allowed;
  - with no valid quote, the slippage is unknown, never zero.
- **The timing gap is reported only,** as the gate requires.
- **Drive only:** the public repository gets SHA-256s and a status line with no price, strike or rupee figure
  (criterion 8 and 8.5). The stop and pass alerts go to #fno-desk only.
- **No order path:** RM2 reads Drive, A16 and Book 1 only. The import test bans Groww and order modules.
- **Owner questions Q1-Q3 as open slots:** each is neutral, with options and a labelled recommendation, and none
  changes a gate number. Q2 fills the gap the gate leaves (when a card counts as skipped). Q3: the gate says "every
  charge included", so (a) actual charges is the reading that fits "real net".
- **Coordination:** the new register row RM2 has the same builder as RM1. It only reads E8, T1 and A16, so there is
  no duplicate.

## Should-fix

**SF1. "Paper net ÷ paper lots" misstates paper's 1-lot cost, which biases the paired test against real.**
- **Evidence:** C1 charges brokerage as a flat Rs 20 per order, plus 18% GST (`fno/costs.py:27,34`), whatever the lot
  count. Book 1's paper trades are sized to its Rs 10,000 cap, while the real test is 1 lot under Rs 5,000, so paper
  usually holds 2 or more lots. Dividing paper net by lots therefore divides the fixed brokerage too.
- **Path:** take a two-leg spread, opened and closed, so 4 orders.
  - Real at 1 lot pays 4 × Rs 23.6 = Rs 94.4 in brokerage and GST.
  - Paper at 2 lots, divided by 2, carries Rs 47.2.
  - So every paired d = real − paper is about Rs 47 worse, with no execution difference at all (about Rs 63 at 3
    lots, Rs 71 at 4).
- **Why it matters:** the binding pass test is lower bound ≥ −Rs 500, with about Rs 387 of noise at n = 20 and SD Rs
  1,000. A built-in −Rs 47 to −Rs 71 is 10-14% of the margin, against real every time. The prediction floor (pass
  item 2) has the same issue, since its evidence record is "scaled to 1 lot".
- **Expected fix (text):** scale paper's gross P&L per unit to 1 lot, then apply C1's charges for 1 lot on each leg's
  orders. The paper pad is per unit, so it scales exactly. Use this for the paired trade and the evidence record
  alike.

## Notes (one line each, no fix asked)

- **Valid quote, both sides:** the gate's valid quote needs "both sides present" as well as depth. Criterion 2 should
  also refuse a screenshot showing only one side.
- **A16 fallback times:** use the mark's observed quote time, not its nominal time (G10's honest-times rule). A
  "10:15" mark is fetched over about 50 seconds, so an order at 10:15:20 must not use a quote fetched at 10:15:40.
- **Stop (b)'s window:** "the last 5 real trades" after every exit equals the gate's "any 5 consecutive" only if
  trades are ordered by exit time. Say so.
- **Gates** (trial merge with origin/main 0659c386, tree 7a35213, clean, `-n auto`):
  - pytest: 6520 passed;
  - `ruff check`: clean;
  - `ruff format --check`: 1155 files formatted;
  - `check_imports`: clean.

**A re-check needs only the pairing and scaling rule (SF1).**

## Addendum 1: revision at c528a9b6: FAIL (1 should-fix, one phrase)

The delta from fb62461a covers the pairing rule, the valid quote, stop (b), criterion 1 and the owner's decisions.
The rename to response 189 is in.

- **SF1 (judge 198): MET.**
  - Paper is restated at 1 lot: gross per unit before pad × the 1-lot units, minus the pad, minus C1's 1-lot charges.
    It is "never paper net ÷ lots", the Rs 94.40 is explained, and criterion 1 pins Rs 94.40 against Rs 47.20.
  - The real side carries actual contract-note charges (Q3).
  - The prediction floor's evidence record is restated the same way.
  - Padding the paper side at the gate's Rs 1 is consistent with the frozen gate. Its Terms say the evidence record
    is filled "after C1 charges and pads" and the Paper pad is "the pad research results already assume", while
    `FILL_PAD_RS` = 0 "never" serves as the gate's pad. It is also the coherent choice: real execution at about the
    pad then gives d ≈ 0, whereas an unpadded paper side would charge real Rs 1 per unit of honest slippage against
    the −Rs 500 margin.
- **Notes 1-3: MET.**
  - The valid quote needs both sides present.
  - The A16 fallback is timed by the snapshot's observed fetch time, never its nominal mark.
  - Stop (b) orders trades by exit time, so "the last 5" checked after every exit covers every run of 5.
- **Owner decisions:** Q1-Q3 match row e7f40e8f (16 Oct, all three as recommended).

**SF2. Where the pad applies is not stated, and it moves d by up to 4×.**
- **Evidence:** the rule reads "gross per unit (entry and exit prices before pad, every leg) × the 1-lot units,
  minus the pad of Rs 1 per unit × those units". Research's `PAD` is "worse on every leg at entry and at exit"
  (`fno/research_engine/cycle_costs.py:24`).
- **Path:** take a 2-leg spread at 65 units.
  - The pad on every leg at entry and exit is 4 × 65 = Rs 260.
  - The pad once per trade is Rs 65.
  - Each paired d then differs by Rs 195, against the binding −Rs 500 margin. One reading favours real by Rs 195 per
    trade relative to the other.
- **Fix (text):** "minus Rs 1 per unit on every leg at entry and at exit (research's `PAD`)". Pin it in criterion 1's
  example.

**Gates (trial merge with origin/main 85990def, tree 5bde1ec, clean, `-n auto`):**
- pytest: 6521 passed;
- `ruff check`: clean;
- `ruff format --check`: 1155 files formatted;
- `check_imports`: clean.

**A re-check needs only the pad phrase and criterion 1's example.**

## Addendum 2: revision at 694b8a2f: PASS

The delta c528a9b6..694b8a2f is 3 lines in `docs/stories/RM-real-money.md` and nothing else, so the builder's claim
holds.

- **SF2: MET.** The pairing now reads "minus Rs 1 per unit on every leg at entry and at exit (research's PAD,
  `fno/research_engine/cycle_costs.py:24`)". Criterion 1 pins it: 2 legs × entry and exit × 65 × Rs 1 = Rs 260 per
  trade, "not Rs 65". This is the research `PAD`'s own scope ("worse on every leg at entry and at exit").
- SF1, notes 1-3, the owner's Q1-Q3 (e7f40e8f) and the rename are unchanged from addendum 1.

**Gates (trial merge with origin/main 72d474c7, tree 31671c3, clean, `-n auto`):**
- pytest: 6521 passed;
- `ruff check`: clean;
- `ruff format --check`: 1155 files formatted;
- `check_imports`: clean.

**Verdict: PASS.** ChatGPT's review follows (rule 9). The code starts only when a version reaches the gate and the
orchestrator says go.

## Addendum 3: revision at 96c444dc (ChatGPT review 125 written in): FAIL (1 should-fix)

Scope as asked: the five review-125 points. Response 199 on main is the orchestrator's answer to review 125.

- **Settlement charges: MET.** Criterion 1 charges a leg settled by E7 with C1's `settlement_charges_breakdown`
  (`fno/costs.py:43`), never an invented closing order's.
- **Two times per leg: MET.**
  - The quote time is the screenshot's capture time, typed from the image, with the file-name check.
  - The order time is the submission time, from Groww's confirmation or the contract note.
  - The two are stored apart. Age = order time − quote time; below 0 or above 5 minutes is "unknown".
  - Criterion 2 pins a 10:00 screenshot as valid for a 10:04 order, unknown for a 10:07 order, and unknown when the
    screenshot comes after the order.
  - The A16 fallback is timed by its observed fetch time.
- **Strictly after: MET, unchanged.** Criterion 6 adds that a missing 10:30 quote is "unknown", never taken from
  10:45.
- **No private figures in git; interrupted writes: MET.** Criterion 9 adds a test that reads the git diff after
  `record-entry` and `record-exit`. A Drive write cut off mid-way never marks an exit as recorded.
- **Stops in exit-time order, and breaches: MET.** A stop takes effect at the exit that crossed it. A real trade
  entered after that exit is a protocol breach and never counts toward a pass. Unknown legs are left out of (b)'s mean
  with their count shown.

**SF1. "Records pending" starts too late, so a stop-crossing exit can go unflagged while another card is placed. This
is the window the orchestrator asked about, and it exists.**
- **Evidence:** the rule sets pending "whenever an entered real trade has no reported exit or settlement by the close
  of the session after its exit alert or expiry". Criterion 10 expects an exit at 10:00 (−Rs 21,000), reported at
  15:00, to make the 12:00 card show "do not place: unreconciled". Under the rule as written, the trade is not pending
  until the close of the next session, so at 12:00 the card shows nothing. The criterion and the rule disagree.
- **Path in normal running:**
  - Session S: E8's exit alert fires at about 10:15, and the owner exits in Groww at 10:20 but reports nothing.
  - Session S, after 15:15: the next card posts with no warning, and the owner places it.
  - Session S+1: the owner places another card in the morning, still with no warning.
  - Only after S+1's close does the status turn pending.

  Two trades are entered after a stop-crossing exit. The breach rule then excludes them from the pass, but it cannot
  give back the real money already risked. Stopping new real trades after a stop is the stop's whole purpose.
- **Fix (text):**
  - Pending starts the moment an open real trade has an exit alert or reaches expiry with no recorded exit or
    settlement, or a Drive write fails, and it lasts until the exit is recorded.
  - "By the close of the next session" stays only as the point where a missing report is escalated: one #fno-desk
    alert, and the trade is listed as unreconciled.
  - Criterion 10 then holds as written.
  - Known limits should say that an exit the owner makes with no exit alert cannot be detected until it is reported.

**Gates (trial merge with origin/main eac6b2b3, tree 4e138a1, clean, `-n auto`):**
- pytest: 6524 passed;
- `ruff check`: clean;
- `ruff format --check`: 1157 files formatted;
- `check_imports`: clean.

**A re-check needs only the start of the "records pending" rule, its escalation line and the Known-limits line.**

## Addendum 4: revision at 73850818: PASS

The delta 96c444dc..73850818 touches the "records pending" bullet, criterion 10 and one Known-limits line. The
orchestrator's request queued at 21:59 UTC and reached me at 23:14.

- **SF1 (addendum 3): MET.**
  - Pending now starts "from the moment an open real trade has a delivered exit alert or reaches expiry with no exit
    or settlement recorded, or a reported fill's Drive write fails, until the record is made".
  - The close of the next session is only the escalation point: one #fno-desk alert naming the trade as unreconciled.
  - Criterion 10 now names the 09:45 alert, pending from 09:45, and the 12:00 card showing "do not place:
    unreconciled". The stop is dated 10:00, and later trades are breaches.
  - With an alert, the window is closed. A stop-crossing exit after an alert can no longer go unflagged while another
    card is placed.
- **The remaining limit, stated as asked:** "An exit the owner makes without an exit alert … cannot be detected until
  it is reported; until then no card warns". That is correct, because only a report can show it.

**Gates:**
- The branch conflicts with main in `reviews/chatgpt/README.md` and `reviews/claude/README.md`, rows only. With the
  conflict markers left in, 4 tests fail.
- With both sides kept (trial tree e98c530, origin/main 65bf6804), `-n auto`: pytest 6814 passed; `ruff check`
  clean; `ruff format --check` 1210 files formatted; `check_imports` clean.

**Verdict: PASS.** Keep both sides of the two README conflicts at the merge. ChatGPT re-reads only if the orchestrator
sends it.
