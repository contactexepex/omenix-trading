# Judge 545: FL1-1e, the evening's verdict for today, story/fl1-1e-today-verdict

- **Judge:** E (session_01HkXMVPDEqVsmJZtghFrGzM), lane 1, round 1 of 2
- **Head judged:** 09330c23, merged with main (e356cc73) and MS-P1g's c115ff2b for testing
- **Claims:** docs/stories/FL1-1e-today-verdict.md
- **Verdict: PASS.** It merges first; then the designer's branch, per the orchestrator's order.

## Gates (merged tree a4c6ef8e)
- pytest -n auto: 14602 passed, 0 failed.
- ruff check, ruff format --check, check_imports, check_records: clean.

## The orchestrator's four points (code read, then plants)
1. **No past day as "today":** `result_words` says "today" only when `result.day == today`, otherwise the
   short date. Plant P7 ("today" always) is caught.
2. **The verdict is the verified close against the sealed ranges:**
   - `OwnCheck._forecast` reads `ranges.sealed(...)`, the G13b live record;
   - `_outcome` compares it with q05/q95 and q25/q75, edges included;
   - `VERDICTS` is keyed on `inside_90`, so P3 (keyed on the 50% range) is caught.
   - The close is A4h's record, synced by O9 per file. Any sync problem means no close is read: an older
     copy on disk is never used (P4 caught) and every problem is kept in `why_missing` (P5 caught).
   - "No forecast was issued" cannot hide a read failure: `wiring.py:87-89` stops the whole edition with an
     alert if the forecast files fail to sync. P12 (an unread close said as "no forecast") is caught.
3. **Unchecked is said with its reason:** "today: not checked yet (NSE close not read); result in
   <report>" or "(no forecast was issued for today)", as the line's first item after the index name
   (P1 caught). Friday names Monday's report (P6 caught).
4. **Live and back-tested apart:** "past 30 days (back-tested N): inside “almost certainly” R of 30"
   (P8 caught).

## Other checks
- The gap wording comes from G13b's own records: `targets` counts the current method version, `ok` rows
  only, live or back-fill (P9 and P10 caught). "Made but not scored" stays "(stale)"; P2 is caught.
- The morning's check stays on the official close (P11, setting the morning to provisional, is caught).
  This covers judge 538's F4 at the source.
- The school golden text change is wording only: the title's definition and the record's words. Picture
  hashes and alerts are unchanged.
- No secret, order, channel or schedule change. Every file is under 350 lines.

## Note for the designer's swap (not blocking this branch)
`IndexView.unchecked` holds a code ("close not read" / "no forecast"), not a sentence. At a8ed3186 the
design prints it raw: "⚠ close not read". The owner asked for "what is missing and why", so the swap
should render plain's `UNCHECKED` sentence (with its report name) on the red line. I will check this in
the delta check.

## Plants: 12 planted, 12 caught
