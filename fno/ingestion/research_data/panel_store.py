"""The warm-up closes the feature history needs before the first panel session (story A10): the file's name and the
content hash used to record each source file's SHA-256."""

from __future__ import annotations

import hashlib

WARMUP_FILE = "warmup_closes.csv"  # closes before the first session, for feature history (story A10)


def file_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
