# Judge 415: unsent alerts print their text; never kept in the run record (story/a4-unsent-alert-text at cac35232)

**Verdict: PASS. Lane 1 (Slack, the daily run's record). The builder may merge after the full gates pass on the exact
pushed tree.**

| Part | Result | Evidence |
|---|---|---|
| 1. The 3 pm quote commands print an unsent alert with its text | MET | `cmd_quotes` wraps its sender once in O1's `ReportedAlerts`; six `print(alerts.send(...))` become `announce()` (prints only a sent outcome), covering record, `--source nse`, `--window` and record-indices |
| 2. The same fix in A16 (`intraday/cli.py`, 3 sites, the dry-run sender included) and A12 (`filings/runs_cli.py`, 2 sites) | MET | `announce` moved to `fno/alerts/output.py` (one copy) |
| 3. **Privacy:** an unsent alert's text never reaches the committed run record | MET | `ChildProcess.lines()` drops `UNSENT` lines; `report()` still relays them to the routine. A raw-file alert's Drive error (which can hold the private folder ID) stays out of `journal/runs/<date>.json` |

**Planted mutations, all caught:**
- unsent lines kept in `lines()`: 1 failed;
- `announce` printing every outcome: 6 failed;
- `ReportedAlerts` removed from `cmd_quotes`: 3 failed.

**Gates:**
- tests/alerts, quotes, daily, intraday and filings: 491 passed.
- Full suite on main plus main-green: **8148 passed, 18 xfailed, 0 failed**.
- ruff and check_imports are clean.

## Interaction with O2 (judge 412), checked on a merge of both branches
tests/e2e plus tests/daily give 87 passed and 1 xfailed, so **nothing turns red.** The e2e children are scripted
(`ScriptedProcess`), so this change does not reach them, and G2's strict xfail stays xfail (see judge 412 addendum 1).

There is one production effect the tests do not see. O2's `quote_parts` decides "the part alerted itself" by finding
"alert NOT sent" in `lines()`. After this change that line is never in `lines()`, so on a Slack-down day a part whose
own alert was unsent also gets O1's `PART_NOT_OK`. That is two unsent lines for one failure, against O2's
one-alert-per-failure criterion; with Slack up there is no effect.

**For O2 round 4:** detect the part's own alert from what `ChildProcess` relayed, for example by counting relayed unsent
lines, not from `lines()`. Add a test with the real `ChildProcess`. This is a note on O2, not a should-fix here.

## Out of scope (stated in the claims)
Other bare `print(alerts.send(...))` sites (for example `librarian_cli`) are left for after the phase-1 freeze.
