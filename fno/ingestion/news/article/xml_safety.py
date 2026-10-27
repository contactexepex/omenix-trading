"""Refusing hostile XML before anything parses it (P2b, must-do 3): a poll is open-web bytes. A feed needs no DTD, so
any DOCTYPE or ENTITY declaration (the way entity-expansion and external-entity attacks are written) is refused
outright, as is a poll over the size cap. The scan is on the raw bytes, case-insensitive, and also on a copy with
the NUL bytes removed, so a UTF-16 or UTF-32 document cannot hide its declaration from an ASCII search; a BOM or
leading white space changes nothing."""

from __future__ import annotations

from fno.ingestion.news import codes

MAX_POLL_BYTES = 5 * 1024 * 1024
FORBIDDEN = (b"<!doctype", b"<!entity")


def refusal(data: bytes) -> str | None:
    """The fixed code to refuse the poll with, or None when it may be parsed."""
    if len(data) > MAX_POLL_BYTES:
        return codes.POLL_TOO_LARGE
    for view in (data.lower(), data.replace(b"\x00", b"").lower()):
        if any(marker in view for marker in FORBIDDEN):
            return codes.UNSAFE_XML
    return None
