"""Small synthetic files in NSE's layouts, each for one session, for the per-dataset promotion tests."""

from __future__ import annotations

import io
import zipfile
from datetime import date

from fno.ingestion.research_data.participant_oi import COLUMNS as OI_COLUMNS
from fno.ingestion.research_data.participant_oi import GROUP_COLUMNS, TOTAL_COLUMNS
from fno.shared.constants import PARTICIPANTS
from fno.shared.nse_files.nse_files import EQUITY_COLUMNS

CELL = 10  # contracts per group column, the same for every participant: every identity of NSE's file holds


def participant_file(day: date, title: str | None = None) -> bytes:
    """Participant-wise OI (or volume, same layout) as on `day`; `title` overrides the title line."""
    title = title if title is not None else f"Participant wise Open Interest (no. of contracts) as on {day:%b %d %Y}"
    group_total = CELL * len(GROUP_COLUMNS) // 2  # six long columns, six short ones
    row = [CELL] * len(GROUP_COLUMNS) + [group_total] * len(TOTAL_COLUMNS)
    lines = [title, ",".join(OI_COLUMNS)]
    lines += [",".join([name, *map(str, row)]) for name in PARTICIPANTS]
    lines.append(",".join(["TOTAL", *(str(v * len(PARTICIPANTS)) for v in row)]))
    return "\n".join(lines).encode()


def zipped(text: str) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        archive.writestr("file.csv", text)
    return out.getvalue()


def fo_udiff_file(*days: date) -> bytes:
    """A UDiFF F&O file (zipped) with one row per given trade date; `fo_udiff_file()` has a header and no rows."""
    rows = [",".join(["TradDt", "TckrSymb"]), *(f"{day.isoformat()},NIFTY" for day in days)]
    return zipped("\n".join(rows))


def equity_file(*days: date) -> bytes:
    rows = [",".join(EQUITY_COLUMNS)]
    rows += [f"{day.isoformat()},ABC,EQ,10,11,9,100,10" for day in days]
    return zipped("\n".join(rows))
