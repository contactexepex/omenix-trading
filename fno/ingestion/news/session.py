"""The news session (P2, R3 and R5): the shared polite `PacedSession` with no cookies and no redirects. Google sets
cookies and sends consent pages by redirect; neither is followed, answered or remembered. NSE's and Yahoo's sessions
are unchanged: this subclass is used by the news fetcher alone."""

from __future__ import annotations

from http.cookiejar import CookiePolicy

from fno.shared.constants import RESEARCH_USER_AGENT
from fno.shared.http_pacing import PacedSession


class RejectAllCookies(CookiePolicy):
    """Stores no cookie and sends none."""

    netscape, rfc2965, hide_cookie2 = True, False, False

    def set_ok(self, cookie, request) -> bool:
        return False

    def return_ok(self, cookie, request) -> bool:
        return False

    def domain_return_ok(self, domain, request) -> bool:
        return False

    def path_return_ok(self, path, request) -> bool:
        return False


class NewsSession(PacedSession):
    def __init__(self, pacer=None):
        super().__init__(pacer)
        self.cookies.set_policy(RejectAllCookies())
        self.headers["User-Agent"] = RESEARCH_USER_AGENT  # who we are, plainly (owner rule 50a79a43)

    def request(self, method, url, *args, **kwargs):
        kwargs["allow_redirects"] = False  # a redirect is a block, never followed
        return super().request(method, url, *args, **kwargs)
