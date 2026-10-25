# Judge 479: MS-P1a, the market school pilot contracts

**Scope:** story/ms-p1-contracts at 756e6545 (builder session_01CmKJ6taCLzfEGg7wt6RC4N). Story MS-market-school.md
sections 3-4 and its Claims; design response 327 rev 2. Lane 1. Round 1 of 2.

**Verdict: FAIL.** There are 4 should-fixes. Criteria 1-6 and 8 are met. Criterion 7 (no order, Slack or Groww import)
is not proven. Three contracts that the parallel parts need are missing, so those parts would define them twice.

## Met (checked)
- **Gates (my run):** pytest -n auto gives 10244 passed and 16 xfailed. ruff check, ruff format, check_imports and
  check_records are clean. The largest file is 200 lines.
- **No forbidden files touched.** The diff touches only `config.yaml` (the `school` block), `fno/config.py` (one
  line), `fno/school/`, `tests/school/` and the story. Nothing touches DAILY_RUN_STEPS, v4 or a frozen file.
- **The `school` block is all off.** `enabled` and `reports` are false and `first_counted` is empty. The limits are
  10,000, 25,000, 1.2 lakh, 5, and 30,000 / 1.5 lakh / 50,000. A test pins them to today's book caps.
- **Write-once and deterministic.**
  - Canonical JSON with sorted keys, no NaN, -0.0 written as 0.0, and an int in a float field written as a float.
  - gzip time is zero.
  - `DashcamStore.seal` is the same for the same records, and other records raise `ReplayConflict`.
- **Seal before fill.** `Seal.covers` requires the same SHA-256 and pushed_at <= the fill time.
  `FillPort.enter`/`exit` take the seal, and `FillResult` is exactly one of filled, refused or state.
- **Banner** has 2 members. **OpportunityCounts** holds eligible >= fillable >= executed >= 0.
- **Records hang together.** A closed road is exactly a `road_closed` decision with the same reason, and a refusal
  carries its proposal.
- **Plants: 13 of my own, 11 caught.** Caught: a seal 5 minutes late, a seal of another file, executed above
  fillable, an open road without a snapshot, an empty fill result, costs above max loss, a law result without a
  reason, gzip time not zero, a bool accepted as a limit, a close without an exit reason, fake fills at mid.

## Should-fixes
1. **The import boundary misses relative and transitive imports (criterion 7).**
   - Defect: `test_boundaries.py` matches only absolute names. `from ...providers.groww import GrowwProvider` and
     `from ...alerts import slack`, planted in `fno/school/roads/`, both pass. The package itself uses relative
     imports (`contracts/roads.py`: `from ...quotes.recorder import DATASET`).
   - Defect: importing `fno.school.contracts` already loads `requests`, `fno.providers` and `fno.intraday.pacing`,
     through `fno/quotes/recorder.py`, just to read a dataset constant. The test's own FORBIDDEN list names
     `requests`, `fno.providers` and `fno.intraday`.
   - Test it must pass: each plant above fails the test. A fresh interpreter that imports every `fno.school`
     module finds none of the forbidden modules in `sys.modules`, or the claim names exactly which ones are allowed
     and why.
   - [reasoning only: resolve each relative import against its file's package; take the dataset names from a
     module that loads no capture code]
2. **The dashcam cannot be asked what is already sealed.**
   - Defect: `DashcamStore` has only `seal(records)` and `read(seal)`. Part j's "a rerun skips sealed decisions",
     part g's sections (a session's records) and part i's two-run comparator each need the seal of a (session,
     slot, kind) without re-deciding. Each would add its own lookup to c's class, outside the contract.
   - Test it must pass: a conformance check that the lookup returns None before `seal` and that Seal after, on the
     fake and on c's store.
3. **Tickets cannot relax "only the account limits" through the contract.**
   - Defect: part f must check tickets with the same laws, with only the account limits relaxed (3.3 and story f,
     including a driver stopped by the daily stop or brake: `TicketReason.DRIVER_STOPPED`). Nothing in `SafetyLaw`
     or the constants says which laws are account limits, so d and f would each decide it.
   - Test it must pass: one frozen definition, tested to be exactly bucket, open risk, new risk a day, margin room,
     daily stop and brake, and never protection, max loss or any quote-gate reason.
