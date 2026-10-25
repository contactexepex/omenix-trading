# Judge 480: MS-P1h, the frozen comparison card

**Scope:** story/ms-p1-card at ff6c813a (builder session_01WeFYCqffRe7et1nfSJyuv5), diff 756e6545..ff6c813a only (part
a is Judge B's). Story MS-market-school.md part h and its Claims. Lane 1 (evaluation records). Round 1 of 2.

**Verdict: FAIL.** 1 blocking, 3 should-fix, 4 minor. Judge H (session_01KNkZVoWvXMkoihKrrXk5Xa; the claim row of 480
carries "session_judgeH" by my mistake).

## Criteria
| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | A card registered after a decision: not counted | MET | `counting.py:73-76` strict ancestry; real-git tests; plants 1, 5 caught |
| 2 | A changed card SHA-256 refuses counting | MET | `counting.py:70`; plant 2 caught; D6 row after decision refused on real git (plant 12 caught) |
| 3 | Five roads on one day: one cluster | MET | `clusters.py`; plants 9, 10 caught |
| 4 | `read_card` accepts the card | MET | measurement yes, hypothesis no, trial 99 (free on main); charges SHA `5177fb36...` recomputed by me |
| - | One measurement card, no Holm family | MET | factory block `hypothesis: no`, `measurement: yes` |
| - | PS5 = trial 94, KL1 = trial 76 | MET | `research/ledger.csv` lines 95 (BANKNIFTY SF TP50) and 77 (NIFTY SC3 EXP) |
| - | First counted session unset | MET in the card, NOT protected in code | finding 1 |
| - | D6 change: old rows unaffected, malformed refused | MET | `journal/versions.csv` is header-only; 3 books render byte-identically; `cs1@1`, `@0`, `CS1@1x`, prefix-only refused; CLI registers `school:CS1@1` and refuses `school:cs1@1` (my run, then reverted) |
| - | Gates | MET | pytest -n auto 10295 passed, 16 xfailed; ruff check/format, check_imports, check_records, check_numbers clean; largest new file 76 lines |

## Findings
1. **Blocking: `school.first_counted` can be set or moved after the decisions.** `CountingRule` reads the date from
   settings at evaluation time and asks nothing of git (`counting.py:58-61`). My run: a 2 Nov decision is
   `before_first_counted_session` with 30 Nov, and `counted=True` once the date is moved back to 2 Nov after the fact.
   The card's §5 promises "in a commit made before that session's decisions"; nothing enforces it. Moving the date
   (back to add good days, forward to drop bad ones) is the cherry-pick the frozen card exists to stop. Expected: the
   commit that set the current `first_counted` value is a strict ancestor of the decision's commit (D6-style pickaxe
   on config.yaml), and a change after counting began is visible (a named reason), with real-git tests for both.
2. **Should-fix: any later card edit un-counts every earlier decision, contrary to the card's own versioning text.**
   `last_commit(CARD_PATH)` is the card's newest change at HEAD (`wiring.py:24`), and `CARD_PATH` is fixed. The card
   says a changed cost model, road, slot or denominator "is a new card version, never an edit", and
   `test_card.py` forces that card edit when `charges:` changes (a SEBI or STT change, as in Apr 2026). Then all
   v1 decisions stop counting. Expected: either the decision names the comparison card's SHA-256 (or version) and the
   rule checks that version's own freeze commit, or the card and story say plainly that any change voids all earlier
   counting, with the orchestrator's decision.
