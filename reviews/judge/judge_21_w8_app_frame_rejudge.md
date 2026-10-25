# Judge 21: story W8 re-judged (round 2)

**Verdict: FAIL** (changed from PASS on 13 Oct 2026, after this file was first written).

**Why it changed:** the new `ui` CI job (minor 2) is not green. The orchestrator reports that run 38335689110 failed
at the step "UI harness" (job 115095122372), while the `web` job passed. I cannot see this repository's CI runs from
this session, so this comes from the orchestrator, not from my own check. A CI job that this story added and that
fails is a should-fix finding: the story is not done until that job runs green. Everything else below stands.

**Earlier verdict text, kept:**

- Judge 19's should-fix finding is fixed, and I re-planted my own bypasses to check it.
- Minor findings 1 and 2 are fixed. Minor 1 rests on a CI run I could not see, so I take it on some evidence only.
- The pushback on minor 3 is accepted.
- One new minor finding, not blocking.

**What I judged:** `exepex/omenix-dashboard` at 2ca3373, cloned read-only to `/tmp`. The builder's answers are in
`reviews/claude/response_6_w8_app_frame.md`.

## Checks run by the judge

```
$ npm ci --ignore-scripts && npm run typecheck && npm test   tsc 0; # tests 347 # pass 347 # fail 0
$ npm run build && node tests/ui/harness.mjs                  147 cases, 0 failed
$ node --test lib/shell/tests/import-graph.test.ts            7 pass, 0 fail
```

I planted each of these in `components/frame/parts.tsx`, ran the import-graph test, and reverted. `git status` was
clean afterwards.

| # | Plant | Result |
|---|---|---|
| a | `import { fixtureShellData } from "@/lib/shell/fixture-source"` (the judge 19 bypass) | **caught**: 3 tests fail |
| b | New `lib/shell/helpers-x.ts` re-exporting the adapter, imported by the component (the judge 19 bypass) | **caught**: 3 tests fail |
| c | Two hops: the component imports a new `@/lib/ui/zz-hop`, which re-exports `../data/companies` (a data client) | **caught**: "frame components reach no adapter, wiring, fixture or data client, directly or transitively" fails |
| d | ``import(`@/lib/shell/fixture-source`)``, a dynamic import written with a template-literal string | **not caught**: 7 of 7 pass, and `tsc` accepts it (new minor finding 1) |

**Watchlist at 1280 px inside the frame.** I looked at the harness screenshot from my own run. The "Most strategies
like" card now reads **RELIANCE** whole, and the KPI cards sit two per row.

**Pushback check.** `grep -rn Opus web/app web/components web/lib` (tests aside) finds nothing. The model name on the
old Rule vs AI page comes from backend payload data, not from dashboard code.

## Judge 19's findings: decisions

| # | Finding | Builder's answer | Judge's evidence | Decision |
|---|---|---|---|---|
| 1 | Should fix: criterion 5 enforcement can be bypassed (the `@/` alias, a re-export) | One resolver handling alias, extensionless, index, re-export, dynamic and require. Three rules: no module but the wiring imports the adapter; only the layout imports the wiring; a transitive walk from every frame component. Planted tests. | Plants a, b and c caught. The test file holds its own planted cases (7 pass). | ACCEPTED |
| 2 | Minor: the UI harness is not in CI | New `ui` job in `.github/workflows/web-tests.yml`: Playwright 1.56.1 pinned, Chromium, build, harness, artifact upload | Workflow read and correct in form. **First run 38335689110: result not verified by me.** This session has no GitHub API access to omenix-dashboard. Some evidence until a green run is seen. | **REJECTED for now:** the run failed at "UI harness" (job 115095122372, reported by the orchestrator). Should fix: make the `ui` job pass in CI. |
| 3 | Minor: the RELIAN / CE word break | The page area is a size container; KPI cards go 2 per row below 1040 px | Screenshot above; harness 147/0 | ACCEPTED |
| 4 | Minor: "AI combined (Opus)" on the old page | Pushback: this is stock-backend payload data, not W8 code. Fix it once, in W9 or the backend, not by patching one page. | Grep confirms no such string in app code. The orchestrator has added "screens never name an AI model" to W9 as an acceptance criterion with a test. **The pushback is correct for W8's scope**, provided that W9 criterion exists. | ACCEPTED |

## Criteria

| # | Criterion | Result |
|---|---|---|
| 1 | Every page inside the frame at 4 widths, with no errors, external requests or overflow | MET (147/0, my run) |
| 2 | Side-by-side comparison | MET (unchanged from judge 19; the builder refreshed the images, and the Watchlist page now has no word break) |
| 3 | Search | MET |
| 4 | One lock rule | MET |
| 5 | Components never reach the adapter or a data client, enforced by a test | MET (plants a-c caught; one exotic syntax remains, minor 1) |
| 6 | No submit path | MET; the scan now covers everything the frame reaches |
| 7 | Code size, typecheck, tests, build | MET (347/347) |

## Engineering standards

- The resolver lives in its own small module (`lib/shell/tests/imports.ts`), shared by the rules (DRY).
- The CSS fix is a container query at its cause, not a page-specific patch.
- No file breaks the 350-line limit, and I found no other breach.

## New finding (minor)

1. **A template-literal string in a dynamic import is not read by the resolver.** For example
   ``import(`@/lib/shell/fixture-source`)``. It compiles and passes the import-graph test.
   - Nobody writes this form by accident, so the risk is low.
   - Expected: treat a backtick string without `${` like a quoted one, or refuse any dynamic import whose argument
     the resolver cannot read.
