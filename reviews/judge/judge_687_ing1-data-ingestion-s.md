# Judge 687: ING1 data ingestion as a separate part (design), judge S (2 of 2)

Branch `story/ing1-data-ingestion` at `6988fc3e2`. **FAIL, lane 1** (2 blocking, 4 should fix, 3 minor). Design only:
I read the text and checked its facts against the code and the git history.

## Criteria

| # | Criterion | Verdict | Evidence |
|---|---|---|---|
| 1 | Inventory matches the code, misses no capture | PARTLY | 27 workflows placed; cited lines right (`constants_operations.py:69-97`, `quote_parts.py:7-8,80-84`, `runner.py:58-76`, `v4_part.py:27-35`); misses B1 |
| 2 | Migration never loses a session's data | NOT MET | finding 2 |
| 3 | No second writer of a write-once record | PARTLY | key and `RawFileConflict` stop it; findings 1 and 3 do not |
| 4 | Reuses O14's retry unchanged | MET | 4.4 matches O14 sections 4 and 5 |
| 5 | Keeps GW1's limits and quiet windows | PARTLY | quiet windows kept; budget wrong (finding 4) |
| 6 | Each step provable on a real session | MET | K10; rehearsal plus a watched first session per Class G step |
| 7 | Two judges per removal; under 500 lines; links | MET | 6.2; 479 lines |

## Findings

1. **Blocking: the system already fetches NSE files and archives them in Drive; the design misses it.**
   `RawFileLibrary.get` falls back to NSE and `put`s the file (`storage/raw_library.py:52-60`, `storage/wiring.py:151-157`).
   Used by `desk/wiring.py:45` (ExitDesk settlement), `forecast_v4_rules/pack_wiring.py:93,167`,
   `scoreboard/wiring.py:116`, `role_value/wiring.py:64`, `checks/wiring.py:126`, `itm_chance/wiring.py:51` and
   `forecast_lab/page_wiring.py:76`. Also missed: `lab release-check` polls NSE (`forecast_lab/wiring.py:75-87`).
   Summary item 6 ("the only place") is false, and K2 (Groww names only) passes all of these. Fix: list them, widen K2,
   move each system reader to `StoredFilesLibrary` plus the 4.5 not-ready stop (desk: two judges), and host
   `release-check`.
2. **Blocking: a Class G swap day can lose the session.** Once the key says `job`, the old path refuses (K3). If the new
   routine does not start, the only guard is a witness "2 minutes before the window" (6.3) on Actions' cron, which 4.3
   itself says is 4-5 h late (`recorder-watch.yml:5`: "best effort"). The hand-run reading is "reasoning only". Fix:
   keep both hosts scheduled and let a dataset-day git claim decide (first push wins, `intraday/claims.py:1-7`): the
   standby takes over only with no claim by T-x. Prove it with a planted no-start in rehearsal; put the hand-run reading
   to the owner.
3. **Should fix: the flip goes by wall clock.** It lands 16:40-08:00 and is read when a path starts (6.1), but late
   overnight Actions runs (03:30, 06:00, 07:41) can span it, so two owners of one day are possible. Fix: key the owner
   by session date (`job_from: <day>`).
4. **Should fix: the Groww budget is wrong.** 21+5+1+4+2 = 33, not 38; 38 needs the rerun's 10
   (`groww_sign_in.py:8-11`). O14 already reaches 129 (`O14-retry-policy.md:132-133`), so K7's cap of 130 leaves about
   one try, and I10's C9 alone needs 3. "The school's 4 slots" may be C20's slots, counted twice. Fix: line up with O14,
   count tries, state I10's room, or ask the owner.
5. **Should fix: the import inventory is short** ("three places"). Also found: `capture_probes/wiring.py:79-81`
   imports `school`; `storage/receipt_publisher.py:10` imports `research_engine`; `storage/content_checks.py:9-12` and
   `filings/wiring.py:12` import `market_read_models`; `record_store/wiring.py:64` imports `daily.alerts`. I1's
   allow-list would be wrong on its first run. `boundary.py` must also place `storage` and `providers`.
6. **Should fix: C5's double writer is already settled by git.** The workflow committed only on 14 and 15 Oct
   (`13a6c8c01`, `fe695efcb`, at 19:35 and 19:13 IST); the daily run committed every session since 16 Oct (`2ec7c6e6d`
   to `d5a247530`). M15 is strong evidence; drop I4's 5-session measurement.
7. **Minor:** the gap list omits C6 (no indices or weeklies row in `health/expectations.py:68-96`).
8. **Minor:** I1 changes which path captures, so it is lane 1 (as section 7 item 7 says), not lane 2.
9. **Minor:** `fno/alerts/` already exists: say "add `reported.py` to it".

## Plants

None. A design has no code to mutate.

## Notes

- To claim my number I printed the tail of `reviews/judge/README.md`, which showed Judge R's row 686. I had already
  formed my findings, did not use it, and checked none of R's points.
