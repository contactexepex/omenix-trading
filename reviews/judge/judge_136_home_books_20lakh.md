# Judge 136: dashboard `story/p1-home-books-20lakh` 093888e7a80aa49eff34aff1e3b1861a1b0561c0 (from main 3df9179; two commits: 1ca2849 Home's F&O books, 093888e the Strategy lab's F&O capital), judge A

This follows up judge 135's note: Home's mock still said the F&O books held Rs 5 lakh after C5.

## Checks, run myself

**Only values and wording changed, with no change of shape.** I compared every leaf of the three data files between
3df9179 and 093888e, and the key sets are identical in all three:

| File | Leaves changed | What changed |
|---|---|---|
| `api/examples/blocks.json` | 4 | The three F&O books' `value` × 4 (500,000 → 2,000,000; each book's `pnl` is 0, so value = capital) and `payload_sha256` |
| `design/mockups/31-dashboard/data.json` | 3 | The same three `value`s × 4 |
| `design/mockups/38-strategy-lab/data.json` | 195 | `fno_capital` × 4. Every other change is an F&O percentage series (`rule`, `hybrid`, `ai`) at about ¼ (ratios 0.227-0.251, the spread from 2-decimal rounding of small values). No rupee figure changed |

- **The `api/` text.** `blocks-fno.yaml`'s `x-empty` and `blocks-home.yaml`'s description change wording only: "Rs 20
  lakh ... (story C5)".
- **The catalog row and the web fixture** are regenerated to match.
- **The lab's code.** `js/1-base.js`'s fallback is `|| 2000000`. The one constant is `FNO_CAPITAL` in
  `_platform/lab_example.py`, read by `lab_data.py`.

**The Manual account is untouched.** Its `capital` is still 500,000 (and US $5,000) in `blocks.json`, and `config.yaml`'s
Manual profile is still `paper_account_rs: 500000`.

**The lab's totals add up.** `node design/mockups/38-strategy-lab/check_totals.js` gives "totals: 9 lines add up"
(stocks plus F&O = total, to the rupee, on the early, review and review-F&O states).

**Dashboard gates at 093888e:**
- `check_contract.py`: OpenAPI valid, examples current, catalog complete, planted breaks caught;
- `check_fno_screens.py`: every rule holds;
- `check_mapping.py`: zero gaps;
- `check_code_size.mjs`: within limits;
- `npm run typecheck`: ok;
- `npm test`: **465 of 465 pass**.

I did not run `npm run build`. No web code changed, only `web/lib/fixtures/blocks.generated.json` (data). The builder
reports the build passing.

### Verdict: PASS for 093888e7a80aa49eff34aff1e3b1861a1b0561c0

The change is values and wording only. The Manual account is unchanged, every rupee result is unchanged, and the
percentages are a quarter of before because the capital is four times larger. The totals add up and every gate passes.
