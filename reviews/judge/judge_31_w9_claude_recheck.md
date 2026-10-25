# Judge 31: story W9, narrow re-check of the "Claude" should-fix (judge 29)

**Verdict: FAIL on main.**

W9's own fix is **ACCEPTED**: "Claude" is gone from every screen, and the gate catches it. But W9 round 2 no longer
holds against main's Home fixture. W11 round 2 resynced Home's "Coming up", and it no longer matches the signed-off
mockup (W9 criterion 2). That is an unlisted difference caused by W11, judged in judge 32's should-fix. **No W9 code
change is needed.** W9 passes once W11's fix restores the signed-off "Coming up".

**What I judged:** `exepex/omenix-dashboard` at ef9bd9a: change 3243782, merged with W11 round 2 (b23daca).

## Checks run by the judge

```
$ node tools/check_code_size.mjs; cd web && node tools/sync-design.mjs --check     ok; design copies current
$ npm ci --ignore-scripts && npm run typecheck && npm test      tsc clean; # tests 363 # pass 363 # fail 0
$ npm run build && node tests/ui/harness.mjs                    148 cases, 0 failed
```

**CI on ef9bd9a:** not seen by me. The orchestrator is confirming it through the API.

### The should-fix: "Claude" on screens

**Grep over `app`, `components` and `lib`,** with tests, comments, imports, model ids, environment-variable names,
allowlisted hosts and internal keys left out. No visible "Claude" string remains:
- The channel labels now read "the AI app" and "AI app".
- The Spend card reads "cost in AI usage".
- The companies help, the explainer messages and the MCP sign-in page are reworded.

One vendor word remains on a screen: the Spend tip's "Anthropic console". It is not the word the owner ruled on; the
orchestrator says it is reworded in the next push. Noted, not counted.

**The detector** (`modelNameIn`):

| Text | Result |
|---|---|
| "the Claude app" | Claude |
| "Claude's view" | Claude |
| "CLAUDE" | CLAUDE |
| "claude" | claude |
| "Claude Code" | Claude |
| "Ask Claude" | Claude |
| "claudette", "Claudia" | null (whole word only) |

**The gate, with a plant built into the app:** Home's footer read "… (ask the Claude app) …". The result:
`home-india`, `frame-page-home-india` (4 widths) and `dark-home-india` FAIL with "names an AI model". Reverted;
`git status` clean.

## Decision

| Finding | Fix | Judge's evidence | Decision |
|---|---|---|---|
| Judge 29 should-fix: "Claude" on screens (owner decision 13986d0) | The detector matches "Claude" as a whole word in any case; the visible text is reworded | Grep, detector cases, and the built plant caught at every width | ACCEPTED |

## Does W9 round 2 still hold on main? No

Main's Home fixture changed with W11 round 2. India Home's "Coming up" now shows:

> RBI 7 Oct, HDFC Life 15, Reliance 16, HDFC Bank 17, ICICI Bank 17, UltraTech 19

The signed-off picture shows:

> RBI 7, Reliance 16, HDFC Bank 17, NSE closed 20, F&O expiry 27, FOMC 29

US Home loses the FOMC, the jobs report and Nvidia. My harness run's `home-india/compare-1280.png` shows the
difference side by side, yet the harness passes (its comparisons are not assertions). W9 criterion 2 ("matches the
signed-off mockup, differences listed") is therefore **not met on main**. The cause and its fix belong to W11
(judge 32).

Judge 29's three minors are still to come in a later push, as the orchestrator says. They are not re-judged here.
