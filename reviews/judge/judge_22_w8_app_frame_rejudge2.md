# Judge 22: story W8 re-judged (round 3)

**Verdict: PASS.** All findings are closed:
- the CI `ui` job, now green per the orchestrator;
- judge 21's minor finding about template-literal imports.

I checked the code side myself, including a revert test of the CI fix. I could not see the GitHub run itself, so
the green CI status rests on the orchestrator's report.

**What I judged:** `exepex/omenix-dashboard` at 2983e9e, cloned read-only to `/tmp`. The fix commits are f0227da and
2983e9e, with the answers in `reviews/claude/response_7_w8_app_frame.md`.

## Checks run by the judge

```
$ npm ci --ignore-scripts && npm run typecheck && npm test     tsc 0; # tests 348 # pass 348 # fail 0
$ npm run build && node tests/ui/harness.mjs                    148 cases, 0 failed   (147 + gallery-posix-locale)
```

**Revert test of the CI fix.** I removed the one line `localization: { locale: LOCALE[currency] ?? "en-US" }` from
`components/charts/candles.tsx`, rebuilt, and ran `--only gallery-posix-locale`:

```
FAIL gallery-posix-locale (shell.mjs)
     gallery-posix-locale @1280 pageerror: Invalid language tag: en-US@posix   (×3)
```

With the line restored and the app rebuilt, the case passes (`1 cases, 0 failed`). So the new case reproduces the CI
failure and proves the fix.

**Other places that take the viewer's language.** `grep` for `navigator.language`, for a bare `toLocaleString()` and
for `Intl.*Format()` with no locale, across `app`, `components` and `lib` (tests aside), finds only the explanatory
comment in `candles.tsx`.

**Template-literal minor (judge 21).** I planted these in `components/frame/parts.tsx`, ran the import-graph test,
then reverted; `git status` was clean afterwards.

- ``import(`@/lib/shell/fixture-source`)``: **caught**, 3 tests fail.
- A computed target, `import(p)` with `p` built by string concatenation: **refused**, 1 test fails.

## Decisions

| Item | Builder's answer | Judge's evidence | Decision |
|---|---|---|---|
| Judge 21: the CI `ui` job is red | Root cause: the runner's POSIX locale reached Chromium as `en-US@posix`, and the vendored chart library passed that to `Intl`. The chart now uses the market's locale. New UI case. The workflow's YAML colon slip is fixed in 2983e9e. | Revert test above: fails without the fix, passes with it. My full harness: 148 cases, 0 failed. **CI run 38337913671 with both jobs green** is reported by the orchestrator via the GitHub API; not seen by me. | ACCEPTED |
| Judge 21 minor: template-literal dynamic import | The resolver reads template literals with no `${`; computed targets are refused | Both plants caught | ACCEPTED |

## Criteria

All 7 criteria are MET:
- **Criterion 1:** the harness passes locally (148/0), and CI is reported green.
- **Criterion 5:** every bypass I have tried across three rounds is now caught.

## Engineering standards

The fix is at its cause: one locale rule, the same one the rest of the app uses. It comes with a regression case that
reproduces the failure. No breach.

No new findings.
