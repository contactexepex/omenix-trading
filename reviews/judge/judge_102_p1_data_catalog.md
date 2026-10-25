# Judge 102: P1, the F&O data catalog: dashboard `story/p1-data-catalog` 3cf4baa7a8bf84df454a6dc4274e5021957d4958 and trading `story/p1-data-catalog` c083b4b36487465bf357868f7b71e96aacf11e65 (lane 1 in both, response 102)

Judge B.

**What I did:**
- **Read:**
  - the story text first (quality rule 1);
  - the claims file;
  - all six `fno-*.yaml` schemas and the paths file in full;
  - the 17 examples, the dashboard check tools, the trading test and pin, and the REPLAN row.
- **Checked against:**
  - design v2 4.1, 4.4, 2.3, 3.1-3.2, 5, 6.2 and 8.3;
  - the owner's rows: contract A, P1 into slice A, the five screens, "4 A", cards in Drive, privacy, and the 14 Oct isolation conditions;
  - the built S2 code.
- **Pin:** hashed every pinned file against the dashboard at 3cf4baa.
- **Planted mutations:** 9 in the dashboard schemas and 3 in trading.
- **Mockups:** rebuilt 39 and 40 and looked at two screenshots.
- **Gates:** ran both repositories' gates, plus a trial merge of trading with `main`.

## Gates

| Where | Result |
|---|---|
| Trading at c083b4b (Slack token unset) | 3,187 passed; `ruff check`, `ruff format --check` (706 files) and `check_imports` clean |
| Trading, trial merge with `origin/main` | clean merge; 3,187 passed; same checks clean |
| Dashboard at 3cf4baa | `check_code_size` passes. `npm ci`, typecheck clean, `npm test` 465/465, `npm run build` compiles. `check_mapping`, `check_contract` (with openapi-spec-validator installed: "OpenAPI 3.1 valid ... every planted break caught"), `render_catalog --check`, `examples --check`, `check_fno_screens` (231 leaves, 25 built, 21/21 planted) and `render_fno_catalog --check` all exit 0 |
| Dashboard `main` | Has not moved since the branch base 5a6a2a1. No existing check tool was changed; the diff adds four new files under `tools/api/` and two CI steps |

## Checks the orchestrator asked for

| # | Question | Result |
|---|---|---|
| 1 | Live strikes, entry ranges or internals? | Keys are clean: the internal-word scan passes and my free-text scan finds no thresholds or model names. Live fields carry `x-visibility: owner`, but changing the card's `trade` or `objections` to public is caught only because the generated table goes stale; regenerating the table passes (should-fix 3). The mock TRADE card uses a real upcoming contract (NIFTY 29 Dec 2026, 22,600/22,450 PE, Rs 52-58); see minor 1 |
| 2 | Pin byte-equal; what moves it | All 33 pinned files have SHA-256 equal to the dashboard at 3cf4baa and to `pin.json`. 3cf4baa is a branch commit, so the merge order must be fixed (condition C1) |
| 3 | The 25 fillable fields | Every `x-record` exists here. The type test catches my retype of `TradeLine.gross` to `str` and my rename of `CheckReport.ok`; a byte change in a pinned schema fails 4 tests. One mapping needs a value translation: `family` (rule, hybrid, ai) comes from `paper_account:book` (book1_rules ...); minor 2 |
| 4 | v4 fields provisional | PARTLY: see should-fix 1 |
| 5 | W10/W11 checks unchanged and passing | MET. No existing check file changed, and all of them pass. The new tag keeps the F&O screens out of the `blocks` rules by design, with its own checks |
| 6 | Mockups 39 and 40 | MET. Rebuilt twice, with no byte change (`git status` clean); `data.json` comes from the catalog. 24 screenshots: card 5 states and weather 3, each at 1280 full, 390 full and 390 viewport. Rendering nits: minor 3 |
| 7 | Card rules traceable? | MET, all traced. "Only rung 3": 4.1 ("A TRADE card is only ever for a version approved to paper (rung 3); anything earlier is WATCH"). RED: 4.1 reason codes, 6.2 and the owner's 14 Oct principles. Failed data check and hard-rule breach: 4.1. Intraday AMBER to RED only: 2.3. Missing weather blocks: owner "4 A". Nothing invented |