3. **Should-fix: the card is wrong or incomplete in places, and it can't be fixed after the freeze without
   finding 2's effect.**
   - "98 counted trials": EDGE1 is trials 71-98, 24 tradeable variants (`research/edge1/RESULTS.md` line 6).
   - "found no simple option rule beating costs" overstates RESULTS ("does not prove that no edge exists").
   - The story names "the denominator and bands of 3.5", but the card freezes no band (strikes of the money, which
     card's `band_steps` sets a road's gate) and no "impossible" bound (EDGE1's bounds are not cited).
   - PS5's and KL1's roads (BANKNIFTY-M, NIFTY-M) are not named.
4. **Should-fix: DRY.** `GitCardHistory` is a second git subprocess adapter beside `fno/research_engine/ledger.Git`,
   which already has `is_ancestor` (with the empty-commit guard), `commits_touching` (its last entry is the last
   change) and `is_shallow`. The test's `RegistryHistory` re-implements `Git.first_commit_containing`. Expected: one
   thin adapter over `Git`, and `Git` itself in the test.

**Minor (fix with the round):**
- (a) `test_the_card_leaves_..._names_no_driver_sha_yet` checks no driver SHA.
- (b) `test_the_registered_sha_is_the_one_in_the_card_constant` tests only a fixture.
- (c) CLI `_book` is untested (both plants survived; `parse_versions` still refuses).
- (d) `clusters.py` and the card say the common group is "frozen once before counting", but nothing freezes it.

## Plants
15 planted, 12 caught. Survivors: `CARD_COMPONENT` renamed (the same constant is on both sides, so part e must use
it), and the two CLI `_book` plants (minor c).

## Notes
- The D6 rows and ledger row 99 are still open, as the Claims say. A PASS here won't cover them. They wait for part e,
  and the orchestrator goes next.
- `build_counting_rule` has no caller yet; it waits for the join-up.
- In a shallow clone the card check fails safe (it doesn't count). D6's pickaxe has its own shallow risk, which comes
  from D6 and isn't this diff's.

## Addendum 1

**Round 2 of 2:** story/ms-p1-card at ecd5f9da, diff ff6c813a..ecd5f9da. **Verdict: FAIL.** 1 should-fix, which the
fix itself introduced, and 3 minor. This was the last round, so the owner decides. (Claim row 480 now carries my
real session id, commit 983e3735.)

**Gates (my run):** pytest -n auto 10,319 passed, 1 skipped (b's band pin), 16 xfailed. ruff, check_imports and
check_records are clean. Largest file is 152 lines.

**Round-1 findings:**
1. **First counted session: ACCEPTED.** The value is read from `config.yaml` at the decision's own commit, and the
   commit that wrote it must be a strict ancestor (`counting.py:74-79`). Real-git tests cover a date moved back, moved
   later, set after the decision, and set in the decision's own commit. My plants caught: the strictness check, the
   tree read at HEAD, the date check.
2. **Card versions: ACCEPTED.** Each decision counts under the last card commit strictly before it, and a later edit
   leaves it counted. Plants caught: first instead of last version, no ancestry filter.
3. **Card text: ACCEPTED.** 24 variants and trials 71-98, the RESULTS wording, the band and the impossible-price rule
   (b's single source, pin test skips until b lands), and PS5's and KL1's roads are all on the page.
4. **DRY: ACCEPTED.** One adapter over `ledger.Git`, and the tests use `Git`.
- **Minors (a)-(d): ACCEPTED.** Tests replaced, the component name pinned, the CLI tested, the "frozen once" wording
  gone.

**New findings:**
1. **Should-fix: a charges change without a new card version is no longer caught.**
   - Round 1's HEAD test is removed. The remaining test checks the cost block only at the card's own last commit
     (`test_card.py:28-36`).
   - The card says "A changed charge schedule is a new card version" (§3), but if someone changes `charges:` in
     `config.yaml` and leaves the card alone, CI stays green. Later decisions then count under a card whose frozen
     cost hash no longer matches the costs they were priced with.
   - Since versions are now forward only, putting back a HEAD check costs nothing: a charges change then forces a
     new card version, which never touches earlier decisions.
   - Expected: a test (or the rule) that fails when the `charges:` block at HEAD (or at the decision's commit) differs
     from the hash frozen in the card version in force.

**Minor:**
- (a) **The pickaxe needs one exact spelling.** `first_commit_containing("first_counted: <date>")` misses a value
  aligned with spaces. In my temp repo, `first_counted:   2026-11-30` gives `set_in=None`, so nothing ever counts,
  silently. Today's line is column-aligned (`first_counted:            # ...`). Normalise the spacing, or find the
  commit through the parsed value; and test it.
- (b) **The impossible-price check covers only band legs.** The card's band paragraph (the orchestrator's ruling) is
  honest that the band measures capture completeness only, and it labels its width "reasoning only". It doesn't say
  that `impossible_keys` also runs only on band legs, and law 5 checks two-sidedness and size, not impossible prices.
  So a traded leg outside the band (shorts about 20 steps out) is never checked for an impossible price. Say so on
  the card.
- (c) The `isinstance(value, date)` guard is untested: a quoted date would reach `.isoformat()` on a string (plant
  survived).

**Plants:** 7 on the new code, 6 caught, 1 survived (minor c).

## Addendum 2

**Third check (owner's decision, DESK_DECISIONS 4149eaa5; only Addendum 1's findings and the known-limits text):**
story/ms-p1-card at 78f9b5e7, diff ecd5f9da..78f9b5e7. **Verdict: PASS.** Lane 1. This check ends h.

**Gates (my run):** pytest -n auto: 10,331 passed, 2 skipped (b's band pin, d's law pin), 16 xfailed. ruff, check_imports
and check_records are clean. `registration/wiring.py` is 94 lines.

**Findings:**
- **Should-fix 1, the charges test at HEAD: ACCEPTED.**
  `test_the_charges_block_in_force_matches_the_cost_hash_frozen_in_the_current_card_version`. My plant (brokerage 20.0
  changed to 21.0 in `config.yaml`, card left alone) fails it. Versions still apply forward only, so it forces a new
  card and never un-counts a decision.
- **Minor (a), spelling: ACCEPTED.**
  - The commit is now found from the parsed value at each touching commit (the start of the value's latest run), not by
    pickaxe.
  - Tests cover bare, aligned, commented, double-quoted and single-quoted lines, and a value set, changed and set
    back.
  - A value that can't be read or traced, or a shallow clone, raises `FirstCountedError` by name instead of counting
    nothing silently.
  - Plants caught: run reset removed, ancestry filter removed, shallow check removed, not-found raise removed, the ISO
    text parse removed.
- **Minor (b), the impossible-price scope: ACCEPTED.**
  - The card says b's rule runs on band legs only. It names d's `ImpossiblePriceLaw` for traded legs.
  - I read that law on story/ms-p1-fills (b9900351, `fno/school/safety/quote_laws.py:53`). It is the position strictly
    inside its payoff bounds at the touch, plus a per-vertical range check, refusing `impossible_leg_price`, as the card
    states.
  - The pin test skips until d lands. j should check it runs.
- **Minor (c), a quoted date: ACCEPTED.** A quoted date counts like a bare one, and a non-date raises (tests).
- **Known-limits text (§6): ACCEPTED.**
  - The expiry-day ELM gap is labelled reasoning only.
  - `margin_room` is in a's `ACCOUNT_LIMITS`, so blocked entries do become `account_limit` tickets, as stated.
  - The P2 fix and P0 probe 4 are named.

**Plants:** 6, all caught.
