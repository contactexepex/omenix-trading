# Judge 93: desk meeting 2, first-strategy candidates: `story/x-first-strategy-candidates` 7e2d3bb (response 92)

**Lane.** The builder labelled this "Lane 2". It adds files under `research/`, which makes it lane 1 under the lanes
rule as merged (da1509f). The orchestrator correctly sent it here.

**What I did.**
- Ran `analysis.py` on the branch and compared its output with `output.txt`.
- Re-derived every number the owner will act on from the primary files: experiment 1's results JSON and `RESULTS.md`,
  desk meeting 1, the 14 Oct quote snapshot and its `meta.json`, response 77's margin rows, and the C2 formula in
  `fno/risk/margins.py`.
- Did not read the 2019-2023 rows of `golden_iv30_rv20.csv` or of the back-fill. The script does not read them either.

## Reproduction

`python -B research/2026-10-14-desk-meeting-2/analysis.py` exits 0. Its output is **byte-identical** to `output.txt`.
`ruff check` and `ruff format --check` are clean on the script, which has 155 lines.

## Claims

| Claim | Result | Evidence |
|---|---|---|
| (1) Zero credible edge after costs. SC gross +978 (2024-26) and +408 (2019-23) against costs of 824 and 814; SF and BF negative | MET (strong evidence) | Recomputed from `results_*.json` with traded and impossible exits removed: SC n 33 and 57, nets +153 and -406. The SF and BF rows match the table. The BF 2019-23 total of -2,642 matches my sum. All the cross-references exist in experiment 1 and desk meeting 1: P4 -29,190 against its opposite -12,422; discovery +21,451.56; stale-close losses -11,346 and -13,728; bull call -27,541; straddle -3,24,905. |
| (2) IV above RV20 in 74-82% of entries; Nov skew 15.35 / 13.8 / 13.1 | MET | F1 above 0: 82% discovery (n 33), 74% challenge (n 50). The skew comes from the snapshot at the Nov future's last price of 22,760 (from `meta.json`): PE 22000 15.35%, PE 22700 13.82%, CE 23400/23500 13.10%. Minor: Black-76 here has no discount factor (r = 0), which biases IV by a few hundredths of a point. That does not change the conclusion. |
| (3) Put spread -243 / -355 (reasoning only) | MET as labelled | Mids 169.425 and 141.60 match the snapshot. The credit of 1,809 and the cap of 8,351 recompute. 93 windows (33 + 60). Exit at 21 days to expiry matches experiment 1's exit rule. |
| (4) Trades needed for 2 SE | MET in response 92; the orchestrator's "280-1,200" is not | Response 92 uses only 1,212, from the positive 2024-26 condor, which is correct. The 281 in `output.txt` comes from the challenge condor's negative mean, so it is the count needed to prove a loss, not an edge. The `output.txt` column "trades for 2 SE" mixes both kinds; see follow-up 2. With the challenge SD of 3,403 and a +153 edge, proving the edge would need about 1,979 trades. The real range is about 1,200-2,000 trades, roughly 100-165 years of monthly trades. |
| (5) Stressed margins: SC 71,428, SF 64,300 | MET as stressed **margin**; **NOT MET as "funds at entry"** (must-fix) | See below. |
| No new P&L on held-out option prices; experiment 1's freeze respected | MET, with should-fix 1 | Sections 1-2 read recorded results only. No option-price P&L is run. Experiment 1's challenge was already run once (a074eb9), and its holdout is recorded as used up (`docs/DESK_DECISIONS.md`, 13-14 Oct). |

## Must-fix: the "funds at entry" figure is the stressed margin, not the funds needed

- **Margin.** C2's stressed margin for SC 300 is `max(0, 1.45 x 8,517.60 + 10,153) + (-10,153) + 59,077.07` =
  **71,427.59**. This matches response 92 (and SF 300: 64,300.40). As a margin, the figure is correct.
- **Where it is mislabelled.** The candidates table gives it as **"Funds at entry per lot (stressed 1.45)"**.
- **What funds at entry really are.** C2's funds-at-entry check (judge 77 addendum 3) is different. At entry the broker
  credits no sold premium but takes the bought premium at once: `max(0, k x scan - NOV) + exposure` + bought premium +
  charges.
  - For SC 300 that is 81,580.59.
  - Add the bought wings at the 14 Oct ask (CE 23500 at 133.10 and PE 21950 at 159.90, x 65 = 19,045).
  - Plus charges, the total is about **Rs 1,00,600**, not Rs 71,428: about 40% more cash needed per lot.