## Must-fix

**1. The Forecast lab has no isolation label and no per-forecast counted status (an owner condition and judge 58's precondition).**
- The owner's 14 Oct acceptance of `sealed_same_day` set condition (2): the label "sealed same day (not full F1)" stays
  on every record and report.
- Judge 58 required G4 reports to honour `model_mismatch`, exposed and breach days, and to show coverage and the
  isolation label.
- The Forecast lab shows the AI books' forecasts but has no field for any of these. `grep -i "sealed\|isolation"`
  finds nothing in the schemas or examples.
- The branch's own fixture builds "today's forecasts" from the 14 Oct live records. Those were generated at 19:27 IST,
  after protocol v2's 15:15 lock, so none counts (the claims file says so itself), yet the lab shows them unflagged.
- Fix:
  - an isolation label per AI forecaster;
  - a per-forecast status, at least: counted, late (not counted), breach (unscored), model mismatch;
  - per-forecaster coverage (made, missing, late).

**2. The card has no daily stress line (design 6.2: "Every card shows, for all open positions, the loss under fixed scenarios").**
- The scenarios are NIFTY −5% and −10% overnight with VIX +50% and +100%, and +5%.
- No card field holds them, and the gap list does not mention it. `worst_cases` is per trade and historical, which is
  a different thing.
- Fix: add the stress block (scenario, total loss across open positions, sum of maximum losses as the ceiling), or
  list it as out of scope with a reason and an owner story.

**3. Gap list (quality rule 2).** The gap list is drawn from the orchestrator's brief, not from the design sections the
story cites. Besides 1 and 2 above, these are in neither "covered" nor "out of scope":
- the weather's v0 checklist baseline (2.3: "any new weather model must beat it and the base rate"). Only the base
  rate is scored;
- coverage and missing-forecast counts (5; "a missing forecast is left out and counted": the schema has no place for
  the count).
Fix: add the gap list against 4.1, 4.4, 2.3, 3.1-3.2, 5, 6.2, 8.3 and the owner rows, with each item covered or out of
scope.

## Should-fix

1. **v4-dependent fields that are not marked provisional.**
   - `FnoForecastComparison.p_value` ("bootstrap p-value ... v4 one-sided"), `interval` ("95%, unadjusted"), `verdict`
     (no futility value) and `scores.n_needed` ("v4: twice the block length") describe v4 as it stood before G6
     revision 1.
   - G6 now uses the larger of a batch-means t-test and a studentized bootstrap, a 97.5% two-look futility bound and
     "futile" as an outcome (`PROTOCOL_v4.md` at dbba574, lines 182-239).
   - Only `min_effect_met`, `variance`, `settle` and the weather scores carry `x-provisional`.
   - Mark the v4 meaning of these shared fields provisional too, or split v3 and v4 comparison shapes.
2. **Fields that force a made-up value before their story exists.**
   - `closed[].fills` requires three E8 fills on every closed trade. Book 1's E4-only trades cannot be published
     without inventing them.
   - `open[].monitor` and `alerts_today` are required before LM1 exists: "alert_only" and 0 would claim a monitor that
     does not run.
   - Allow null, or a `not_measured` state, until E8 and LM1 exist (the story's own rule: "never faked").
3. **Visibility downgrade is not guarded.** My plants that made `FnoCardTrade` or `advocate.objections` public pass
   `check_fno_screens`. They fail only `render_fno_catalog --check`, which a regenerated table also passes. Pin the
   owner-only paths (card trade, legs, entry, exit plan, objections, open legs) in the check, with a planted break.
4. **Strategy lab `results[].costs` includes "its allocated AI and data costs" per strategy version.** The built S2
   (`fno/scoreboard/book_board.py:5`, judge 87) charges operating and AI costs at book level only, "so no rupee is
   counted twice". Per-version costs must be charges and pads only. Book-level AI and data costs belong on a book line.
5. **Unguarded rules.** My plants that survived every check:
   - card `max_loss` maximum raised from 10,000 to 50,000 (the owner's per-trade cap);
   - the "settle needs 60 outcomes" rule deleted.
   Add planted breaks for both.

## Conditions for the merge (not findings)

- **C1. Merge order.** Merge the dashboard first. Re-pin trading at the dashboard's merge commit (byte-equal files, new
  commit in `pin.json`), then merge trading. My merge check will verify that the pinned commit is on the dashboard's
  `main`.
- **C2. P2 conflict.** The builder's note (P2 commits pages under `reports/dashboard/`) is right and important: P2 must
  keep owner-visibility fields out of any public commit.

## Minor

1. **The mock TRADE and WATCH cards use real upcoming contracts.** They show `NIFTY26DEC22600PE` near today's spot with
   an entry range, labelled Mock and PAPER ONLY. Design 4.1's illustration does the same, but decision 9's reasoning
   ("publicly readable calls") favours an expired expiry or a clearly fictional level in public mocks.
2. **`family` needs a translation from `paper_account:book`.** It takes rule, hybrid or ai from book1_rules,
   book2_hybrid, book3_ai; name the mapping in the field table.
3. **Mockup 40, missing state.** It prints "None" in "The last sessions" (a Python null leaking to text), and shows
   "Within the limit" with no session counted. It does not say that new trades are blocked, though `blocks_new_entries`
   is true (owner "4 A").
4. **TRADE needs rung exactly 3.** A rung-4 version still trades on paper. Fine while `real_money_eligible` is
   `const false`; revisit with RM1.
5. **The claims file still says the trading push was refused.** c083b4b is on the remote; update the line.

## Per-criterion table

| Criterion | Builder's claim | My evidence | Result |
|---|---|---|---|
| 1 Five screens, schema, endpoint, three cases | 17 examples | Read every schema; the examples cover positive, negative and empty for each | MET |
| 2 Examples validate in both repositories, Mock, 2.7.0, page key, hash | tests and checks | `check_fno_screens` and the trading tests pass; my pinned-schema byte change fails 4 tests | MET |
| 3 Every leaf documented; built fields name real records with types | type test | Retyping and renaming are caught; but fields without a story force made-up values, and the v4 meanings are stale | PARTLY (should-fixes 1, 2) |
| 4 Paper, PAPER ONLY, no internal names, never-sent lists | checks | Keys and text clean; visibility downgrade unguarded; per-version AI cost wrong | PARTLY (should-fixes 3, 4) |
| 5 Mockups from the catalog only | build and check | Deterministic rebuild; data from the catalog; 24 screenshots | MET (minor 3) |
| 6 Planted breaks | 21/21 | Their 21 caught; 4 of my 9 schema plants survived every check, 2 of them real gaps (max_loss cap, settle rule); 2 more caught only by the stale table | PARTLY (should-fixes 3, 5) |
| 7 Gates | as listed | Reproduced in both repositories and on the trial merge | MET |
| Design coverage (quality rule 2) | gap list from the brief | Missing: isolation label and counted status, stress line, v0 weather baseline, coverage counts | **NOT MET** (must-fixes 1-3) |

## Claims vs reality

- **"All 33 files byte-identical".** True, by my hash check.
- **"21 of 21 planted breaks caught".** True. My own plants found the gaps above.
- **"v4-only fields carry x-provisional".** True for v4-only fields, but not for shared fields whose v4 meaning G6 has
  since changed.
- **"Design rules ... TRADE rung 3, never in RED".** Traced to the design; not invented.
- **"3187 passed".** Reproduced at c083b4b and on the trial merge.
- **Two independent reviews and their 20 findings.** Each "fixed" item I spot-checked is in the code:
  - visibility never downgraded through `$ref`;
  - the card rules;
  - the type test;
  - `page_key` asserted.

**Verdict: FAIL** for dashboard 3cf4baa7a8bf84df454a6dc4274e5021957d4958 and trading
c083b4b36487465bf357868f7b71e96aacf11e65:
- must-fix 1: the Forecast lab's isolation label and counted status (an owner condition);
- must-fix 2: the card's stress line (design 6.2);
- must-fix 3: the gap list against the design sections;
- should-fixes 1-5.

The contract's structure, the privacy design, the pin and the drift tests are sound, and the card rules trace to the
design.

## Addendum 1 (15 Oct 2026): T1's real card fields, dashboard d3f80938630da7381c47996da88252b342235085 and trading 8142710ef7a3d7b93e7474640a9bce5239db7422

The orchestrator sent this addendum before my FAIL message reached it, so it does not address must-fixes 1-3 or
should-fixes 1-5 above. They stay open. This addendum judges only the T1 card fields and the new test.

**Scope:**
- Dashboard 3cf4baa..d3f8093 is one commit: `fno-card.yaml`, `fno-screens-common.yaml`, the examples, mockup 39 and
  one line of `check_fno_screens.py`.
- Trading c083b4b..8142710 is one commit: re-pin, a fixture, a new test file and two lines in the P1 test.

| Item | Result | Evidence |
|---|---|---|
| Pin | MET | All 33 pinned files have SHA-256 equal to the dashboard at d3f8093 and to `pin.json` (my hash loop) |
| Fixture is T1's real record | MET | `cmp` of `tests/fixtures/cards/t1_delivery_2026-10-15.json` against `research/cards/deliveries/2026/2026-10-15-a1.json` at 9f540e9: byte-equal |
| New card fields public-safe | MET | All of them are counts, dates, plain-text gaps, repository paths with SHA-256, and the house forecast with back-fill and live records apart. None holds a strike, an entry range or a strategy internal. The Drive path in T1's record names a file by day and timestamp only. Live legs and entry ranges stay under `FnoCardTrade` (owner visibility) |
| `late_generated_at` and back-fill vs live | MET, and it narrows must-fix 1 for the card | The card now flags a late capture and keeps back-fill records apart from live ones, as T1's real post did (I read the post, read only). The Forecast lab still lacks the isolation label and per-forecast status (must-fix 1 stands) |
| Is the XFAIL a weakened test? | Not weakened; acceptable | It is a new test, and it is expected to fail only while `research/cards/deliveries/` holds no record. **It flips to a hard check by itself:** I copied T1's record into that folder and all 3 tests pass. A planted bad record (status TRADE with no trade) fails. `-rx` prints the reason in every run. **What enforces the flip:** the records arriving with T1's merge (T1's `CARD_DELIVERIES_FOLDER` is the same path). Follow-up below |
| Gates | MET | Trading at 8142710: 3,190 passed, 1 xfailed; ruff, format (707 files) and imports clean; `git merge-tree` with `origin/main` clean. Dashboard at d3f8093: `check_mapping`, `check_contract`, `render_catalog --check`, `check_fno_screens` (21/21), `render_fno_catalog --check`, `examples --check` and code size all exit 0; mockups 39 and 40 rebuild with no byte change |

**Follow-ups (not blocking; for T1's merge):**
1. When T1 merges, replace the test's hard-coded `research/cards/deliveries` with T1's `CARD_DELIVERIES_FOLDER` and
   drop the XFAIL branch: assert that at least one record exists. Otherwise, if T1 ever moves the folder, the test
   would expect-fail for ever unnoticed. The same goes for the copied 15:25 constant (`VALID_UNTIL_UTC`).
2. The test fills the card's text sections (forecast lines, weather) from the empty example, as the builder says. T1
   writing its Drive card record as JSON in FnoCard's shape would let the whole card be validated. This is a T1
   proposal, reasoning only.
3. `FnoRecordHash.kind` becomes `path` and `FnoCardForecast.record` becomes `backfill`/`live`, both breaking changes
   inside the unreleased 2.7.0. That is acceptable before the first merge; after it, such a change needs a version bump.

**Verdict for the addendum's own content: MET.** **P1 overall stays FAIL** until judge 102's must-fixes 1-3 (Forecast
lab isolation label and counted status, the card's stress line, the gap list against the design sections) and
should-fixes 1-5 are fixed and re-judged.

## Addendum 2 (15 Oct 2026): all judge 102 findings, dashboard 02664369f05a21c6642e2336b40a54fc7e2d29be and trading e4bade7ebaaec34caeadc2d4a7f2967eaf5d9476

**Scope:**
- Dashboard d3f8093..0266436: four commits (judge 102 fixes, the family mapping, the three-pair stress line, and
  Home's `limit_max`).
- Trading: the branch's own diff from its merge base with `main`, which is the re-pin, the tests, the story text,
  REPLAN and claims addenda 2-3.

### Gates

- **Trading at e4bade7:** 3,568 passed, **0 xfailed**; ruff, format (764 files) and imports clean.
- **Trading, trial merge with `origin/main` (6aa3a45):** clean; 3,569 passed; same checks clean.
- **Dashboard at 0266436:**
  - `npm ci`, typecheck clean, `npm test` 465/465, `npm run build` compiles;
  - `check_mapping`, `check_contract`, `render_catalog --check`, `check_fno_screens` (289 leaves, 56 built, 26/26
    planted), `render_fno_catalog --check`, `examples --check` and code size: all exit 0;
  - mockups 31, 39 and 40 rebuild with no byte change.
- **Pin:** all 33 files byte-equal to the dashboard at 0266436 and to `pin.json`.

### Judge 102 items

| Item | Result | Evidence |
|---|---|---|
| MF1 isolation label, status, coverage | **MET, one hole** | `isolation_label` is forced to "sealed same day (not full F1)" when `isolation` is `sealed_same_day`; my plant removing that rule is caught. Per-value status: counted, pending, late, breach or model_mismatch. Coverage counts per forecaster, plus `n_missing`. The 14 Oct fixture now asserts every value `late`. **Hole:** an AI book can be declared `isolation: code` with a null label and the page validates (my probe on `book2_hybrid`); see should-fix 1 |
| MF2 stress line | **MET** | The `stress` block is owner-only and pinned in `OWNER_PATHS`. Exactly three paired scenarios are enforced by `prefixItems` and `const`; my plant dropping the third pair's VIX const is caught. The examples are checked so that no line exceeds `max_loss_sum`. The pairing (−5/+50, −10/+100, +5/0) is the orchestrator's reading of design 6.2's list (response 113 #4) and is labelled so |
| MF3 gap list | **MET** | Rebuilt against 4.1, 4.4, 2.3, 5.2-5.8, 3.1-3.2, 6.2, 8.3 and the owner rows. Each item is covered, or out of scope with a reason: close-proxy label, full reliability table, stability, drift screen, cost-wall internals, effective sample |
| SF1 v4 fields | **MET** | `p_value`, `interval` (v3 only), `verdict` (+`futile`), `futility_upper_bound` and `n_needed` are rewritten to G6 revision 1 and marked `x-provisional`. Dropping a provisional mark is not caught (minor 1) |
| SF2 made-up values | **MET** | `closed[].fills`, `open[].monitor` and `alerts_today` are nullable before E8 and LM1, with an example of each |
| SF3 visibility | **MET** | `OWNER_PATHS`: my plant that makes the card's `trade` public now fails `check_fno_screens` itself |
| SF4 per-version AI cost | **MET** | `results[].costs` is charges and pads only; `books[].ai_and_data_costs` is book-level, null until S2 |
| SF5 surviving plants | **MET** | Nine schema probes. My `max_loss` 50,000 plant and the settle-rule plant are now caught |
| Minors 1-5 | **MET** | `MOCKNIFTY26DEC10600PE`-style contracts far from any real level; family mapping named; mockup 40 says "No colour" and "No new paper trade today: a missing weather blocks new trades"; push line fixed |
| T1 follow-up | **MET** | Imports `CARD_DELIVERIES_FOLDER` and `CARD_VALID_UNTIL` from `fno.constants`; reads T1's real record on `main`; asserts that at least one record exists; fixture copy removed |

**Home `limit_max` (Rs 1,50,000, owner "2 A").**
- The change is consistent with judge 105's should-fix 4, and the schema does not constrain the number.
- Until C5 merges, though, `main` publishes 30,000 while the contract text says 1,50,000.
- `docs/stories/P-publishing.md:413` (P10) still says "`limit_max` = C2's `max_stress_loss_rs`". That is judge C's
  item for C5.
- Merge this dashboard change no earlier than C5, or note the gap in the merge message.
- Mockup 31 is a signed-off screen, and its `changes.md` has no row for the new number (minor 2).

### Should-fix

1. **Tie the AI books to a non-code isolation.** Owner condition 2 (14 Oct) puts the label on every AI record.
   - Add a rule: `kind: family` with `family` hybrid or ai requires `isolation` to be `sealed_same_day` or `full_f1`.
     Then the label rule applies.
   - Add a probe that declares `book2_hybrid` as `code` with a null label.

### Minor

1. `x-provisional` marks are not guarded: my plant renaming the one on `p_value` passes. A check that every v4 field
   listed in the gap list keeps its mark would do.
2. Add a `changes.md` row to mockup 31 for `limit_max` 30,000 → 1,50,000 (owner "2 A").
3. **My mutations:** 5 dashboard plants, 4 caught (the 5th is minor 1), plus the isolation probe above.

**Verdict: FAIL** for dashboard 02664369f05a21c6642e2336b40a54fc7e2d29be and trading
e4bade7ebaaec34caeadc2d4a7f2967eaf5d9476, on should-fix 1 only. It is one schema rule and one probe. Everything else in
judge 102 and addendum 1 is met.

## Addendum 3 (15 Oct 2026): dashboard 1eef671072e21c59a54e548df535291ddf9b4825, trading 22ac79b27169d970071500227800e88eba61bedd

**Scope:**
- Dashboard 0266436..1eef671 is one commit: one schema rule, the provisional guard, two plants and a `changes.md` row.
  No web or TypeScript change, so the web gates of addendum 2 stand.
- Trading e4bade7..22ac79b is one commit: re-pin and claims.

**Gates:**
- Pin: all 33 files byte-equal to 1eef671.
- Dashboard: `check_fno_screens` passes, 28/28 planted, along with `check_contract`, `check_mapping`, both
  `render --check` runs, `examples --check` and code size.
- Trading: trial merge with today's `origin/main` is clean; **3,673 passed**; ruff, format (790 files) and imports clean.

| Item | Result | Evidence |
|---|---|---|
| Should-fix 1: an AI book declared `code` | **PARTLY** | The new rule fires when `kind` is family and `family` is hybrid or ai. My probe (`book2_hybrid`, `code`, label null) is now refused, and the plant deleting the rule is caught. **But setting `family: null` on the same AI book skips the rule:** `kind: family`, `family: null`, `isolation: code`, label null validates (my probe). Nothing forces `family` to be set when `kind` is family. Mislabelling `kind` as baseline does the same |
| Minor 1: provisional marks guarded | **MET** | `PROVISIONAL_PATHS` with `check_provisional`; removing `p_value`'s mark is a planted break and is caught |
| Minor 2: mockup 31 `changes.md` row | **MET** | The row records 30,000 → 1,50,000, owner "2 A", and "the dashboard merges only after C5" |

### Should-fix (narrower than before)

1. **Key the AI-book rule on the forecaster's id, not only on `kind` and `family`.**
   - Either require `isolation` to be `sealed_same_day` or `full_f1` when `id` is `book2_hybrid` or `book3_ai` (the AI
     books, `AI_BOOKS`); or require `family` to be non-null when `kind` is family, and `kind: family` for those ids.
   - Add my two probes: family null, and kind baseline.
   - It is one rule and two probes; owner condition 2 is otherwise enforced.

**Merge order (agreed):**
1. C5 first: judge 105 PASS, then the ChatGPT round under rule 9.
2. The dashboard.
3. Re-pin trading at the dashboard's merge commit.
4. Trading.

**Verdict: FAIL** for dashboard 1eef671072e21c59a54e548df535291ddf9b4825 and trading
22ac79b27169d970071500227800e88eba61bedd, on should-fix 1 only (the family-null and kind dodge). Everything else is met.

## Addendum 4 (15 Oct 2026): dashboard 13e76b4c25b789dbc6441d64287a75cee3e187a8, trading 5e91b0eee67b50a289b719029d513815002cfd88

**Scope:**
- Dashboard 1eef671..13e76b4 is one commit: four schema rules keyed by forecaster id, two probes and the plant. No web
  or TypeScript change.
- Trading 22ac79b..5e91b0e is one commit: re-pin and claims.

| Item | Result | Evidence |
|---|---|---|
| Addendum 3 should-fix: the AI-isolation dodge | **MET** | Rules by id: `book2_hybrid` must be family hybrid, `book3_ai` family ai, both `sealed_same_day` or `full_f1`; `book1_rules` must be family rule; and `kind: family` needs a non-null family. All my probes are refused: `code`; family null with `code`; kind baseline with family null and `code`; `book3_ai` relabelled as family rule with `code`; a sealed book with a wrong label. The valid example still validates. The 12 probes include both of mine. The plant that removes every id and family rule is caught (28/28) |
| Pin | **MET** | All 33 files byte-equal to 13e76b4 and to `pin.json` |
| Dashboard checks | **MET** | `check_fno_screens` (289 leaves, 56 built, 28/28 planted), `check_contract`, `check_mapping`, both `render --check` runs, `examples --check` and code size: all exit 0. The web gates of addendum 2 stand (no web or TypeScript change since 0266436) |
| Trading gates | **MET** | Trial merge with today's `origin/main` (F8/BG1 included): its only conflict is index rows in `reviews/claude/README.md` (keep both). The merged tree gives **3,852 passed**; ruff, format (820 files) and imports clean |

Note, not a finding: `book1_rules` may still carry a sealed label. That adds a label and dodges nothing.

**Verdict: PASS** for dashboard 13e76b4c25b789dbc6441d64287a75cee3e187a8 and trading
5e91b0eee67b50a289b719029d513815002cfd88.

**Merge order (agreed):**
1. C5 first (it waits for its ChatGPT round under rule 9), because Home's `limit_max` text assumes C5.
2. The dashboard at exactly 13e76b4.
3. Re-pin trading at the dashboard's merge commit: byte-equal files, the new commit in `pin.json`, the README index
   conflict resolved by keeping both.
4. Trading.
5. The quality rule 8 run: `check_fno_screens` on the dashboard's `main` and `tests/market_read_models` on trading's
   `main`.

My merge check verifies:
- that both merges equal their recomputed trees;
- that the pinned commit is an ancestor of the dashboard's `main`;
- that no file changed except the pin.

## Addendum 5 (15 Oct 2026): merge check, P1 merged as dashboard 3df9179 and trading b092c58

**Order.** C5 merged first, at a8379e6, which is an ancestor of b092c58. Then the dashboard, then trading re-pinned and
merged, as agreed.

| Check | Result | Evidence |
|---|---|---|
| Dashboard merge exact | MET | 3df9179's parents are 5a6a2a1 (`main`) and ff1ec22. `git merge-tree --write-tree` of the two equals 3df9179's tree (empty diff), and 3df9179 is on the dashboard's `main`. ff1ec22 is my passed 13e76b4 plus one commit, the Mock paper accounts at Rs 20 lakh after C5 (3 files), which judge A passed as judge 135 |
| Trading merge exact | MET | b092c58's parents are d95d89f (`main`) and f20dcff; the recomputed merge equals its tree. Since 5e91b0e the branch adds only e2e3d78 (merge of `main`, with C5, and re-pin at ff1ec22; judge 135) and f20dcff (the pin's commit field set to 3df9179, one line) |
| Pin at the dashboard merge | MET | All 33 pinned files in b092c58 have SHA-256 equal to the dashboard at 3df9179 and to `pin.json`; `pin.json` names 3df9179, which is on the dashboard's `main` |
| Rule 8 | MET | The orchestrator's log records `python -m fno market contract-check`: "pinned W11 contract 2.7.0 (commit 3df91797c830): same as the dashboard's". I re-ran it myself: `check_fno_screens` on today's dashboard `main` holds every rule, 28/28 planted, and `check_contract` passes; `tests/market_read_models` on trading `main` gives 181 passed |

**Follow-up, not a P1 defect: the pin now drifts by design.**
- The dashboard has since merged story/p1-home-books-20lakh (b9c41ec, judge 136).
- That changes `api/examples/blocks.json` and `api/schemas/blocks-home.yaml`: the books' description and examples move
  to Rs 20 lakh, and the description text alone changes in the schema.
- So trading's pinned copy at 3df9179 differs from the dashboard's `main` in those two files, and `contract-check` will
  now report the difference.
- No validation rule changed, so published pages still validate.
- The re-pin to b9c41ec is a lane-1 change for trading.

**Verdict: merge check PASS.** P1 is done in both repositories.
