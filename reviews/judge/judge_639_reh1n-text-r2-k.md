# Judge 639: REH1n story text round 2, `story/reh1n-new-quote-parts` at 5fa97694c (round 2 of 2, judge K, judge 2 of 2)

**FAIL, lane 1** (what `fno/quotes/` takes as a good result; what a rehearsal posts), text only. 1 should-fix, 1 note.
Judged by reading. The change against main is `docs/stories/REH1-rehearsal-mode.md` alone (+91 lines). I did not
coordinate with the 635 session.

**Doc-reading tests** on 5fa97694c, Slack token set:
- Runs 2-5: 932 passed, 13 xfailed.
- Run 1 had 1 failure, under load (109 s against 46-50 s). Its name did not print, and the four reruns did not reproduce it.
- The diff is one Markdown file, so a test reading it would fail every time; this failure is not REH1n's.
- No post in #fno-desk, #fno-forecast or #fno-intraday from 00:11 UTC on.

## Checks

| Asked | Verdict | Own evidence |
|---|---|---|
| SF1: a marker OR a sidecar on or before D | MET | Design 1 states it, with the reason (A4 writes each attempt's sidecar at once and the marker later). N3 adds the case "only one sidecar on D, no marker", which stays "window closed", alerted, exit 1, with the plant "the rule reading markers only" |
| m2: steps with their own live key | MET | the gap list's last row: each is its own `LiveFrom` step, `not_live` before its key's date, and outside REH1n's scope |
| m3: the register row | MET | `WORK_REGISTER.md` on main, line 110: REH1n's row names `fno/quotes/indices.py`, `fno/quotes/cli.py`, `recorded_quotes.py` and `exercised_line.py`, and that the orchestrator is told in place of the gone A4c/A4f owner |
| `recorder.py`, `constants.py`, `window.py` byte-identical | MET | `git diff --quiet origin/main 5fa97694c` is empty for all three; the branch's own diff is the one story file |
| The one wrong case, restated | **PARTLY** (SF1) | see below |

## Findings

1. **Should fix: the wrong case is wider than "a crash before the first attempt's sidecar".**
   - The rule reads `mode.record`: the checkout's committed record (`fno/rehearsal/mode.py:32`). An attempt's sidecar reaches it only when its part ends and the run's one thread commits it (`fno/daily/quote_parts.py:1-8`), not when A4 writes it.
   - So on a capture's first day, the record can also hold nothing for a part that *did* run. Three ways, all in today's code:
     - **a hung part:** `HUNG` = "still running at HH:MM, after its window: stopped, nothing of it committed" (`quote_parts.py:48`);
     - **a part never committed:** "NOT committed" with no hand fix, or "committed, NOT pushed" when no later push carries it (lines 33-35);
     - **a lost container:** the container dies mid-part, and the local sidecars go with it.
   - Each reads as "not a part of the day" on that first day, never a failure. Monday is v4's first live day, so these are its exposures too. A v4 part that hangs past 14:40 is the likeliest of them.
   - **Fix (text):** state the case as "no sidecar or marker of the stem reached the record by D", and name the three paths.
   - Optional closer (reasoning only): for a stem that is a part of its own (the `v4` dataset), the real `journal/runs/<D>.json` already records each part with `started_at` (for example 23 Oct's `quotes_done.result.parts`). A part listed there is a part of D, so its empty record is a failure. A stem inside a part (the weekly in `indices`) has no such witness, so for it the text is the fix.

## Note

- "Never reads a day after D" goes by the file's day, not by when it was committed. A sidecar dated D but committed on D+1 (a hand fix) counts. That makes the stem a part (stricter), never "not a part", so it hides no failure. REH1p's visibility rule is the right place if the dates should also be commit times.

## For round 2's close

This is the last round, so the owner or the orchestrator decides. SF1 needs only the restated wrong case: one paragraph, no code. With it, I would pass the text.

## Addendum 1: round 3 (granted by the owner, 25 Oct), `story/reh1n-new-quote-parts` at 80b522bf6 (judge K)

**PASS, lane 1, text only.** 1 minor. The branch's change against main is `docs/stories/REH1-rehearsal-mode.md` alone.
Doc-reading tests on 80b522bf6, Slack token set: 963 passed, 13 xfailed. No post in the three channels from 08:34 UTC
on. I did not coordinate with the 635 session. The file's size (over 2,000 lines) is DOC1's item, as the orchestrator
says.

| Checked | Verdict | Own evidence |
|---|---|---|
| SF1: the wrong case was wider than stated | fixed | "The wrong cases" now names my three paths: hung (`HUNG`), not committed or not pushed, a lost container. Each is closed or named below |
| Design 1b's facts | true | `journal/runs/<D>.json`'s `steps.quotes.inputs.parts` is `['nifty', 'nse', 'indices']` on 21 and 23 Oct. 23 Oct's "Desk run 2026-10-23 step quotes" was committed at 08:37:14 UTC (14:07:14 IST), the run's first step, before any part. `QuotePart.canonicals` holds one (dataset, stem) for `nifty`, for `nse` (NSE's `nifty`) and for `v4` (`v4_part.py:33`), and four for `indices` (its three indices and the weekly). So the plan can witness the single-stem parts only, as stated, and 21 Oct's listed `indices` without the weekly shows why it must not count for a multi-stem part |
| The paths, one by one | correct | the plan's 14:07 push precedes every capture, so a hung, uncommitted or lost single-stem part is still named in it. The leftovers are named: residual 1 (no push of D's run log at all: the whole day is missing from the record, loudly) and residual 2 (a new stem inside `indices` on its first day) |
| N3 | covers it | a planted D run log that lists `v4` with no `v4` sidecar or marker stays a failure. The plants: the log not read; read from the rehearsal's 14:05 clone; a multi-stem listing counted |
| Gap list | done | its own row, with the residuals named |

**m1 (minor):** 1b reads D's run log from the record's `main`, beyond the rehearsal's own 14:05 clone. That is safe in
value, because the `quotes` step's entry is written once at 14:07 on D. But REH1p's point-in-time rule shows a file only
once its commit time is at or before the replay clock. Say that the plan is read under the same rule. The quote parts
ask from 14:29 on, after the 14:07 commit, so the outcome does not change.
