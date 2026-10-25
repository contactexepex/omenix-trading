# Judge 488: MS-P1d, safety laws, accounts and fills (first judge)

**Scope:** story/ms-p1-fills at 96704ef8 (builder session_014VUoPfMfRWNXyJSnXxB5NL), on MS-P1a's round-2 contracts.
Lane 1, money piece: first of two independent judges (JUDGE.md "Two judges for money pieces"). I did not read
judge I's verdict. Round 1 of 2.

**Verdict: PASS.** Nothing blocking, no should-fix. Three notes, one of them for the owner.

## Gates (my run, full suite as asked)
- pytest -n auto: **10519 passed, 16 xfailed, 0 failed.** The builder's 4 failures do not reproduce at this tip.
- `ruff check`, `ruff format`, `check_imports` and `check_records` (8179 files) are clean.

## The orchestrator's checks
- **Law partition.** One law per reason, in a fixed order: protected, max loss, bucket, open risk, new risk a day,
  margin room, daily stop, the 4 quote-gate laws, impossible price, brake. `refusals()` keeps every reason once. The
  reasons map onto a's ACCOUNT_LIMITS, DRIVER_STOPS and TRADE_VALIDITY.
- **The Rs 10k cap on three figures.** The cap is the largest of the proposal's figure, C2's figure at mids with the
  pad, and B2's figure at the touch the fill takes. It passes at the limit and refuses at limit + 1, and it fails
  closed on any uncheckable leg.
- **Law 3 fails closed.** A C2 `RiskInputError` or `NakedShortLeg` refuses.
  - Margin room refuses with `MARGIN_NOT_CHECKED` unless every position has a sourced row in C2's margins file,
    which holds NIFTY only. A missing or malformed file runs C2, and C2 refuses.
- **Stop and brake at the limit or above.**
  - The daily stop refuses at a loss of 25,000 or more.
  - The brake engages on a fully marked row 1.2 lakh or more below the high. It holds while engaged until a review
    row dated on or after the engagement. The high restarts after a lift, and an unmarked session never engages it.
- **The brake-lift file.** `research/school/reviews/brake_lifts.csv` must have exactly its 3 columns; a row needs a
  review reference; rows dated on or after the session are ignored; a malformed file raises an error, never a lift.
- **The bucket.** {NIFTY}, {BANKNIFTY+FINNIFTY}, {MIDCPNIFTY} through C2's `BucketMap`, unedited. Any other index or
  structure fails closed.
- **Fills at the touch, all legs or none.**
  - Entry only after the seal covers the file and by the session's 15:30 close, never before its snapshot finished,
    through E4's `price_leg`/`entry_problems` and `FillMaker`. Any gate refusal fills nothing.
  - An exit with any leg unquoted waits (`exit_waiting_quote`).
- **Bhavcopy settlement.** E7's `NseFinalSettlement` reads the stores only (`ArchivedOnly` never fetches). It returns
  intrinsic value with C1's settlement charges, or `settlement_needed`.
- **Privacy (00cc5786).** `journal/school/` is in the record scan's forbidden account paths and in `.gitignore`.
  Accounts are mirrored through E2c's private files and committed nowhere.

## Plants: 25 of my own, 24 caught
- **Caught:**
  - the touch dropped from the cap; the proposal's figure dropped; the cap refusing at the limit; a C2 law failing
    open;
  - the stop and the brake passing at the limit; the brake latch ignored; the brake engaging only above the limit;
  - a review before the engagement lifting; the high not restarted; unmarked rows engaging the brake; a review row
    without a reference; a review look-ahead;
  - margin passing without data; NIFTY margin rows used for other indices; FINNIFTY in its own bucket;
  - impossible price made inclusive; two expiries allowed;
  - a fill despite a gate refusal; a partial exit; a fill after the close; the wrong settlement state; the
    archived-only source returning bytes; the stop measured from the first session.
