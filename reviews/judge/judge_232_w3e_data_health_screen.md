# Judge 232: W3e, the F&O data health screen

Dashboard `story/w3e-data-health` at 59ef046 (W3 builder 0134MoC6f7aAJVcHRBiyATo6; claims: response_39 and its
addendum 1). It is built on main f4f7f40. Story W3 (trading `docs/stories/W3-fno-screens.md`, build step 5: "manifests,
checks, the publish run status"; answer (a): "data health = the existing Control item, with an F&O section"). Contract
`FnoDataHealth` 2.8.0 (unchanged in 2.10.0), mockup 44. Lane 1. Judge D, 16 Oct 2026.

**PASS.**

| Criterion | Result | Evidence |
|---|---|---|
| The W12 pattern | MET | `lib/fno-data-health/` has the contract types, one interface (`DataHealthData.health()`), the Azure adapter (page `data_health` through `lib/fno`'s reader), the fixture adapter loaded only without a database, one wiring line, and a pure `view.ts`. The import-graph test finds the screen and its route `fno/data-health`. |
| India only, absent in the US | MET | `generateStaticParams` returns India only, `dynamicParams = false` and `notFound()`. The build output has only `/india/data-health` (no US html in `.next/server/app/us`). The route test shows the nav item in India's Control group and absent in the US. |
| Dates, counts and statuses only | MET | Contract types: `source`, `plain`, `last_day`, `rows`, `gaps`, `status`; publish `status`, `run_on`, `reason`; check `status`, `run_on`, `problems`. The schema is closed (`additionalProperties: false`) with x-never-sent "any data value". `reason` is "why it failed, in plain words (never a value)". |
| As mockup 44 | MET | The status words, how-to text and three-column runs grid match `44-data-health/js/2-health.js` and `template.html`. The how-to times match trading's crons: publish `40 1 * * *` UTC = 07:10 IST (`market-publish.yml:14`) and health check `21 12 * * *` UTC = 17:51 IST (`health-check.yml:11`). |
| Every state | MET | `health.test.ts` covers published/ok, failed with its reason and 3 problems (sources in payload order), nothing run, the singular "1 problem", and a source with no file. |
| Page key and not-read list | MET | `FNO_PAGES.getFnoDataHealth = "data_health"` is removed from notRead, and the integration test's page record includes it. |
| Shared CSS (`.cards3`) | MET | The duplicate-CSS test found the runs grid copying paper books' `.books`. Both now use `:where(.fno-screen) .cards3` (same declarations and the same 1099 px single column). Paper books keep `.sec .cards3{margin-top:0}`, which is more specific than the base rule. Both page roots carry `fno-screen`. The rename is in W3c's `paper-books.css` and `paper-books-accounts.tsx` only, with no leftover `.books`. |
| Nav choice (reasoning only) | Accepted | Control's existing "Data health" item, until now "soon" in both markets, opens this page in India only, so the US loses a "soon" placeholder. That follows answer (a) and mockup 44 (India only). Keeping a US placeholder would need a per-market page in the nav model for one item. The orchestrator accepted this and will tell the owner. |
| Gates on 59ef046 | MET | `check_contract` and `check_fno_screens` 0, code size OK, `sync-design` clean, `tsc` OK, `npm test` 529/529 (0 skipped), `next build` 0. |
| No duplicate (WORK_REGISTER) | MET | W3e is the W3 builder's own step. There is no second reader or adapter of `data_health`. |

**Note:** the screen ships when P2e publishes `data_health`. Until then, with the database set, it shows "not
published" (answer (c)).
