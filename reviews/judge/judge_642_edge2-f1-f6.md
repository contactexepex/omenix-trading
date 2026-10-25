# Judge 642: EDGE2 F1 and F6, story/edge2-f6-participant-oi at a5cc130f (judge J, round 1 of 2)

**FAIL**, lane 1: 2 should-fix, 4 minor. The "no edge" results stand, reproduced by my own reruns. Trial merge with
main 82ad1586 (381bf7d0): 16,686 passed, 1 skipped, 13 xfailed; ruff, format, check_imports (2,790), check_records
(9,344) and check_numbers clean. The 44725e7e merge was run too: 16,628 passed.

## Criteria (the orchestrator's checks)
| Item | Verdict | My evidence |
|---|---|---|
| F1 (1) freeze before the run, code hash | MET | GitHub push log: 270959dd at 23:09:31Z; the discovery commit b9b23f9d at 23:10:22; results pushed at 23:20:21Z. `code_hash()` = 9cbe34ce at 47c01637, 270959dd and a5cc130f; protocol SHA-256 2105e363 unchanged |
| F1 (2) held-out unread, rows fresh | MET | `seal.allowed` refuses FINNIFTY and MIDCPNIFTY unless opened, and `nominated_for_held_out` refuses with no nominee (R1-R3 caught). No `heldout.json`. The new FINNIFTY and MIDCPNIFTY weekly rows are `fresh`: `research/` holds FINNIFTY prices only in the Aug-Sep 2026 modelled backtest |
| F1 (3) costs, pads, -Rs 105 | MET | My rerun gives discovery.json identical except `head`. -105.44 = 230.79 - 162.55 - 173.67 (pads 4 x Rs 1 x mean lot 43.4). I priced three trades by hand from the closes with `fno.costs`: gross equal; charges within 0.22, the STT on the padded sell (0.15% x pad x lot x 2). The G1 rows reproduce exactly from the cards |
| F1 (4) RC1 | MET by reading and rerun; test gap m1 | Draws the same count from all the structure's cycles, taken or not; seed 20261025; share >= the gated mean, as protocol section 8 |
| F1 (5) append-only | MET | Against main: 0 removed lines in ledger.csv and gates.csv. The ledger edit is B4's one-time fill of `first_run_on` and `run_commit` |
| F1 (6) WF-G15 never retested | PARTLY | m2 |
| F6 (1) registration before any OI read | MET | 57bddc27 at branch creation (23:25:18Z), before the code (23:28:54Z) and the freeze 06646081 (23:54:29Z); discovery committed 23:55:08. Main's participant-OI row was `fresh, none` |
| F6 (2) futures STT 0.05% | MET | `FuturesRates` 0.05% sell STT, Rs 183/crore, stamp 0.002%, GST 18%, as the school probe cites (NSE/FATAX/73524, NSE/FA/73061). The protocol's Rs 966 example recomputes exactly. My F6 rerun matches except `head` |
| F6 (3) trial 118's G1 row honest | NOT MET | S2 |
| F6 (4) 115-120 under edge2-f6 | MET | Experiment `edge2-f6-participant-oi-futures-2026-10-25` |

## Findings
**S1 (should fix) B4's guard now refuses every trial 109-120.** `Ledger(root).require_registered("109")` (and 114,
115, 118, 120) raises `NotRegistered: ... changed after it was frozen`: `protocol_path` is the idea card and the G1
inputs were appended to the cards after `protocol_commit` (b9b23f9d, ed28d6b7). EDGE1's `protocol_commit` e7a2029d
holds its G1 inputs (71 and 95 pass). The factory verdict, the trial guard and any reader of the freeze proof see these
trials as altered after their freeze. Fix without rewriting frozen bytes: point `protocol_path` at F1_PROTOCOL.md or
F6_PROTOCOL.md (as GR1 does), or keep result-derived G1 inputs out of the frozen card, or change B4 (lane 1); plus a
test that runs `require_registered` on the real rows 109-120.

