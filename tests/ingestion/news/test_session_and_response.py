"""The news session (P2, R3 and R5) and what an answer is (N11): no cookies, no redirects followed, and a consent page,
a redirect or a refusal is a block, not a parse failure."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler

import pytest
import requests
from requests.adapters import BaseAdapter

from fno.ingestion.news import codes
from fno.ingestion.news.response_check import classify
from fno.ingestion.news.session import NewsSession
from fno.shared.nse_pacer import NsePacer
from tests.ingestion.news.fakes import CONSENT_PAGE, RSS, LocalServer

URL = "https://feeds.example/rss"


class Wire(BaseAdapter):
    """Answers from a script and keeps every request it was sent."""

    def __init__(self, *answers):
        super().__init__()
        self.answers, self.sent = list(answers), []

    def send(self, request, **kwargs):
        self.sent.append(request)
        status, headers = self.answers.pop(0)
        response = requests.Response()
        response.status_code, response._content, response.url = status, RSS, request.url
        response.headers.update(headers)
        response.request = request
        return response

    def close(self):
        pass


def session(*answers):
    s = NewsSession(NsePacer(spacing={"feeds.example": 0.0}, clock=lambda: 0.0))
    wire = Wire(*answers)
    s.mount("https://", wire)
    return s, wire


class CookieServer(LocalServer):
    """/set answers with a cookie, /look records the Cookie header it was sent."""

    def __init__(self):
        seen = self.seen = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                if self.path == "/look":
                    seen.append(self.headers.get("Cookie"))
                self.send_response(200)
                if self.path == "/set":
                    self.send_header("Set-Cookie", "consent=yes; Path=/")
                self.send_header("Content-Length", "0")
                self.end_headers()

            def log_message(self, *args):
                pass

        super().__init__(Handler)
        self.url = self.base


def test_a_cookie_set_by_an_answer_is_neither_kept_nor_sent_back():
    server = CookieServer()
    try:
        news = NewsSession(NsePacer(spacing={"127.0.0.1": 0.0}, clock=lambda: 0.0))
        news.get(f"{server.url}/set", timeout=10)
        news.get(f"{server.url}/look", timeout=10)
        assert server.seen == [None] and len(news.cookies) == 0
        ordinary = requests.Session()  # the control: an ordinary session does send it back
        ordinary.get(f"{server.url}/set", timeout=10)
        ordinary.get(f"{server.url}/look", timeout=10)
        assert server.seen[1] == "consent=yes"
    finally:
        server.close()


def test_a_redirect_is_returned_not_followed():
    s, wire = session((302, {"Location": "https://consent.example/x"}))
    response = s.get(URL)
    assert response.is_redirect and len(wire.sent) == 1


def test_the_session_says_who_it_is():
    assert "fno-desk" in session()[0].headers["User-Agent"]


@pytest.mark.parametrize("root", [b"<rss version='2.0'>", b"<feed xmlns='x'>", b"<rdf:RDF xmlns:rdf='x'>"])
def test_a_feed_in_any_of_the_three_formats_is_a_feed(root):
    assert classify(200, False, b"<?xml version='1.0'?>" + root) == codes.FETCHED


@pytest.mark.parametrize(
    ("status", "redirect", "body", "code"),
    [
        (200, False, CONSENT_PAGE, codes.BLOCK_PAGE),  # a consent or CAPTCHA page at HTTP 200
        (200, False, b"", codes.BLOCK_PAGE),
        (302, True, RSS, codes.BLOCK_PAGE),
        (301, False, RSS, codes.BLOCK_PAGE),
        (429, False, RSS, codes.REFUSED),
        (403, False, RSS, codes.REFUSED),
        (500, False, RSS, codes.FETCH_FAILED),
        (404, False, RSS, codes.FETCH_FAILED),
    ],
)
def test_every_other_answer_has_its_fixed_code(status, redirect, body, code):
    assert classify(status, redirect, body) == code
