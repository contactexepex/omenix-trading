"""Groww as the 15-minute snapshot source (story A16). It holds only a `ReadOnlyGroww` (criterion 10): read calls by
name, nothing else. A failure is kept by its exception class name only (an exception's text could carry a credential).

Order inside a snapshot: the index quote first (the realised variance's input, sent right at the mark; with the
1-minute candle fallback when Groww gives the index no time), then the near future, the two chains, and one quote per
contract within 6% of the index level, at most 4 at a time and 4 a second, and nothing asked after the mark's quiet
window (story GW1)."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta

from ..models import IST, now_ist
from ..providers.groww import _payload, listed_expiries, parse_groww_chain, parse_groww_quote_book
from ..providers.groww_quiet_windows import QUIET_SECONDS
from .document import CallRecord, SnapshotDocument
from .expiry_plan import UNDERLYING, Expiries, ExpiryPlan
from .index_reading import CANDLE_SYMBOL, QUOTE_BASIS, candle_reading, candle_window, quote_reading
from .pacing import RatePacer
from .read_only import ReadOnlyGroww
from .source import IntradayQuoteSource

SPOT_BAND = 0.06  # strikes within 6% of the index level (design 2.1)
INDEX_SYMBOL = "NIFTY"
FUTURE_SYMBOL = "NIFTY{expiry:%y}{month}FUT"  # e.g. NIFTY26OCTFUT (step 0: the form get_quote accepts)
# GW1: A16 asks only inside its mark's quiet window, where every other Groww reader is refused, and at 4 a second, so
# its few unpaced extras never take a long mark over 300 a minute. Step 0 measured 5 a second clean with 4 workers.
WORKERS, PER_SECOND = 4, 4
WINDOW_ENDED = "QuietWindowEnded"  # not asked: the mark's quiet window had ended (judge 638 finding 2)
CALL_TIMEOUT_SECONDS = 10  # a hung call is a failure, never a stuck loop
QUOTES_RETRIED = "quotes_retried:{count}"
MAX_CODE_LENGTH = 12  # Groww's error codes are short words (e.g. 429); anything longer is not kept
EXPIRY_PLAN, INDEX_PARSE, CHAIN_PARSE = "expiry_plan", "index_parse", "chain_parse"
PARSE_ERRORS = (TypeError, ValueError, OverflowError, IndexError, KeyError, AttributeError, OSError)


def groww_listed_expiries(client: ReadOnlyGroww, clock: Callable[[], datetime] = now_ist) -> Callable[[], list[date]]:
    """Groww's expiry list read through the read-only client (for `ExpiryPlan`)."""
    return lambda: listed_expiries(client, UNDERLYING, clock().date())


