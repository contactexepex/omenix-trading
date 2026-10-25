"""The dates-only list of US trading days (story A17b): exchange-calendar facts taken from the Drive-only index tables,
never their values (orchestrator's decision, owner away). A date is listed when either table has it; a Nasdaq-only
date is one of Nasdaq's holiday rows (a repeated close) and is listed, never counted as a session."""

from __future__ import annotations

from .us_index_sources import CboeSp500Source, NasdaqNdxSource

FIELDS = ("date", "in_sp500", "in_nasdaq100")
SP500_CUE, NASDAQ100_CUE = CboeSp500Source.cue, NasdaqNdxSource.cue


def us_trading_dates(sp500: list[dict[str, str]], nasdaq100: list[dict[str, str]]) -> list[tuple[str, int, int]]:
    in_sp500 = {r["value_date"] for r in sp500}
    in_nasdaq100 = {r["value_date"] for r in nasdaq100}
    return [(day, int(day in in_sp500), int(day in in_nasdaq100)) for day in sorted(in_sp500 | in_nasdaq100)]
