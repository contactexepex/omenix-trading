"""Where G13's chains come from (section 1): A4's canonical 3 pm snapshots (Groww first, then NSE's public chain; A4c's
indices by their own stems) and, for the exploratory back-fill only, the end-of-day panel's traded closes."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import replace
from datetime import date

from ..quotes.drive_only_store import RawQuoteHashMismatch, RawQuoteMissing, RawQuoteStoreUnavailable
from ..quotes.recorder import DATASET, NONE_MARKER, NSE_DATASET, QuoteSnapshotRecorder
from ..research_data.panel_reader import NiftyPanel
from ..research_data.quote_snapshots import parse_snapshot
from ..storage.raw_store import RawFileStore
from .chain import ChainDay, ChainSource, ExpiryChain, Quote
from .constants import SOURCE_GROWW, SOURCE_NSE, SOURCE_PANEL

DATASETS = {SOURCE_GROWW: DATASET, SOURCE_NSE: NSE_DATASET}
UNREADABLE = "{source} raw quote file unreadable: {error}"
PANEL_EXPIRIES = 2  # the two nearest monthlies, as A4 records
PANEL_CLOSE_TIME = "T15:30:00+05:30"


class ChainUnavailable(RuntimeError):
    """A chain was recorded but cannot be read (Drive down, file missing or failing its hash)."""


class SnapshotChains(ChainSource):
    """The day's canonical snapshot of each source in turn; a `none` or absent marker means not captured there."""

    def __init__(self, store: RawFileStore, sources: Sequence[str] = (SOURCE_GROWW, SOURCE_NSE)):
        self.store, self.sources = store, tuple(sources)

    def chain(self, underlying: str, day: date) -> ChainDay | None:
        """The first source with a readable chain; a source that fails to read is passed over (and named), so a
        Drive outage on Groww's file still records NSE's chain. Raises only when a chain exists and none is readable."""
        failures = []
        for source in self.sources:
            try:
                found = self._from(source, underlying, day)
            except ChainUnavailable as error:
                failures.append(str(error))
                continue
            if found is not None:
                return replace(found, source_note="; ".join(failures))
        if failures:
            raise ChainUnavailable("; ".join(failures))
        return None

    def _from(self, source: str, underlying: str, day: date) -> ChainDay | None:
        dataset = DATASETS[source]
        marker = self.store.get(
            QuoteSnapshotRecorder.path(day, f"{underlying.lower()}_{day:%Y%m%d}.canonical", dataset)
        )
        snapshot_id = marker.decode().strip() if marker else NONE_MARKER
        if snapshot_id == NONE_MARKER:
            return None
        try:
            csv_bytes = self.store.get(QuoteSnapshotRecorder.path(day, f"{snapshot_id}.csv", dataset))
            meta_bytes = self.store.get(QuoteSnapshotRecorder.path(day, f"{snapshot_id}.meta.json", dataset))
        except (RawQuoteMissing, RawQuoteHashMismatch, RawQuoteStoreUnavailable) as error:
            raise ChainUnavailable(UNREADABLE.format(source=source, error=error)) from error
        if not csv_bytes or not meta_bytes:
            raise ChainUnavailable(UNREADABLE.format(source=source, error=f"{snapshot_id} files absent"))
        snapshot = parse_snapshot(day, csv_bytes, meta_bytes)
        expiries = tuple(
            ExpiryChain(expiry, tuple(Quote(q.strike, q.kind, q.mid, q.bid, q.ask, q.valid, None, q.contract_id)
                                      for q in snapshot.quotes_for(expiry)),
                        _future(snapshot.future_for(expiry)))
            for expiry in snapshot.expiries
        )  # fmt: skip
        finished = json.loads(meta_bytes)["finished_at"]
        return ChainDay(underlying, day, source, snapshot_id, hashlib.sha256(csv_bytes).hexdigest(), finished,
                        snapshot.spot, expiries)  # fmt: skip


def _future(quote) -> float | None:
    return quote.close if quote is not None and quote.close > 0 else None


class PanelEodChains(ChainSource):
    """NIFTY's end-of-day panel: traded closes as prices (no bid/ask), the two nearest futures' expiries, the session's
    close as spot. Exploratory back-fill only (`backfill_eod`)."""

    def __init__(self, panel: NiftyPanel):
        self.panel = panel

    def chain(self, underlying: str, day: date) -> ChainDay | None:
        session = self.panel.session_on(day)
        futures = sorted(f.expiry for f in self.panel.futures.get(day, ()) if f.expiry >= day)[:PANEL_EXPIRIES]
        if session is None or session.underlying is None or not futures:
            return None
        expiries = []
        for expiry in futures:
            future = self.panel.future_on(day, expiry)
            options = sorted(self.panel.options_on(day, expiry), key=lambda o: (o.strike, o.kind))
            quotes = tuple(Quote(o.strike, o.kind, o.close, volume=o.volume) for o in options)
            expiries.append(ExpiryChain(expiry, quotes, future.close if future and future.volume > 0 else None))
        digest = hashlib.sha256(repr((session, expiries)).encode()).hexdigest()
        return ChainDay(underlying, day, SOURCE_PANEL, f"panel_{day:%Y%m%d}", digest, f"{day}{PANEL_CLOSE_TIME}",
                        session.underlying, tuple(expiries))  # fmt: skip