- **Survived (equivalent):** "C2 at mids" dropped from the cap. At the touch, the sold legs fill at the bid and the
  bought legs at the ask, so B2's touch figure is never below C2's mid figure on the same cost model (the builder's
  `test_max_loss_counts_the_touch...` shows touch > mids) [reasoning only]. Not a should-fix.

## Notes
1. **For the owner: margin room will make most of the pilot tickets.**
   - C2's margins file holds rows only for NIFTY SC, SF and BF at widths 100-300.
   - Under the orchestrator's revised ruling (no margin data, no new entry), every BANKNIFTY, FINNIFTY and
     MIDCPNIFTY proposal is refused `margin_room`. So is every credit or debit spread (PCS, CCS, CDS, PDS) and every
     NIFTY width outside 100-300.
   - These become `ticket: account_limit`. So until margin data exists for other indices and structures, the paper
     accounts hold NIFTY condors and flies only.
2. **Impossible price, per vertical.** `ImpossiblePriceLaw` checks the position total at the touch.
   - EDGE1's revision-7 rule also checks each vertical. At the touch, a vertical sold for more than its width (a stale
     bid) could hide behind a negative other vertical in a condor.
   - That needs two bad quotes at once, so it is a note, not a should-fix [reasoning only]. If it is added, only the
     per-vertical upper bound applies: at the touch a negative vertical is a costly trade, not an impossible one.
