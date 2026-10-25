# Judge 41: W11 follow-ups re-judged (judge 40's should-fix)

**Verdict: PASS.** Judge 40's should-fix is ACCEPTED. There is 1 new minor finding.

- **What the stock tool stores now:** only what it owns, `FollowedCompaniesIndia {as_of, companies}`.
- **Who counts:** exepex/trading tags its own NSE rows "ours" and counts over them. There is no merge, and every
  input has the publisher that holds it.
- **The label** is corrected to "Orchestrator decision, 13 Oct 2026 (judge 40)".
- **The served contract** is unchanged.

**What I judged**
- **Repository:** `exepex/omenix-dashboard` at 39e3676.
- **Claims:** `reviews/claude/response_20_w11_judge40_followed_list.md`, which supersedes response 17.

## Checks run by the judge

```
$ python3 tools/api/check_contract.py     (openapi-spec-validator 0.7.2)
  contract: 70 paths (43 block endpoints), 82 block examples, 137 block schemas, 873 catalogued leaf fields, 54 planted breaks
  contract: OpenAPI 3.1 valid; examples valid and current; catalog complete; screen rules hold; every planted break caught
$ python3 tools/api/check_mapping.py; python3 tools/api/examples.py --check; node tools/check_code_size.mjs      all green
$ git diff --stat 616d0e8 39e3676 -- api/examples api/schemas/blocks-screener.yaml api/schemas/blocks-responses.yaml api/paths
  2 files changed, 4 insertions(+), 3 deletions(-)
```

- **What changed in the served files:** only metadata. The `x-read-model` text, `x-inputs: [FollowedCompaniesIndia]`
  on the two operations, and the `ours` description, which replaced its `x-catalog`. No example changed.
- **My W11 round-2 US plants** (J1, J2, J5, J7, J9, J10): still all 6 caught.

### My plants through `check_stored` (with the bundled validator)

| # | Plant | Result |
|---|---|---|
| K0 | Nothing changed (control) | no problem reported (correct) |
| K1 | Served `ours.n` off by one | **caught**: "the ours counts are not the NSE rows of the stock tool's followed companies" |
| K2 | Served `ours.screens.delivery` off by one (the judge-40 field) | **caught** |
| K3 | A followed company's NSE row loses its `ours` tag | **caught**: "rows tagged ours ['ADANIPORTS'] differ from the stock tool's followed list" |
| K4 | The list dated an earlier day (2026-10-09) | not flagged. **Correct:** the list's `as_of` is "the day the list holds from", so an older list still applies. See the minor finding. |

These are on top of the builder's 6 plants (a company missing from the list, counts in the list, an untracked row
tagged ours, and the three table checks), all caught.

## Judge 40's findings: decisions

| # | Finding | Fix | Judge's evidence | Decision |
|---|---|---|---|---|
| 1 | Should fix: the stock tool's part needed NSE delivery data | The stock tool stores only `FollowedCompaniesIndia`; exepex/trading counts `ours` over its own NSE rows for that list | `check_followed` ties tags to the list and the served counts to those rows; K1-K3 caught | ACCEPTED |
| 1b | "Owner decision (a)" was not an owner record | The label now reads "Orchestrator decision, 13 Oct 2026 (judge 40)" | Read in `blocks-stored.yaml:14` | ACCEPTED |
| 2 | Minor: the catalog showed `ours` leaves under the first universe's publisher | Gone: one publisher (exepex/trading) for every India summary leaf | Read | ACCEPTED |
| 3 | Minor: stored tables built in memory | Unchanged; acceptable as before | – | stays as noted |

Judge 40's item 3 (the Sunday 1 Feb session in `design/`) is still waiting on the orchestrator's assignment. It is not
part of this push.

## Finding (minor)

1. **Which list applies to which close is unstated.** `FollowedCompaniesIndia.as_of` is a date the list "holds from",
   but nothing says that the counts for a close must use the latest list dated **on or before** that close. A list
   published the morning after, which adds a company, must not recount the previous close. Expected: one line in the
   schema description, and a semantic check that the list's `as_of` is not after the table's close.

## Addendum: the minor re-checked (omenix-dashboard f3e7f5f)

**ACCEPTED.** W11's follow-ups have no open finding.

- The schema now says: "The counts and tags of a close use the latest list dated on or before that close, never a
  later one". All contract checks are green, with 55 plants caught.
- My own plants through `check_stored`:

| List dated | Close | Result |
|---|---|---|
| 2026-10-12 | 12 Oct | accepted |
| 2026-10-09 | 12 Oct | accepted |
| 2026-10-14 | 12 Oct | **refused**: "the list of 2026-10-14 is later than the close 2026-10-12" |
