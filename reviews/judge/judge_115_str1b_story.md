# Judge 115: story STR1b text, activation gates for the one- and two-leg structures (quality rule 1; judge C)

Date: 15 Oct 2026 (UTC). Branch `story/str1b-activation-gates` at **53abdc0e9dc6678b2caf1e2ae4475ee19ad6420e** (text only:
`docs/stories/B-research-engine.md`, STR1b). Checked against ChatGPT review 100, response 114, judge 106 (minors 1-6)
and the code it will change.

## Verdict: FAIL (text), 7 should-fix; the five design points ruled below

The story covers every point of review 100 and every judge 106 minor (gap list checked line by line). The direction is
right, but seven gaps would let the built story pass while still leaving an activation path open or counting money
wrongly:
- no code-enforced activation gate;
- shadows left unscoped;
- 0.45 × debit still counted twice on debit verticals;
- a binding that is too broad in one place and too narrow in another;
- "before any margin lookup" not achievable as written;
- a bypass test aimed at the wrong function;
- the shape rule's chain left unspecified.

All are text fixes; code starts after the re-check.

## Coverage of the inputs

| Input | Covered by | Check |
|---|---|---|
| Review 100 pt 1: C4-bound pass before any fill; bypass test; C2 derives shape and bought-only from legs | Scope 1-2, criteria 1-4 | Yes, with should-fixes 4-7 |
| Pt 2: broker margin, premium, stress reserve, total funds; no 0.45 × premium on LC/LP; verticals bounded without counting premium twice; not S2's denominator | Scope 3, criteria 5-6 | Partly: should-fix 3 |
| Pt 3: ATM is a mechanical definition; 3%-OTM is its own code | Out, with reason | Yes |
| Pt 4.1 E5, 4.2 E7, 4.3 E4/E8, 4.4 per-code dates, 4.5 cost wall first, 4.6 separate accounting | Criteria 8, 9, 10-11, 7; Out (R1); 5-6 | Yes. E8 must also be an enforced gate: should-fix 2 |
| Judge 106 minors 1, 2, 3, 5, 6 | 5-6, 7, 1-2, 12, 8-10 | Yes. Minor 4 (text) was fixed in response 114 |

## Rulings on the five design points

**(a) `StructureMatchesLegs` rebuilds the labelled structure with B2: ACCEPTED, with two conditions.**
- It reuses the proposer's own B2 code, so it is not independent. It does not need to be: its job is to make C2's label
  honest, and C4 stays the independent shape check.
- **Condition 1: one chain rule.** It must rebuild on exactly the chain D2 built from: D2's `live_chain`, with valid,
  non-stale quotes of the opportunity's expiry, and the market's spot. Otherwise a correct D2 proposal can be refused,
  or a stale-quote strike accepted (should-fix 7).
- **Condition 2: "before any margin lookup".** `RiskManager.evaluate` runs every rule. Either the manager stops after a
  failed shape rule, or `MarginRoom` derives `bought_only` from the legs itself and never reads a row for an unknown or
  mismatched code. Criterion 1 needs a test that observes no margin read (should-fix 5).

**(b) Binding covers terms and legs, not prices, plus the margin row, the `margins.csv` SHA and the snapshot: ACCEPTED,
with three changes (should-fix 4).**
- **Excluding prices is right:** the fill is at the execution quotes, and E4's entry limit against C2's own entry cash
  (judge 71) already bounds the price.
- **Add the book and the version to the hash:** book, strategy name and version, and `rule_sha256`. A pass for Book 1's
  version cannot then fill a shadow's or another version's identical legs.
- **Fix the canonical encoding:** sorted-key JSON, strikes and widths as decimal strings (`25000` and `25000.0` must
  hash alike). C4 and E3 compute it from plain values.
- **Do not gate on the whole `margins.csv` SHA.** The file is append-only and A14 can append between 15:00 and 15:15
  when GitHub's schedule runs late (it has run hours late). Equality would refuse every fill that day for nothing.
  Gate on the file read at the decision being a byte-for-byte **prefix** of the file at the fill (append allowed; edit
  or removal refused), plus the bound row still present. Record the SHA for audit.

