"""The instructor v1's frozen thresholds (story MS-INS). Each value is also in `research/school/INSTRUCTOR_V1.md`'s
`thresholds` block; a test pins the two together. All are first guesses [reasoning only]; a change is instructor v2."""

RANGE_Z = 1.645  # cause 1: outside the option-implied 90% range
SHOCK_Z = 2.0  # causes 7 and 8
MARKET_WIDE_COUNT = 3  # cause 8: of the 4 underlyings
COMPONENT_SHARE = 0.40  # causes 3, 4 and 5: the component's share of the loss (or gain)
DIRECTIONAL_SHARE = 0.20  # stance: a 1% forward move changes the value by this share of the maximum loss
GAP_STOP_MULTIPLE = 1.25  # cause 6: the loss beyond the card's stop
WHIPSAW_MULTIPLE = 1.0  # cause 11: holding would have done better by this multiple of the loss (or gain)
NOISE_SDS = 1.0  # cause 12
NOISE_QUANTILES = 201  # cause 12: the model outcome's frozen quantile grid
POOR_FIT_RS = 200.0  # part b: the residual's floor for "poor fit"
POOR_FIT_SHARE = 0.25  # part b: and its share of the Greek components
MIN_SESSIONS = 30  # part d: valid counted sessions before "watching" or "not established" (327 P2)
MIN_BATCHES = 2  # part d: fewer whole batches give no bound ("too few independent batches")
BATCH_HOLD_MULTIPLE = 1.5  # part d: batch = 1.5 x the pair's longest hold (batch = hold failed the 10% null gate)
MIN_BATCH = 10  # part d: and never under 10 sessions
SELLER_FALSE_POSITIVE_PCT = 46  # part d: the skewed-seller null's worst upper end (45.6%), printed on seller rows
SESSIONS_PER_WEEK = 5  # part d: calendar days to sessions for a card's hold
MONTHLY_CYCLE_DAYS = 36  # part d: the longest hold to the nearest monthly expiry (REF can enter at 36 days)
WEEKLY_CYCLE_DAYS = 7  # part d: the same for a weekly expiry

THRESHOLDS = {
    "range_z": RANGE_Z,
    "shock_z": SHOCK_Z,
    "market_wide_count": MARKET_WIDE_COUNT,
    "component_share": COMPONENT_SHARE,
    "directional_share": DIRECTIONAL_SHARE,
    "gap_stop_multiple": GAP_STOP_MULTIPLE,
    "whipsaw_multiple": WHIPSAW_MULTIPLE,
    "noise_sds": NOISE_SDS,
    "noise_quantiles": NOISE_QUANTILES,
    "poor_fit_rs": POOR_FIT_RS,
    "poor_fit_share": POOR_FIT_SHARE,
    "min_sessions": MIN_SESSIONS,
    "min_batches": MIN_BATCHES,
    "batch_hold_multiple": BATCH_HOLD_MULTIPLE,
    "min_batch": MIN_BATCH,
    "seller_false_positive_pct": SELLER_FALSE_POSITIVE_PCT,
    "sessions_per_week": SESSIONS_PER_WEEK,
    "monthly_cycle_days": MONTHLY_CYCLE_DAYS,
    "weekly_cycle_days": WEEKLY_CYCLE_DAYS,
}
