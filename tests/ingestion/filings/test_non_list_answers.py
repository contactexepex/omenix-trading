"""F1: a results list that NSE answers with something other than a list (seen 27 Oct 2026 on the insurance list of
FLUOROCHEM and JUBLFOOD: `string indices must be integers`) is named in the failure line and fails only that company's
read. Offline: the parsers are fed bodies by hand, NSE is never called."""

from __future__ import annotations

from datetime import date, datetime
from unittest.mock import MagicMock

import pytest

from fno.ingestion.filings.index import (
    NseInsuranceResultsIndex,
    NseIntegratedResultsIndex,
    NseLegacyResultsIndex,
    NseShareholdingIndex,
    listed,
)
from fno.ingestion.filings.librarian import FilingsLibrarian
from fno.shared.models import IST

SINCE = date(2024, 1, 1)
LEGACY_ROWS = [
    {
        "toDate": "31-Mar-2026",
        "broadCastDate": "20-Apr-2026 10:00:00",
        "exchdisstime": "20-Apr-2026 10:00:00",
        "xbrl": "https://nsearchives.nseindia.com/x.xml",
        "consolidated": "Consolidated",
    }
]


def getter(body):
    return lambda path, params: body


@pytest.mark.parametrize("index", [NseLegacyResultsIndex, NseInsuranceResultsIndex, NseShareholdingIndex])
@pytest.mark.parametrize("body", [{"msg": "x"}, "an error page", 7])
def test_a_body_that_is_not_a_list_is_a_named_failure_not_a_type_error(index, body):
    with pytest.raises(ValueError, match="not a list of rows"):
        index(getter(body)).filings("ACME", SINCE)


@pytest.mark.parametrize("index", [NseLegacyResultsIndex, NseInsuranceResultsIndex, NseShareholdingIndex])
@pytest.mark.parametrize("body", [None, [], {}, ""])
def test_an_empty_answer_is_no_filings(index, body):
    assert index(getter(body)).filings("ACME", SINCE) == []


def test_a_normal_list_still_gives_its_filings():
    filings = NseLegacyResultsIndex(getter(LEGACY_ROWS)).filings("ACME", SINCE)
    assert [f.period_end for f in filings] == [date(2026, 3, 31)]


def test_the_failure_line_names_the_shape_and_the_keys_but_never_a_value():
    with pytest.raises(ValueError) as error:
        listed({"message": "secret-looking-value-123", "code": 7}, "NSE insurance results list")
    text = str(error.value)
    assert "['code', 'message']" in text and "secret-looking-value-123" not in text
    with pytest.raises(ValueError) as error:
        listed("secret-looking-text", "x")
    assert "secret-looking-text" not in str(error.value) and "str" in str(error.value)


def test_the_integrated_list_answered_with_a_list_is_a_named_failure():
    with pytest.raises(ValueError, match="not an object"):
        NseIntegratedResultsIndex(getter([1, 2])).filings("ACME", SINCE)


@pytest.mark.parametrize("data", [{"x": 1, "y": 2}, "text", ["a", "b"], 7])
def test_an_integrated_answer_whose_data_is_not_a_list_of_rows_is_a_named_failure_not_an_attribute_error(data):
    index = NseIntegratedResultsIndex(getter({"data": data, "totalCount": 5}))
    with pytest.raises(ValueError, match="not a list of rows"):
        index.filings("ACME", SINCE)


def test_a_list_of_text_rows_is_a_named_failure_for_every_list():
    for index in (NseLegacyResultsIndex, NseInsuranceResultsIndex, NseShareholdingIndex):
        with pytest.raises(ValueError, match="rows that are not objects"):
            index(getter(["a", "b"])).filings("ACME", SINCE)


def test_a_very_long_key_name_is_cut_in_the_failure_line():
    with pytest.raises(ValueError) as error:
        listed({"k" * 500: 1}, "x")
    assert len(str(error.value)) < 200


def test_one_odd_integrated_company_fails_its_own_read_and_the_run_goes_on():
    bodies = {"BAD": {"data": {"x": 1}, "totalCount": 5}, "GOOD": {"data": [], "totalCount": 0}}
    index = NseIntegratedResultsIndex(lambda path, params: bodies[params["symbol"]])
    now = datetime(2026, 10, 27, 12, 0, tzinfo=IST)
    librarian = FilingsLibrarian([index], MagicMock(), MagicMock(), lambda: now, log=lambda text: None)
    report = librarian.run(["BAD", "GOOD"], SINCE, datetime(2026, 10, 27, 23, 0, tzinfo=IST))
    assert report.checked == ["BAD", "GOOD"] and report.failed == {"BAD"} and len(report.failures) == 1


def test_one_odd_company_fails_its_own_read_and_the_run_goes_on_to_the_next():
    bodies = {"BAD": {"msg": "x"}, "GOOD": []}
    index = NseInsuranceResultsIndex(lambda path, params: bodies[params["symbol"]])
    now = datetime(2026, 10, 27, 12, 0, tzinfo=IST)
    librarian = FilingsLibrarian([index], MagicMock(), MagicMock(), lambda: now, log=lambda text: None)
    report = librarian.run(["BAD", "GOOD"], SINCE, datetime(2026, 10, 27, 23, 0, tzinfo=IST))
    assert report.checked == ["BAD", "GOOD"] and report.finished == ["GOOD"] and report.failed == {"BAD"}
    assert len(report.failures) == 1 and report.failures[0].startswith("BAD: NSE insurance results list not read:")
    assert "not a list" in report.failures[0] and not report.complete
