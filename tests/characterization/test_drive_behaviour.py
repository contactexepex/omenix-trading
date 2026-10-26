"""Story R1c, step 0: today's exact Drive behaviour, pinned BEFORE the Drive session moves onto the shared resilience
layer. DriveSession: which statuses are retried, the waits (2, 8, 30, 60), the one re-sign-in on 401, Google's 403 rate
limits, what is raised. The upload store: a create retried after a dropped connection makes exactly one file (Drive
answers 409 to the repeat, and the bytes are read back). No network, no real sleep. Passes on `main` unchanged."""

from __future__ import annotations

import hashlib
import json

import pytest
import requests

from fno.ingestion.storage.drive_session import DriveSession
from fno.ingestion.storage.google_drive_upload import GoogleDriveUploadStore
from fno.ingestion.storage.raw_store import RawFileConflict, StoredCopyDamaged
from fno.shared.resilience.retry import RetryPolicy
from fno.shared.resilience.settings import settings_for


class Reply:
    def __init__(self, status=200, body=None, content=b""):
        self.status_code, self.body, self.content = status, body, content

    def json(self):
        if self.body is None:
            raise ValueError("no body")
        return self.body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)


def google_error(status, *reasons):
    return Reply(status, {"error": {"errors": [{"reason": r} for r in reasons]}})


class Scripted:
    """A requests.Session stand-in answering from a script (exceptions are raised), counting calls."""

    def __init__(self, *script):
        self.script, self.calls, self.headers = list(script), 0, {}

    def get(self, url, **kw):
        self.calls += 1
        step = self.script.pop(0)
        if isinstance(step, BaseException):
            raise step
        return step

    post = patch = get


def no_jitter(waits):
    """The injected policy (the story's one adaptation): the live waits are the table plus up to 25% more."""
    return RetryPolicy(settings_for("drive").retry, waits.append, uniform=lambda low, high: low)


def drive(*script, tokens=None):
    waits, session = [], Scripted(*script)
    issued = iter(tokens or ["t1", "t2", "t3"])
    return DriveSession(lambda: next(issued), session, waits.append, no_jitter(waits)), session, waits


@pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
def test_each_temporary_status_is_retried_after_2_8_30_60_then_raised(status):
    d, session, waits = drive(*[Reply(status)] * 5)
    with pytest.raises(requests.HTTPError):
        d.get("u")
    assert waits == [2, 8, 30, 60] and session.calls == 5


def test_recovery_after_a_temporary_failure():
    d, session, waits = drive(Reply(503), Reply(200, {"ok": 1}))
    assert d.get("u").json() == {"ok": 1} and waits == [2] and session.calls == 2


@pytest.mark.parametrize("status", [400, 404, 409, 418])
def test_other_statuses_are_raised_at_once_without_a_wait(status):
    d, session, waits = drive(Reply(status))
    with pytest.raises(requests.HTTPError):
        d.get("u")
    assert waits == [] and session.calls == 1


def test_accepted_statuses_are_returned_not_raised():
    d, session, waits = drive(Reply(409))
    assert d.post("u", accept=frozenset({409})).status_code == 409 and waits == []


def test_a_plain_403_is_a_refusal_not_retried():
    d, session, waits = drive(google_error(403, "forbidden"))
    with pytest.raises(requests.HTTPError, match="Google: forbidden"):
        d.get("u")
    assert waits == [] and session.calls == 1


@pytest.mark.parametrize("reason", ["rateLimitExceeded", "userRateLimitExceeded"])
def test_googles_403_rate_limit_is_retried_on_the_same_waits(reason):
    d, session, waits = drive(google_error(403, reason), google_error(403, reason), Reply(200))
    assert d.get("u").status_code == 200 and waits == [2, 8]


def test_a_rate_limit_403_that_never_clears_is_raised_with_googles_reason_after_5_calls():
    d, session, waits = drive(*[google_error(403, "rateLimitExceeded")] * 5)
    with pytest.raises(requests.HTTPError, match="Google: rateLimitExceeded"):
        d.get("u")
    assert waits == [2, 8, 30, 60] and session.calls == 5


def test_a_403_with_no_readable_body_is_a_refusal():
    d, session, waits = drive(Reply(403))
    with pytest.raises(requests.HTTPError):
        d.get("u")
    assert waits == [] and session.calls == 1


def test_a_dropped_connection_and_a_timeout_are_retried_then_raised_as_they_were():
    d, session, waits = drive(requests.ConnectionError("x"), requests.Timeout("y"), Reply(200))
    assert d.get("u").status_code == 200 and waits == [2, 8]
    d, session, waits = drive(*[requests.ConnectionError("down")] * 5)
    with pytest.raises(requests.ConnectionError):
        d.get("u")
    assert waits == [2, 8, 30, 60] and session.calls == 5


def test_401_signs_in_again_once_and_retries_without_a_wait():
    d, session, waits = drive(Reply(401), Reply(200), tokens=["old", "new"])
    assert d.get("u").status_code == 200 and waits == [] and session.headers["Authorization"] == "Bearer new"


