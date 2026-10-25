"""A rehearsal reaches no live source (story REH1): in a rehearsing process every outbound HTTP call is checked
before it is made. Allowed: Google's Drive API and token endpoint (the dryrun store's reads and writes; the store, not
this guard, keeps writes under `dryrun/`), and Slack's posting calls. Refused: every market source (Groww, NSE,
global cues), Anthropic, GitHub's API and anything else, so no real AI routine is ever fired. Checked twice: at
`requests`' session (the whole URL), and at the connect of `http.client` and of `urllib3` (the host) for code that does
not use requests (judge 560: urllib3 overrides http.client's connect). A raw socket is not checked: nothing in the
package opens one (the stated limit)."""

from __future__ import annotations

import http.client
from urllib.parse import urlsplit

import requests

ALLOWED_HOSTS = frozenset({"www.googleapis.com", "oauth2.googleapis.com", "slack.com", "files.slack.com"})
SLACK_CALLS = ("/api/chat.postMessage", "/api/files.getUploadURLExternal", "/api/files.completeUploadExternal",
               "/api/conversations.info", "/api/api.test")  # fmt: skip
REFUSED = "rehearsal: no live call ({method} {host}{path}); a rehearsal reads only the day's recorded data"


class RehearsalCallRefused(RuntimeError):
    """A rehearsing process tried to reach a live source: refused before the call is made."""


def allowed(method: str, url: str) -> bool:
    parts = urlsplit(url)
    if parts.hostname not in ALLOWED_HOSTS:
        return False
    return parts.hostname != "slack.com" or parts.path in SLACK_CALLS


def check(method: str, url: str) -> None:
    if not allowed(method, url):
        parts = urlsplit(url)
        raise RehearsalCallRefused(REFUSED.format(method=method.upper(), host=parts.hostname, path=parts.path))


def install() -> None:
    """Wraps the two call paths of this process once; a second install changes nothing."""
    if getattr(requests.Session.request, "_rehearsal_guard", False):
        return
    import urllib3.connection

    request = requests.Session.request

    def guarded_request(self, method, url, *args, **kwargs):
        check(method, url)
        return request(self, method, url, *args, **kwargs)

    guarded_request._rehearsal_guard = True
    requests.Session.request = guarded_request
    # urllib3's HTTPS connection has a connect of its own, apart from its HTTP one and from http.client's
    connections = (http.client.HTTPConnection, urllib3.connection.HTTPConnection, urllib3.connection.HTTPSConnection)
    for connection in connections:
        connection.connect = _guarded_connect(connection.connect)


def _guarded_connect(connect):
    def guarded(self):
        host = getattr(self, "_tunnel_host", None) or self.host
        if host not in ALLOWED_HOSTS:
            raise RehearsalCallRefused(REFUSED.format(method="CONNECT", host=host, path=""))
        return connect(self)

    return guarded
