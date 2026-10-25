# Judge 24: story W9, the signed-off Home screen in the real app

**Verdict: FAIL.** There are 2 should-fix findings, 1 owner decision and 2 minor findings.

What works:
- the screen matches the signed-off mockup;
- the import-graph rule holds against every plant I tried;
- tests, typecheck, build and the full UI harness pass.

What fails:
- **Criterion 4:** its "no adding across groups" check can be beaten on this very fixture. A sum of two groups placed
  in a component renders, and every test stays green.
- **Criterion 5:** the display-name rule is a list of names that already misses a current model family.

**What I judged**
- **Repository:** `exepex/omenix-dashboard` at 5074aaa, cloned read-only to `/tmp`.
- **Claims:** `reviews/claude/response_8_w9_home.md`, with images in `reviews/claude/w9/`.
- **Story:** W9 in trading's `docs/stories/X-cross-repository.md`, 6 criteria.

## Checks run by the judge

```
$ node tools/check_code_size.mjs                code size: every file within 350 lines or its listed size
$ cd web && node tools/sync-design.mjs --check  design copies current
$ npm ci --ignore-scripts && npm run typecheck && npm test && npm run build
  tsc clean; # tests 360 # pass 360 # fail 0; build exit 0
$ node tests/ui/harness.mjs --out /tmp/w9ui      148 cases, 0 failed
```

The run includes `home-india` (5 widths), `home-us`, `home-open`, `home-dark`, the three trade tabs, and the frame,
dark and shell cases for Home.

**CI run 38344099253** (both jobs green on 5074aaa) is reported by the orchestrator. I did not see it.

### Screens compared with the mockup (my own run's images)

I looked at `home-india` at 1280 and 390 px and at `home-us` at 1280 px:
- **Sections and order:** match the mockup.
- **Figures:** every one I compared matches, including the group cards (+₹1,800.00, −₹9,309.36, No strategy yet,
  +₹1,015.81; the F&O books at ₹0.00), the Baselines line (−₹8,293.55), the six open-trade rows and the tab counts.
- **Differences:** only the ones the builder lists (theme button, Ask icon).
- **The gallery Home images used for the comparison** are unchanged since the sign-off commit e8cd360.
  `page.html` and some F&O gallery images changed later, through stories 32 to 34, but none of the Home states did.
- **`notes.md`:** changed since e8cd360 only by the sign-off header and a corrected source path (cadf1d2). The
  contract rows are unchanged.

### Criterion 4: planted sums on the rendered screen

Each plant was built into the app; the Home cases were run, then everything was reverted.

| # | Plant | Where | UI money check | Unit tests | Result |
|---|---|---|---|---|---|
| P1 | The AI team card's total = AI team + Rule-based | `lib/home/groups.ts` (pure logic) | (not run) | **1 fails** ("a group card's headline is the block's own total") | caught |
| P2 | The same sum, India | `components/home/who-trades.tsx` | **passes in all 4 India Home cases** | **360 pass** | **NOT caught** |
| P2 | The same sum, US ($99 + $39.66 = $138.66) | the same | `home-us`, `dark-home-us`, `frame-page-home-us` fail | 360 pass | caught |
| P3 | Cross-currency: the You card's account = ₹5,01,800 + $5,008.49, shown as ₹5,06,808 | the same | `home-india`, `dark-home-india`, `frame-page-home-india` fail | 360 pass | caught |

**Why P2 slips in India:**
- On screen, the AI team card read **−₹8,293.55**: the sum of Rule-based (−₹9,309.36) and AI team (+₹1,015.81).
  I saw this in the screenshot.
- That sum equals the Baselines total exactly, and the check only asks whether a shown figure is *some* number in the
  market's fixture. It allows 251 values in India and 216 in the US.
- This is exactly the builder's stated doubt, and it happens on the real fixture, not in theory.
- I also counted, using the check's own code, how many sums or differences of two money fields would be accepted:
  - **India:** 17 of 56 pairs, most of them by adding a zero.
  - **US:** 3 of 30 pairs.
  - **Cross-currency (₹ plus $):** 2 of 48 pairs.

### Criterion 5: probing the display-name rule (`applyDisplayNames`)

| Backend name | Shown |
|---|---|
| `AI combined (Opus)` | `AI team · combined A` (correct) |
| `AI solo (Claude Opus 4.8)` | `AI team · solo` (correct) |
| `AI combined (Fable 5)` | **`AI combined (Fable 5)`**: a current model family, untouched |
| `AI reasoning (o3)` | **`AI reasoning (o3)`**: untouched |
| `News agent on claude-sonnet-5` | **`AI team · News agent on claude--5`**: garbled, still names Claude |
| free text: `The Opus agent and claude-haiku-4 agreed; Sonnet 4.5 dissented.` | **`... and claude-AI team-4 agreed; AI team 4.5 dissented.`** |

**The every-case check passes today** (148 cases), because no fixture holds these forms.

**Where "Claude" appears.** `grep` over `app`, `components` and `lib` (tests aside) finds these strings a user can
see:
- the companies page help tip ("the Claude app");
- the assistant Spend card ("on the Claude API");
- the conversation channel label "Claude app";
- the assistant's error and not-configured messages ("The Claude API is rate limited now ...").

