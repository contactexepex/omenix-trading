# Judge 215: LM1 story text, the position monitor, alert only (quality rule 1; judge E)

Date: 16 Oct 2026. Branch `story/lm1-monitor` at **8145355d** (`docs/stories/LM1-position-monitor.md`, response
217, register and plan rows). Text only.

## Verdict: PASS (story text); 3 notes

| Check | Status | Evidence (mine) |
|---|---|---|
| Alert only, no trade path | MET | No entry, exit, order or fill path. Criterion 1's import test is design 4.2's own "no entry code path" check. An intraday exit-rule hit is one information alert with no EXIT or CLOSE word and no price, and it never sets E8's T |
| Real scenario, no premature code | MET | No open paper or shadow position and an empty registry (the text; consistent with `journal/` and the registry on `main`). The code starts only with the first position and A16 past its trial (REPLAN: "a monitor with nothing to watch adds nothing") |
| Every number sourced | MET | 50/80% loss, NIFTY within 0.5% of a short strike, 1.5% move, VIX +10%, 30 minutes stale, the expiry window: all are design 4.2's checks ("thresholds are proposals, owner decides"), kept as an open owner slot in `config.yaml` `monitor`. The limits (one per condition per position per hour; a summary after 10 DANGER) and the first-line and 60-minute rules are 6.5's |
| Design 4.2 covered | MET | Every check, output and metric (latency, missed alerts through the weekly replay, false alarms, uptime from the mark rows), the interfaces (`PositionMonitor`, `MonitorCheck`, `ExitRule`, `AlertSender`, A16's source) and the failure modes (heartbeat, staleness first, the storm limit, no entry path). VIX and the intraday weather are honest "waits" with named owners; the card's uptime line is asked of its builder; `intraday_exits` is LM2 |
| Reuse, no second copy | MET | `heartbeat_state`, `SILENT_AFTER` (30 min) and the 09:45-15:45 window exist (`fno/intraday/heartbeat.py:17-18,68`). `IntradayRecorder` (`fno/intraday/recorder.py:69`), A16's 6% band (`groww_source.py:23`), E4's `ExitRule` (`fno/desk/exit_rules.py:29`), E2c's `build_private_files` (`fno/desk/wiring.py:65`) and O1's `ReportedAlerts` (`story/o1-daily-run`, `fno/daily/alerts.py:14`) are all real. No second sender or silence checker |
| Privacy | MET | Alert records name positions and marks, so they go to Drive through `PrivateFiles`. The public rows carry counts and times only; criterion 7 scans them |
| Not twice | MET | The public mark row is the one-handling marker (Drive up or down, and after it recovers); one writer per file; the write order keeps a crash visible |
| Checked against O1, E6 and E8 | MET | O1: the alert path and the 15:15 boundary come from the timetable, never typed. E8: distinct prefix ("F&O monitor:" vs "F&O paper desk <book>: EXIT"), and T only from E8's own post. E6: no overlap, since the monitor pauses nothing |

## Notes (not blocking)

1. **E8 is a dependency.** `ExitTiming` and `AlertThenWait` (`fno/desk/exit_timing.py`) exist only on
   `story/e8-code-part1`, not on `main`. Add E8 to Depends.
2. **Market-wide alerts per position.** The big move, VIX and staleness conditions are about the market, not one
   position. "One per condition per position per hour" (6.5's wording) would send N copies of the same NIFTY 1.5%
   DANGER when N positions are open. Make market-level conditions one alert per hour, naming the positions affected.
   Owner's call if it wants 6.5's literal reading.
3. **"No price" in criterion 6** means no contract price or mark. A NIFTY move in percent, and the index level for the
   strike-distance check, must be allowed. Write the test so it does not forbid them.

**Verdict: PASS for 8145355d** (story text). Code waits for the first open position and A16 past its trial, as the
text says.
