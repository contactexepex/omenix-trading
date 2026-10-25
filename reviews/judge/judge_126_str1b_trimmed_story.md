# Judge 126: STR1b story text trimmed under "keep the design simple": `story/str1b-activation-gates` 5e20bbcc349b17c09fc6868fc1c877ae335994dd (quality rule 1, text only; judge A)

**Number note.** STR1b's response is 115, and `judge_115` is judge C's file, so I used 126, the next free number.

**What I checked:**
- `6b62348..5e20bbc`, the STR1b section of `docs/stories/B-research-engine.md`, and `response_115`'s trace table;
- each dropped guard's stated reason, read against the code on `main` today;
- under the owner's 15 Oct rule (DESK_DECISIONS "Keep the design simple"): a should-fix needs a concrete path in the
  normal running of this system, with evidence.

## (a) Do the 4 kept items close every real path? YES, with one note

| Kept item | A real path? | Check |
|---|---|---|
| Capital split (scope 1, criteria 1-2) | Yes, on every LC/LP/CDS/PDS trade | The 0.45 × premium (Rs 15,828.64 on the real ATM call) and 0.45 × debit (Rs 3,572.89 on the real CDS 200 row) would be counted as capital. The wording is judge 115 ruling (c) unchanged: capped for the six codes only, with SF/SC/BF proven unchanged on the real 14 Oct `i1` rows |
| Per-code approval dates (scope 2, criterion 3) | Yes | The owner's broker checks will arrive one code at a time |
| Margin row named, and still there at the fill (scope 3, criterion 4) | **Naming the row: yes** (audit). **The "row gone" refusal: no real path found** | A14 writes `margins.csv` append-only (`fno/nse_margins/margin_log.py:1`, `open(..., "a")`). A14's late append between the 15:00 decision and the 15:15 fill is real, and criterion 4 rightly accepts it. But a bound row can disappear only by a hand edit. That is the same class of scenario the trim drops elsewhere. **Note 1** |
| Activation gate (scope 4, criterion 5) | Yes | See (c) |

## (b) Does each dropped guard's reason hold? YES, all four, verified in code

1. **C2 rebuilding the label from the legs.**
   - The only order builder on `main` is Book 1's `ReplayedOrders` (`fno/books/book1_orders.py`). `EntryOrder(` is
     built nowhere else in `fno/`.
   - It replays D2's evaluator on the stored inputs and must reproduce the stored records exactly. Every order is
     therefore D2's own B2-built proposal, whose label matches its legs by construction.
   - C4's independent shape check is the gate. Judge 106 probed it with 54 planted naked shorts and every mislabelled
     shape refused.
2. **Hash-binding the C4 pass to the proposal, book and version.** The reason is stronger than the response says.
   - `RecordedC4Pass` (`fno/desk/recorded_c4.py`) refuses an edited run through `DecisionStore.edited`.
   - `ReplayedOrders` refuses an order unless the replay reproduces the committed records, `validity.c4` included.
   - So the filled proposal **is** the checked one. A different proposal needs a hand edit, which is refused.
3. **`VerifiedPass` and the static call-site test.**
   - `EntryDesk.enter` has one caller, `fno/desk/daily_steps.py:162`, after the validity gate.
   - `record_fill(... FILL_OPEN / FILL_UNWIND)` occurs only in `fno/desk/entries.py:137,147`.
4. **`apply_fill` reduce-only.**
   - `ExitDesk._close` records `FILL_CLOSE` only for `closing_quotes(snapshot, position.holdings)`.
   - `_settle` settles only `position.holdings` of expired expiries (`fno/desk/exits.py`).
   - Both read the holdings from the journal. A risk-adding close needs a hand-built fill.

## (c) Does the activation gate alone keep STR1 codes inactive until STR1b-2 and E8 exist? YES, today. One note for later

- **Today.** The only trading path is Book 1: D1's playbook versions, then D2, then `ReplayedOrders`, then E3. The
  shadows go through D2's shadow path. The gate sits in D1's loader and status changer and in D2's shadow path, so it
  covers both.
- Criterion 5 tests both refusals, and also tests "STR1b-2 removed: shadow allowed, paper still refused".
- **Note 2 (design-documented, not built).** Book 3 registers its own strategies in `book3/strategies/registry.csv`
  through `fno/book3/registry.py` (D5, `docs/stories/D-playbook-decisions.md:173-196`), not through D1's loader. No
  Book 2 or Book 3 code exists on `main` (`fno/` has no `book3`), so no path exists today. But if Book 3 is built before
  STR1b-2 and E8, its registry would not meet this gate.
  - Under the owner's rule this is a one-line Known limit, not a guard: "an order path outside D1 (Book 3's registry,
    D5) must check `STR1_ACTIVATION_PENDING` in its own story".

## ChatGPT (rule 9)

- **Yes, a line should be added.** STR1b touches money and fills. The trim drops three of review 100 point 1's asks
  that response 114 had accepted:
  - C2 deriving the shape from the legs;
  - the proposal-hash binding;
  - the bypass test.
- `response_115` already holds the table "for ChatGPT and the owner", with a restore route (6b62348).
- **Ask:** one line in STR1b's quality-rules text: "ChatGPT reviews the trim (`response_115`) before STR1b-1's
  merge; a point it upholds with a real path is restored from 6b62348". Without it, a reversal of an accepted review
  point would never reach the reviewer who made it. That is a CLAUDE.md rule ("Everything for the other AI goes in the
  repository"), not an imagined case.

## Other checks

- **The gap list is consistent.**
  - Judge 115 should-fix 1 (shadows) and 2 (the gate) map to criteria 5 and 10.
  - Should-fix 3 (the cap) maps to 1 and 2.
  - Should-fixes 4-8 and review 100 point 1's other parts are under Known limits, each with its reason.
  - Point 1's margin-row part is kept.
- **"Judge verifies: removes a bound margin row between decision and fill."** Under the new rule I will not plant
  that, since it is a hand edit (note 1). I will check that C4 names the row, that an A14 append fills, and the other
  listed checks: the CDS 200 and CCS splits by hand, SF/SC/BF on the real rows, a code added to the map, and an STR1
  version refused.
- **Known limits are one line each**, as the rule asks.

## Notes (one line each, not findings)

1. Scope 3's "bound row gone" refusal guards only a hand edit (A14 is append-only). Keep "C4 names its row" for audit.
   The refusal and criterion 4's second bullet could go under rule point 4: the orchestrator's call.
2. Add the Known-limit line for order paths outside D1 (Book 3's D5 registry).
3. Add the rule-9 line for ChatGPT's review of the trim.

### Verdict: PASS for 5e20bbcc349b17c09fc6868fc1c877ae335994dd (story text)

- **No should-fix.** Every dropped guard's reason holds in today's code (verified). The four kept items cover the
  real paths, and the activation gate holds every STR1 code today.
- **The three notes** are one-line text additions. I recommend note 3 (ChatGPT) before the code's merge.
