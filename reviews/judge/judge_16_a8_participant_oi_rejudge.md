# Judge 16: story A8 re-judged (round 2)

**Verdict: FAIL, pending only.** Nothing is left for the builder. Judge 15's should-fix finding is ACCEPTED as fixed,
and I verified it on the real data.

Two criteria still wait on things outside the builder's hands:
- **Criterion 1 (Drive coverage):** waits on the owner's Drive upload route.
- **Criterion 3 (measured release rule):** needs 20 bracketed days of release times.

There is one new minor finding.

**What was judged:** trading `main` with fix commit 8681d7e, and the "Judge 15" section of
`reviews/claude/response_40_2026-10-13-a8-participant-oi.md`. I read in full `fno/research_data/last_written.py` (28
lines) and `LastWriteBoundRule` in `availability.py`.

## Checks run by the judge

```
$ python -m pytest -q                                          534 passed
$ python -m pytest -q tests/research_data/test_participant_oi_availability.py tests/research_data/test_participant_oi_cli.py   16 passed
$ python -m fno participant-oi rule
rule: next session at 15:00 IST (the default until release times are measured); no earlier than each file's recorded last write (1929 days); measured days: 0 of 20
```

I also ran my own count through the wired rule (`build_participant_oi_rule`), comparing it with the plain
next-session rule:

```
held back 105 of 1929                      (95 of them in 2019; the rest unchanged)
2024-01-15 -> 2025-01-16 15:00 IST         (rewritten 15 Jan 2025 13:30 GMT = 19:00 IST, so the next decision)
2026-10-13 (no recorded write yet) -> 2026-10-14 15:00 IST   (default rule)
```

## Judge 15's findings: decisions

| # | Finding | Builder's fix | Judge's evidence | Decision |
|---|---|---|---|---|
| 1 | Should fix: rewritten files were used at the default time without a flag | `LastWriteBoundRule` sets the first usable time to max(rule time, the first decision at or after Last-Modified + 30 min). It wraps any rule, so it also applies once the measured rule is in force. The recorder stores Last-Modified and SHA-256 at first sight; `recheck_recent` logs `rewritten`; `watch` exits 1 on REWRITTEN | My count above holds back exactly the 105 rewritten days, and the 1,824 others are unchanged. The 15 Jan 2024 example gives 16 Jan 2025 15:00, which I checked by hand from the live header in judge 15. Tests pass. **Bounding rather than refusing is correct:** the current bytes really are known from their write time on, and an earlier decision falls back to an older usable file or gets none. | ACCEPTED |
| 2 | Pending: Drive half of criterion 1 | Waits on the upload route | Unchanged | Still pending |
| 3 | Pending: measured half of criterion 3 | Waits on 20 bracketed days | Unchanged | Still pending |
| 4 | Minor: 96753c5 has no trailer | Not rewritten, because it is shared history; later merges carry the trailer | That is the right call: never rewrite shared `main` | ACCEPTED |
| 5 | Minor: the 15:00 decision time is assumed | One constant; `describe()` names the time | The `rule` output above names "15:00 IST" | ACCEPTED |

## Engineering standards

- `LastWriteBoundRule` is a decorator over the `AvailabilityRule` interface, so it adds behaviour without changing the
  existing rules.
- `last_written.py` is small and single-purpose.
- The margin reuses the existing `SAFETY_MARGIN`, so there is one constant (DRY).
- Every file is under 350 lines.
- No breach found.

## New finding (minor)

1. **Minor:** `recheck_recent` re-reads only the last 5 seen files.
   - A rewrite months later is not caught by the daily recorder. The 15 Jan 2024 file, for example, was rewritten a
     year later.
   - The historical table catches such rewrites only up to its date (13 Oct 2026).
   - Expected: a periodic Last-Modified sweep of all files (one HEAD request each, about 1,900 requests, for example
     monthly), appended to the records `latest_writes` reads, so the bound also covers later rewrites.
