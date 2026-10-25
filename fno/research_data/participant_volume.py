"""Reads NSE's daily participant-wise trading volume (story A23): the sister file of participant OI, read by A8's
reader with one difference measured in the back-fill (21 Oct 2026). NSE left stray rows with no participant name
under the TOTAL row on 15 Sep 2021, 14 Oct 2022 and 18 Oct 2022 (someone's sums). As A8 ignores columns without a
header name, rows without a participant name are ignored here; the five named rows still pass every check."""

from __future__ import annotations

import csv
import io
from datetime import date

from .participant_oi import ParticipantOi, read_participant_oi

FIRST_BODY_LINE = 2  # the title, then the header


def read_participant_volume(data: bytes, filename: str, day: date) -> ParticipantOi:
    """Contracts bought (`long`) and sold (`short`) per participant and group; BadFile as A8's reader."""
    return read_participant_oi(_named_rows_only(data), filename, day)


def _named_rows_only(data: bytes) -> bytes:
    try:
        lines = data.decode("utf-8-sig").splitlines()
    except UnicodeDecodeError:
        return data  # A8's reader names it
    kept = lines[:FIRST_BODY_LINE] + [line for line in lines[FIRST_BODY_LINE:] if _named(line)]
    return "\n".join(kept).encode()


def _named(line: str) -> bool:
    cells = next(csv.reader(io.StringIO(line)), [])
    return bool(cells and cells[0].strip())
