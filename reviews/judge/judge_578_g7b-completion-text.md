# Judge 578: G7b completion story text, `story/g7b-completion` at 485cf6053 (round 1 of 2, judge K)

**FAIL, lane 1, rule 1 (text first).** 5 should-fix, 5 minor. Judged by reading; doc-reading tests on 485cf6053: 829 passed, 15 xfailed.

## Criteria (rule 1 and rule 2 checks, against PROTOCOL_v4 1.1, 1.4, 1.5, 3.1, 3.2, 4, 5, the calibration part, response 250, main)

| Check | Verdict | Evidence |
|---|---|---|
| Builder's gap table (what is missing) | MET | `constants.py:203-204` ids only; `premium_ratio_window`, `proxy_drift`, `v4_outcome`, `v5_outcome` have no caller outside `fno/forecast_v4/` (grep; tests only); `scoring.py:26` `NOT_STARTED`; `research/forecasts/v4/` has no v4_/v5_ folder |
| 3.1 / 3.2 formulas (raw, premium-adjusted, option-implied, base rates, primaries) | MET | match 3.1 word for word; `z(x)` sign checked (P(S_T<x) under ln S_T ~ N(ln F - s^2 tau/2, s^2 tau)); chi-square(5) closed form and F(11.0705)=0.95 correct |
| 1.4 V4 terms and units | PARTLY | golden 13.656/13.567/15.384 match 1.4; expiry choice "among the expiries the pack holds" breaks "nearest listed" (SF1) |
| 1.5 V5 terms, outcome, first_seen_at | PARTLY | strict inside, 15:30 refusal match `settlement.py`; A11 archive-time gap not verified (SF3) |
| 1.6 / section 4 point-in-time and deadline | PARTLY | pack hash guard, system_late, 15:10 by receipt time stated; refit timing and day label loose (m3, m4) |
| Gap list complete (rule 2) | PARTLY | covers 1.1, 1.3-1.5, 3.1, 3.2; sections 4 and 5 for V4, V5 and part f absent (SF5) |
| W1-W7 needed and plain | PARTLY | W1, W2, W6, W7 needed and plain; W3, W4, W5 not (SF2-SF4) |
| G10 dependency | PARTLY | step order matches G10's text (edd8e4d0a: `v4_release`, then `forecasts_v4_pack`); interface item 2 wrong (SF1) |
| Lane, owner rules, size, storage (Drive only, O9) | MET | lane 1; DESK_DECISIONS 24 Oct rows 320-321 cited; O1 part reviewed by O1's builder |

## Findings

1. **Should fix: V4's expiry can silently be a farther one.** Scope rule and interface item 2: `e` = nearest expiry with >= 5 sessions "among the expiries the pack holds". G10's answer (edd8e4d0a) holds `e`, the other monthly and the first >= 5-session expiry. If that weekly's chain fails to capture, the rule picks the monthly: not 1.4's "nearest listed".
   - Fix expected: pick `e` from the expiries listed at the cutoff (`ListedExpiries`, `fno/quotes/expiry_listing.py:26`, with its provenance, or a list stored in the pack), in G7b's one pure function. Void (`no_v4_expiry`) when the pack lacks that expiry's ATM legs. Add a criterion 9 case: monthly present, weekly missing, so void.
2. **Should fix: W5 drops a rule that protocol and repository already have.** 1.6 keeps `last_trade_time` for "the 'traded today' check". A4's `quote_validity` (`fno/quotes/quote_validity.py:21-38`) refuses a quote with no trade today, because Groww gives no quote time. W5 says "no traded-today condition", and the owner table says "the protocol does not define live".
   - Fix expected: reuse `traded_today` through the pack's `last_trade_time` (one rule, one place). Or show data that ATM legs always trade by 14:30 and tell the owner plainly that this rule is being dropped and why.
3. **Should fix: A11's archive time is left open, but it exists.** Drive's `createdTime` of the raw file is already read behind `CreationTimes` (`fno/storage/creation_times.py:14-28`, used by A17b). A11's `revisions.py:25` holds `available_from` / `found_at` for later versions.
   - Fix expected: name `CreationTimes` at `NseDailyFoSource.path_for(e)` as the first version's archive time, with a test. Then drop W4, or state why `createdTime` is not acceptable. The owner row "no file stores today" is wrong as written.
4. **Should fix: W3 is presented as forced.** 1.1's no-pooling rule is about scored series. The window already mixes measures (an EOD IV proxy for a 14:30 IV, 3.1). Close-proxy and intraday-with-overnight `RV_s` estimate the same daily variance.
   - Fix expected: give the owner the alternative (the close-proxy ratio, available now, with a measure mismatch) and W3's cost (V1's and part f's baseline missing about 2 years). Label it reasoning only.