**(c) Capital split; SF/SC/BF unchanged, shown row by row: the split ACCEPTED; the cap must change (should-fix 3).**
- **The four figures and LC/LP's zero reserve are right.** By algebra, `broker_margin + stress_reserve` (uncapped) equals
  today's `at_entry` margin, so nothing moves for four-leg codes unless the cap binds.
- **The cap still counts a debit spread's premium twice.** Capped "at the worst terminal loss", a debit vertical keeps
  0.45 × debit as a reserve, while that debit is already in `premium_paid`.
  - Judge 106's real CDS 200 row (scan = NOV = 7,939.75; exposure 29,538.53) gives
    `stress_reserve` = 1.45 × 7,939.75 − 7,939.75 = **Rs 3,572.89**. The cap (worst loss ≈ 7,939.75 plus charges)
    does not bind.
  - Total funds are then exposure + debit + 3,572.89. That is the double counting review 100 forbade ("without counting
    premium twice").
- **Required wording:** for the six STR1 codes, the stressed SPAN component `max(0, k × scan − NOV)` is capped at
  `max(0, worst terminal loss − net premium paid at entry)`. That gives 0 for LC, LP, CDS and PDS (their loss is already
  paid), and the full stressed figure up to `width − credit` for CCS and PCS.
- **Leave SF, SC and BF out of the cap.** BF is a debit structure too, and the owner's 1.45 came from a BF 300 margin
  rise (response 77). Capping BF would loosen a four-leg rule the owner set, so that is the owner's call, not this
  story's. Restricting the cap to the six codes makes "four-leg unchanged" true by construction. The row-by-row test
  then guards it.
- **"Every row of `margins.csv`" is empty today:** the file holds a header and no rows (judge 105). Prove "unchanged"
  on NSE's real 14 Oct `i1` rows for SF, SC and BF at every width (judge 77's and judge 106's file, SHA-256
  `d85b883a…0e8b5b`) as fixtures.

**(d) Per-code broker approval dates: ACCEPTED.**
- Add one boundary: a code's row for the day before its own `passed_on` is printed, never written; the row on the day
  itself is written.
- Note the order with C5 (`story/c5-risk-buckets`, open): both change `config.yaml` `risk`. Whichever merges second
  resolves with both sides.

**(e) E5/E7/E4 tests; E8 as a skipped pending-gate test: NOT ENOUGH on its own (should-fix 2).**
- A skipped test is a reminder, not a gate: nothing in code stops a playbook version with PCS from being approved to
  paper, or registered as a shadow, the day the owner's broker check lists PCS, with E8 still unbuilt.
- **Required: a code-enforced activation gate.** D1 (the playbook loader and the status changer) and D2's shadow path
  refuse any version whose structure is a STR1 code while an activation record in code is incomplete. For example:
  `STR1_ACTIVATION_PENDING = ("E8",)`, plus each gate this story closes when it passes. A test pins that a STR1-code
  version is refused today.
- **E8 test:** prefer `pytest.mark.xfail(strict=True)` over a skip, as P1 did, on a test that imports E8's
  `OwnerTiming` and runs the 60-minute case.
  - It fails today, so it shows as xfail, visible in every run's summary.
  - The day E8 exists it XPASSes, and strict mode turns that into a suite failure. That forces the gate's removal to be
    a deliberate, judged change.
  - A plain skip never flips by itself.

## The offered split: ACCEPTED, with one condition

- STR1b-1 (criteria 1-7) and STR1b-2 (8-11) are independent in code.
- **Condition:** the activation gate (should-fix 2) lands in STR1b-1 and lists STR1b-2 and E8 as pending. Merging part
  1 alone then leaves every new code refused.
- Criterion 12 applies to both parts.
- STR1b-1 touches `MarginRoom`, which C5 also changes. Build STR1b-1 on `main` after C5 merges, or state the conflict.

