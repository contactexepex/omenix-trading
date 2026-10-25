"""G13c's paths in Drive's `data` area (O9) and its receipts in the checkout."""

from __future__ import annotations

ROOT = "itm_chance/v1"
CALIBRATION = f"{ROOT}/calibration"
DATA_AREA = "data"  # O9's area (`fno/storage/data_wiring.py`)


def calibration_path(underlying: str, last_settled: str | None, content_sha256: str) -> str:
    """Named by the last settled expiry and the content's SHA-256: new inputs, a new path; the same bytes, the same."""
    return f"{CALIBRATION}/{underlying.lower()}_{last_settled or 'none'}_{content_sha256[:12]}.json"


def receipt_pathspecs() -> tuple[str, ...]:
    return (f"receipts/{DATA_AREA}/{ROOT}/",)
