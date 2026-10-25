# Judge 35: W11 re-judged (round 3), and W9 re-checked on the same main

**Verdicts:**
- **W11: PASS.** Judge 32's should-fix is ACCEPTED: Home's documented events query reproduces the signed-off Home,
  and a DOM assertion guards it.
- **W9: PASS on this main.** Home's "Coming up" matches the signed-off picture again, so judge 31's FAIL-on-main is
  lifted. The "Claude" fix stands (judge 31). Judge 29's three minors are fixed.

**What I judged:** `exepex/omenix-dashboard` main at ed21a5a, which contains W11 round 3 (58c3e74 via e1ca308) and the
W9 minors. The answer is `reviews/claude/response_12_w11_screener_markets_api.md`. CI run 38386030184 on ed21a5a is
reported green by the orchestrator; not seen by me.

## Checks run by the judge

```
$ python3 tools/api/check_contract.py     (openapi-spec-validator 0.7.2)
  contract: 64 paths (37 block endpoints), 72 block examples, 113 block schemas, 753 catalogued leaf fields, 32 planted breaks
  contract: OpenAPI 3.1 valid; examples valid and current; catalog complete; screen rules hold; every planted break caught
$ python3 tools/api/check_mapping.py      mapping: zero gaps both ways
$ python3 tools/api/examples.py --check   examples current
$ cd web && npm ci --ignore-scripts && npm run typecheck && npm test      tsc clean; # tests 371 # pass 371 # fail 0
$ node tools/sync-design.mjs --check      design copies current
$ npm run build && node tests/ui/harness.mjs      148 cases, 0 failed
```

### Home's events

| Example | Rows | Equal to the signed-off rows (1c026c4)? |
|---|---|---|
| `getEvents_india` (Home; `market_first`, Home's tracked tickers, limit 6) | RBI 7, Reliance 16, HDFC Bank 17, NSE closed 20, F&O expiry 27, FOMC 29 | **yes** |
| `getEvents_us` | JPM 13, CPI 14, FOMC 28, Apple 29, jobs report 6 Nov, Nvidia 17 Nov | **yes** |
| `getEvents_india_home20` (the stock tool's 20 companies, from 13 Oct) | HDFC Life 15, Reliance 16, HDFC Bank 17, **NSE closed 20, F&O expiry 27, FOMC 29** | market-wide events kept |
| `getEvents_us_home20` | JPM 13, **CPI 14**, BofA 14, Progressive 14, **FOMC 28, jobs report 6 Nov** | market-wide events kept |

**My plant** is different from the builder's (theirs drops `market_first`). I dropped Home's `tickers` filter in
`examples_screens.py`, so every calendar company was eligible, and regenerated the examples. `check_contract.py`
reports "getEvents_india: Home's view is not the signed-off Coming up of 31-dashboard", and the same for the US.
Reverted; tree clean.

**The DOM assertion** (`comingUpProblems`) reads the signed-off rows straight from
`design/mockups/31-dashboard/data.json`, not from the fixture, and compares day and title in order. It runs in the
India and US Home cases, which pass in my full run.

## Judge 32's should-fix: decision

| Finding | Fix | Judge's evidence | Decision |
|---|---|---|---|
| Home's query dropped the signed-off market events on a real calendar | `order=market_first` with Home's tracked `tickers`; `check_home_events` covers both the signed-off rows and the real calendar; DOM assertion against the mockup's data | Table and plant above; harness 148/0 | ACCEPTED |

The builder's rule takes each company's *next* result (one row per company), slightly different from my proposal (the
nearest results). On both data worlds it gives the signed-off rows, and it is more sensible: it never shows two
results of one company. Accepted.

## W11 criteria (story as written)

All 6 are MET. Criterion 6 is now MET in substance as well: Home's signed-off output is unchanged, and an assertion
proves it.

## W9 on this main

- **Criterion 2 (matches the signed-off mockup):** MET again. Home's events equal the signed-off rows, and the DOM
  assertion passes.
- **Criterion 5:** MET. The "Claude" fix comes from judge 31. Judge 29 minor 1 is fixed: my probes give `fable-5`,
  `FABLE 5.1` and `claude_opus_4` → caught; "a sonnet about markets" and "magnum opus" → not matched.
- **Judge 29 minor 2** (rule names that depend on the detector): resolved by minor 1.
- **Judge 29 minor 3** (a card's sources from its own group): a node test (`lib/home/tests/blocks.test.ts:55`), plus
  a permanent harness plant, "a group figure under another group's source".

**W9: PASS.** No open finding. The empty-state examples remain a W10 proposal, not a W9 criterion.

## Addendum: the W9 minors push (1bbcfde, `response_10_w9_home.md`), probed at ed21a5a

- **Vendor and brand names:**
  - matched: "the Anthropic console" → Anthropic, "OpenAI API" → OpenAI, "ChatGPT said" → ChatGPT, "Qwen2.5" → Qwen2.5;
  - left alone: "a haiku" → no match.

  "Anthropic console" remains only in a code comment (`assistant-page.tsx:70`), not on a screen.
- **Baseline:** `base.llm_only.v1` "claude_opus_4 only" shows as "Baseline".
- **Dotted ids:** "scored by anthropic/claude-3.5-sonnet" becomes "scored by AI team/AI team". No model is named, but
  the text reads oddly. Cosmetic; not a finding.
- **The hydration fix:** `startTransition` is present in `components/frame/use-frame-state.ts:109`. The one-off React
  #418 failure was not reproduced by the builder or by me, so the root cause is **some evidence** only. The full
  harness passes (148/0).

W9 stays **PASS**.
