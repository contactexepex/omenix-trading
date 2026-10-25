# Judge 449: FL1-1d-2 code, sections, key points and levels (story/fl1-1d2-sections at 1edc0921)

**Verdict: PASS (lane 1), with 2 minor findings. The builder may merge: pull, one full run on the merged tree, push.**
Both editions stay off (`forecast_lab.live_from` null).

The builder named 6eeeeef5. The branch then moved to 1edc0921: 2984ac98 sends a late morning's own alerts (judge
444.1's minor), and a merge of `main` brings in FL1-1d-1 (merged at 71165115). I judged 1edc0921.

## Checked myself
- **Gates:** on 1edc0921 merged with today's `main` (no conflicts), one run:
  - 9,337 passed, 16 xfailed;
  - `ruff check` clean; 1,749 files formatted;
  - imports clean; record scan clean (7,476 files).

  Strong evidence.
- **11 planted mutations, all caught** (`tests/forecast_lab`):
  - an A17 "behind" reading shown as current;
  - Brent's limit at 30 days;
  - the evening VIX shown;
  - a missing OI wall shown as 0;
  - flows taken from any day;
  - GIFT's A22 status ignored;
  - US cues counted "the miss's way" in any direction;
  - the "Built from" point dropped;
  - a failed Section not alerted;
  - the morning's own check even after G13b scored the day;
  - up to 6 key points.
- **The as-of rules are as judged in 438.1:**
  - A17 is read only through its own reader at `OPEN`, with `live_only`;
  - Brent is "last print" up to 10 days old, with its date;
  - VIX is shown in the morning only, from the official file (the list's 15.70 against the official 15.68 is the
    stated reason);
  - flags, levels and flows are taken from the day only;
  - GIFT comes from A22b's verified early file, shown only on `ok` or `late`, and named when missing.
- **Never a crash.** Every Section read and the levels table sit inside `try`. A read error becomes a `failed`
  SectionView, named in the system line and alerted once with the report (`maker.py`). Strong evidence: code plus
  W9.
- **Privacy.** The S&P 500 and Nasdaq-100 go to Slack and the Drive record only. The test fixtures use made-up levels
  (100.0, 101.0).
- **Release logs.** They sit under `research/data/forecast_lab/release/`, as A8's do under
  `research/data/participant_oi/`. The check is read-only, has no schedule, and does not touch A8's workflow.
- **The routine steps call other owners' commands unchanged.** These are A9's `data-librarian` and P8's
  `data-snapshot`, as the orchestrator assigned on 22 Oct. "not published by the source" is the only line that means
  "not out yet", and `test_librarian_words.py` pins it (my note in 438).
- **Every difference from the text is listed under "FL1-1d-2 as built", with its decider.** I checked items 1-8
  against the code: the morning's own result on the official close (orchestrator), release check scope, "the miss's
  way" for US equities only, no evening VIX, GIFT, the levels, and the librarian words.

## Minor
1. **USD/INR in the evening.** The 438.1 table says "the rate dated D, else the latest on or before the previous
   session". `GlobalCueSection` reads every cue at the 09:15 cutoff, so the evening never shows D's RBI rate
   (published about 13:30). This is safe, never stale, but it differs from the text and is not in the as-built list.
   Add it there, or read the evening at the edition's own time.
2. **The evening's key points when the forecast was right.** `evening_points` returns at most 2 context cues and can
   return none, while the owner's rule is 2-4 points. When fewer than 2 exist, say plainly that there was nothing
   notable: "no notable moves in our data".
