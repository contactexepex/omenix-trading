# Judge 241: BG1 stop-rule alert names the calendar fallback: `story/bg1-fallback-alert` 0409a53e (lane 1, an alert)

Judge B. F8/BG1 builder. Source: A14c's A7 audit (response 239 item 5) and the orchestrator's rule of 16 Oct: every A7
user fails loudly and by name, with no silent fallback.

## Checks
- **The gap is real (code read).** `_last_session` falls back to the last weekday when the calendar has no rows for
  the review year (2027 today), and records the note in `review.notes`. The printed lines showed it, but the #fno-desk
  alert (`review_reached`, sent from `budget/cli.py:100`) dropped it.
- **The fix.** The alert appends "; the date is not confirmed: <notes>", naming the calendar and the missing year. A
  confirmed date's alert is byte-for-byte unchanged, which the test checks.
- **Loud, named, nothing invented.** The fallback date is labelled as not confirmed, never presented as NSE's. The
  builder's reason for posting with the note rather than refusing is right: the last weekday is on or after the true
  last session (a holiday can only move the true date earlier), so the alert can be late, never early, and refusing
  would silently hold the review.
- **No double post introduced.** The posting path (`_stop_rule`, one `send` per run) is unchanged, and only the text
  changes.
- **My plant** (dropping the appended note) fails the new test.
- **Gates.** `-n auto`: **6,959 passed, 0 failed**. Ruff is clean. `tests/budget`: 133 passed.

**Verdict: PASS for 0409a53e.**