3. **Story wording.** Story d's acceptance 1 says "passes at its limit". Story 3.3 says the stop acts when the loss
   "reaches" its limit, and the brake on equity "falls ... below". The code follows 3.3 and the orchestrator ("at the
   limit or above"); acceptance 1's line should say so.

## Addendum 1

**Scope:** story/ms-p1-fills at 9ed80bc7, the diff since 96704ef8. Round 2 of 2 (first judge).
- 7064a030 only merged a's `NO_VALID_QUOTES`.
- 9ed80bc7 adds judge I's two fixes (the brake-lift date, the no-store settlement) and the per-vertical check from my
  note 2.

**Verdict: FAIL on one test-only should-fix** (the code is correct as read). My PASS of round 1 is withdrawn until
the test is in.

**Gates (my run):** 10530 passed, 16 xfailed. `ruff check`, `ruff format` and `check_imports` are clean.

**The diff, checked:**
- **Brake-lift date.** `first_review_day` is the first Saturday of the month after the engagement; December rolls to
  January of the next year. A lift row dated before that day is a `ReviewFileError`, never a lift.
- **No store.** `build_settlement_source` stops by name (`SettlementStoresNotConfigured`) when no store can be read,
  instead of waiting forever with expired positions at their worst case.
- **Per vertical.** Each bought-sold pair of one type and expiry is valued at the mids as the pair worth more at
  expiry (lower call less higher call, higher put less lower put). It must lie in [0, width], and the position total
  stays strict at the touch.
  - I accept the builder's answer to my "upper bound only" remark. At the mids, a negative vertical is impossible,
    unlike at the touch, so both bounds belong there.
- **Plants: 7 new, 6 caught.** Caught: the vertical's lower bound dropped, a put vertical oriented as a call, an
  early review lifting, the review day on the 1st of the month, December rolling into the same year, the no-store
  check removed. My 25 earlier plants: still caught, except the equivalent "C2 at mids" one.

**Should-fix.**
- Defect: dropping the vertical's upper bound (`0 <= v[0]` only) passes every test.
- It is not equivalent. For a credit spread (CS1's PCS or CCS) the position bound is checked at the touch. So a
  spread whose mids are worth more than its width (a stale mid, the case this check exists for) passes when the
  bid-ask makes the touch total fall inside the bounds.
- Test it must pass: a two-leg credit spread whose mid value is above its width while its touch value is inside the
  payoff bounds is refused `impossible_leg_price`. The plant above then fails it.

**Next:** that one test. The orchestrator decides whether confirming it counts as a round. I will re-run the plant
and confirm in one line; nothing else is reopened.

**Closed (orchestrator, 22 Oct 2026, relaying the owner).** The owner decided the d dispute in favour of judge I's
ranges rule: a per-vertical check at the mids would flag valid wide quotes and contradict b's accepted gate. The test
asked in 488.1 is therefore not added. My per-vertical intent stands, judged by judge I on ranges. I have nothing more
to judge on d. The builder had added the 488.1 test at 6019ab44 and reported my plant caught, but the owner's ruling
supersedes it. I did not judge the ranges version.

## Addendum 2

**Scope:** MS-P1d follow-up part 1, story/ms-p1d-margin at 6ef6f40b (based on main a275a0ff). Money piece: first of
two judges, independent of judge I. Round 1 of 2.
- Law 3 now runs C2's `MarginRoom`, unedited, on MS-P1m's `build_road_margin`.
- C2's inputs are built through `road_terms`, `road_proposal` and `road_open_trade`.
- `MarginRows` is removed.
- The desk-codec boundary is pinned.

**Verdict: PASS.**

- **Gates (my run):** 11266 passed, 1 skipped, 16 xfailed. `ruff check`, `ruff format` and `check_imports` are clean.
- **One set of terms for margin and units.** Every C2 law's proposal and every held position go through
  `RoadTradeTerms`, built from the trade's own index, single expiry, one-unit legs and lot. A leg ratio or two
  expiries is refused before C2. So C2's margin (priced from the terms) and C2's units (counted from the
  trade) read the same lot.
- **Fail closed, with the cause.** A margin that cannot be read, for the proposal or any held trade, is a
  `margin_room` refusal with the note "margin not checked: <named cause>", never a number.
- **The desk codecs.** No school module imports either desk codec, the composition roots load neither, and
  `TradeTerms(**asdict(RoadTradeTerms))` raises, so a school trade cannot be silently stripped of its legs there.
- **Plants: 7 new, 7 caught.**
  - The terms' lot set to 1 (the 840 vs 54,600 case); every trade priced as NIFTY; contracts named as NIFTY (the
    two-index case).
  - Two expiries accepted; an unreadable margin passing; the cause not named; an open trade carrying no units.
  - My earlier d plants still hold. The "C2 at mids" plant is still equivalent; four no longer apply (their code
    was replaced).

**Note.** Now that law 3 uses this margin, any held position whose margin cannot be read refuses every entry of
that account until it closes. Examples: an expiry past, a missing day file, an out-of-model expiry. This is fail
closed and stated in MS-P1m. The owner should expect a driver's account to sit idle on such days.

## Addendum 3

**Scope:** MS-P1d follow-up part 2, story/ms-p1d-verticals, diff 390d7131..c3f75f28. Money piece: first of two
judges, independent of judge I. Round 1 of 2.
- `ImpossiblePriceLaw` now calls b's `impossible_keys` on the proposal's legs only. d's own vertical copy is removed.
- Settlement reads b's `build_archive_stores`.

**Verdict: PASS.**

- **Gates (my run):** 11632 passed, 16 xfailed. `ruff check`, `ruff format` and `check_imports` are clean.
- **One rule for the gate and the law, as the owner decided ("ranges").** A pair of the proposal's legs of one type
  and expiry is impossible only when no price inside both bid-ask ranges fits [0, width] (1e-9 tolerance). A bid
  above what the option can ever be worth is also flagged. Only the proposal's own legs are judged, so a stale far
  strike elsewhere in the chain cannot refuse a trade. The strict position bound at the touch stays.
- **Settlement.** It reads the service account's Drive, else the owner's, else `RawFilesNotConfigured` by name. So
  settlement still never waits forever on a store nobody can read.
- **Plants: 4, 4 caught.** The per-vertical check off; the whole chain judged instead of the proposal's legs; the
  position bound off; an empty store list built without an error.

## Addendum 4

**Scope:** MS-P1d follow-up part 3, story/ms-p1d-entries, diff 80625b19..fdd64766: `SchoolAccounts.entries(driver_id)`
for j's settlement before the first view. Money piece: first of two judges, independent of judge I. Round 1 of 2.

**Verdict: PASS.**

- **Gates (my run):** 11660 passed, 16 xfailed. `ruff check`, `ruff format` and `check_imports` are clean.
- **Read-only, under the lock.** `_locked` is the shared lock-and-pull and `_writer` wraps it, so `entries` takes
  the same lock and the same once-per-run Drive pull, and writes nothing (no equity row, no account opened).
- **Never half a record.** A ledger that disagrees with the position records raises before anything is returned.
- **Plants: 4, 3 caught.** Caught: the consistency check skipped; `entries` starting the account (a write); a pull
  on every call.
  - Survived, equivalent: the "never opened gives ()" short cut removed. A never-opened account has no files, so
    the general path also returns (), and `test_entries_write_nothing...` proves nothing is created.

## Addendum 5

**Scope:** MS-P1d law order, story/ms-p1d-law-order at 2de9c037 (from main). The quote gates and `impossible_price`
now run before the risk laws: protected, the 4 quote gates, impossible_price, max_loss, bucket_cap, open_risk,
new_risk_day, margin_room, daily_stop, brake. Money piece: first of two judges, independent of judge I. Round 1 of 2.

**Verdict: PASS.**

- **Gates (my run):** 11663 passed, 16 xfailed. `ruff check` and `ruff format` are clean.
- **Only the order changes.** Every law still runs and `refusals()` keeps every reason, so no outcome changes. Who
  refuses is the same; only the first-named reason moves.
  - A ticket's `ticket_laws_pass` reads all results, not their order.
  - f's `named_refusal` still puts a driver stop first, then the first trade-validity reason, so a missing or
    one-sided quote is now named before `max_loss` (the BANKNIFTY missing-mid case).
- **Pinned tests.** `test_the_laws_in_their_fixed_order` pins the new order. Two tests check that a missing and a
  one-sided quote are named first while `max_loss` is still in the list, and one checks that a valid quote with too
  large a loss still names `max_loss` alone.
- **Plants: 3, 3 caught.** The old order restored; impossible_price before the gates; impossible_price dropped.

## Addendum 6

**Scope:** MS-P1d part 4, practice quote rules (design A), story/ms-p1d-practice at fc3ad7d4. It sits on the law
order (on main) and a3 (9ede0d1e), and was judged against a3; it merges only after a3. Money piece: first of two
judges, independent of judge I. Round 1 of 2.

**Verdict: PASS.**

- **Gates (my run):** 11830 passed, 16 xfailed. `ruff check`, `ruff format` and `check_imports` are clean.
- **LIVE.**
  - An unmeasured two-sided quote gives E4 no size, and the gate names it `size_not_measured` before any size
    reason.
  - A live exit on it waits (`closing_quotes` finds no size).
  - A quote missing a price stays `one_sided_quote`, since `size_not_measured` needs `two_sided`.
- **PRACTICE.**
  - Only an unmeasured size becomes no limit (`math.inf`); a measured size passes exactly as live.
  - The size and sell-back laws that pass on an unmeasured size carry `PRACTICE_SIZE_NOTE`.
  - Missing, one-sided and invalid quotes stay refused under both rules.
- **Isolation.** `build_safety_laws` and `build_fill_port` use `LIVE`, and practice is built only in the two
  `practice_wiring` modules. The AST test fails any other school module that imports a practice composition, calls
  `laws_with`, or writes `practice=True`. No `10**9` or `SIZE_GATE_WAIVED` remains in `fno/` (grep).
- **Plants: 8, 8 caught.**
  - Live unmeasured given no limit; practice waiving measured sizes too.
  - A one-sided quote named `size_not_measured`; `size_not_measured` never named; an unmeasured quote named
    `size_above_displayed`.
  - The practice note dropped; a live exit waiving size; the live laws built as practice.

**Notes.**
1. The isolation test covers `fno/school` only, and spots practice rules by the text `practice=True`. A positional
   `QuoteRules(True)` or a practice import from outside `fno/school` would pass it. No such code exists [reasoning
   only].
2. As in judge 507: j's `allocate` reads raw sizes (missing means 0), not through `QuoteRules`. The simulator must
   not route practice fills through it, or every one becomes `size_shared`.