## Should-fix (text, before code starts)

1. **Shadows are unscoped.**
   - Design v2 runs the first V-ideas as `exploratory_shadow`, and they are the most likely first users of verticals.
   - Shadow accounts are paper accounts with their own fills (`journal/shadow/…`).
   - The story must say whether shadow entry fills need the same bound C4 pass (and through which C4 mode), or that STR1
     codes are refused for shadows by the activation gate until they do.
2. **Code-enforced activation gate**, plus the E8 test as a strict xfail (ruling e).
3. **Capital cap without double-counting the debit**, restricted to the six codes, proven on the real 14 Oct `i1` rows
   (ruling c).
4. **Binding:**
   - add the book and the version (name, version, `rule_sha256`);
   - a defined canonical encoding;
   - `margins.csv` checked as an append-only prefix plus the bound row, not by whole-file equality (ruling b).
5. **"Before any margin lookup":** state the mechanism (stop after the shape rule, or a leg-derived `bought_only` that
   reads no row for a mismatched label), and test that no margin is read (ruling a).
6. **The bypass test targets the wrong level.**
   - The primitive that records an entry fill is `DeskRecords.record_fill` with `FILL_OPEN` (and `FILL_UNWIND`), which
     calls `AccountWriter.apply_fill`; `EntryDesk.enter` is only today's caller.
   - The static test must list every call site that records an opening fill, by action, so a new direct caller fails
     it. Shadow fills included (should-fix 1).
7. **`StructureMatchesLegs` must rebuild on D2's own `live_chain`** for the opportunity's expiry, never a chain of its
   own (ruling a).

## Minor (text)

- Criterion 1's "81 pairs" includes the 9 true labels: say 72 mislabelled pairs refused and 9 true labels passing.
- Criterion 8: name the alert class and say the pending exit stays visible in the account, not only in a desk record.
- Criterion 9: the settlement source must be NSE's final settlement price from that expiry's own file (E7's
  `SttlmPric`), never a later close.

## Project rules

Text only; lane 1 (acceptance criteria). It lists its test files, a mutation per criterion and a real output sample
(quality rules 3-6). The size budget is respected (`composition.py` must not grow).

**Verdict: FAIL for 53abdc0e9dc6678b2caf1e2ae4475ee19ad6420e** (story text), on should-fixes 1-7. A re-check needs only
the STR1b section.

## Addendum 1 (15 Oct 2026): revised text at 0462f71bcacd01989b89f190e8704da2d7fa52cf

