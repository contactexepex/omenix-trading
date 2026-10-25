"""Forecast records as files (stories G2 and G3): CSV text in the frozen schema's column order, gzip with fixed bytes
(no file name, no time) for the back-fill, and reading them back with the schema's checks."""

from __future__ import annotations

import csv
import gzip
import io
from collections.abc import Iterable

from .schema import RECORD_COLUMNS, ForecastRecord
from .schema_v2 import RECORD_COLUMNS_V2, ForecastRecordV2


def records_csv(records: Iterable[ForecastRecord]) -> str:
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=RECORD_COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(r.row() for r in records)
    return out.getvalue()


def records_gzip(records: Iterable[ForecastRecord]) -> bytes:
    buffer = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buffer, mtime=0) as fh:
        fh.write(records_csv(records).encode("utf-8"))
    return buffer.getvalue()


def read_records(text: str) -> list[ForecastRecord]:
    return [ForecastRecord.from_row(row) for row in csv.DictReader(io.StringIO(text))]


def records_csv_v2(records: Iterable[ForecastRecordV2]) -> str:
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=RECORD_COLUMNS_V2, lineterminator="\n")
    writer.writeheader()
    writer.writerows(r.row() for r in records)
    return out.getvalue()


def read_records_v2(text: str) -> list[ForecastRecordV2]:
    return [ForecastRecordV2.from_row(row) for row in csv.DictReader(io.StringIO(text))]
