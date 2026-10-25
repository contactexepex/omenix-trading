"""Composition root of the book side (stories F1 and G5): the only place that picks the routine's concrete transport
and clock. Standard library only (no `fno.config`, which needs PyYAML), so `python -m fno.ai` needs no install."""

from __future__ import annotations

import os
import time
from pathlib import Path

from ..models import now_ist
from .book import BookSession
from .run_timing import RunTiming, routine_session_id
from .transport import GitMainTransport

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


REMOTE_SESSION_ENV = "CLAUDE_CODE_REMOTE_SESSION_ID"  # set in every cloud session; the routine's own id (story F8c)


def build_book_session(root: Path = REPOSITORY_ROOT, env=os.environ) -> BookSession:
    transport = GitMainTransport(root)
    timing = RunTiming(root, transport, now_ist, routine_session_id(env.get(REMOTE_SESSION_ENV, "")))
    return BookSession(root, transport, now_ist, time.sleep, timing)