Text only (`git diff 53abdc0 0462f71`: one file, the STR1b section and STR1's status line).

| Item | Status | Evidence |
|---|---|---|
| sf 1, shadows | MET | Shadow and paper entry fills take the same bound-C4 path (playbook mode against the shadow's own account; orchestrator's logged decision). The activation gate refuses STR1 codes for shadows until STR1b-2 passes |
| sf 2, activation gate and strict xfail | MET | `STR1_ACTIVATION_PENDING = {"STR1b-2": ("shadow", "paper"), "E8": ("paper",)}`. D1's loader and status changer, and D2's shadow path, refuse STR1 versions while the gate is open. Criterion 8 tests the gate both shipped and with "STR1b-2" removed. The E8 test is `xfail(strict=True)` importing `OwnerTiming` |
| sf 3, capital | MET | For the six codes only: `stressed_span` is capped at `max(0, worst terminal loss − max(0, net debit))`. That gives 0 reserve for LC, LP, CDS and PDS, and at most `width − credit` for CCS and PCS. SF/SC/BF are uncapped, so they equal today's figure by algebra. This is proven on the real 14 Oct `i1` rows, and the CDS figure is checked by hand |
| sf 4, binding | MET | Hash fields: book, version, `rule_sha256`, trade ID, terms, legs. Sorted JSON with decimal strings (`25000` equals `25000.0`). `margins.csv` is checked as a bound-length prefix with its SHA, plus the bound row; an append is accepted, an edit or truncation refused, and both SHAs recorded |
| sf 5, no margin read | MET | The manager stops reading data after a failed shape rule (later rules "not run"); criterion 1's spy records zero reads |
| sf 6, bypass at the primitive | MET for openings | `record_fill` requires a `VerifiedPass` for `FILL_OPEN` and `FILL_UNWIND`; a static test lists their call sites, shadows included |
| sf 7, D2's chain | MET | It rebuilds on D2's own `live_chain`, and a stale-quote strike is refused |
| Minors | MET | 72 mislabelled pairs plus 9 true labels; the pending exit stays open in the account and is alerted; `SttlmPric` comes from the expiry day's own file |
| Split | MET | STR1b-1 = scope 1-6 and criteria 1-9, including the gate; STR1b-2 = criteria 10-13. Built after C5 merges |

### The orchestrator's question: can the pass-free CLOSE and SETTLE be abused? Yes, today; one should-fix

**`AccountWriter.apply_fill` never checks direction** (read: `fno/books/account.py:134-151`).
- It refuses a reused fill ID and a fill on an already **closed** trade.
- It accepts any fill on a **new** trade ID, and any fill that adds to or flips a held position.
- `DeskRecords.record_fill` passes the action through untouched.

So under the revised text, with the pass required only for `FILL_OPEN` and `FILL_UNWIND`, a caller could record
`FILL_CLOSE` on a new trade ID, or a "close" that sells more than is held, and open risk with no C4 pass. That is the
exact bypass the binding exists to stop. The static call-site test lists only `FILL_OPEN`/`FILL_UNWIND` sites, so it
would not see it.

**Should-fix 8 (text, then code in STR1b-1).** `record_fill` with `FILL_CLOSE` or `FILL_SETTLE` is accepted only when
every one of its fills reduces an existing open holding of the same trade and contract, in absolute units, by at most
what is held:
- never a new trade ID;
- never a contract the trade does not hold;
- never more units than held;
- never a change of sign.

Add these as cases in criterion 4:
- close on a new trade ID;
- close of a contract not held;
- a close that sells one more unit than held (it flips a long into a short);
- a close that adds to a short;
- settle of a non-expiring leg;
- settle of more units than held.

Each must be refused, and the static test must list every `FILL_CLOSE`/`FILL_SETTLE` call site too.

**Why this is right (risk manager, reasoning only).** A risk-reducing exit needs no pre-trade check, but only if
"risk-reducing" is enforced. E4's exits and E7's settlement already only reduce holdings, so the check costs them
nothing.

**`FILL_UNWIND`.** It needs the pass of the order it unwinds, which is consistent. With should-fix 8, an unwind could
equally be checked as reducing only. Keeping the pass is acceptable and stricter.

**Verdict: FAIL for 0462f71bcacd01989b89f190e8704da2d7fa52cf** on should-fix 8 only (text). Judge 115's seven
should-fixes and three minors are all met. A re-check needs only scope 2's exit sentence and criterion 4.

## Addendum 2 (15 Oct 2026): 6b62348baaaa28a773eca71a5ee7c9835a23ebd0

Only scope 2 and criterion 4 changed, plus the test-plan line and status (`git diff 0462f71 6b62348`: one file).

**Should-fix 8: MET.**
- **The rule's place.** The reduce-only rule for `FILL_CLOSE` and `FILL_SETTLE` now lives in `AccountWriter.apply_fill`,
  the primitive that writes the ledger. Callers cannot go round it.
- **What it refuses:** a new trade ID, a contract not held, more units than held (a flip), an addition to the holding,
  and a settle of an unexpired leg.
- **Criterion 4's cases:** my six refused cases plus two accepted ones (an exact full close and a partial close).
- **The static test** lists the call sites of all four actions.

**Two points for the code (minor; I check them when I judge STR1b-1):**
1. `apply_fill` does not know a fill's action today (E1's `Fill` has none; `DeskRecords.record_fill` holds it). So
   the action, or an opening/reducing intent, must reach `apply_fill` with the fill.
