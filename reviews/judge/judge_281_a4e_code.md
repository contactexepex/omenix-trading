# Judge 281: A4e code, the named 14:30-14:40 quote window (story/a4e-named-quote-window, code 6a82a96f, tip f2466390)

Judge B, 16 Oct 2026. Lane 1 (the 3 pm recorder; Groww; a v2-recorded file; one line of E2b's commit guard). Text:
judge 278 addendum 2 (merged ac35f980). Claims: `reviews/claude/response_278_a4e-named-quote-window.md`. Builder:
01MKtUHB.

**Verdict: PASS.**

| Criterion | Result | Evidence |
|---|---|---|
| 1 Default unchanged | MET | `DEFAULT_WINDOW` is A4's constants, and the default recorder has no `CaptureLog`, so its sidecar stays A4's. `tools/forecast_live_golden.py`: "live golden cases unchanged: case_a, case_b" (my run); every existing quotes, desk and timetable test passes |
| 2 Named window | MET | `record()` reads `self.window`; no market request after 14:40:00. `CaptureLog.request_allowed` guards the expiry list, each chain and the levels (the builder's self-review gap, fixed), and the quote books stop at `stop_requests_at = window.end`. A request at 14:40:00 is allowed, at 14:40:01 refused; a late answer keeps its real time |
| 3 Separate dataset | MET | `quote-snapshots-v4`; its quote files go to Drive only (A4b's store now takes the dataset). `.gitignore` (`groww/**/*.csv`), the record scan (`research/data/quotes/groww/` + `.csv`) and E2b's `RawQuoteGuard` (now `<quotes>/groww/`) all cover it |
| 4 Clock | MET | A16's `ClockCheck`, one rule (`intraday.wiring.build_clock_check`, moved, not copied), read before the first and after the last request. A failed reading keeps its place as `clock_unchecked`; `clock_status` is the worst |
| 4b Each field's own times | MET | `chains`: per chain call `expiry`, `spot`, `request_sent_at`, `response_received_at`. `levels_requested_at` and `levels_received_at` bracket the one levels call (an upper bound for VIX and futures). After the window, levels are a recorded failure, never raised |
| 5 Refusals before any request | MET | `named_window` raises `ConfigError` for an unknown name, wrong keys, a bad time, start not before end, or a bad wait; `--window` with `--source nse` is refused |
| 6 Size, lint, imports, suite | MET | `recorder.py` 340 lines (counted on the tip) |

**My mutations (real cases, all caught):**
- The window's end check removed: 3 tests fail.
- The expiry list no longer guarded: 1 test fails.
- E2b's guard back on the default dataset only: 1 test fails.
- The named window writing into the default dataset: 3 tests fail.

**Notes only:**
- The `CLAUDE.md` edit lists the new composition root `fno/quotes/window_wiring.py`, as the code rules require.
- The clock check is a network read before the first request, so a 14:30 attempt's first market request lands a
  moment after 14:30:00. That is inside the pack's window and honest.
- Not run live: nothing schedules it yet (O1 and the owner). G10 part (b) builds the pack from this sidecar.

**Gates (run by me on f2466390):** 7,712 passed (`-n auto`, Slack token unset), no failures. `ruff check`: clean.
`ruff format --check`: 1,391 files already formatted. `check_imports`: clean. Live golden: unchanged.

## Addendum 1: code at 9db8b84c

**PASS stands.** The one change since f2466390 is a move: `build_clock_check` goes, unchanged, into its own small
root `fno/intraday/clock_wiring.py`, used by A16's `wiring.py` and by A4e's `window_wiring.py`. CLAUDE.md's root list
names it.

Checked:
- Importing `fno.quotes.window_wiring` no longer loads A16's Groww intraday graph (`fno.intraday.groww_source` is not
  in `sys.modules`; my check).
- The two edited tests keep their intent. A16's composition-root test lists the new root, and A16c's one-server-clock
  test now checks `clock_wiring.py`, which imports `server_clock`, beside the same three modules.

**Gates (run by me on 9db8b84c):** 7,714 passed. `ruff check`: clean. `ruff format --check`: 1,392 files already
formatted. `check_imports`: clean. Live golden: unchanged.
