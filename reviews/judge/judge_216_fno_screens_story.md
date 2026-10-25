# Judge 216: F&O screens story text, P2 pages and W3 screens (story/fno-screens at adf3a2cc)

**Verdict: FAIL, 2 should-fix.** The design is sound:
- one `BlockBuilder` per screen in the existing 07:10 `market-publish` run, so no new publisher, job or schedule;
- private inputs stay in memory through E2c's `PrivateFiles`;
- logs carry counts and hashes only;
- empty and "not published" states are shown honestly;
- "Paper" goes on every money figure.

One should-fix is about a privacy claim the owner relies on, and it must be stated plainly. The other is a wrong
record count. I checked against main and the real files on 16 Oct (IST); the repository's visibility comes from
GitHub's API.

## The orchestrator's five checks

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Privacy | PARTLY | `ContractBroken` claim verified (below). Rules 1-6 are right for the private inputs. But the weather "never sent" rule protects values that are already public: should-fix 1 |
| 2 | No new publisher, job or schedule | MET | One `BlockBuilder` per screen in `build_market_blocks()`, riding the 07:10 run; Known limit: the screens show the previous session |
| 3 | Per-screen counts against the real files | PARTLY | Weather 2,409 days (2017-01-03 to 2026-10-14), GREEN 1,634, AMBER 149, RED 121, not scored 505, all `backfill_exploratory`: exact. Card: 1 delivery, `2026-10-15-a1.json`, `reason_code: no_approved_strategy`, a `_test` Drive file: exact. Live v2 and AI v1: 2 days each: exact. Ledger 54 rows, registry 0: exact. 3 books with 2 daily-totals rows each: exact. AI usage 1 row, costs 1, no budget signal: exact. No scoreboards; no `health_runs.csv`: exact. **Manifests wrong:** should-fix 2 |
| 4 | Empty states labelled honestly | MET | weather "0 live / back-fill, exploratory"; books 0 open trades; scoreboards "not run yet"; screens "not published" until their page lands |
| 5 | Paper and design rules | MET as text | rule 6 (Paper, Example, empty never shown as zero); mockups with positive, negative and empty cases at 1280 and 390 |

**`ContractBroken` verified.** `fno/market_read_models/contract.py:71` builds each line as
`f"{path}: {e.message}"`, and jsonschema's `message` quotes the failing instance (for example "25000 is greater than
the maximum of 10000"). The exception text reaches the Actions log. Changing it to path plus rule (validator name)
before the first private page is right, and criterion 3 tests it.

## Should-fix

1. **The weather's thresholds and `reaches` colours are already public, so "never shown" hides nothing.**
   - **The repository is public:** `GET /repos/exepex/trading` returns `"visibility": "public"`.
   - **The input thresholds are in public code:** `fno/weather/checklist_v0.py:22`,
     `RED_LIMITS = (1.30, 0.20, 0.020, 0.25)` for `vix_ratio, vix_change5, move5, rv10`. The model's colour floors are
     at `fno/weather/constants.py:23`.
   - **Every committed weather record carries each input's `reaches` colour next to its value.** That is 2,409 files
     under `research/forecasts/v4/weather/`; for example `2026/2026-10-14.json`: `move5 0.0164 → AMBER`,
     `vix_ratio 1.114 → AMBER`, `rv10 → GREEN`.
   - **What follows:** the story's reason for rule 4 ("the per-input `reaches` colour over 2,409 days would let the
     levels be read back") describes something anyone can already do from the public repository, and the levels need
     no reading back: they are in the source.
   - **Fix:** the story must say this plainly. Keeping the screen free of thresholds is still fine as a display rule,
     but it gives no secrecy. Put one question to the owner, with the facts:
     - (a) accept the levels as public (they are a published rule, not a secret edge); or
     - (b) make them private from now on: move M1's per-input `reaches` and the limits out of the public tree, as was
       done for `us_move`.

     State the cost of (b): git history keeps every past value public forever, and that cannot be undone.
   - Until the owner answers, do not describe rule 4 as protecting the levels.
2. **Data-health counts are wrong.**
   - The table says "20 manifests (~21.7k rows)".
   - At adf3a2cc, `research/data/manifests/` holds **33 CSV files** (19 at the top level, 14 in `filings/`,
     `global-cues/` and `groww-candles/`) with **57,178 lines**. The 19 top-level files have 17,910 data rows on main.
   - Neither figure is 20 / 21.7k.
   - **Fix:** give the count with its definition (files, recursive or not; data rows without headers), so P2e's
     fixture test can check it.

## Notes (not should-fix)

- **A Drive outage freezes every page, not just the private ones.** `fno market publish` runs
  `download_private_records()` first and stops the whole command when Drive cannot be read. So all pages, including
  the public weather and data-health pages, stay at the previous publication. Rule 2 reads as if only the private page
  stays behind; write what happens.
