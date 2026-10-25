"""The AI books' clock (protocol v2 section 5, applied to Books 2 and 3): the commitment counts only if GitHub logged
its push by 15:15:00 IST (the same deadline as `ForecastRecordV2.on_time`); the reveal waits until a few seconds after
it, so no book's answer is readable before every commitment is in; the collection waits for reveals until 15:30. A run
that starts after 15:13 (the capture's last pull for the snapshot) can only give late answers: it fires no AI book.
The times themselves are v2's run terms (`run_terms.V2_TERMS`, G11); these names keep their v2 callers."""

from __future__ import annotations

from datetime import date, datetime, time

from ..models import IST
from .run_terms import V2_TERMS

LATEST_START = time(15, 13)  # protocol v2 section 5: the capture pulls for the snapshot until 15:13 IST at most

receipt_deadline = V2_TERMS.receipt_deadline
reveal_from = V2_TERMS.reveal_opens
reveal_deadline = V2_TERMS.reveal_deadline


def latest_start(day: date) -> datetime:
    return datetime.combine(day, LATEST_START, tzinfo=IST)
