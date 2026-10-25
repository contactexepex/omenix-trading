"""Starting the routine that reasons on new data (story O6). `RoutineTrigger` is the interface; `RoutineFireTrigger`
calls Claude Code's routine API trigger (`/fire`, a research preview checked on 13 Oct 2026: one bearer token per
routine, at most 30 fires an hour). Only the pointer is sent, never data. Every failure raises `FireFailed` with a
reason a person can act on; no message ever contains the token."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol

import requests

FIRE_URL = "https://api.anthropic.com/v1/claude_code/routines/{trigger_id}/fire"
FIRE_HEADERS = {"anthropic-beta": "experimental-cc-routine-2026-04-01", "anthropic-version": "2023-06-01"}
FIRE_TIMEOUT_SECONDS = 30
REFUSED_TOKEN = (
    "HTTP {status}: the routine's token was refused (expired or revoked); generate a new one on the routine's page"
)
RATE_LIMITED = "HTTP 429: more than 30 fires this hour; the next run fires the rest"
OTHER_STATUS = "HTTP {status} from the routine API"
NOT_REACHED = "routine API not reached ({error})"
SESSION_FIELDS = ("claude_code_session_url", "claude_code_session_id")


class FiredText(Protocol):
    """What a routine is fired with: a pointer that writes itself as one line of text (O6's batch pointer, F1's book
    pointer)."""

    def to_text(self) -> str: ...


class FireFailed(RuntimeError):
    """The routine was not started; the message says why (never containing a credential)."""


class RoutineTrigger(ABC):
    name: str = "routine"

    @abstractmethod
    def fire(self, pointer: FiredText) -> str:
        """Starts one run with the pointer as its text; returns the run's link (empty if the API gave none)."""


class RoutineFireTrigger(RoutineTrigger):
    def __init__(self, name: str, trigger_id: str, token: str, session: requests.Session | None = None):
        self.name, self._trigger_id, self._token = name, trigger_id, token
        self._session = session or requests.Session()

    def fire(self, pointer: FiredText) -> str:
        headers = {**FIRE_HEADERS, "Authorization": f"Bearer {self._token}"}
        try:
            response = self._session.post(
                FIRE_URL.format(trigger_id=self._trigger_id),
                headers=headers,
                json={"text": pointer.to_text()},
                timeout=FIRE_TIMEOUT_SECONDS,
            )
        except requests.RequestException as error:
            raise FireFailed(NOT_REACHED.format(error=type(error).__name__)) from None
        if response.status_code in (401, 403):
            raise FireFailed(REFUSED_TOKEN.format(status=response.status_code))
        if response.status_code == 429:
            raise FireFailed(RATE_LIMITED)
        if not response.ok:
            raise FireFailed(OTHER_STATUS.format(status=response.status_code))
        return _session_link(response)


def _session_link(response: requests.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return ""
    return next((str(body[f]) for f in SESSION_FIELDS if isinstance(body, dict) and body.get(f)), "")


class UnconfiguredTrigger(RoutineTrigger):
    """Used when the routine's settings are missing: every fire fails loudly, naming the settings to add."""

    def __init__(self, name: str, missing: tuple[str, ...]):
        self.name, self._missing = name, missing

    def fire(self, pointer: FiredText) -> str:
        raise FireFailed(f"routine {self.name} not configured: add the secrets {', '.join(self._missing)}")
