"""V4's and V5's probabilities from the frozen terms (PROTOCOL_v4.md section 3.1; story G7b completion): V5's
option-implied baseline (lognormal on the implied variance, "risk-neutral, not a real-world probability"), and the two
rule forecasters with zero fitted parameters: `v5_ewma_lognormal` (the same formula on the EWMA close-proxy variance)
and `v4_ewma_chi2` (each of the 5 session variances `s2 x Z^2`, so their sum over `s2` is chi-square with 5 degrees).
A probability that cannot be computed is missing, never filled."""

from __future__ import annotations

import math

from ..analytics import norm_cdf
from ..forecast_v4.terms import SESSIONS_A_YEAR
from .baselines import MISSING, Value
from .option_terms import OptionTerms, Void
from .v4_expiry import V4_MIN_SESSIONS


def inside_probability(forward: float, strike: float, premium: float, variance: float) -> float:
    """P(K - P < S_T < K + P) when `ln S_T ~ N(ln F - v / 2, v)`; a lower edge at or below 0 has probability 0."""

    def below(x: float) -> float:
        return 0.0 if x <= 0 else norm_cdf((math.log(x / forward) + variance / 2) / math.sqrt(variance))

    return below(strike + premium) - below(strike - premium)


def chi2_5_cdf(x: float) -> float:
    """The chi-square distribution function with 5 degrees of freedom (closed form)."""
    if x <= 0:
        return 0.0
    return math.erf(math.sqrt(x / 2)) - math.sqrt(2 * x / math.pi) * math.exp(-x / 2) * (1 + x / 3)


def option_implied_probability(terms: OptionTerms | Void) -> Value:
    """V5's primary baseline: the mean leg IV over `tau = C_e / 365`; void terms give missing."""
    if isinstance(terms, Void):
        return Value(MISSING)
    return Value.of(inside_probability(terms.forward, terms.strike, terms.premium, terms.iv**2 * terms.years),
                    positive=False)  # fmt: skip


def v5_ewma_lognormal(terms: OptionTerms | Void, session_variance: float | None) -> Value:
    """The same formula on physical variance: `S_e x s2`, `s2` the EWMA per-session close-proxy variance."""
    if isinstance(terms, Void) or session_variance is None or session_variance <= 0:
        return Value(MISSING)
    return Value.of(inside_probability(terms.forward, terms.strike, terms.premium, terms.sessions * session_variance),
                    positive=False)  # fmt: skip


def v4_ewma_chi2(terms: OptionTerms | Void, session_variance: float | None) -> Value:
    """P(sum of the 5 session variances < T), `T = sigma_IV^2 x 5 / 252` (the window's integrated implied variance)."""
    if isinstance(terms, Void) or session_variance is None or session_variance <= 0:
        return Value(MISSING)
    threshold = terms.sigma_iv_session_clock**2 * V4_MIN_SESSIONS / SESSIONS_A_YEAR
    return Value.of(chi2_5_cdf(threshold / session_variance), positive=False)