4. **No fleet contract for the harness.**
   - Defect: part i must make "the fake fleet" give each planted fault's exact reason code, and part j's real runner
     must then pass the same harness. There is no `FleetRunner` protocol and no fake fleet, so i must write its own
     loop in j's order (roads, gate, drivers, laws, seal, fills, ...), a second definition of j.
   - Test it must pass: a `FleetRunner` protocol (`run(session, mode)`) with a fake that passes a conformance check:
     one sealed outcome per scheduled (road, driver), decisions sealed before any fill.
   - [reasoning only: or the story drops i's fleet run until j exists]

## Notes (no action required)
- `OpportunityCounts` has no scheduled count, so a rate built from it alone would drop `road_closed` and
  `unavailable` from the denominator (3.5). g must count denominators from the decision records; worth a line in
  g's story.
- A refused ticket is a `REFUSED` decision, the same as a refused trade, so only f's counts tell them apart.

**Next:** fixes 1-4 with their tests, then round 2.

## Addendum 1

**Scope:** story/ms-p1-contracts at 35458460, round 2 of 2. The four findings of judge 479 are fixed. Additive
extras: `LawResult.note`, `NoTradeReason.NO_VALID_QUOTES`, `FillResult.cash`, the law split, and MS-P1j's
requirements. One rename: `TicketReason.DRIVER_STOPPED` is now `ACCOUNT_LIMIT`.

**Verdict: PASS.** One story line must be corrected before merge (below). The code is consistent.

**Gates (my run):** 10272 passed, 16 xfailed. `ruff check`, `ruff format`, `check_imports` and `check_records` are
clean.

**Findings 1-4:**
1. **Import boundary: met.**
   - Relative imports are now resolved against each file's package. My two plants (Groww provider, Slack alerts, as
     relative imports in `fno/school/roads/`) are now caught.
   - The contracts take the sides and datasets from school constants, pinned equal to their sources.
   - In a fresh interpreter, importing every `fno.school` module loads none of `growwapi`, `slack_sdk`,
     `fno.providers`, `fno.intraday`, `fno.alerts` or `requests` (I checked by walking the package).
2. **Dashcam lookup: met.** `DashcamStore.find(session, slot, kind) -> Seal | None` is in the contract and the
   conformance check. My plant (find always None) is caught.
3. **Law split: met, with the orchestrator's ruling.**
   - The split: ACCOUNT_LIMITS = bucket, open risk, new risk a day, margin room; DRIVER_STOPS = daily stop, brake;
     TRADE_VALIDITY = everything else. The three are a tested partition.
   - My round-1 test also counted the stops as relaxed for tickets. The orchestrator ruled otherwise (reviews 138 and
     139: "relax only account-level cash/bucket limits"; a stopped or braked driver issues no tickets). I accept it:
     it is the stricter reading, and it is frozen in one place. My plant (daily stop relaxed) is caught.
4. **Fleet contract: met.** `FleetRunner.run(session, mode) -> SessionRun`, with the fake fleet in the real order
   (decide, laws, seal, fill), a rerun skip and the off switch.
   - Caught: no rerun skip, refused decisions filled, unsealed decisions allowed.
   - Also caught: `FillResult.cash` with charges added instead of taken off.

**Plants this round:** 19 of my own, 19 caught (the 13 of round 1 plus 6 new).

**Required before merge (one line, story text):** `docs/stories/MS-market-school.md` line 342 (story f) still says
tickets are issued "on a driver stopped for the day". That contradicts the contract table (line 214) and
`DRIVER_STOPS` in code. Test it must pass: f's text says a stopped or braked driver issues no tickets, and an
account-limit refusal becomes `ticket: account_limit`. The orchestrator checks this line at merge; no new round.

**Note:** `requests` left the static FORBIDDEN list. School code may now import it directly, while the fresh-interpreter
check covers only the contract modules. A Slack post through raw `requests` would pass the static test. Parts g and j
are where it matters; their judges should check that reports go only through FL1's section interface.

The final tip is 19eb4206: it adds only 4 lines of story text (a third MS-P1j requirement, the share refused for
quotes per road) to 35458460, and the code is unchanged. The PASS covers 19eb4206. The line-342 correction is still
required at merge.

## Addendum 2

