# Judge 453: G13d story text, each contract's next-session premium range from a stated volatility rule (4ac13cce)

Judge B, 22 Oct 2026. Lane 1: a new story with forecast and evaluation records, Drive, and later a daily step.
- Builder: G13/G13b (session_01UkTaDeTRF9ksDgQB9cTU5C).
- Branch: `story/g13d-premium-ranges`, head 4ac13cce.
- Register row on main ca73f2d8.
- Number claimed with `tools/claim_number.py`.

## Verdict: FAIL (1 should-fix)

The rule is stated once, with no fitted parameter, and the design is sound. One thing is undefined: what "judge" means
once the report has enough sessions.

## Criteria

| Check | Result | Evidence |
|---|---|---|
| The rule | MET | see "The rule" below |
| What the rule leaves out | MET | stated in advance: IV against the index (put ranges too narrow on down days), skew movement, the spread |
| Baselines | MET | `no_change` and `decay_only` are points. A point's QS is its absolute error: with G13's (2/5) x the sum over 5 levels, 2.5 \|y - q\| x 2/5 = \|y - q\| (checked) |
| Outcome | MET | d+'s 3 pm mid from the same source, valid two-sided quotes only; missing is unscored and counted |
| Unit and intervals | MET | averaged per session first, then G4's block bootstrap over sessions; rows are never treated as independent; criterion 3 tests that the session weights are equal |
| Sealing | MET | reuses G13b's seal (not a copy): late if pushed after 15:30 IST on d |
| No back-fill | MET | right: EOD closes are a different target |
| O1 steps | MET | with O1's owner, `live_from` null until a judged go-live |
| Readers, wiring, acceptance criteria | MET | testable, including a real-data run on 16 and 19 Oct that the judge can rerun |

### The rule
- The forward's quantiles come from G13's ATM IV over h = calendar days / 365, with the -σ²h/2 drift.
- Each contract is re-priced with Black-76 at its own IV of d (sticky strike), one day less.
- A put's quantiles are the reversed values. This is a valid quantile mapping, because the premium is monotone in F at
  fixed IV.

## Should-fix 1: "too few sessions to judge" with no stated rule for judging

The report says "too few sessions to judge" until 60 sessions, and Q1 asks whether the desk may use the ranges for
stops "if the rule's ranges cover well". The story never says what "judge", "scores well" or "cover well" mean.

**Why this is normal running:** at session 60 the report must print something under that heading. Without a rule
written now, the bar is set after seeing three months of scores. That is the kind of after-the-fact choice the project
avoids everywhere else.

**Fix (pick one and write it down).** Either:
- **(a)** state the reading at 60 sessions per underlying, for example:
  - "covers well" = the session-averaged 90% coverage's block-bootstrap 95% interval lies inside [0.85, 0.95], and the
    50% coverage's inside [0.40, 0.60];
  - "beats carry" = the paired session-averaged QS difference against `decay_only` has its interval below 0;
  - each per underlying, with the delta and days buckets descriptive only;
- **(b)** say plainly that the report never judges, so Q1's answer needs its own protocol later, and drop "too few
  sessions to judge".

60 is acceptable as a stated number, provided it is marked as reasoning only.

## Notes (one line each)

1. **Data spend.** If Q2's second rule (a spot-vol slope) is built after reading this report, the sessions scored here
   are exposed for it. Record that in DATA_SPEND when Q2 is registered.
2. **Special sessions.** d+ may be a special session with no 3 pm chain. Such rows are unscored and counted; name the
   reason.
3. **Premium floor.** Relative QS (QS divided by d's mid) explodes for near-zero premiums. State a floor or report it
   only for mids above a stated level.

## Addendum 1: revision 2 at 9f9618e4 (number 453.1, claimed with `tools/claim_number.py`)

**PASS.** Should-fix 1 is met with option (a), written before any score.

### The verdict rule
Per underlying, on all ranged contracts (the buckets are descriptive only):
- **covers well:** the session-averaged 90% coverage's block-bootstrap 95% interval lies inside [0.85, 0.95], and the
  50% coverage's inside [0.40, 0.60];
- **beats carry:** the paired rupee-QS difference against `decay_only` has its interval below 0 (against `no_change` it
  is only reported);
- **fails:** an interval lies wholly outside its band, or the QS interval wholly above 0;
- otherwise **not yet decided**.

### The looks
- They are fixed at 60, 120 and 250 sessions and at no other count, and Q1 relies on the 250-session look. The extra
  chance of a lucky pass from three looks is stated.
- The stated power arithmetic checks out: an SD of 0.2 over the square root of 60 is 0.026, so the 95% interval is about
  ±0.05, the band's own width. That holds if sessions are independent; autocorrelation would widen it.
- Criterion 3b tests the rule.

### The notes
- A special-session d+ with no chain has its own reason.
- Relative QS uses max(mid, Rs 2) and is descriptive only; the verdict uses rupee QS.
- If Q2 is built, its sessions are recorded in DATA_SPEND.