2. **Where the pass check lives.** The `VerifiedPass` check sits in `record_fill`, one level above `apply_fill`. Today
   `record_fill` is `apply_fill`'s only caller in `fno/`, `tools/` and `research/` (my grep), but a new direct caller
   would skip the pass. The static test must therefore also list every call site of `AccountWriter.apply_fill`, or the
   pass check must move down into `apply_fill`.

**Verdict: PASS for 6b62348baaaa28a773eca71a5ee7c9835a23ebd0** (story text, quality rule 1).
- Judge 115's seven should-fixes, three minors and should-fix 8 are all met.
- STR1b-1 code may start after C5 merges.
- I judge the code against criteria 1-9 and the two points above.

## Addendum 3 (15 Oct 2026): STR1b-1 code at 918c5ef8c9b9d64afeffae7bd2b91356640394c1

The capital split, per-code broker approvals, C4's margin row and the activation gate (story text as trimmed in judge
126). Judged on the real paths, under the owner's "keep the design simple" rule.
- Gates: 5,261 passed; ruff, format and imports clean.
- `merge-tree` with `origin/main`: only `reviews/claude/README.md` (index rows). With E1b (ddcefcc): no conflict.

## Verdict: PASS (code)

### The builder's correction to scope 1: ACCEPTED, with the evidence below

- **As passed,** the cap would replace the stressed SPAN figure with "the worst loss beyond the premium". On a credit
  spread that is below the broker's own unstressed figure. CCS 100 on 14 Oct: broker `scan − NOV` Rs 6,893.25 against
  a cap of Rs 2,564.25. C2 would then check less money at entry than Groww blocks, which breaks the standing rule that
  C2 is never looser than the broker at entry (judge 77 addendum 3).
- **The correction,** `max(broker, min(stressed, cap))`, keeps the broker floor and caps only the stress extra. That is
  the right reading of the story's purpose: no stress reserve on money that cannot be lost twice.
- **My recomputation on all 31 real STR1 rows** of `tests/risk/fixtures/margins_2026-10-14.csv` (lot 65), using its own
  scan and NOV:
  - LC, LP, CDS and PDS (debit rows): cap 0, so the SPAN figure used is the broker's (0). Judge 106 minor 1's 0.45 ×
    premium reserve on long options is gone (LC ATM: Rs 15,828.64 uncapped stress, now 0).
  - CCS and PCS: the broker figure is above the cap on every width, so the figure used is the broker's (CCS 100: Rs
    6,893.25; PCS 100: Rs 5,698.55).
  - On every row: broker ≤ used ≤ uncapped stress.
- **For the owner, in plain words:** on today's real data the 1.45 stress adds nothing for the six STR1 codes. C2 checks
  what Groww blocks, plus the premium for bought legs. For a defined-risk spread that is already at least its worst
  loss. SF, SC and BF keep the 1.45 unchanged.

### Real paths

| Real path | Status | Evidence |
|---|---|---|
| C4 equals C2 on the margin | MET | `validity_margin.span_cap` and `stressed_per_lot` are C4's own arithmetic with the same broker floor (no `fno.risk` import), and the builder's 47 real rows match |
| Capital split recorded | MET | `capital_at_entry` writes the broker margin, premium paid, stress reserve, total and `capital_tied` (broker plus premium) into C2's record. Scoreboard B counts `capital_tied`, never the reserve |
| Per-code broker approvals | MET | `BrokerApprovals` holds one approval per code. `config.yaml` is migrated to SF, SC and BF on 14 Oct (the codes that check compared). STR1 codes have none yet, so no STR1 row is written and C2 refuses such trades (fail closed) until a check passes for each |
| Activation gate | MET | The loader refuses a registered or paper/paused version of an STR1 code while `STR1_ACTIVATION_PENDING` lists a gate for that use. An unregistered research draft still loads |

**Verdict: PASS for 918c5ef8c9b9d64afeffae7bd2b91356640394c1** (code), including the scope 1 correction. Rule 9:
ChatGPT next.
