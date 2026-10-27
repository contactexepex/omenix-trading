"""Talks to the Google Drive API for every Drive store: signs in again once when the access token expires and retries
Google's temporary failures after growing waits. Knows nothing about folders or files."""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import UTC, datetime

import requests

from fno.ingestion.storage.retry_policy import retry_after_seconds
from fno.shared.resilience.outcomes import Outcome, Verdict
from fno.shared.resilience.retry import RetryPolicy
from fno.shared.resilience.settings import settings_for

TIMEOUT_SECONDS = 60
UNAUTHORIZED = 401  # the access token expired: sign in again once
TRANSIENT = frozenset({429, 500, 502, 503, 504})  # Google's temporary answers: wait and try again
DRIVE_RETRY_AFTER_CAP_SECONDS = 120.0  # a Retry-After wait is at most this; the shortest workflow timeout is 900 s
FORBIDDEN = 403
RATE_LIMIT_REASONS = frozenset({"rateLimitExceeded", "userRateLimitExceeded"})  # Google sends these as 403, not 429


class DriveSession:
    def __init__(
        self,
        token: Callable[[], str],
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
        policy: RetryPolicy | None = None,
    ):
        """`token` returns a fresh access token; it is asked again when Drive answers 401 (tokens last about an
        hour, so a long run would otherwise fail midway). `policy`: the retry waits (the shared `drive` policy by
        default; a test passes one with no jitter)."""
        self.token, self.sleep = token, sleep
        self.policy = policy or RetryPolicy(settings_for("drive").retry, sleep)
        self.session = session or requests.Session()
        self._sign_in()

    def _sign_in(self) -> None:
        self.session.headers["Authorization"] = f"Bearer {self.token()}"

    def request(self, method: str, url: str, accept: frozenset[int] = frozenset(), **kwargs) -> requests.Response:
        """A call that signs in again once when the token has expired and retries temporary failures (429, 5xx,
        dropped connections) after growing waits. Statuses in `accept` are returned as answers; any other error, or
        the last temporary failure, is raised."""
        send = getattr(self.session, method)
        signed_in_again = False

        def attempt() -> requests.Response:
            nonlocal signed_in_again
            response = send(url, timeout=TIMEOUT_SECONDS, **kwargs)
            if getattr(response, "status_code", None) == UNAUTHORIZED and not signed_in_again:
                self._sign_in()  # not a retry: no wait, not counted
                signed_in_again = True
                response = send(url, timeout=TIMEOUT_SECONDS, **kwargs)
            return response

        done = self.policy.run(attempt, _classify)
        if done.error is not None:
            raise done.error  # a dropped connection or a timeout, re-raised as it was
        if done.outcome is Outcome.OK and getattr(done.result, "status_code", None) in accept:
            return done.result
        _raise_with_reason(done.result)
        return done.result

    def get(self, url: str, **kwargs) -> requests.Response:
        return self.request("get", url, **kwargs)

    def post(self, url: str, **kwargs) -> requests.Response:
        return self.request("post", url, **kwargs)


def _classify(response: requests.Response | None, error: Exception | None) -> Verdict:
    """What an answer means for the retry policy: a dropped connection or timeout, a temporary status and Google's 403
    rate limit are tried again (a `Retry-After` is a floor, capped); every other answer ends the call here."""
    if error is not None:
        if isinstance(error, (requests.ConnectionError, requests.Timeout)):
            return Verdict(Outcome.RETRY, answered=False)
        raise error
    status = getattr(response, "status_code", None)
    if status in TRANSIENT or _rate_limited(response, status):
        asked = retry_after_seconds((getattr(response, "headers", None) or {}).get("Retry-After"), datetime.now(UTC))
        return Verdict(Outcome.RETRY, retry_after=None if asked is None else min(asked, DRIVE_RETRY_AFTER_CAP_SECONDS))
    return Verdict(Outcome.OK)


def _reasons(response: requests.Response) -> list[str]:
    """Google's error reasons (e.g. "userRateLimitExceeded") from an error answer; empty when it gives none."""
    try:
        errors = response.json().get("error", {}).get("errors", [])
    except (ValueError, AttributeError):
        return []
    return [e["reason"] for e in errors if isinstance(e, dict) and isinstance(e.get("reason"), str)]


def _rate_limited(response: requests.Response, status: int | None) -> bool:
    """Drive's 403 that means "slow down" (retry later), told apart from a real refusal by Google's error reason."""
    return status == FORBIDDEN and any(reason in RATE_LIMIT_REASONS for reason in _reasons(response))


def _raise_with_reason(response: requests.Response) -> None:
    """raise_for_status, with Google's reason added so a failure says why (never a credential: reasons are codes)."""
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        reasons = _reasons(response)
        if not reasons:
            raise
        raise requests.HTTPError(f"{exc} (Google: {', '.join(reasons)})", response=response) from exc
