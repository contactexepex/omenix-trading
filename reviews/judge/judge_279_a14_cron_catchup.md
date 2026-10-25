# Judge 279: A14 nse-margins catch-up crons (story/a14-cron-catchup at 088372b3)

**Verdict: PASS. Lane 1 (a schedule). The builder may merge after the full gates pass on the exact pushed tree.**

## The change
`.github/workflows/nse-margins.yml` gets two more slots, 05:00 IST (`30 23 * * *`) and 06:30 IST (`0 1 * * *`), between
the 03:30 main run and the 07:45 retry. A new test checks that every slot, on time, falls on the session's IST date
before 09:15 and that `due_session` gives that day. WORK_REGISTER has one row, with the same builder as A14's other rows.

## Criteria
| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | A run with nothing new writes nothing | MET | `job.run`: no pending days gives "nothing new up to <day>", exit 0; `concurrency: nse-margins`, no cancel |
| 2 | Every slot gives the right IST day | MET | new test; `due_session` uses IST time |
| 3 | A late run cannot write a wrong row | MET | the 09:00 IST cutoff applies to NSE's file (`span.created`), not to the run, so any start time is safe |
| 4 | Gates on a trial merge with main | MET | 7706 passed; ruff, check_imports and format clean |

## Planted mutations (workflow file, all reverted)
| Mutation | Caught |
|---|---|
| 06:30 slot moved to 09:30 IST (after the open) | yes |
| 05:00 slot moved to 23:30 IST of the previous day (the wrong session) | yes |
| A slot deleted | yes (count of 4) |
| 05:00 slot moved to 00:00 IST (still the right day, before the open) | passes, correctly: not a bug |

## Notes (not should-fix)
1. **The evidence for "GitHub dropped a slot" is weaker than the comment says.** I checked the GitHub Actions runs:
   - On the morning of 16 Oct the schedule in force was e2b4c783's: 07:45 and 08:30 IST (02:15 and 03:00 UTC).
   - The 03:30 IST slot only reached main at 06:08 UTC (3c333417).
   - The only scheduled run, 38865754022, started at 07:12 UTC, which is **12:42 IST, 3 h 27 min after the open**.
   - The workflow file was also edited at 05:38 and 06:08 UTC, while those slots were waiting. A change to the file
     may be why a queued scheduled event was lost, rather than GitHub dropping it at random.

   The extra slots are harmless either way, so this does not block. The comment should still say "one of two never
   started", not that GitHub drops slots as a known behaviour.
2. **The catch-ups cover a dropped slot, not lateness.** If GitHub starts them 4-5 h late, as it did on 14-16 Oct, they
   land at about 10:00 and 11:30 IST, after the open. Only the 03:30 slot lands before 09:15 even 5 h late. Monday
   19 Oct is the first live day of the 03:30 slot: worth a look at its start time.
3. **A problem that lasts all morning (Drive down, NSE's file missing) now posts up to 4 alerts that day instead of 2.**
   Each run that still has a failing pending day alerts. The later lines carry information ("still failing"), so I
   accept it, but O10's one-alert-per-failure rule may later want to merge them.
4. The new comment line is 197 characters long. The file already had lines over 120, and YAML is outside ruff, so this
   is style only.