- **Duplicate register rows.** `docs/WORK_REGISTER.md` rows 21 ("W3a-h") and 32 ("F&O screens in the dashboard")
  name the same builder (0134MoC6) for the same `web/` work. Same owner, so this is not a conflict, but merge them
  into one row.
- **Ownership check.** P2 (BR1 builder), W3 (E4c/E4d builder) and the contract and mockups (01XFXpbk) each have one
  owner, and the old P2 text is replaced, not duplicated. No second publisher, reader or adapter is planned.

## Addendum 1: heads a939fd23 and 1799b120 (weather_history page, contract 2.8.0, gateway entry points)

**Verdict: FAIL stands.** Should-fix 1 and 2 are not addressed yet; these commits predate the verdict. Should-fix 1
gains part (b), the orchestrator's question.

- **The gateway entry points (rule 5), accepted.** Naming every route the gateway serves under `MB_GATEWAY=1` and
  proving the import-graph test with a planted import is a real check. It is closer than "a test".
- **Contract 2.8.0, additions only, and `weather_history`'s shape:** fine as text.
- **The orchestrator's question: can the thresholds be read back from `weather_history`? Yes, the colour levels
  can.**
  - Each row carries the colour and the four figures it is computed from: p1, p5 and their base rates b1, b5.
  - `fno/weather/colour.py` makes the colour a pure function of those four: RED when
    `p1 >= max(10%, 2.5·b1)` or `p5 >= max(35%, 2.5·b5)`, AMBER at 6% / 20% and 1.5 times.
  - With about 2,400 labelled rows, the RED and AMBER floors and multiples fall out of where the colours change. The
    149 AMBER and 121 RED days bracket them.
  - The per-input checklist limits (`RED_LIMITS`) cannot be read back from this page, since it carries no input
    values.
  - So if the lead's reading of the owner's rule covers the colour levels (it turned down the `weather_method` page
    that would show them), the history page breaks that reading. It must either drop the base rates, or the
    probabilities, or say so.
- **Should-fix 1, now in two parts:**
  - (a) everything in question is already public in this public repository, which is addendum 0's point: the rule in
    `colour.py`'s docstring and constants, `RED_LIMITS`, and `reaches` in 2,409 committed files;
  - (b) the new history page would show the colour levels again by read-back.

  The owner should decide this once, with these facts: the levels are public (show them, or stop pretending they are
  hidden), or private from now on (move them out of the public tree, accept that history keeps them, and cut the
  history page down to colour and label).
- **Should-fix 2** (the manifest count): still open.

## Addendum 2: head 44132385 (response 219 addendum 1)

**Verdict: PASS.** Both should-fixes are fixed, and both notes are applied.

- **Should-fix 1(a).** Rule 4 now says plainly that the weather's input levels are a screen rule, not a secret. It
  cites `checklist_v0.py:22`, `constants.py:23` and the `reaches` in all 2,409 committed records, and it puts one
  owner question: (a) accept them as public, or (b) make them private from now on, with history staying public. The
  builder recommends (a), marked as reasoning only. That is honest and complete.
- **Should-fix 1(b), the history read-back: settled as written, with one note.**
  - The owner's rule (16 Oct) is about the input levels: "the level at which an input turns a colour".
    `weather_history` carries no input values, so it cannot show those.
  - What it does let a reader recover is the colour rule's floors and multiples (`colour.py`). Those are the model's
    owner-decided levels (design 2.3, "Weather thresholds accepted"), stated in public code, not input levels.
  - So under the owner's own wording, the page keeps the rule. The stricter reading the lead used to turn down
    `weather_method` would also catch this page.
  - **Note:** add one sentence to the owner question, "the history page lets the colour rule's floors and multiples
    be read back, as the public `colour.py` already states them", so the owner decides with every fact in front of
    them.
- **Should-fix 2.** The count is now 33 manifest CSVs, 57,178 lines, with the command that produced it in the table,
  and 17,910 data rows in the 19 top-level files. This matches my recount.
- **Notes.** Rule 2 now says a Drive stop halts the whole publish, public pages included. The duplicate W3a-h
  register row is removed, and the text row points to the screens builder's row.

## Addendum 3: head 5e938904

**Verdict: PASS stands, and addendum 2's note is closed.** Rule 4's owner question now covers the probability rule
too. Probability, base rate and colour together over about 2,400 days of `weather_history` let the floors and
multiples be read back:
- under (a), that is fine;
- under (b), the history page drops the probabilities or the colour, and today's page shows only one of them.

The drivers' `push` is defined without levels: it is the sign of the change since the previous session. Drivers are
ordered by the size of that change against their own 250-session typical change, never by a model coefficient (which
is on the never-sent list). No input level or `reaches` can be derived from either.