**Scope:** MS-P1a2, story/ms-p1-contracts-a2 at 6a9dfde6. It branches from main, is additive, and is a short lane-1
check. The additions are `RoadDay.strike_steps` (each expiry's own step, after judge 482 SF1), `RoadStatus.detail`,
a stricter catalogue conformance check, and a comment on `Seal.pushed_at`.

**Verdict: PASS.**

- **Gates (my run):** 10283 passed, 16 xfailed. `ruff check`, `ruff format` and `check_imports` are clean.
- **Strike steps.** `strike_steps` must name every recorded expiry, each step above zero, with the nearest equal to
  `strike_step`. `step_for(expiry)` never falls back to another expiry's step. It is optional, so existing callers
  are unchanged. The conformance check now requires a real catalogue (part b) to fill it for every open road.
- **Detail.** Only a closed road carries one; the fleet records it under `ROAD_DETAIL_INPUT`.
- **Plants: 3, 3 caught.** Nearest step not equal to `strike_step`; detail on an open road; steps not covering every
  expiry.

**Note: what `Seal.pushed_at` now means.** It is the receipt commit's time, and the proof of the push is the remote
receipt (`seal` returns only after the push). In a live run, fills come after `seal` returns, so the order is kept.
But a replay or audit that checks `covers` on old seals compares commit time, not push time. A commit made before the
fill but pushed after it would pass there. Any after-the-fact check of "sealed before fill" should use O8's push
evidence, not `pushed_at` [reasoning only].

## Addendum 3

**Scope:** MS-P1a3, story/ms-p1-contracts-a3 at 9ede0d1e. It adds the `LedgerReader` port with its conformance check
and fake, `SlotQuote.sizes_measured`, and `RefusalReason.SIZE_NOT_MEASURED`. Lane 1, money piece (it changes what a
valid quote is): first of two judges, independent of judge I.

**Verdict: PASS.**

- **Gates (my run):** 11666 passed, 16 xfailed. `ruff check`, `ruff format` and `check_imports` are clean.
- **The `sizes_measured` invariant.** An unmeasured quote must carry no size: `__post_init__` raises if `bid_qty` or
  `ask_qty` is set. The default stays True, so every existing quote and capture keeps today's meaning.
- **`two_sided` and `mid` for unmeasured quotes.** Such a quote is two-sided on valid, bid and ask alone; a measured
  one still needs both sizes. `mid` is unchanged.
- **SIZE_NOT_MEASURED** falls in TRADE_VALIDITY (not an account limit, not a stop), and `test_law_split` pins the
  partition.
- **The decoder stays strict: I agree.** `from_plain(SlotQuote, {...})` without `sizes_measured` raises
  `KeyError('sizes_measured')`, which I checked. No real school record exists yet, so nothing on file breaks. A
  silent default on decode would let an old record pass as "measured" without saying so.
  - Had records existed, this layout change would have needed `RECORD_SCHEMA_VERSION` 2.
- **`LedgerReader`** matches d's `SchoolAccounts.entries`: read-only, in recorded order, () for an account never
  opened. The fake and its conformance check pass.
- **Plants: 6, 6 caught.** An unmeasured quote with sizes; measured sizes ignored; unmeasured never two-sided; the
  default flipped to unmeasured; SIZE_NOT_MEASURED counted as a stop; fake entries out of order.

**Note for d part 4 and SIM-c.** An unmeasured quote is now `two_sided`. So the refusal of a live fill on it must be
d's (`size_not_measured`), and E4's size check must never treat a missing size as enough. That belongs in d part 4's
tests.

## Addendum 4

**Scope:** MS-P1a4, per-expiry lots, story/ms-p1a4-lots at 03a467b0 (from main). It adds `RoadDay.lots` and
`lot_for(expiry)`, and e's proposal builder now uses `lot_for(plan.expiry)`. Lane 1 (lots size money): first of two
judges, independent of judge I.

**Verdict: PASS.**

- **Gates (my run):** 13804 passed, 16 xfailed. `ruff check` and `ruff format` are clean.
- **The contract.**
  - `lots` must name every recorded expiry, each lot above zero, with the nearest equal to `lot`.
  - `lot_for` never falls back to another expiry's lot.
  - Without `lots`, a recorded expiry carries `lot` and an unrecorded one has none. b guarantees that case by
    closing a road on mixed lots, and the conformance check proves it on b's real catalogue.
  - Optional and additive: existing callers are unchanged.
- **e's use.** `ProposalBuilder.build` sizes the candidate and the proposal (`risk_proposal.lot_size`, `units`) on
  the plan's own expiry's lot. No other school code reads `road_day.lot` for sizing (grep).
- **Plants: 4, 4 caught.** The nearest lot not checked; `lot_for` falling back to the nearest; an unrecorded expiry
  given the lot; the driver using the nearest lot.
