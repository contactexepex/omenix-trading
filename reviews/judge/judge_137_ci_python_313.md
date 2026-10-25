# Judge 137: CI and scheduled jobs to Python 3.13: `story/ci-python-3-13` 1b53a43477189090cede0826b6d079e144d5ee41 (on main 109255b), judge A

**The problem it fixes (judge 129 addendum 2).** CI on `main` has been red since the R2 merge (72ffc31, 09:11 UTC).
R2's `reading.py` uses `itertools.batched`, which needs Python 3.12 or later, and CI ran 3.11.

## The change

12 workflow files, 13 lines, each exactly `python-version: "3.11"` → `"3.13"`:
- `checks.yml`;
- `filings-archive.yml`, `flows-download.yml`, `forecast-capture.yml` (2 lines), `forecast-scores.yml`,
  `index-closes.yml`, `market-publish.yml`, `nse-margins.yml`;
- `participant-oi-release.yml`, `participant-oi-sweep.yml`, `participant-oi-watch.yml`, `quote-recorder-nse.yml`.

There is no other change.

## Checks, run myself

**The choice of fix: right.**
- R2's `r2study/reading.py` is pinned by R2's FREEZE.md, so editing it would break that freeze.
- Every session and routine runs 3.13 (this container: 3.13.16). A CI on 3.11 tested a Python nothing else uses, which
  is how the break stayed hidden.
- One runtime removes the root cause.

**Freeze hashes.** I searched every freeze record and the freeze tests for pinned workflow files. Only
`.github/workflows/panel-days.yml` is pinned (`research/forecasts/FREEZE_v3.md:48`, `6971c687…24b5a`).
- It is unchanged on the branch.
- Its SHA-256 recomputed now equals the pin.
- None of the 11 changed scheduled jobs is pinned by any freeze.

**The 3.11 exception is safe today.**
- All of `fno/` parses with Python 3.11 syntax (`ast.parse(feature_version=(3, 11))`: 0 errors).
- `datetime.UTC`, used in `fno/cards`, exists from 3.11.
- `itertools.batched` occurs only in R2's research folder, which the panel job never imports.
- Real evidence: the scheduled `panel-days` run of 12:04 UTC today, on 3.11 against `main` 109255b, succeeded (run
  38731902347).

**Gates as CI would run them.** In a fresh Python 3.13 venv, I installed `requirements.txt` (and ruff), as
`checks.yml` does:
- every package imports;
- `env -u FNO_SLACK_BOT_TOKEN python -m pytest -q`: **5535 passed**;
- `ruff check fno tests tools`: clean;
- `python tools/check_imports.py`: clean.

The scheduled jobs install only `requirements.txt` (`quote-recorder-nse.yml` explicitly never the Groww SDK), so that
same install covers them.

## Note (one line)

The known limit is stated correctly: until a v3 re-freeze, code the panel job imports must stay 3.11-safe. The panel
job's own green runs are the check, and the next real test is the first `checks` run on `main` after this merge.

### Verdict: PASS for 1b53a43477189090cede0826b6d079e144d5ee41

- A version change only.
- No freeze touched: the one pinned workflow is unchanged and its hash verified.
- The 3.11 exception is shown safe by syntax and by today's green run.
- The full suite passes on a clean 3.13 install.
- **Merge check:** the first `checks` run on `main` after the merge must be green. That also completes M1's merge check
  (judge 129 addendum 2).

## Addendum 1 (15 Oct 2026): merge check, 7d98370505e03f212913be433d365dce96245794

| Check | Result |
|---|---|
| Recomputed merge equals the merge commit | **MET.** `git merge-tree --write-tree 7bedcfb 6b37b0e` gives 35ee3d5…, which equals 7d98370's tree. 6b37b0e contains 1b53a43 |
| Branch files identical | **MET.** `.github/workflows/` at 7d98370, and still at c791051, equals 1b53a43 byte for byte |
| CI on `main` | **MET.** `checks` run 38743169675 on c791051 succeeded, a full run of about 9 minutes; 38743349971 (8aca45d) and 38743424608 (73b488a) also succeeded. Every tree contains 7d98370 |

**Note: green CI needed one more lane-2 change after this merge** (c791051, `story/ci-green-tests`). On 3.13 in CI, two
tests failed that pass locally:
- the D3b test, which needs a git identity in CI;
- the A16b verifier test, which read real back-fill rows instead of a temporary folder.

These are test-environment fixes, not code. They are recorded for the day's lane-2 audit.

**Story done.**
