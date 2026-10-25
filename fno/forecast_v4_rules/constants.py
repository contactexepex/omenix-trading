"""Story G7b's forecaster ids (folder names under `research/forecasts/v4/`, G8's lookup keys). Kept here because
`fno/constants.py` is at its 350-line limit, as `fno/weather/constants.py` is (story E4c); phase 1's ids stay there."""

from __future__ import annotations

V4_RULE_V2_CLOSE_BLEND = "v2_close_blend"  # V2's `rules` slot (proposed for registration at v4's freeze)
V4_RULE_V3_CLOSE_BLEND = "v3_close_blend"  # V3: reported only (terms.REPORTED_ONLY)
V4_RULE_V7_VIX_SIDE = "v7_vix_vs_mean20"  # V7: reported, descriptive only (terms.DESCRIPTIVE_ONLY)
V4_RULE_V4_EWMA_CHI2 = "v4_ewma_chi2"  # V4: reported only (story G7b completion)
V4_RULE_V5_EWMA_LOGNORMAL = "v5_ewma_lognormal"  # V5: reported only (story G7b completion)
V4_BASELINE_PREMIUM_ADJUSTED_INTRADAY = "premium_adjusted_implied_intraday"  # W3's yardstick A (owner, 24 Oct: both)
