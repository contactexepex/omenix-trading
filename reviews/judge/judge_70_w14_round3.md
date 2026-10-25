# Judge 70: W14 round 3 (omenix-dashboard): 9c50f24 on `main` (after the fact) and branch `story/w14-round3` dc68754

Date: 14 Oct 2026. Claims: `reviews/claude/response_32_w14-owner-strategy-lab.md` and its addendum (branch).
9c50f24 reached `main` at 00:35:56 UTC without a PASS, the fourth breach of the owner's rule.

## Verdict

- **Branch dc68754 (the "By company" redesign): PASS.** The builder may merge.
- **9c50f24 (neutral labels, drawdown and picks wording), after the fact:** acceptable.
- **Must-fix as its own story:** the "no internal term on any screen" check is **NOT MET**. Three screens still show
  strategy thresholds (below).

## Gates (branch tip, separate worktree, built)

- `npm test`: 452 pass, 0 fail.
- UI harness `--only w14`: 36 cases, 0 failed. These include `w14-lab-company-map-25` and the
  `w14-no-backend-names-*` scans of Home (India, US), Strategy lab, Help, Rule vs AI, Paper portfolios, the stock
  page, Stock strategies and Track record, HTML and address.

## The owner's ask for "By company", checked on the harness screenshots and by plants

| Owner's ask | Result |
|---|---|
| Companies as rows, full names and tickers | Met: "Oil and Natural Gas Corporation Limited / ONGC" wraps, never overlaps |
| Full values | Met: every cell whole (for example −7.92L) |
| First 8, then "Show all" | Met. **My plant** (first 30 instead of 8): the case fails, with no "Show all" to click |
| Full width | Met at 1280 px: six strategy columns, "6 of 15 strategies fit here" |
| One strategy at a time on a phone | Met at 390 px: one column, chosen with "Sort by". **My plant** (2 columns on a phone): "2 strategy columns on a phone, not 1" |
| An overlap test | Met: bounding-box overlap, clipping and right-edge checks. The builder's 40 px-column mutation fails it |

## 9c50f24 after the fact

- Neutral fixed labels (Rule-based 1-8, Always buy, Follow yesterday, Baseline 3, AI team A-D) are applied **on the
  server in every `/api/v1` answer**, and in the client and adapters.
- An unknown strategy gets a hashed neutral label, never its backend name.
- The harness name scans pass on all the pages listed above.
- The drawdown-limit and picks wording are text changes.

No defect found in what it does.

## NOT MET: internal terms still on screens (owner's rule, 13 Oct: "strategy internals stay private")

I searched the branch's pages:
- **Trade story:** `lifecycle/[date]/_parts/story.tsx:130` shows "Chance of a rise 61% (its bar: 55%)", and
  `lifecycle-page.tsx:41` says "below its bar".
- **Stock strategies:** `strategies-page.tsx:298-300` tooltips say "the strategy's bar (55%)" and "filtered out by
  its regime rule".
- **Track record:** `track-record-page.tsx:368-372` shows per-band thresholds ("whenever the model's chance clears
  its threshold", and the bar per row).

The builder listed the first and the endpoints as still open, and they come from the `lifecycle`, `strategies` and
`track-record` endpoints. They are live on the deployed app today. They are not made worse by this branch, so they
do not block its merge, but they need their own story now:
- drop `threshold` and regime wording from those three endpoints with the same allow-list pattern as the Strategy lab
  API;
- remove the texts from the three pages;
- extend the `w14-no-backend-names` scan to the words "bar", "threshold" and "regime rule".

## Process

The fourth breach. The branch, by contrast, followed the rule.

## Addendum 1 (merge check, omenix-dashboard 11ca4a3)

**MET.** 11ca4a3 has parents d05b467 (main) and dc68754 (the passed tip). My recomputed merge of the two equals
11ca4a3 exactly. At 11ca4a3 (my runs):
- `npm test`: 452 passed, 0 failed;
- `tools/check_code_size.mjs`: passes.

I cannot read omenix-dashboard's GitHub Actions from this session (the repository is outside this session's GitHub
scope), so CI there is not checked by me. My local gates are the evidence.
