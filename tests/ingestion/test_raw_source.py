"""NSE archive source adapters (``fno/ingestion/storage/raw_source.py``) driven by a FAKE HTTP session.

These assert the adapter builds the right URL and archive path, round-trips a file name to its day, and maps HTTP
status to the retry policy's outcome (bytes, None for 404, ``RawFileRefused`` for 403). No real NSE call."""

from __future__ import annotations

from datetime import date

import pytest

from fno.ingestion.storage.raw_source import (
    FiiDerivativeStatsSource,
    NseDailyFoSource,
    NseIndexCloseSource,
    NseLegacyFoSource,
    ParticipantOiSource,
    RawFileRefused,
    RawSourceUnavailable,
)

DAY = date(2026, 10, 12)


def test_daily_fo_path_filename_and_url() -> None:
    assert NseDailyFoSource.filename_for(DAY) == "BhavCopy_NSE_FO_0_0_0_20261012_F_0000.csv.zip"
    path = NseDailyFoSource.path_for(DAY)
    assert path == "nse/derivatives/fo-bhavcopy/2026/10/BhavCopy_NSE_FO_0_0_0_20261012_F_0000.csv.zip"
    assert NseDailyFoSource.url_for(path) == (
        "https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_20261012_F_0000.csv.zip"
    )
    assert NseDailyFoSource.day_for_path(path) == DAY


def test_legacy_fo_filename_round_trip_and_nested_url() -> None:
    name = NseLegacyFoSource.filename_for(DAY)
    assert name == "fo12OCT2026bhav.csv.zip"
    assert NseLegacyFoSource.day_for(name) == DAY  # inverse of filename_for
    path = NseLegacyFoSource.path_for(DAY)
    # The legacy archive nests the file under /YYYY/MON/.
    assert NseLegacyFoSource.url_for(path) == (
        "https://nsearchives.nseindia.com/content/historical/DERIVATIVES/2026/OCT/fo12OCT2026bhav.csv.zip"
    )


def test_index_close_and_participant_and_fii_filenames() -> None:
    assert NseIndexCloseSource.filename_for(DAY) == "ind_close_all_12102026.csv"
    assert ParticipantOiSource.filename_for(DAY) == "fao_participant_oi_12102026.csv"
    assert FiiDerivativeStatsSource.filename_for(DAY) == "fii_stats_12-Oct-2026.xls"


def test_fetch_returns_bytes_on_200(http_fakes) -> None:
    session = http_fakes.Session(routes=http_fakes.Response(status_code=200, content=b"zip-bytes"))
    source = NseDailyFoSource(session, sleep=lambda _s: None)
    assert source.fetch(NseDailyFoSource.path_for(DAY)) == b"zip-bytes"
    assert session.requested == [NseDailyFoSource.url_for(NseDailyFoSource.path_for(DAY))]


def test_fetch_none_on_404(http_fakes) -> None:
    source = NseDailyFoSource(http_fakes.Session(routes=http_fakes.Response(status_code=404)), sleep=lambda _s: None)
    assert source.fetch(NseDailyFoSource.path_for(DAY)) is None


def test_fetch_refused_on_403(http_fakes) -> None:
    source = NseDailyFoSource(http_fakes.Session(routes=http_fakes.Response(status_code=403)), sleep=lambda _s: None)
    with pytest.raises(RawFileRefused):
        source.fetch(NseDailyFoSource.path_for(DAY))


def test_fetch_published_carries_last_modified(http_fakes) -> None:
    headers = {"Last-Modified": "Mon, 12 Oct 2026 10:00:00 GMT"}
    session = http_fakes.Session(routes=http_fakes.Response(status_code=200, content=b"csv", headers=headers))
    source = NseIndexCloseSource(session, sleep=lambda _s: None)
    published = source.fetch_published(NseIndexCloseSource.path_for(DAY))
    assert published is not None
    assert published.data == b"csv"
    assert published.last_modified is not None
    assert published.last_modified.year == 2026 and published.last_modified.tzinfo is not None


def test_last_written_uses_head(http_fakes) -> None:
    headers = {"Last-Modified": "Mon, 12 Oct 2026 10:00:00 GMT"}
    session = http_fakes.Session(routes=http_fakes.Response(status_code=200, headers=headers))
    source = NseDailyFoSource(session, sleep=lambda _s: None)
    stamp = source.last_written(NseDailyFoSource.path_for(DAY))
    assert stamp is not None
    assert session.method_calls == ["HEAD"]  # a header-only read, never a full download


def test_server_error_retries_then_raises(http_fakes) -> None:
    waits: list[float] = []
    session = http_fakes.Session(routes=http_fakes.Response(status_code=503))
    source = NseDailyFoSource(session, sleep=waits.append)
    with pytest.raises(RawSourceUnavailable):
        source.fetch(NseDailyFoSource.path_for(DAY))
    assert waits  # it waited between retries (never a real sleep)