- **The put spread's estimate has the same omission.** Rs 32,000-35,000 leaves out the bought put (about 142 x 65 =
  Rs 9,200) and the credit not counted at entry.
- **Why it matters.** The owner sizes the account from these figures.
- **Fix.** Label 71,428 and 64,300 as "stressed margin". Add the funds-at-entry figure computed with C2's formula, and
  correct the put-spread estimate on the same basis.

## Should-fix

1. **Register the put-spread model in `research/ledger.csv`.** It replays a new structure on the 93 experiment-1
   windows, 2019-2023 included. It uses NIFTY moves and today's prices, not historical option prices, but it is still
   one more look at spent history. Response 92's red-team section says such looks must be counted.
2. **Fix the "trades for 2 SE" column.** In `output.txt` it is meaningful only where the mean is positive. Print it only
   for positive means, or label it "to prove the sign".

## Not checked, reasoning only

- **The SEBI weekly-expiry rule.** The response itself says it was not re-checked.
- **Exposure at 2% of notional.** Response 77 recorded a 5.6% exposure gap against Zerodha's calculator. Every
  margin and funds figure here inherits that open item.

## Verdict: FAIL for 7e2d3bb

One must-fix: the funds-at-entry label and figures. The analysis itself is sound and reproducible, and the headline
conclusion of zero candidates with an edge after costs is supported by strong evidence.

## Addendum 1 (14 Oct 2026): c128d81 (docs only, on top of 7e2d3bb)

**Verdict: FAIL.** The judge 93 must-fix is still open, and the new lead adds a wrong number.

| Item | Result | Evidence |
|---|---|---|
| Judge 93 must-fix: funds at entry | **NOT MET** | The candidates table still labels 71,428 as "Funds at entry per lot (stressed 1.45)". By C2's formula, SC 300 needs about Rs 1,00,600 at entry: 81,581, plus the bought wings at 19,045, plus charges. |
| New lead: "about 280-1,200 trades" | **NOT MET (must-fix)** | The 281 comes from the challenge condor's negative mean (-406). It is the count of trades needed to prove a loss, not an edge. The edge range is about **1,200-2,000** trades: 1,212 using SD 2,667; 1,979 using SD 3,403, both at +153. The lead should say this, as the statistician section already does. |
| Story sizing: medium, 8-10 files, one interface change | MET as an estimate (reading the code) | `Structure.legs` returns "the four legs" (`structures.py:77-78`). C4 refuses anything but four legs of SF, SC or BF (`validity_modes.py:47-61`). `BODY_SOLD` lists only those three codes. `fno/nse_margins/` has a job and rows per known code. The files named are the right ones. "A day of building" is reasoning only. |
| Costs about Rs 410 against 820 | MET (some evidence) | Pads 260 (Rs 1 x 2 legs x 2 sides x 65) plus charges of about 150. That is half the four-leg cost of 520 pads plus about 300 charges. Consistent with experiment 1's costs of 814-824. |
| Margin about Rs 32-35k against 71k | PARTLY (reasoning only) | Exposure on one short leg is 29,538.54 (half of 59,077.07). Scan risk for a 150-wide put spread is unknown: no SPAN row exists. At k 1.45 the stressed margin is plausibly Rs 35,000-40,000, a little above the estimate. It is again margin, not funds at entry. Funds at entry also add the bought put, about Rs 9,200 at the 14 Oct mid of 141.60 x 65, plus charges: roughly Rs 45,000-50,000 in all. Label it as margin, or give both. |
| "Build only if B0's put half shows gross above about Rs 410 after 6-12 cycles" | PARTLY (a weak proxy) | B0's put half sells the put at about 0.98 x forward, with the wing as wide as the cap allows (up to 300 points). Option A sells at about 0.97 x forward with a 150-point wing. The strikes, width and premium differ, so B0's put-half gross is not A's gross. Also, 6-12 cycles at a per-trade SD in the thousands cannot tell Rs 410 from zero: the same arithmetic as the lead. Present it as a rough indication, not a test. Record B0's per-leg fills so the put half can be read at all. |