**S2 (should fix) Trial 118's G1 `passed` is live, built on inputs the protocol itself rejects.** The H5 cards give G1
n = 1,451 overlapping trades with the plain SD, while the frozen protocol's error is Newey-West lag 4. `fno factory
report` prints "trial 118 of 120; last gate G1 passed"; only F6_RESULTS.md's prose corrects it. My -Rs 316 is right
(739 - 1.2816 x 824), but "about sqrt(5) too tight" is wrong: NW / iid = 824 / 527 = 1.56 (FD-H5 0.95, CD-H5 1.06).
Fix: close 118 with the factory's own next gate (`factory spend` logs `exploratory`, as EDGE1's 94 went), say so in its
card and LEDGER.md row, and correct the sqrt(5) line.

**m1 (minor, tests only, outside the code hash)** Surviving plants: RC1 drawing from taken trades only (R9) and its >=
boundary (R8), the gate's traded-volume filter (R15), `code_hash` without study.py (R18), EWMA lambda 0.97 (R19), F6
keeping exits after the seal day (F2), F6's NW lag 0 for H5 (F4). Add a test for each, R9, F2 and F4 first.
**m2 (minor)** "Never retest WF-G15 on this data" is only in F1_RESULTS.md prose: add it to card 111 and the LEDGER row.
**m3 (minor)** F1 protocol section 7 promised `research/edge2/LOT_CHECK.md` before a held-out read; it does not exist
and `held_out_lots.py` says the circulars were not read. Harmless while unread; state it in section 11 or Limits.
**m4 (minor)** `registered_on` and gates `on` are 24 Oct (UTC), `first_run_on` 25 Oct (IST); DATA_SPEND keeps the old
"Participant open interest | history | fresh | none" row beside its new split rows.

## Plants (mine): 27 of 34 caught
F1 17 of 22 (seal x3, point in time, settlement close, week clusters, 30 clusters, Holm, gate boundary, 3 nomination
conditions, pad, condor offset, UDiFF lot, moved expiry, at most 2); F6 10 of 12 (seal day, STT 0.02%, entry day, level
window, client fade, pads, 2 nomination conditions, GST, roll). Survivors in m1. Own worktree, PYTHONDONTWRITEBYTECODE=1.

## Notes
- Token set for both suites (1792884295-1792885435, 1792887370-1792888021): only REH1 "DRY RUN ... replay" posts in the
  first window, nothing in the second; neither study holds Slack code.
- My F6 rerun once died on a Drive "connection reset" (ChunkedEncodingError, no retry); the second try passed. That is
  the storage layer, not this story.

## Addendum 1: round 2 (the last), story/edge2-f8-fii-side-spread at 56031075 (F1, F6 and F8)
**PASS**, lane 1: S1 and S2 are closed; 6 minor, none blocking. Trial merge with main 3b1ffcdd (7802738c): 16,868
passed, 1 skipped, 13 xfailed; ruff, format, check_imports (2,810), check_records (9,380) and check_numbers clean.
- **S1 closed** (1c47c871). The 12 cards are back to their frozen text; `require_registered` passes for every trial
  101-123. The new `test_each_frozen_edge2_card_is_unchanged_since_its_freeze` catches my plant (a G1 line added to
  card 109).
- **S2 closed** (67d383f4). An appended G1 row gives 118 `screened_out`: net -316.2 = 1397.2 - 1.2816 x 823.7 - 657.7,
  and the first row stays as logged.
  - The factory acts on the last row (`GateLog.last`, read by `GateOrder.ready`), so `factory spend` can no longer run
    on 118; `factory report` prints "last gate G1 screened_out".
  - `GateOrder.row` still returns the first G1 row, but every gate that reads it needs 118 to have passed first.
- **F8 is MET with my evidence.**
  - Push log: freeze d38baa12 at 00:16:09Z, then the discovery commit eedfa040 at 00:16:58. `code_hash()` f4fd512c at
    the freeze and at the head; protocol and cards unchanged since 1f69681c.
  - My rerun gives discovery.json identical except `head`: side averages -282, -219 and -388; P0W10 futile below
    -300, as the frozen rule says.
  - Discovery imports no participant-OI code and prices only 2019-2024 cycles. The 2025-26 NIFTY option prices it
    loads are F1's, already spent.
  - DATA_SPEND keeps participant OI 2025-26 `fresh`. Trials 121-123 sit in O12e's block `edge2-f8`.
- **Plants: 13 of 14 caught.**
  - Caught: futility -400; the side average from puts only; the gross bar; Holm on p_side; the RC1 call count; the
    forward at the close; entry at the close; the pad; the put side; the seal; the distance; the frozen-card edit; the
    118 row dropped (by the gate log's history check).
  - Survived: the forward's put-leg volume filter (V7).
- **Minor, none blocking:**
  - (a) Round 1's m1-m4 are not done; they carry over.
  - (b) F6_RESULTS.md:37 still says "about sqrt(5) too tight"; the measured ratio is 1.56.
  - (c) F8_RESULTS.md's Answer still says P0W5 and P5W5 "go to the held-out read ... which waits for a lane-1 judge",
    and discovery.json lists both as `nominated`, so `study_f8.py heldout` would open the seal. **This PASS is not
    that judge's pass: the read stays waived by the orchestrator.** Say so in the Answer and in F8_FREEZE.md.
  - (d) V7 needs a test.
- Slack, with the token set (1792889088-1792889784): nothing in any channel.
