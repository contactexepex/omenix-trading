# Judge 668: EDGE2 F9, the event IV crush, round 1

Branch `story/edge2-f9-event-crush` at `e3ec093af`. **FAIL**, lane 1 (research records edited by hand, research
code): 2 should-fix, 2 minor. The answer itself, no edge after costs and nothing nominated, reproduces exactly.

## Criteria (the orchestrator's eight points)

| Item | Verdict | Evidence |
|---|---|---|
| (1) Registration first; events fixed from A6; 2021-22 Budgets | MET | Order: registration `739d3a0b6` (02:24), then code `80fdcd342`, freeze `effae5117`, results `e3ec093af`. Protocol, cards and events have not changed since `739d3a0b6`. `f9_events.csv` is A6's 58 scheduled rows of the 3 types at registration, exactly; the 3 off-cycle rows are out. The rule is `announced_on < entry session`: 2021 (announced 30 Jan, entry 29 Jan) and 2022 (31 Jan, 31 Jan) fail it as written, and the result says so |
| (2) Freeze before the run, code hash | MET | `code_hash()` at HEAD = `a255a04c...` = F9_FREEZE; protocol SHA-256 `9536e524...` = F9_FREEZE; no study file changed after `80fdcd342`. The pre-freeze inputs check read entry closes but changed no code |
| (3) Costs and the Rs 820 bar | MET | `fno.costs` on the protocol's example: entry Rs 163.3, exit Rs 132.3, pads Rs 520, Rs 815.5. My rerun gives charges plus pads of Rs 603-641 a trade |
| (4) Ordinary-day control | PARTLY | Same `setup`, structures, charges and pad. Not year-matched as registered: should-fix 1 |
| (5) FINNIFTY and MIDCPNIFTY back to `fresh` | MET | `registered` at `739d3a0b6` and `effae5117`, `fresh` only after nothing was nominated, as F1's weekly rows. The study's symbols and cache key are NIFTY and BANKNIFTY only; no code names the held-out indices |
| (6) Ledger 124-127 | MET | Appended in `edge2-f9-event-iv-crush-2026-10-25`; protocol and run commits filled in at the freeze and the run, as F8's rows; `require_registered` passes for 123-127; LEDGER.md total 127 |
| (7) Worst events and the cap | NOT MET | should-fix 2 |
| (8) No G1 inputs in the frozen cards | MET | Matches judge 642's S1: the cards are unchanged since registration (`test_each_frozen_edge2_card_is_unchanged_since_its_freeze`, 124-127 pass); gates.csv holds G0 rows only |
| Reproduction | MET | My rerun of `study_f9.py discovery` from the stores: `discovery.json` is identical but for `head` |

## Findings

1. **Should-fix: the control is not the registered one, and nothing says so.** Protocol section 7 registers "2,000
   draws of the same number of non-event sessions ... **same years**"; `summary.event_control_p` samples from all
   control days pooled. Section 10 says "Deviations: None yet", and the result cites p_event as evidence. My
   year-matched draws (same seed, same counts per year as the events): p_event 0.0035 / 0.011 / 0.048 / 0.044
   (CONDOR-E0, FLY-E0, CONDOR-E1, FLY-E1), against the reported 0.002 / 0.008 / 0.039 / 0.034. Nothing is
   nominated either way. Fix: record the deviation in F9_RESULTS (the protocol is frozen) and give the
   year-matched values beside the pooled ones.
2. **Should-fix: the one incomplete exit, left unnamed, is the 2024 election-day BANKNIFTY trade, and the worst and
   by-type figures leave it out.** It is the study's largest gamma event (BANKNIFTY -8.2%). Its nets are
   -Rs 2,334 (FLY-E0), -2,275 (FLY-E1) and -1,514 (CONDOR-E0), each excluded from the decided mean by the rule.
   Three statements need correcting:
   - "worst single trades lost Rs 2,147 (FLY-E0)";
   - "the 3 election-result trades +Rs 1,798 (CONDOR-E0: +Rs 3,226)": with it, (3 x 1,798 - 2,334) / 4 = +Rs 766 and
     +Rs 2,041;
   - "Skips: ... 1 incomplete exit": this names neither the trade nor its loss.

   The risk-manager line's Rs 885-2,334 is right. Fix: name the trade and its nets, and give the worst trade and
   the election figures with and without it.
3. **Minor: no test pins the event list or the code to the freeze.** Dropping the last row of `f9_events.csv` passes
   all 258 research tests. Expected: `code_hash()` equal to F9_FREEZE's value in a test.
4. **Minor: "at most 2 nominated" is untested.** That cap set to 3: 258 passed.

## Plants

14 planted on `e3ec093af`, one at a time. 12 caught: the look-ahead `<=`, control gap 0, the gross bar at 0,
incomplete exits counted, the SE per trade, the 30-event floor off, `>` in p_event, p_event out of the nomination,
the Rs 2 pad check off, the 5-session floor at 0, entry on the event day, E1 as E0. 2 survived (minors 3 and 4).

## Notes

- Gates on a trial merge with main `096024142`, committed locally (B4's guard refuses an uncommitted ledger; never
  pushed): 17,462 passed, 13 xfailed, 0 failed; ruff, format, `check_imports`, `check_records` clean.

## Addendum 1: round 2 at `9c7961346` (the last round)

**PASS**, lane 1: both should-fixes and both minors closed; 1 minor left (wording). The round changes only
`F9_RESULTS.md` and `tests/research_edge2/test_f9.py`; the frozen protocol, code, events, cards and ledger are
byte-identical to round 1.

| Round-1 finding | Verdict | Evidence |
|---|---|---|
| S1. Control not year-matched, no deviation | FIXED | a new Deviations section and both p_event columns; the year-matched 0.011 / 0.044 / 0.0035 / 0.048 equal mine |
| S2. The 2024 election BANKNIFTY exit unnamed | FIXED | named, with nets -2,334 / -2,275 / -1,514 and CONDOR-E1 none, as I found; election means on all trades +765 (FLY-E0), +2,041 (CONDOR-E0), -410 (FLY-E1), which equal (2 x 522 - 2,275) / 3 from my rerun's rows |
| m3. Freeze not pinned | FIXED | `test_the_code_hash_is_the_frozen_one`: my plant (last event row dropped) is caught |
| m4. Nomination cap untested | FIXED | `test_at_most_two_variants_are_nominated_lowest_p_first`: plants "cap 3" and "order by name" are caught |

**Minor (left):** two lines were not updated.
- The Gamma bullet still says "the worst single trades lost Rs 2,147 (FLY-E0)" with no "decided" qualifier.
- The answer's evidence label still says "p_event 0.002-0.039".

The new bullets just above correct both, so a reader is not misled. Expected: the word "decided" in the first line,
and the year-matched range in the second.

**Gates:** trial merge with main `b58ddecdb`, committed locally (never pushed): 17,538 passed, 13 xfailed, 0 failed;
ruff, format, `check_imports`, `check_records` clean. **Plants:** 3, all caught.
**Narrow check of the minor (orchestrator's request): `c48249edd` PASS, the last minor closed.** One commit on
`9c7961346`, `F9_RESULTS.md` only (3 lines): the worst FLY-E0 trade is now -Rs 2,334, the incomplete 2024
election-day exit (-Rs 2,147 among decided trades). The other variants' worst trades are unchanged; their incomplete
losses, -2,275 and -1,514, are smaller. The label is now p_event 0.002-0.048, pooled and year-matched. Record scan
clean; the doc-reading tests plus `test_f9.py`: 950 passed, 13 xfailed.