def test_a_second_401_is_raised_and_the_token_is_asked_only_twice():
    asked = []
    session = Scripted(Reply(401), Reply(401))
    d = DriveSession(lambda: asked.append(1) or "t", session, lambda s: None)
    with pytest.raises(requests.HTTPError):
        d.get("u")
    assert len(asked) == 2 and session.calls == 2


def test_401_then_a_temporary_failure_is_still_retried():
    d, session, waits = drive(Reply(401), Reply(503), Reply(200), tokens=["a", "b"])
    assert d.get("u").status_code == 200 and waits == [2]


def test_only_one_re_sign_in_per_call_even_after_a_temporary_failure():
    asked = []
    session = Scripted(Reply(401), Reply(503), Reply(401), Reply(200))
    d = DriveSession(lambda: asked.append(1) or "t", session, lambda s: None)
    with pytest.raises(requests.HTTPError):
        d.get("u")  # the second 401 is not answered with a third sign-in
    assert len(asked) == 2 and session.calls == 3


def test_a_rate_limit_reason_on_a_status_other_than_403_is_not_retried():
    d, session, waits = drive(google_error(400, "rateLimitExceeded"))
    with pytest.raises(requests.HTTPError):
        d.get("u")
    assert waits == [] and session.calls == 1


def test_the_session_is_signed_in_on_construction():
    d, session, _ = drive(tokens=["first"])
    assert session.headers["Authorization"] == "Bearer first"


# ---- the upload store: a retried create makes exactly one file --------------------------------------------------


class FakeGoogle:
    """A small in-memory Drive behind the requests-level interface. `drop_after_create` makes the first create apply on
    the server and then drop the connection, as a real network can."""

    def __init__(self, drop_after_create=False):
        self.items, self.headers, self.drop = {"root": ("", None, b"")}, {}, drop_after_create
        self.folder_ids: set[str] = set()
        self.created, self.ids = [], iter(f"id{n}" for n in range(1000))

    def get(self, url, params=None, **kw):
        params = params or {}
        if url.endswith("/generateIds"):
            return Reply(200, {"ids": [next(self.ids) for _ in range(params["count"])]})
        if params.get("alt") == "media":
            return Reply(200, content=self.items[url.rsplit("/", 1)[1]][2])
        query = params["q"]
        parent = query.split("'")[1]
        name = query.split("name = '")[1].split("'")[0]
        folder = "mimeType = " in query
        hits = [
            {"id": i, "name": n}
            for i, (n, p, _) in self.items.items()
            if p == parent and n == name and (i in self.folder_ids) == folder
        ]
        return Reply(200, {"files": hits})

    def post(self, url, files=None, params=None, **kw):
        if files is not None:
            meta = json.loads(files["metadata"][1])
            data = files["file"][1]
        else:
            meta, data = kw["json"], b""
        if meta["id"] in self.items:
            return Reply(409, {"error": {"errors": [{"reason": "fileIdInUse"}]}})
        self.items[meta["id"]] = (meta["name"], meta["parents"][0], data)
        self.created.append(meta["name"])
        if "folder" in meta.get("mimeType", ""):
            self.folder_ids = self.folder_ids | {meta["id"]}
        if self.drop and files is not None:
            self.drop = False
            raise requests.ConnectionError("dropped after the create got through")
        return Reply(200, {"id": meta["id"], "md5Checksum": hashlib.md5(data).hexdigest()})  # noqa: S324


def store(fake, waits=None):
    waits = [] if waits is None else waits
    return GoogleDriveUploadStore("root", lambda: "t", fake, waits.append, no_jitter(waits))


def test_a_create_retried_after_a_dropped_connection_yields_exactly_one_file():
    fake, waits = FakeGoogle(drop_after_create=True), []
    s = store(fake, waits)
    s.put("nse/a/file.csv", b"bytes")
    assert fake.created.count("file.csv") == 1 and waits == [2]
    assert s.get("nse/a/file.csv") == b"bytes"


def test_the_same_bytes_again_change_nothing_and_different_bytes_conflict():
    fake = FakeGoogle()
    s = store(fake)
    s.put("nse/a/file.csv", b"bytes")
    s.put("nse/a/file.csv", b"bytes")
    assert fake.created.count("file.csv") == 1
    with pytest.raises(RawFileConflict):
        s.put("nse/a/file.csv", b"other")


def test_a_repeat_create_whose_bytes_differ_is_reported_as_damage():
    fake = FakeGoogle(drop_after_create=True)
    s = store(fake)
    original = fake.post

    def corrupt(url, **kw):
        if kw.get("files") is not None:
            name, _, mime = kw["files"]["file"]
            kw["files"] = {
                **kw["files"],
                "file": (name, b"damaged", mime),
            }  # what the server holds is not what we meant
        return original(url, **kw)

    fake.post = corrupt
    with pytest.raises(StoredCopyDamaged):
        s.put("nse/a/file.csv", b"bytes")


def test_ids_are_reserved_from_drive_in_a_batch_of_100():
    fake = FakeGoogle()
    s = store(fake)
    s.put("nse/a/file.csv", b"bytes")
    assert len(s._new_ids) == 100 - 3  # one batch of 100 asked for; a folder, a folder and a file used