**The model the assistant used** is logged (`store.ts`), never rendered: no screen reads `row.model`.

### Criterion 3: my own import plants into `components/home/`

| Plant | Result |
|---|---|
| `@/lib/home/fixture-source` (alias) | caught: 3 fail |
| A re-export hop through a new `lib/ui/zz-hop.ts` to the wiring | caught: 3 fail |
| ``import(`@/lib/home/fixture-source`)`` (template literal) | caught: 3 fail |

All plants were removed; `git status` is clean.

## Criteria

| # | Criterion | Judge's own evidence | Result |
|---|---|---|---|
| 1 | Every gallery state the fixture covers, 390 to 1680 px, check clean | 148 cases, 0 failed, Home cases included | MET |
| 2 | Matches the signed-off mockup, differences listed | Comparisons above; the listed differences are honest | MET |
| 3 | Components depend only on `HomeData`; enforced by an import-graph test | 3 plants caught | MET |
| 4 | No figure adds across groups, markets or currencies (a test over rendered numbers against the fixture) | Cross-currency caught (P3). **A cross-group sum in a component is not caught in India** (P2): the test checks membership in a set, not each figure against its own field. | **PARTLY** |
| 5 | No screen names an AI model; one display-name rule; a test over every fixture state | Today's fixtures are clean, and the "Opus" leaks on old pages are fixed. **The rule misses Fable and o3 and garbles model ids.** "Claude" is shown on four screens or messages. | **PARTLY** |
| 6 | Code size, typecheck, tests, build | All pass. The old Home (586 lines) is gone from the allowlist, and Rule vs AI shrank from 459 to 458. | MET |

## Claims vs reality

- **"Planted sums are caught on every run":** true only for the two planted *values* inside `homeMoneyChecks`. Those
  are synthetic numbers checked against the set, not sums produced by the screen. A real cross-group sum produced by
  a component passes (P2).
- **"A card's total *is* the block's total" (unit test):** true for `groupCard`; it bites (P1). But it covers only
  the pure logic: the component can still change the figure.
- **"Every case of every page fails if the rendered text names a model":** true for the names in `MODEL_NAME`. The
  list is what fails (finding 2).
- **The "Claude" judgement call:** honestly flagged by the builder. My reading is under the owner decision below.
- **Hybrid in the US:** the signed-off picture `gallery/home-us-1280.png` itself shows "Hybrid (0)". The builder
  followed the picture and did not edit the frozen notes. Correct; see minor finding 1.

## Engineering standards

- Small single-purpose files: the largest new one is `contract.ts` at 183 lines.
- Pure logic is separate from the components.
- One adapter line in `wiring.ts`.
- The display-name rule sits at the adapter boundaries rather than in components (good design).
- No size or structure breach.
- Finding 2 is a design weakness: a list of names is not the rule.

## Findings

1. **Should fix: criterion 4's check accepts any figure that happens to equal some fixture number.**
   - **Evidence:** P2. The AI team card showing Rule-based + AI team (−₹8,293.55, the Baselines total) passes all 360
     tests and all 148 UI cases.
   - **Expected:** check each rendered figure against **its own** source field, not the whole fixture. For example,
     each figure element carries the block path it shows (`data-src="groups.ai.total.net"`), and the case compares
     value for value. Add a planted cross-group sum in a component as a test.
2. **Should fix: the display-name rule is a list of model names, and the list is already incomplete.**
   - **What it misses:** "Fable" (a current model family) and "o3". Hyphenated model ids come out garbled
     ("claude--5", "claude-AI team-4").
   - **Why this is not far-fetched:** the stock tool's names, such as `ai.combined.opus.v1`, are named after the
     model they run on, so new model names will reach Home through the same path.
   - **Expected:**
     - derive an AI strategy's display name from its id family and role, never by stripping words from free text;
     - make the pattern cover vendor families and model-id forms (`claude-…`, `gpt-…`, `o\d`, Fable and the
       rest), replacing whole tokens;
     - add tests for each of the forms above.
3. **Owner decision (flagged, not counted against the builder): "Claude" on screens.**
   - Criterion 5 says "No screen names an AI model". Claude is the name of an AI model family (Opus, Sonnet and the
     rest are Claude models).
   - Read literally, "the Claude app", "the Claude API" and the "Claude app" channel label breach the rule. The
     builder reads them as product and channel names.
   - If the owner exempts product and channel names, this item is closed. If not, the fix is one word in the
     pattern plus copy edits on the companies help tip, the assistant Spend card, the channel label and the
     `explainer.ts` messages.
4. **Minor: `notes.md` row 5 says "Hybrid (India)", while the signed-off US picture shows a Hybrid tab.** The frozen
   contract contradicts itself. The builder followed the picture and the owner's fifth round. Expected: the owner
   corrects row 5 through the orchestrator, as the notes' own change rule requires.
5. **Minor: three coded empty states are not shown by any fixture state:** "Nothing needs you", "Nothing scheduled"
   and "No news stored yet". I could not see them rendered. Expected: a fixture state, or a component test, for each.
