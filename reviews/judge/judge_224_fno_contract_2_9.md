# Judge 224: dashboard contract 2.9.0 (story/fno-contract-2-9 at be3629c)

**Verdict: PASS on the content, merge after one step.** be3629c does **not** contain main 1972241
(`git merge-base --is-ancestor` fails). The screens lead must merge main in first. The merged head needs
`check_contract` and `check_fno_screens` again, plus a look at the `examples` file, the one big file both sides
touch. On be3629c itself, `check_contract` and `check_fno_screens` exit 0 ("10 pages, 32 Mock examples").

## Against the owner's decision (trading `docs/DESK_DECISIONS.md`, 16 Oct, ad562ca1)

- **"Weather levels stay public":** `weather_history` gets `p_big_1d`, `p_big_5d`, `base_rate_1d` and
  `base_rate_5d` back, required. The 2.8.0 strict-form `x-never-sent` line is removed, and the input values and
  `reaches` stay never sent. This matches the decision exactly ("Screens still never send the levels themselves, but
  `weather_history` may carry each session's chances beside its colour in contract 2.9"). Judge 217 should-fix 1 was
  a rule pending the owner, and the owner has now answered it.
- **"Field A only":** `FnoForecastHistory` carries each forecaster's running `mean_loss` and `n` per G4 report. Its
  `x-never-sent` keeps "single forecasts and their outcomes (field B)" out, as the owner decided.

## `forecast_history` against G4's real reports (my read of `research/forecasts/scores/2026-10-16.json`)

- **The modes:** the report holds `close_proxy` (2024-01-01 to 2026-10-12, the back-fill) and `live_1500_proxy`
  (2026-10-15), each with 20 forecaster-and-question summaries. The contract's `label` maps `live_1500_proxy` to
  live and `close_proxy` to `backfill_exploratory`, and the series are "never joined". That is right.
- **The fields:** each summary has `counts.resolved` (671 for baseline A's back-fill) and `primary.mean_brier`
  (0.2476) with `primary.scored` (671). These are the contract's `n` (x-record `score_summary:scored`) and
  `mean_loss`. They exist under those names.
- **One point per report (`as_of`), not per session:** right, since G4 writes one report per day (13, 15 and 16 Oct
  exist; 14 Oct has none, so it has no point).
- **`primary_baseline` dropped,** with the yardstick taken from the Forecast lab page: one copy, which is right.
- **The text says that `n` counts answers as they resolve** (up to the horizon), so a period average is over answers
  that came in during it, mostly forecasts made earlier. That is honest.

## `MOCKUPS_ALSO`

The check now also compares a mockup's `data.json` `also` block with the catalog's examples for each listed
operation. **I planted a mismatch myself** (emptied one `getFnoForecastHistory` state in 37's `also`):
`check_fno_screens` reported "37-forecasts/data.json: its data differs from the catalog's getFnoForecastHistory
examples" and exited 1. The rule works. The orchestrator described a committed planted "also" break, but I found none
in the checks (only my manual plant). Add it to the planted-breaks list so it stays caught.

## Notes (not should-fix)

- **The period-average formula** `(n2·m2 − n1·m1)/(n2 − n1)` holds only if a later report's scored set contains the
  earlier one unchanged. That is G4's design (resolved answers are never re-scored). If the back-fill is ever rebuilt
  (a new `backfill_commit`), the two reports straddle different data. The screen should not difference across a
  change of `inputs.backfill_sha256`. The contract could carry a per-point input hash, or say so.
- **`mean_loss` for v4 (QLIKE):** "G8 adds it; the record named holds only Brier today". It is honest that the v4
  series will be empty until G8 publishes it.

## Addendum 1: head 709cb8c (main 1972241 merged in)

**PASS.**

- 709cb8c contains 1972241 (`--is-ancestor` passes). `api/` and `tools/` are unchanged from be3629c, so the content
  judged above stands.
- **Gates:**
  - `check_contract` and `check_fno_screens` exit 0;
  - re-running `sync-design` leaves the tree clean, so the fixture is exact;
  - `npm test` gives 499 passed, 0 failed, 0 skipped. W3a part 2 still passes on the 2.9 fixture: it reads only the
    2.8 fields.
- **Still a note, not a block:** the planted "also" mismatch is a manual check (yours and mine), not a committed
  planted break. Add it to the checks' planted list when next touching `check_fno_screens.py`.

## Addendum 2: head cf9692e (judge 224's points done)

**PASS.**

- **The planted "also" break is committed.** `planted_also` copies each `MOCKUPS_ALSO` mockup's data into a scratch
  folder, empties one example of each further operation, runs `check_mockups` and requires the mismatch to be
  reported. `check_fno_screens` exits 0 with it in place.
- **Back-fill rebuilds are handled.** Each series requires `backfill_sha256`, enforced by `if`/`then`/`else` on its
  label: a string for `backfill_exploratory` (G4's `inputs.backfill_sha256`, which exists in the real report), null for
  live. The text says a rebuilt back-fill starts a new series and the period difference is taken only within one. Two
  new probes (a rebuilt series without the hash, a live one with it) are refused.
- **The check change is accepted.** The closed-object rule now also skips `/then` and `/else`, as it already skipped
  `/if`. Those nodes only add conditions to their parent object, which is still checked closed (opening the series
  item is still reported, as the lead showed).
- **Gates:** `check_contract` ("every planted break caught") and `check_fno_screens` exit 0 on cf9692e.

## Addendum 3: head 07c8683 (`accounts[].open_risk_cap` added)

**PASS.**

- **The new field:** `FnoPaperTrades.accounts[].open_risk_cap` is a required INR (Paper) field, from C5's
  `risk.profiles.books.open_risk_cap_rs`. Trading's `config.yaml:55` reads `open_risk_cap_rs: 150000`.
  `open_max_loss`'s description now says "against open_risk_cap" instead of naming Rs 1.5 lakh in the text.
- **Not a strategy rule:** it is a book limit, like `brake.pause_at`, which judge 217 accepted. It reveals no
  strategy's rules.
- **It removes a copied owner number:** mockup 41's `2-books.js` drew `cap = 150000` hard-coded and now reads
  `a.open_risk_cap`. It also unblocks W3c's cap bar (judge 225's accepted deviation): the screen can now draw it from
  the payload.
- **Gates:** `check_contract` and `check_fno_screens` exit 0 on 07c8683. The examples, catalog and fixture all carry
  the field.
- **Note:** P2c must fill this field from config through the existing risk settings reader, not a typed 150000, when
  it builds the `paper_trades` page.

## Addendum 4: contract 2.10.0 at 7ccdff8 (story/fno-contract-2-10, on main e74c939)

**PASS.**

- **Shape:** 7ccdff8 contains main e74c939. It is cf9692e (addendum 2) plus 07c8683 (addendum 3), merged at 6b44e5c
  (no conflict changes: `git diff 07c8683 6b44e5c` adds only main's side), then one commit that bumps the version.
- **The bump is mechanical:** `git diff 6b44e5c 7ccdff8` changes only version strings (32 `schema_version` values in
  the examples, "2.9.0" to "2.10.0" in the mockup labels, build.py notes, catalog and schema descriptions). It adds
  a 2.10 note in `openapi.yaml` and `api/README.md`, and regenerates the mockup screenshots and the web fixture.
  - Screenshots: 25 PNGs of mockups 42-46 change by about 300 bytes each, which is the drawn "contract 2.10.0" label.
    Mockup 41's screenshots are unchanged, as the lead said.
- **Minor bump is consistent with 2.9:** the two new fields are required, so 2.9 `forecast_history` and `paper_trades`
  payloads are rejected. That is the same treatment 2.9 gave `weather_history`, and is acceptable while no F&O
  screen page is published.
- **Planted breaks I added (each rejected by `check_fno_screens`, exit 1; `check_contract` exits 0, as expected for an
  F&O-only rule):**
  - removing `open_risk_cap` from the paper-trades example: "'open_risk_cap' is a required property";
  - `backfill_sha256` null on a `backfill_exploratory` series: "None is not of type 'string'";
  - `schema_version` 2.9.0: "schema_version 2.9.0 is not 2.10.0";
  - removing `backfill_sha256` from every series: rejected, but with a crash (see the note below).
- **Gates on 7ccdff8:** these all exit 0: `check_contract`, `check_fno_screens`, `examples`, `render_catalog`,
  `render_fno_catalog`, `check_semantics`, `check_stored`, `check_chain`, `check_calendar` and `check_mapping`.
  `sync-design` leaves the tree clean, `tsc` passes, `npm test` gives 499/499 (0 skipped), and `next build` exits 0.
- **No copied cap:** mockup 41 reads `a.open_risk_cap` (`2-books.js:13`). No 150000 is found in `web/` on 7ccdff8 or
  `story/w3c-paper-books` outside unrelated tests.
- **Note (not blocking):** when an example lacks `backfill_sha256` completely, the `fno_rules.py:67` probe raises a
  KeyError before the schema problem is printed. The check still fails, and examples are generated, so normal running
  never reaches this.
- **Merge order:** W3c and W3d were built on 2.9.0. Whichever merges after 2.10 must take main and re-run `npm test`
  against the 2.10 fixture.
- **Later (orchestrator, 16 Oct 06:37 UTC):** cf9692e and 07c8683 were already on dashboard main ea75be3 (merged as
  7731d0e) before this check, so 7ccdff8 would only bump version strings. It is not merged, and the contract stays
  2.9.0. My earlier reading, that main stopped at 709cb8c, came from main e74c939 and was out of date by then.

## Addendum 5: story/fno-probe-report at e7bc792 (addendum 4's note fixed)

**PASS.** 7ccdff8 (2.10) is withdrawn by the screens lead as redundant, and addendum 4 stays on record only.

- **Shape:** e7bc792 contains main ea75be3. Its one commit changes only `tools/api/fno_rules.py` (+5 -1; the file now
  has 118 lines).
- **The fix:** `check_probes` catches `KeyError`, `IndexError` and `StopIteration` from a probe's change and reports
  "probe on <example> cannot plant <what>: its example lacks the part it changes". It does not crash, and it still
  fails closed: the problem is appended and the exit is 1. Putting the guard in `check_probes` covers every probe,
  instead of one. These are the error types a probe's change raises when the example has lost a part, so the guard
  hides no other bug.
- **Shown:** I removed `backfill_sha256` from every series of `getFnoForecastHistory_india_ahead`. The check exits 1
  with nine "'backfill_sha256' is a required property" problems, the probe line `KeyError('backfill_sha256')`, and
  the mockup mismatch. It gives no traceback.
- **Gates on e7bc792:** `check_contract` and `check_fno_screens` exit 0, and code size is OK.
- **Correction (06:46 UTC):** the "not merged" line above is out of date. Dashboard main 38dfee6 merged 7ccdff8
  after all, so the contract is 2.10.0 (version label only, as addendum 4 found).
- **Re-head 025aa59:** story/fno-probe-report now merges main 38dfee6. Its diff against main is identical to
  addendum 5's diff of e7bc792 against ea75be3 (`fno_rules.py` +5 -1). `check_contract` and `check_fno_screens` exit 0.
  The PASS stands.
- **W3c a2efbb3 against main 38dfee6:** a trial merge is clean, both checks exit 0 and `npm test` gives 520/520.
  W3c's PASS (judge 225 addendum 1) holds on the 2.10.0 main.
