"""Reads one session's archived NSE files and computes its rows (story P6). Windows follow the W11 contract's
examples (a year and a week of equity and index files, three months of F&O files), but the sessions come from NSE's
calendar (SessionCalendar), never from weekdays. A missing file stops the build: a session is never built partly.
Reference lists use the copy archived on the session's day or the latest before it, else the nearest after it."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

from ..research_data.calendar import SessionCalendar
from ..storage.raw_source import (
    NseDailyFoSource,
    NseDeliverySource,
    NseEquityBhavcopySource,
    NseIndexCloseSource,
)
from ..storage.raw_store import RawFileStore
from ..storage.snapshot_source import (
    CorporateActionsBySymbolSource,
    CorporateActionsSource,
    EquityListSource,
    Nifty500ListSource,
    SymbolChangeSource,
)
from .blocks import SessionRows
from .chain_session import ChainBuilder, history_start
from .corporate_actions import CorporateAction, adjusted, read_corporate_actions, unexplained
from .fno_rows import FnoRowBuilder, UnderlyingDay, underlying_days
from .followed import FollowedCompaniesSource
from .forecast_history_inputs import ScoreReportsReader
from .forecast_lab_inputs import ForecastLabReader
from .frame_inputs import FlowsReader, frame_inputs
from .home_inputs import HomeInputsReader
from .index_rows import index_rows, industries
from .nse_files import (
    EquityBar,
    read_delivery,
    read_equity_bhavcopy,
    read_equity_list,
    read_fo_rows,
    read_index_figures,
    read_nifty500_list,
)
from .stock_rows import UNIVERSE_NIFTY_500, stock_rows, stock_series
from .symbol_changes import joined, read_symbol_changes
from .weather_inputs import WeatherInputsReader

EQUITY_WINDOW = timedelta(days=372)  # the examples' window: a year of sessions (250) and a week to spare
INDEX_WINDOW = timedelta(days=372)
FNO_WINDOW = timedelta(days=95)  # three months of F&O files: the ATM IV's range
SNAPSHOT_SEARCH_DAYS = 10
READERS = 8  # files read at once from the archive


class IncompleteSession(RuntimeError):
    """A file the session needs is not archived; nothing is built."""

    def __init__(self, day: date, missing: list[str]):
        super().__init__(f"{day}: {len(missing)} archived file(s) missing, nothing built: {', '.join(missing[:5])}")
        self.missing = missing


class SessionRowsBuilder:
    def __init__(
        self,
        store: RawFileStore,
        calendar: SessionCalendar,
        fno: FnoRowBuilder,
        followed: FollowedCompaniesSource,
        chain: ChainBuilder,
        home: HomeInputsReader,
        flows: FlowsReader,
        weather: WeatherInputsReader | None = None,
        score_reports: ScoreReportsReader | None = None,
        forecast_lab: ForecastLabReader | None = None,
    ):
        self.store, self.calendar, self.fno, self.followed = store, calendar, fno, followed
        self.chain, self.home, self.flows, self.weather = chain, home, flows, weather
        self.score_reports, self.forecast_lab = score_reports, forecast_lab

    def build(self, day: date) -> SessionRows:
        missing: list[str] = []
        series, actions = self._equity(day, missing)
        fo = self._files(NseDailyFoSource, min(day - FNO_WINDOW, history_start(day)), day, missing)
        indices = self._files(NseIndexCloseSource, day - INDEX_WINDOW, day, missing)
        delivery = self._file(NseDeliverySource.path_for(day), missing)
        names, members = (self._snapshot(s.path_for, day, missing) for s in (EquityListSource, Nifty500ListSource))
        followed = self.followed.on_or_before(day)
        if followed is None:
            missing.append(f"the stock tool's followed-companies list on or before {day}")
        actions += self._own_lists(day, unexplained(series, actions), missing)
        flows = self.flows.on(day)
        missing[:0] = self.flows.problems(day, flows)  # named reasons first: the alert shows the first few items
        if missing:
            raise IncompleteSession(day, missing)
        names = read_equity_list(names, EquityListSource.FILENAME)
        parsed = [(d, read_fo_rows(data, name)) for d, name, data in fo]  # each file parsed once
        history = self._fno_history([(d, rows) for d, rows in parsed if d >= day - FNO_WINDOW])
        rebased = on_todays_basis(series, actions, day)
        stocks = stock_rows(
            rebased,
            day,
            names,
            read_nifty500_list(members, Nifty500ListSource.FILENAME),
            read_delivery(delivery, NseDeliverySource.filename_for(day)),
            set(history),
            followed.companies,
            cut={symbol for symbol, bars in rebased.items() if len(bars) < len(series[symbol])},
        )
        figures = [(d, read_index_figures(data, name)) for d, name, data in indices]
        nifty_500 = [r for r in stocks if UNIVERSE_NIFTY_500 in r["u"]]
        chain = self.chain.build(day, parsed, indices)
        fno = self.fno.rows(history, day, names)
        return SessionRows(
            day, stocks, fno, index_rows(figures), industries(nifty_500), chain, self.home.on(day),
            frame_inputs(self.calendar, day), flows, self.weather.on(day) if self.weather else None,
            self.score_reports.on(day) if self.score_reports else None,
            self.forecast_lab.on(day) if self.forecast_lab else None,
        )  # fmt: skip

    def symbols_to_look_up(self, day: date) -> list[str]:
        """Symbols with an unexplained price jump in the session's window whose own corporate-action list is not
        archived yet (the daily routine archives them before building)."""
        missing: list[str] = []
        series, actions = self._equity(day, missing)
        if missing:
            raise IncompleteSession(day, missing)
        return [s for s in unexplained(series, actions) if self._find(self._own_list_path(s), day) is None]

    def _equity(self, day: date, missing: list[str]) -> tuple[dict[str, list[EquityBar]], list[CorporateAction]]:
        """The window's raw equity series, renamed stocks joined to their old symbol's sessions, and NSE's
        corporate-action list up to the session (empty if missing)."""
        equity = self._files(NseEquityBhavcopySource, day - EQUITY_WINDOW, day, missing)
        listed = self._snapshot(CorporateActionsSource.path_for, day, missing)
        renames = self._snapshot(SymbolChangeSource.path_for, day, missing)
        series = stock_series(read_equity_bhavcopy(data, name) for _, name, data in equity)
        actions = read_corporate_actions(listed, CorporateActionsSource.FILENAME) if listed else []
        changes = read_symbol_changes(renames, SymbolChangeSource.FILENAME) if renames else []
        return joined(series, [a for a in actions if a.ex_date <= day], [c for c in changes if c.effective <= day])

    def _own_lists(self, day: date, symbols: list[str], missing: list[str]) -> list[CorporateAction]:
        actions = []
        for symbol in symbols:
            data = self._find(self._own_list_path(symbol), day)
            if data is None:
                missing.append(f"{symbol}'s own corporate-action list (an unexplained price jump)")
            else:
                actions += [a for a in read_corporate_actions(data, f"{symbol}.json") if a.ex_date <= day]
        return actions

    @staticmethod
    def _own_list_path(symbol: str) -> Callable[[date], str]:
        return lambda d: CorporateActionsBySymbolSource.path_for_symbol(d, symbol)

    def _files(self, source, start: date, end: date, missing: list[str]) -> list[tuple[date, str, bytes]]:
        days = self.calendar.sessions(start, end)
        with ThreadPoolExecutor(max_workers=READERS) as pool:
            files = list(pool.map(lambda d: self.store.get(source.path_for(d)), days))
        missing += [source.path_for(d) for d, data in zip(days, files) if data is None]
        return [(d, source.filename_for(d), data) for d, data in zip(days, files) if data is not None]

    def _file(self, path: str, missing: list[str]) -> bytes:
        data = self.store.get(path)
        if data is None:
            missing.append(path)
        return data

    def _snapshot(self, path_for: Callable[[date], str], day: date, missing: list[str]) -> bytes | None:
        data = self._find(path_for, day)
        if data is None:
            missing.append(f"{path_for(day)} (no copy within {SNAPSHOT_SEARCH_DAYS} days)")
        return data

    def _find(self, path_for: Callable[[date], str], day: date) -> bytes | None:
        """The copy filed on `day` or the latest before it, else the nearest after it (a back-filled session)."""
        offsets = [-n for n in range(SNAPSHOT_SEARCH_DAYS + 1)] + list(range(1, SNAPSHOT_SEARCH_DAYS + 1))
        for offset in offsets:
            data = self.store.get(path_for(day + timedelta(days=offset)))
            if data is not None:
                return data
        return None

    @staticmethod
    def _fno_history(fo: list[tuple[date, list[dict[str, str]]]]) -> dict[str, list[UnderlyingDay]]:
        history: dict[str, list[UnderlyingDay]] = {}
        for d, rows in fo:
            for u in underlying_days(d, rows):
                history.setdefault(u.symbol, []).append(u)
        return history


def on_todays_basis(
    series: dict[str, list[EquityBar]], actions: list[CorporateAction], day: date
) -> dict[str, list[EquityBar]]:
    """Each symbol's bars adjusted for its corporate actions with an ex-date up to `day` (never a later one)."""
    by_symbol: dict[str, list[CorporateAction]] = {}
    for action in actions:
        if action.ex_date <= day:
            by_symbol.setdefault(action.symbol, []).append(action)
    return {symbol: adjusted(bars, by_symbol.get(symbol, [])) for symbol, bars in series.items()}
