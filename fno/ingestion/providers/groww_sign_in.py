"""One Groww sign-in per process and token day, and never a storm (story GW1, part 1).

Groww allows 150 sign-ins per 24 hours (research/school/probes/2026-10-22-p0-1-groww-chain.md). Before GW1 a failed
sign-in left no client, so every later call signed in again: A16 alone could make 160-210 a day and lock the next
morning out. Here a failed sign-in is remembered: no new try before its back-off (5, then 10 minutes), at most
`TRIES_A_DAY` tries per process and token day, and every call in between fails at once without reaching the network.

The day's worst case (judge 637 m1): about 38 processes sign in on a session day. A16's 7 fires each run up to 2h45m
and are rerun at the tool's 2-hour limit, so up to 21 processes. The daily run's Groww children (NIFTY, A4c, v4, E3,
A16b) make 5, and 10 with a rerun. Then the pre-open capture (1), the school's 4 slots and 2 by hand. With every
sign-in failing all day: 38 x 3 = 114 tries, under Groww's 150 per 24 hours. A normal day: about 38."""

from __future__ import annotations

import threading
from collections.abc import Callable
from datetime import date, datetime, time, timedelta

from fno.shared.models import now_ist

TOKEN_EXPIRY_TIME_IST = time(6, 0)
FIRST_WAIT = timedelta(minutes=5)
TRIES_A_DAY = 3
PAUSED = "Groww sign-in paused after {failures} failed tr{plural} this token day; {when}"
NEXT_TRY = "next try at {at:%H:%M:%S} IST"
NO_MORE_TRIES = "no more tries until 06:00 IST"
FIRST_FAILURE = (
    "Groww sign-in failed ({name}); this process tries again after {minutes} minutes, at most {tries} tries a day"
)


def token_day(moment: datetime) -> date:
    """Tokens live from 06:00 IST to 06:00 the next day; this names the window a moment falls in."""
    return (moment - timedelta(hours=TOKEN_EXPIRY_TIME_IST.hour, minutes=TOKEN_EXPIRY_TIME_IST.minute)).date()


class GrowwSignInPaused(RuntimeError):
    """A call asked for the client while the sign-in waits out its back-off; nothing reached Groww."""


class _SignInFailed(Exception):
    """Carries a failed sign-in's own error and its alert line out of the lock."""

    def __init__(self, error: Exception, alert: str):
        super().__init__()
        self.error, self.alert = error, alert


class GrowwSignIn:
    def __init__(self, sign_in: Callable[[], object], clock: Callable[[], datetime] = now_ist,
                 on_failure: Callable[[str], None] | None = None):  # fmt: skip
        """`sign_in` makes the client (one sign-in); `on_failure` hears the first failure of each token day, as one
        line naming the exception's class only (its text could carry a credential)."""
        self.sign_in, self.clock, self.on_failure = sign_in, clock, on_failure
        self._lock = threading.Lock()
        self._client, self._client_day = None, None
        self._failed_day: date | None = None
        self._failures, self._next_try = 0, None

    def client(self):
        """The signed-in client of this token day, signing in only when allowed; raises otherwise. The first failure's
        alert is sent after the lock is released, so a slow alert never holds the other threads."""
        alert = None
        try:
            with self._lock:
                return self._client_now()
        except _SignInFailed as failed:
            alert = failed.alert
            raise failed.error from None
        finally:
            if alert and self.on_failure is not None:
                self.on_failure(alert)

    def _client_now(self):
        now = self.clock()
        day = token_day(now)
        if self._client is not None and self._client_day == day:
            return self._client
        if self._failed_day != day:
            self._failed_day, self._failures, self._next_try = day, 0, None
        self._refuse_while_paused(now)
        try:
            client = self.sign_in()
        except Exception as exc:
            raise _SignInFailed(exc, self._failed(now, exc)) from None
        self._client, self._client_day, self._failures, self._next_try = client, day, 0, None
        return client

    def _refuse_while_paused(self, now: datetime) -> None:
        if self._failures >= TRIES_A_DAY:
            raise GrowwSignInPaused(self._paused(NO_MORE_TRIES))
        if self._next_try is not None and now < self._next_try:
            raise GrowwSignInPaused(self._paused(NEXT_TRY.format(at=self._next_try)))

    def _failed(self, now: datetime, exc: Exception) -> str:
        """Counts the failure and sets the next try; the alert line for the day's first failure, else ""."""
        self._failures += 1
        self._next_try = now + FIRST_WAIT * 2 ** (self._failures - 1)
        if self._failures > 1:
            return ""
        return FIRST_FAILURE.format(name=type(exc).__name__, minutes=FIRST_WAIT.seconds // 60, tries=TRIES_A_DAY)

    def _paused(self, when: str) -> str:
        return PAUSED.format(failures=self._failures, plural="y" if self._failures == 1 else "ies", when=when)
