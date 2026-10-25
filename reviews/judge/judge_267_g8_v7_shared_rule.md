# Judge 267: G8's V7 outcome from G7's shared rule (story/g8-v7-shared-rule at d3deddd1)

Judge B, 16 Oct 2026. Lane 1 (scoring), before the v4 freeze. Builder: A16/G8 (session 01VK88Lx). Claims are in the
builder's message: V7 now comes from G7's `series.vix_up_outcomes`, as V6 does, with byte-identical outcomes.

**Verdict: PASS.**

| Item | Result | Evidence |
|---|---|---|
| G8 no longer forms V7 itself | MET | `outcomes.py` drops `vix[i + horizon] > vix[i]`; `_binary` reads V6a, V6b and V7 through `OutcomeSeries`; `G7Series.vix_up_outcomes` maps G7's rule at `HORIZON_SESSIONS[V7]` |
| Same outcomes on real data | MET, reproduced | my own script on `origin/main` and on d3deddd1 dumps every V7 outcome from the committed warm-up closes: 2,406 outcomes each, byte-identical |
| The new test is a real reference | MET | it compares the live adapter with `VIX(t+5) > VIX(t)` built by hand over more than 1,500 days. My plant (horizon 4 in the adapter) fails 1 test |
| G7's test fake | OK | `CommittedSeries.vix_up_outcomes` returns G8's former rule, so G7's test still compares G7's rule with an independent reference, not with itself. The builder told R2/G7 |
| Freeze | OK | `fno/forecast_scoring/v4/` is byte-checked only from the v4 freeze, which has not been made |

## Note only (for R2/G7, not this diff)

G7's `vix_closes` leaves out a row with no VIX close, and `vix_up_outcomes` zips the list with itself shifted by 5.
Across a missing VIX close, "5 sessions later" is then 6 sessions later, silently. It cannot bite G8 today:
`G7Series.sessions()` still does `vix[c.day]` for every regular close, so a missing VIX raises `KeyError` for every
question (loud), as G8's old rule did. G7's own forecasters use the same rule, so R2/G7 may want it to refuse or void
across a gap rather than slip. No missing VIX close exists in the committed history (the 2,406 outcomes agree).

## Gates (run by me on d3deddd1)

`env -u FNO_SLACK_BOT_TOKEN python -m pytest -q -n auto -p no:cacheprovider`: 7,265 passed. `ruff check`: clean.
`ruff format --check`: 1,294 files already formatted. `check_imports`: clean.