5. **Should fix: sections 4 and 5 are missing from the gap list.** Not covered for V4, V5 and the part f series: Brier primary; log score, reliability and Brier skill score against the base rate; block L 10 and 20; reported numbering after 15; never in the family; `system_late` out; a rule-forecaster row received after 15:10 is a miss. Criterion 15 tests none of these. "Scoring maths is G8's" is no reason: part e is G8's side.
   - Fix expected: add the rows and criterion 15 cases.

**Minor.**
- m1: part f says the first `d` "after" 16 Oct, but W7's rule gives 15 Oct. Also state that the live and back-fill cohorts stay apart in part f.
- m2: `S_e` is not defined for V5's `e` in `v5_ewma_lognormal`.
- m3: say that a month's ratio is computed once, on the refit day, from inputs present then, and stored; never recomputed later with files archived late.
- m4: 1.6 asks for the day label "on every v4 record"; name where new rows get `A`.
- m5: check `pack.future.expiry > d` and that it is monthly (else void); do not trust the pack for this.

## Plants

None: text round, judged by reading (JUDGE.md, text-only changes).

## Notes (not findings)

- Look-ahead check: V5 is read only from its written outcome record. Base rates and live rows are written once at capture, so they are point in time by construction. The 15:29:59 / 15:30:00 boundary matches `SETTLEMENT_TIME` (`desk/settlement.py:29`).
- Applying the 15:10 stop to pack-derived *baselines* is stricter than section 4 requires. Accepted as safe; it can cost baseline-missing days.

## Addendum 1: round 2, `story/g7b-completion` at 644ae68da (judge K, own session)

**PASS (text), lane 1.** Every should-fix is fixed and checked against the code. 3 minor notes for the build. Judged by reading; doc-reading tests on 644ae68da: 829 passed, 15 xfailed.

| Finding | Verdict | Own evidence |
|---|---|---|
| SF1 V4 expiry | fixed | `e` only from `pack.v4_expiry`; void `no_v4_expiry` when its ATM legs are missing ("monthly present, weekly missing: void", criterion 9); `v4_expiry_mismatch` re-checks 5 sessions on A7. G10 d4e72f20d (story lines 1110-1127) names `v4_expiry` from the sidecar, never recomputed, and imports `first_v4_expiry` with the same signature (criterion 20) |
| SF2 traded today | fixed | A4's `traded_today` (`quote_validity.py:11-18`) through an adapter on `last_trade_time`, never copied; G10's `ChainQuote` keeps `last_trade_time` (G10 text line 886). Leaving sizes out is stated plainly: the pack has none |
| SF3 A11 time | fixed | `CreationTimes` on `NseDailyFoSource.path_for(e)`, then A8's log; raw files never change (`revisions.py:1-8`), so Drive's created time belongs to the first version; W4 dropped; criterion 8 cases |
| SF4 W3 | fixed | the two options with their costs; B recommended, labelled reasoning only; the owner row is in plain words |
| SF5 sections 4 and 5 | fixed | gap rows for 4, 5.2, 5.3-5.6; criterion 15 cases; `terms.BLOCK_LENGTH` (V4 10, V5 20) and `comparison.seed_word` exist; 15:10:00 on time and 15:10:01 late match `commitment.on_time` |
| m1-m5 | fixed | 16 Oct's A16 row is void (`research/data/intraday/rv/2026/nifty_rv_20261016.csv`); `ListedExpiries.listed(u, d)` reads files from `d-1` back (`expiry_listing.py:44-45`), so it is point in time; `monthly_expiries` exists |

**The two dependencies still open with G10:**
- **(a) Receipt path in `v4_deadline`: stated correctly.** G10's verdict reads `CommitmentTimes.row_received_at`, which works on repository CSV rows. G7b's live rows are Drive files, so they need the receipt path (`file_received_at`). The story asks for exactly this. Until G10 covers it, G8's existing "deadline not checked" count makes the gap visible, never silent (G10 text item 8).
- **(b) The future's `last_trade_time` or day volume: stated, but incompletely (minor n1).** Interface item 4 states it, and 7cab92b06 carries volume only into the builder's tuples, not into `FutureQuote`. But the "Open" list names only (a). It does not say that without (b) every V5 day is void (`no_trade_today`), so V5's primary baseline never exists.

**Minor (for the build's first commit or claims; none blocks):**
- n1: add (b) to the Open list, with that consequence. Never relax W5 for the future without the owner.
- n2: the ratio path `v4/ratios/<question>/<YYYY-MM>.json` has no measure. A B-built V1 ratio would then collide with an A ratio if the owner picks A. Put the measure in the path. Also, "the V2 / V3 window's ratio, at `h` = 1" means the close-proxy method at `h` = 1: say it so.
- n3: the owner's W2 and W5 rows talk about "option" quotes only; say that the future's mid also needs a trade that day.

Plants: none (text round).
