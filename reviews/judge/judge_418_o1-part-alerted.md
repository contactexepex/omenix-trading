# Judge 418: O1 fix, a part's own alert read from its whole output (story/o1-part-alerted at 30237369)

**Verdict: PASS. Lane 1. Merge soon: the regression is live on main since 1f005e5a** (the A4 fix that strips unsent
lines from `lines()`, as judge 412 addendum 1 note 2 and judge 415 predicted).

| Check | Result | Evidence |
|---|---|---|
| The root cause | MET | `QuoteParts._finish` decided "the part alerted itself" from `lines()`, which no longer holds "alert NOT sent", so on a Slack-down day a part whose own alert went unsent also got `PART_NOT_OK`: two unsent lines for one failure |
| The fix sits on the interface, not in a patch | MET | `Process.alerted()` (abstract), `ChildProcess.alerted()` reads the whole output via `alerted_in`, `ALERT_OUTCOMES = (SENT, UNSENT)`; `_finish` takes it |
| Privacy is kept | MET | `lines()` still drops unsent lines; the test checks the folder ID never appears in the kept lines |
| A test with the real `ChildProcess` | MET | `tests/daily/test_part_alerted.py`: unsent, sent and silent, exactly one alert each |
| Planted mutation | caught | `alerted()` reading `lines()` instead of the whole output: 1 failed |
| Gates on a trial merge with main | MET | 8660 passed, 17 xfailed, 0 failed; ruff and check_imports clean |

**Note (not should-fix):** `alerted()` is true for *any* own-alert line, so a part that posted an unrelated alert (for
example "no same-day trades") and then failed for another reason gets no `PART_NOT_OK`. The old rule behaved the same,
and the part's own alert still names it; worth a test when A4's alerts change.

## Addendum 1: the one version is story/a4-alerted-flag at ebc76665 (30237369 withdrawn)
**Verdict: PASS. Lane 1. This is the head to merge, soon (the regression is live).** The O1/O2 builder withdrew
30237369 in favour of this one and agrees as the files' owner, so there is one version.

**Same root fix as above:**
- `Process.alerted()` is abstract, and `ChildProcess` reads the whole output through one rule, `printed_an_alert`
  (`OWN_ALERT = SENT or "alert NOT sent"`);
- `_finish` takes it, and `lines()` still drops unsent text.

**What this version adds:**
- the fakes (`FakeProcess`, e2e `ScriptedProcess`) use the same rule, and their `lines()` drop unsent lines as
  `ChildProcess` does;
- O2's strict G2 xfail is removed, because the e2e NIFTY child is wired with `ReportedAlerts` as `cmd_quotes` is;
- the O1 builder's real-`ChildProcess` three-case test is kept.

**Planted mutations, both caught:**
- `alerted()` reading `lines()`: 1 failed;
- the e2e NIFTY child without `ReportedAlerts`: 1 failed, so the slack-down outage test bites.

**Gates on a trial merge with main:** 8661 passed, 16 xfailed, 0 failed; ruff and check_imports clean.

**Note:** the e2e harness mirrors `cmd_quotes`' wiring rather than calling `cmd_quotes`. If `cmd_quotes` ever stops
wrapping in `ReportedAlerts`, judge 415's own `cmd_quotes` tests catch it (my plant M3 there), so the pair is covered.

## Addendum 2: which head merges
The two builders' messages crossed. **Both heads pass:** 30237369 in the main verdict above, and ebc76665 in addendum 1.
They share the same root fix, so either may merge.

The builders now agree on this order:
1. 30237369 merges first (the orchestrator merges it; the O1 builder's session cannot);
2. the A4 builder then sends ebc76665's extras rebased on it (the fakes' `lines()`, `ReportedAlerts` in the e2e NIFTY
   child, G2's xfail removed). I judge only that small diff. Addendum 1's checks of those extras stand: the plant on
   the e2e NIFTY child was caught.

Never merge both as they are: they would conflict on the same lines of `processes.py` and `quote_parts.py`.

## Addendum 3: the extras alone (story/a4-alerted-extras at c8052a40, on main 8ced7208)
**Verdict: PASS. Tests only (4 files, +7 -14, no product code). It may merge after the full gates pass on the exact
pushed tree.**

- The test fakes' `lines()` (`FakeProcess`, e2e `ScriptedProcess`) drop unsent lines, as `ChildProcess` does;
  `alerted()` stays main's `alerted_in`.
- The e2e NIFTY child is wired with `ReportedAlerts`, as `cmd_quotes` is.
- G2's strict xfail is removed, so slack-down runs for real.

**Planted mutation:** the e2e NIFTY child without `ReportedAlerts` makes `test_outages.py` fail (1 failed), so the
slack-down case bites.

**Checks on a trial merge with main:** tests/e2e plus tests/daily give 91 passed; ruff is clean. The builder reports the
full suite at 8,661 passed and 0 failed.