class GrowwIntradaySource(IntradayQuoteSource):
    name = "groww"

    def __init__(self, client: ReadOnlyGroww, plan: ExpiryPlan, lot_size: int,
                 clock: Callable[[], datetime] = now_ist, pacer: RatePacer | None = None):  # fmt: skip
        self.client, self.plan, self.lot_size, self.clock = client, plan, lot_size, clock
        self.pacer = pacer or RatePacer(PER_SECOND)
        self._window_end = datetime.max.replace(tzinfo=IST)  # set by each `take`
        self._expiries: dict[date, Expiries] = {}
        self._prepare_notes: list[str] = []

    def prepare(self, session: date) -> None:
        self._prepare_notes = []
        for step, action in (("sign_in", lambda: self.client.EXCHANGE_NSE), (EXPIRY_PLAN, lambda: self._plan(session))):
            try:
                action()
            except Exception as exc:  # a note only: the snapshot tries again, and its own calls decide its status
                self._prepare_notes.append(f"prepare {step}: {type(exc).__name__}")

    def take(self, session: date, mark: datetime) -> SnapshotDocument:
        self._window_end = mark + timedelta(seconds=QUIET_SECONDS)
        index = self._call("index", lambda api: api.get_quote(trading_symbol=INDEX_SYMBOL, exchange=api.EXCHANGE_NSE,
                           segment=api.SEGMENT_CASH, timeout=CALL_TIMEOUT_SECONDS))  # fmt: skip
        doc = SnapshotDocument(self.name, UNDERLYING, session, mark, index, None, None,
                               notes=list(self._prepare_notes))  # fmt: skip
        self._read_index(doc)
        try:
            expiries = self._plan(session)
        except Exception as exc:
            doc.failures.append(f"{EXPIRY_PLAN}: {type(exc).__name__}")
            return self._finish(doc)
        doc.expiries = expiries.to_json()
        doc.future = self._future(expiries.monthly)
        chains = [self._chain(expiry, doc) for expiry in expiries.chains]
        doc.chains = [record for record, _ in chains]
        contracts = []
        for record, chain in chains:
            picked = self._contracts(chain, doc.index_level or chain.spot) if chain else []
            record.meta["contracts"] = len(picked)  # per chain: an empty chain is never hidden by the other one
            contracts += picked
        doc.expected_contracts = len(contracts)
        with ThreadPoolExecutor(WORKERS) as pool:
            doc.quotes = list(pool.map(self._quote, contracts))
            self._retry_failed(doc, contracts, pool)
        doc.two_sided_contracts = sum(1 for q in doc.quotes if _two_sided(q))
        return self._finish(doc)

    def _retry_failed(self, doc: SnapshotDocument, contracts: list[dict], pool: ThreadPoolExecutor) -> None:
        """Asks once more, at the same pace, for every quote that failed (16 Oct: single 429s happen even with one
        recorder). A retried quote keeps its own request and answer times; the note counts the retries."""
        failed = [i for i, q in enumerate(doc.quotes) if q.failure and contracts[i]["symbol"]]
        if not failed:
            return
        for i, record in zip(failed, pool.map(self._quote, [contracts[i] for i in failed]), strict=True):
            doc.quotes[i] = record
        doc.notes.append(QUOTES_RETRIED.format(count=len(failed)))

    def _read_index(self, doc: SnapshotDocument) -> None:
        """The level and its source time: the quote's own, else one finished 1-minute candle's close and end."""
        try:
            level, source_time = quote_reading(doc.index.payload)
            basis = QUOTE_BASIS if source_time else ""
            if source_time is None and not doc.index.failure:
                doc.index_candle = self._call("index_candle", lambda api: api.get_historical_candles(
                    exchange=api.EXCHANGE_NSE, segment=api.SEGMENT_CASH, groww_symbol=CANDLE_SYMBOL,
                    candle_interval=api.CANDLE_INTERVAL_MIN_1, timeout=CALL_TIMEOUT_SECONDS,
                    **candle_window(doc.index.response_received_at)))  # fmt: skip
                if not doc.index_candle.failure:
                    candle = candle_reading(doc.index_candle.payload, doc.index_candle.response_received_at, doc.mark)
                    level, source_time, basis = candle if candle[1] else (level, None, "")
        except PARSE_ERRORS as exc:  # an unexpected shape: no level, named, never a crash
            doc.failures.append(f"{INDEX_PARSE}: {type(exc).__name__}")
            return
        doc.index_level, doc.index_source_time, doc.index_basis = level, source_time, basis

    def _finish(self, doc: SnapshotDocument) -> SnapshotDocument:
        """Names every failed call in the document's failures and stamps when it was complete."""
        extra = [r for r in (doc.index_candle, doc.future) if r]
        doc.failures += [call.name for call in [doc.index, *extra, *doc.chains, *doc.quotes] if call.failure]
        doc.finished_at = self.clock()
        return doc

    def _plan(self, session: date) -> Expiries:
        if session not in self._expiries:
            self._expiries = {session: self.plan.plan(session)}
        return self._expiries[session]

    def _call(self, name: str, request, meta: dict | None = None) -> CallRecord:
        """Every call of a mark is paced, and none starts once the mark's quiet window has ended: it is recorded as a
        failure, unasked, as the other readers are let in then (GW1; a late or long mark ends there too)."""
        self.pacer.wait()
        sent = self.clock()
        if sent >= self._window_end:
            return CallRecord(name, sent, None, None, WINDOW_ENDED, meta or {})
        try:
            payload = _payload(request(self.client))
        except Exception as exc:  # name and code only: an exception's text could carry a credential
            return CallRecord(name, sent, None, None, failure_name(exc), meta or {})
        return CallRecord(name, sent, self.clock(), payload, "", meta or {})

    def _future(self, monthly: date) -> CallRecord:
        symbol = FUTURE_SYMBOL.format(expiry=monthly, month=f"{monthly:%b}".upper())
        return self._call(f"future {symbol}", lambda api: api.get_quote(trading_symbol=symbol,
                          exchange=api.EXCHANGE_NSE, segment=api.SEGMENT_FNO, timeout=CALL_TIMEOUT_SECONDS),
                          {"symbol": symbol})  # fmt: skip

    def _chain(self, expiry: date, doc: SnapshotDocument):
        record = self._call(f"chain {expiry}", lambda api: api.get_option_chain(exchange=api.EXCHANGE_NSE,
                            underlying=UNDERLYING, expiry_date=expiry.isoformat(), timeout=CALL_TIMEOUT_SECONDS),
                            {"expiry": expiry.isoformat()})  # fmt: skip
        if record.failure:
            return record, None
        try:
            return record, parse_groww_chain(
                record.payload, UNDERLYING, expiry, self.lot_size, record.response_received_at
            )
        except PARSE_ERRORS as exc:
            doc.failures.append(f"{CHAIN_PARSE} {expiry}: {type(exc).__name__}")
            return record, None

    @staticmethod
    def _contracts(chain, level: float) -> list[dict]:
        low, high = level * (1 - SPOT_BAND), level * (1 + SPOT_BAND)
        picked = sorted((strike, kind, q.symbol) for (strike, kind), q in chain.quotes.items() if low <= strike <= high)
        return [{"expiry": chain.expiry.isoformat(), "strike": s, "type": k, "symbol": sym} for s, k, sym in picked]

    def _quote(self, contract: dict) -> CallRecord:
        if not contract["symbol"]:
            return CallRecord(f"quote {contract['expiry']} {contract['strike']:g} {contract['type']}", self.clock(),
                              None, None, "NoTradingSymbol", contract)  # fmt: skip
        symbol = contract["symbol"]
        return self._call(f"quote {symbol}", lambda api: api.get_quote(trading_symbol=symbol,
                          exchange=api.EXCHANGE_NSE, segment=api.SEGMENT_FNO, timeout=CALL_TIMEOUT_SECONDS),
                          contract)  # fmt: skip


def failure_name(exc: Exception) -> str:
    """The class name, plus Groww's short error code when it gives one: Groww sends its rate limit as `status:
    FAILURE` with code `429`, which the SDK raises as a plain GrowwAPIException (16 Oct), so the class alone hid it.
    A code that is not a short word is dropped rather than risk keeping text."""
    code = str(getattr(exc, "code", "") or "")
    return f"{type(exc).__name__}:{code}" if code.isalnum() and len(code) <= MAX_CODE_LENGTH else type(exc).__name__


def _two_sided(record: CallRecord) -> bool:
    if record.failure or not isinstance(record.payload, dict):
        return False
    try:
        book = parse_groww_quote_book(record.meta.get("symbol", ""), record.payload)
    except PARSE_ERRORS:
        return False  # an unreadable book is not counted two-sided; its raw answer is kept
    return bool(book.bid and book.ask)