Must-fix:
1. Relabel the funds-at-entry row, and give C2 funds-at-entry figures for SC 300 and for Option A.
2. Correct the lead's trade range to about 1,200-2,000.

Should-fixes 1 and 2 from judge 93 remain open.

## Addendum 2 (14 Oct 2026): 8737596

| Item | Result | Evidence |
|---|---|---|
| Must-fix: funds at entry separate from margin, by C2's formula | MET | Script section 7 implements C2's formulas (`fno/risk/margins.py`; judge 77 addendum 3). Its output: SC 300 stressed margin 71,428; funds at entry **1,00,784** = 81,581 + 19,045 bought wings at the ask + 158 entry charges (`fno.costs.order_charges` with `config.yaml` charges). That agrees with my estimate of about 1,00,600 plus charges. Put spread 22000/21850: NOV is −1,761.50 at today's fills (bought at ask 142.10, sold at bid 169.20). With scan bounded by the SC 100 and SC 200 rows (2,650.70 and 5,423.60), stressed margin is 33,382 to 37,403 and funds are 44,453 to 48,473; I recomputed both bounds by hand. The scan bound is labelled an estimate (no NSE row exists), which is honest. The table now has separate rows for stressed margin and funds at entry. |
| Must-fix: the trade range in the lead | MET | The lead says "about 1,200-2,000 trades, i.e. about 100-165 years". The response discloses that the earlier 280 figure proved a loss, not an edge. The script prints 1,212 and 1,979. |
| Should-fix: ledger row for the put-spread model | MET | Row 42 is `retrospective`, `hypothesis` no, with no protocol. That is correct: the model's result was seen before the row was written. `LEDGER.md` adds the missing 37-41 line and row 42, and the total trial count is now 42. |
| Should-fix: the 2 SE column | MET | The column is printed only where the mean is positive ("no edge to prove" elsewhere), plus the 1,979 line. |
| `tests/research/test_ledger_guard.py` | MET: an honest update, not loosened | The pinned id list grows from 1-41 to 1-42 (`range(1, 43)`), so the test still requires every row and no gaps. It adds an assertion that row 42 is `retrospective`. No assertion was removed or weakened. Under the merged lanes rule this test edit adds a check, so it is not a weakened test. |
| Reproduction and gates | MET | `analysis.py` output is byte-identical to `output.txt`. On a trial merge with `main`, 3,150 tests passed with the Slack token unset; `ruff check` and `ruff format --check` are clean, including the research script; `check_imports` is clean. |

Still open, inherited from response 77: the 5.6% exposure gap against Zerodha. It applies to every margin and funds
figure here, and the response says so.

**Verdict: PASS for 8737596.** Merge it. After the merge I check `main` and CI.

## Addendum 3 (14 Oct 2026): c3a2569, the tip to merge (docs and script only, on top of 8737596)

- **Scan ceiling.** The put spread's scan ceiling is now its full loss: width 150 x 65 + NOV (−1,761.50) = 7,988.50.
  That is correct. A defined-risk vertical cannot lose more than its width minus its current value, so no SPAN scenario
  exceeds it. At k 1.45 the stressed margin is 41,122 and the funds at entry are 52,192. The ranges are now about
  33,400-41,100 and 44,500-52,200, labelled as estimates, with the exact figure deferred to A14's calculator.
- **B0's put half.** It is now labelled "an indication only, not a test". The text gives both reasons: the strikes and
  width differ from the candidate, and 6-12 trades cannot tell Rs 410 from zero. It requires per-leg fills. This
  matches addendum 1.
- **Reproduction.** `analysis.py` output is byte-identical to `output.txt`, and `ruff check` and `ruff format --check`
  are clean. Nothing outside the research script, its output and response 92 changed after 8737596, which addendum 2
  ran in the full suite.

**Verdict: PASS for c3a2569.** Merge exactly that. After the merge I check `main`.

## Addendum 4 (14 Oct 2026): merge 7258fa2 MET

- **The merge is exact.** Its parents are d8dfb3b and c3a2569, and it equals my recomputed `git merge-tree` exactly.
- **No unjudged change on `main` since.** Nothing under `fno`, `tests`, `tools`, `.github`, `config.yaml`, `db`,
  `research`, `agents` or `playbook` changed after it; the later commits are logs and judge files.
- **CI is pending.** I confirm it with the 17:35 UTC audit.
