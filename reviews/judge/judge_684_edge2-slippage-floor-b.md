# Judge 684: EDGE2 slippage note, one tick floor (story/edge2-slippage-floor @ a77e9f78a), judge B, round 1 of 2

**PASS (0 blocking, 0 should-fix, 0 minor). Lane 1** (it regenerates a research results file; orchestrator). Follow-up
to my CP1 m5 (judge 681.1). I did not read any other judge.

| Check | Result | My evidence |
|---|---|---|
| One tick floor, MS-SIM-b's | MET | `half_spread` returns `relative_half_spread(quote) × quote.mid`. The local `max(gap/2, TICK/2)` and the `TICK` import are gone. Algebra: `max(gap/2, TICK/2)/mid × mid`, the same value up to float rounding |
| NSE rows unchanged in meaning | MET | Before: `valid and bid > 0 and ask >= bid`. Now a `SlotQuote(bid, ask, None, None, None, valid, sizes_measured=False)`, so `two_sided` = `valid and bid and ask`, and `relative_half_spread` refuses `ask < bid`. These are the same set of quotes for any non-negative price. Sizes are still not required (`sizes_measured=False`, as before) |
| Results file: float noise only | MET | Recursive numeric diff of `summary.json`, main against the branch: **59 numbers changed, largest relative change 1.11e-15**; no key, list length, string or count changed |
| Reproducible | MET | I re-ran `python research/edge2/slippage.py` on a trial merge with main (verified captures through `CaptureReader`, read-only). It reports 3,966 Groww quotes, 916 NSE quotes and 5 skip lines. Its output is **byte-identical** to the committed `summary.json` (empty `git status`) |
| Frozen protocols, ledger, held-out data | MET | The branch changes only `research/edge2/slippage.py` and its `summary.json`. No `research/ledger.csv`, `PROTOCOL`, `FREEZE` or `research/evaluation/` file is touched. The script reads only the 13-23 Oct 15:00 captures and NSE's public-chain CSVs, holds no trial and reads no held-out set (no ledger row names it) |
| Full gates on a trial merge with main | MET | ruff (fno, tests, tools and the script), format (2,747), imports (2,909), record scan (9,544), numbers clean; **17,570 passed, 1 skipped, 13 xfailed** |

**Note, not a finding:** no test covers `slippage.py`; it is a descriptive script, and before and after this change
its output is checked only by regenerating `summary.json`. That check is what I ran above.
