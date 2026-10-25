"""Composition root of the AI books' decision routine side (story F1t): the only place that picks the routine's
concrete transport, clock and publisher. Standard library only (no `fno.config`, which needs PyYAML), so
`python -m fno.ai_trading` needs no install."""

from __future__ import annotations

import os
import time
from pathlib import Path

from ..ai.book_wiring import REMOTE_SESSION_ENV
from ..ai.run_timing import RunTiming, routine_session_id
from ..ai.sealed_publish import SealedPublisher
from ..ai.transport import GitMainTransport
from ..models import now_ist
from .paths import DECISION_RUN, timing_path
from .session import DecisionSession
from .versions import REGISTRY

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def build_decision_session(root: Path = REPOSITORY_ROOT, env=os.environ) -> DecisionSession:
    transport = GitMainTransport(root)
    session = routine_session_id(env.get(REMOTE_SESSION_ENV, ""))
    timing = RunTiming(root, transport, now_ist, session, DECISION_RUN, timing_path)
    return DecisionSession(root, REGISTRY, SealedPublisher(transport, now_ist, time.sleep), timing)
