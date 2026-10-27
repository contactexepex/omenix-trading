"""F2 (judge 58 N2): a row that is an object but has a field that is not text (`"toDate": null`, `xbrl: 5`,
`broadCastDate: {}`) used to raise an AttributeError, which the librarian does not catch, and so ended the whole run.
Now every such field is a ValueError that names the field and the type (never the value), and the run goes on.
Offline: NSE is never called."""

from __future__ import annotations

from datetime import date, datetime
from unittest.mock import MagicMock

import pytest

from fno.ingestion.filings.index import (
    NseInsuranceResultsIndex,
    NseIntegratedResultsIndex,
    NseLegacyResultsIndex,
    NseShareholdingIndex,
    required_text,
    text_field,
)
from fno.ingestion.filings.librarian import FilingsLibrarian
from fno.shared.models import IST

SINCE = date(2024, 1, 1)
LINK = "https://nsearchives.nseindia.com/x.xml"
NOT_TEXT = [5, 1.5, True, {}, [], {"a": 1}]


def legacy_row(period_end: str = "toDate") -> dict:
    return {
        period_end: "31-Mar-2026",
        "broadCastDate": "20-Apr-2026 10:00:00",
        "exchdisstime": "20-Apr-2026 10:01:00",
        "xbrl": LINK,
        "consolidated": "Consolidated",
    }


def untimed_row() -> dict:
    return {**legacy_row(), "broadCastDate": "-", "exchdisstime": "-", "filingDate": "20-Apr-2026 10:00"}


INTEGRATED_ROW = {
    "type": "Integrated Filing- Financials",
    "qe_Date": "31-Mar-2026",
    "broadcast_Date": "20-Apr-2026 10:00:00",
    "creation_Date": "20-Apr-2026 09:00:00",
    "xbrl": LINK,
    "consolidated": "Consolidated",
}
SHAREHOLDING_ROW = {
    "date": "31-Mar-2026",
    "broadcastDate": "20-Apr-2026 10:00:00",
    "systemDate": "20-Apr-2026 09:00:00",
    "xbrl": LINK,
}

# (list class, the body it is given for one row, that row)
CASES = {
    "legacy": (NseLegacyResultsIndex, lambda row: [row], legacy_row()),
    "insurance": (NseInsuranceResultsIndex, lambda row: [row], legacy_row("periodEnd")),
    "legacy, no times": (NseLegacyResultsIndex, lambda row: [row], untimed_row()),
    "integrated": (NseIntegratedResultsIndex, lambda row: {"data": [row], "totalCount": 1}, INTEGRATED_ROW),
    "shareholding": (NseShareholdingIndex, lambda row: [row], SHAREHOLDING_ROW),
}
EVERY_FIELD = [(name, field) for name, (_, _, row) in CASES.items() for field in row if field != "type"]


def read(name: str, row: dict):
    index, body, _ = CASES[name]
    return index(lambda path, params: body(row)).filings("ACME", SINCE)


@pytest.mark.parametrize("name", CASES)
def test_the_untouched_row_reads(name):
    assert len(read(name, CASES[name][2])) == 1


@pytest.mark.parametrize("bad", NOT_TEXT)
@pytest.mark.parametrize(("name", "field"), EVERY_FIELD)
def test_a_field_that_is_not_text_is_a_named_value_error_in_every_list(name, field, bad):
    row = {**CASES[name][2], field: bad}
    with pytest.raises(ValueError, match=f"field {field}: NSE sent {type(bad).__name__}, not text"):
        read(name, row)


PERIOD_DATES = [("legacy", "toDate"), ("insurance", "periodEnd"), ("integrated", "qe_Date"), ("shareholding", "date")]


@pytest.mark.parametrize(("name", "field"), PERIOD_DATES)
def test_a_missing_or_null_period_date_is_a_named_failure(name, field):
    nulled = {**CASES[name][2], field: None}
    absent = {k: v for k, v in CASES[name][2].items() if k != field}
    for row in (nulled, absent):
        with pytest.raises(ValueError, match=f"field {field}: NSE sent none"):
            read(name, row)


@pytest.mark.parametrize("name", ["legacy", "integrated", "shareholding"])
def test_a_null_link_is_still_a_filing_without_an_xbrl_file(name):
    filings = read(name, {**CASES[name][2], "xbrl": None})
    assert [f.url for f in filings] == [""]


def test_the_failure_line_names_the_field_and_the_type_never_the_value():
    with pytest.raises(ValueError) as error:
        text_field({"xbrl": {"secret-looking-key": "secret-looking-value"}}, "xbrl")
    assert "secret-looking" not in str(error.value) and "xbrl" in str(error.value) and "dict" in str(error.value)
    assert required_text({"a": "x"}, "a") == "x" and text_field({}, "a") is None


def test_one_row_with_a_null_date_fails_its_own_read_and_the_run_goes_on():
    bodies = {"BAD": [{**legacy_row(), "toDate": None}], "GOOD": []}
    index = NseLegacyResultsIndex(lambda path, params: bodies[params["symbol"]])
    now = datetime(2026, 10, 27, 12, 0, tzinfo=IST)
    librarian = FilingsLibrarian([index], MagicMock(), MagicMock(), lambda: now, log=lambda text: None)
    report = librarian.run(["BAD", "GOOD"], SINCE, datetime(2026, 10, 27, 23, 0, tzinfo=IST))
    assert report.checked == ["BAD", "GOOD"] and report.failed == {"BAD"} and len(report.failures) == 1
    assert "field toDate" in report.failures[0]


@pytest.mark.parametrize("bad", NOT_TEXT)
def test_a_row_with_no_times_is_judged_placeable_only_by_a_readable_link(bad):
    """The classic list's old rows (no broadcast time, no filing date) are kept only when they have an XBRL file, so the
    link is read before anything else is."""
    row = {**legacy_row(), "broadCastDate": "-", "exchdisstime": "-", "xbrl": bad}
    with pytest.raises(ValueError, match="field xbrl: NSE sent"):
        read("legacy", row)
