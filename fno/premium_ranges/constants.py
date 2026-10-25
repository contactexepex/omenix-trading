"""G13d's fixed strings and numbers (story text rev 2, judge 453.1)."""

from __future__ import annotations

from datetime import time

LEVELS = (0.05, 0.25, 0.50, 0.75, 0.95)
RULE, NO_CHANGE, DECAY_ONLY = "sticky_strike_v1", "no_change", "decay_only"
METHODS = (RULE, NO_CHANGE, DECAY_ONLY)
LIVE = "live"
SCHEMA, SCORE_SCHEMA = "g13d_premium_v1", "g13d_premium_scores_v1"
DEADLINE = time(15, 30)  # sealed by the close of day d: no later price of d is known at the seal
ISSUE = "1500"  # the 3 pm chain's issue (one per day)

NO_IV = "no contract IV"
EXPIRES_BY_NEXT = "the expiry is the next session or earlier"
NO_DISTRIBUTION = "no G13 distribution for the expiry"
NO_ATM_IV = "no ATM IV for the expiry"
NO_NEXT_CHAIN = "d+ has no 3 pm chain"
NO_NEXT_QUOTE = "no valid two-sided quote at d+"
OTHER_SOURCE = "d+'s chain is from another source"

RELATIVE_FLOOR = 2.0  # rupees: relative QS divides by max(d's mid, 2) (judge 453 note)
DELTA_BUCKETS = ((0.0, 0.15), (0.15, 0.35), (0.35, 0.65), (0.65, None))  # |delta| at d, low end included
DAYS_BUCKETS = ((2, 7), (8, 21), (22, None))  # calendar days to expiry at d, both ends included
LOOKS = (60, 120, 250)  # scored sessions per underlying at which the verdict is read, and at no other count
BAND_90, BAND_50 = (0.85, 0.95), (0.40, 0.60)
COVERS_WELL, BEATS_CARRY, FAILS, NOT_YET = "covers well", "beats carry", "fails", "not yet decided"
