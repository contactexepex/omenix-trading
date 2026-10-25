# Judge 235: W3g, the AI usage and budget screen

Dashboard `story/w3g-budget` at 87af294 (W3 builder 0134MoC6f7aAJVcHRBiyATo6; claims: response_41). It is built from
main f4f7f40, on contract 2.10.0 (`FnoBudget`), with mockup 43. Story W3, step 7: "BG1's meter and signal; no model
names"; answer (a): budget in Control. Lane 1. Judge D, 16 Oct 2026.

**PASS.**

| Criterion | Result | Evidence |
|---|---|---|
| W12 pattern | MET | `lib/fno-budget/` has types, one interface, the Azure adapter (page `budget`), the fixture adapter only without a database, one wiring and a pure `view.ts`. The page key is removed from notRead and added to the integration record. |
| India only, in Control | MET | The build has `/india/budget` and no `/us/budget`. The nav item "AI usage and budget" sits in Control with `india: true` (route test). |
| Minutes only, no model or session | MET | The view writes minutes and percent of cap. The test scans every view output of all three examples for ₹, Rs, rupees, a model name (claude, opus, sonnet, haiku, gpt) and `session_`. |
| No copied BG1 share | MET | No 80%, 50% or "half" appears (same test). The level comes from the payload in words ("Alert: close to the cap", "Stop: the cap is reached"), and there is no alert tick. Contract 2.11 (judge 233, a570f0d) adds `share_pct`, `alert_pct` and `stop_pct`, so the tick and shares can follow from the payload. |
| States | MET | The tests cover ok (bar 33.9, "34% of the cap used"), alert (84), plan basis with stop and pct 112 drawn full (100), and none (unknown, no bar, the note, no rows). The groups follow the payload's order. |
| Root class collision | MET | `assistant.css:32-34` has a global `.budget` grid, so the root is now `ai-budget`. `.facts2` moves to `fno-screen.css` with the same declarations. |
| Gates on 87af294 | MET | `check_contract` and `check_fno_screens` 0, code size OK, `sync-design` clean, `tsc` OK, `npm test` 530/530 (0 skipped), `next build` 0. |

**Note:** whichever of W3g and 2.11 merges second should draw the alert tick from `alert_pct` and say `share_pct` of the
basis, as mockup 43 now does.
