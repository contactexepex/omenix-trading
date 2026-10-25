"""Black-Scholes pricing, Greeks and option-chain statistics (``fno/shared/analytics.py``): pure functions, so the
assertions are real maths, not mocks."""

from __future__ import annotations

import math

import pytest

from fno.ingestion.providers.sample import SampleProvider
from fno.shared import analytics as an

SPOT, STRIKE, T, R, SIGMA = 22500.0, 22500.0, 0.08, 0.065, 0.14


def test_put_call_parity_holds() -> None:
    """European parity with no dividends: C - P == S - K*e^(-rT)."""
    call = an.bs_price(SPOT, STRIKE, T, R, SIGMA, "CE")
    put = an.bs_price(SPOT, STRIKE, T, R, SIGMA, "PE")
    assert call - put == pytest.approx(SPOT - STRIKE * math.exp(-R * T), abs=1e-6)


def test_call_rises_and_put_falls_with_spot() -> None:
    lo_c = an.bs_price(SPOT - 200, STRIKE, T, R, SIGMA, "CE")
    hi_c = an.bs_price(SPOT + 200, STRIKE, T, R, SIGMA, "CE")
    lo_p = an.bs_price(SPOT - 200, STRIKE, T, R, SIGMA, "PE")
    hi_p = an.bs_price(SPOT + 200, STRIKE, T, R, SIGMA, "PE")
    assert hi_c > lo_c  # call gains as spot rises
    assert hi_p < lo_p  # put loses as spot rises


def test_price_never_below_intrinsic() -> None:
    itm_call = an.bs_price(SPOT + 1000, STRIKE, T, R, SIGMA, "CE")
    assert itm_call >= (SPOT + 1000) - STRIKE * math.exp(-R * T) - 1e-6


def test_zero_time_or_vol_is_intrinsic() -> None:
    assert an.bs_price(100, 90, 0.0, R, SIGMA, "CE") == pytest.approx(10.0)
    assert an.bs_price(100, 90, T, R, 0.0, "PE") == pytest.approx(0.0)  # OTM put, no time value


def test_longer_expiry_and_higher_vol_cost_more() -> None:
    assert an.bs_price(SPOT, STRIKE, 0.2, R, SIGMA, "CE") > an.bs_price(SPOT, STRIKE, 0.02, R, SIGMA, "CE")
    assert an.bs_price(SPOT, STRIKE, T, R, 0.30, "CE") > an.bs_price(SPOT, STRIKE, T, R, 0.10, "CE")


def test_implied_vol_round_trips() -> None:
    price = an.bs_price(SPOT, STRIKE, T, R, SIGMA, "CE")
    recovered = an.implied_vol(price, SPOT, STRIKE, T, R, "CE")
    assert recovered == pytest.approx(SIGMA, abs=1e-3)


def test_implied_vol_none_at_or_below_intrinsic() -> None:
    intrinsic = max(SPOT - STRIKE, 0.0)
    assert an.implied_vol(intrinsic, SPOT, STRIKE, T, R, "CE") is None


def test_greeks_have_the_right_signs() -> None:
    call = an.bs_greeks(SPOT, STRIKE, T, R, SIGMA, "CE")
    put = an.bs_greeks(SPOT, STRIKE, T, R, SIGMA, "PE")
    assert 0.0 < call.delta < 1.0
    assert -1.0 < put.delta < 0.0
    assert call.gamma > 0.0 and put.gamma > 0.0
    assert call.vega > 0.0 and put.vega > 0.0
    assert call.delta - put.delta == pytest.approx(1.0, abs=1e-3)  # parity of deltas


def test_chain_statistics_on_sample_chain() -> None:
    provider = SampleProvider({})
    expiry = provider.expiries("NIFTY")[0]
    chain = provider.chain("NIFTY", expiry)
    pcr = an.put_call_ratio(chain)
    pain = an.max_pain(chain)
    move = an.straddle_expected_move(chain)
    assert pcr is not None and pcr > 0.0
    assert pain in chain.strikes()
    assert move is not None and move > 0.0
    # The ATM straddle move should be a small fraction of spot, not a wild number.
    assert 0.0 < move < chain.spot
