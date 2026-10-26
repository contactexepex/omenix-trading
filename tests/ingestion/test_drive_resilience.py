"""Story R1c: the Drive session on the shared resilience layer, and the invariant that no manifest row, receipt, log
row or index entry is ever written for a file Drive does not hold. Offline; Drive is a fake, sleeps are recorded."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
import requests

from fno.ingestion.storage import drive_session
from fno.ingestion.storage.data_store import DataStore
from fno.ingestion.storage.drive_session import DRIVE_RETRY_AFTER_CAP_SECONDS, DriveSession
from fno.ingestion.storage.manifest_folder import FingerprintingStore, ManifestFolder
from fno.ingestion.storage.raw_source import ParticipantOiSource
from fno.ingestion.storage.raw_store import RawFileStore
from fno.ingestion.storage.receipts import ReceiptFolder
from fno.shared.resilience.retry import RetryPolicy
from fno.shared.resilience.settings import settings_for
from tests.characterization.test_drive_behaviour import Reply, Scripted, google_error

DAY_PATH = ParticipantOiSource.path_for(datetime(2026, 10, 12, tzinfo=UTC).date())


def policy(waits, jitter_top=False):
    return RetryPolicy(
        settings_for("drive").retry, waits.append, uniform=(lambda lo, hi: hi) if jitter_top else (lambda lo, hi: lo)
    )


def drive(*script, jitter_top=False):
    waits, session = [], Scripted(*script)
    return DriveSession(lambda: "t", session, waits.append, policy(waits, jitter_top)), session, waits


def with_retry_after(status, value):
    reply = Reply(status)
    reply.headers = {"Retry-After": value}
    return reply


# ---- the retry layer --------------------------------------------------------------------------------------------


def test_live_waits_lie_between_the_old_table_and_a_quarter_more():
    waits = []
    session = Scripted(*[Reply(503)] * 5)
    live = DriveSession(lambda: "t", session, waits.append)  # the default policy, real jitter
    with pytest.raises(requests.HTTPError):
        live.get("u")
    for wait, floor in zip(waits, (2, 8, 30, 60)):
        assert floor <= wait <= floor * 1.25


def test_a_retry_after_of_300_waits_120_each_time_and_all_five_tries_are_made():
    d, session, waits = drive(*[with_retry_after(503, "300")] * 5)
    with pytest.raises(requests.HTTPError):
        d.get("u")
    assert waits == [DRIVE_RETRY_AFTER_CAP_SECONDS] * 4 == [120.0] * 4 and session.calls == 5  # capped, never stopped


def test_a_retry_after_raises_a_wait_but_never_shortens_one():
    d, session, waits = drive(with_retry_after(503, "30"), with_retry_after(503, "1"), Reply(200))
    assert d.get("u").status_code == 200 and waits == [30, 8]  # the first wait stretched; 1 s leaves the 8 s floor


def test_a_retry_after_on_the_last_try_gives_up_without_a_wait():
    d, session, waits = drive(*[Reply(503)] * 4, with_retry_after(503, "60"))
    with pytest.raises(requests.HTTPError):
        d.get("u")
    assert waits == [2, 8, 30, 60] and session.calls == 5


def test_a_rate_limit_403_honours_retry_after_too():
    reply = google_error(403, "rateLimitExceeded")
    reply.headers = {"Retry-After": "45"}
    d, _, waits = drive(reply, Reply(200))
    assert d.get("u").status_code == 200 and waits == [45]


def test_the_401_re_sign_is_not_a_retry_and_adds_one_send_not_one_wait():
    d, session, waits = drive(Reply(401), *[Reply(503)] * 5)
    with pytest.raises(requests.HTTPError):
        d.get("u")
    assert waits == [2, 8, 30, 60] and session.calls == 6  # 401, its re-send (the first try), then four more tries


def test_drive_settings_have_no_breaker_and_nothing_in_drive_code_builds_one():
    assert settings_for("drive").breaker is None
    root = Path(__file__).resolve().parents[2] / "fno" / "ingestion" / "storage"
    for name in ("drive_session.py", "google_drive.py", "google_drive_upload.py", "drive_items.py", "index_store.py"):
        assert "CircuitBreaker" not in (root / name).read_text("utf-8"), name


def test_the_old_wait_table_is_gone_and_every_drive_call_goes_through_the_session():
    root = Path(__file__).resolve().parents[2] / "fno" / "ingestion" / "storage"
    assert "RETRY_WAITS" not in (root / "drive_session.py").read_text("utf-8")
    assert not hasattr(drive_session, "RETRY_WAITS")
    for path in root.glob("*.py"):  # the only direct HTTP call besides the session is the OAuth token refresh
        if path.name not in ("drive_session.py", "raw_source.py", "owner_token.py"):
            text = path.read_text("utf-8")
            assert "self.session.get(" not in text and "self.session.post(" not in text, path.name


# ---- the invariant: no record without its file ----------------------------------------------------------------


class DropsAfterTheCreate(RawFileStore):
    """A Drive store whose create got through on the server, then the connection died and every try after it failed:
    the file is there, `put` raises (what the caller sees once the retries are exhausted)."""

    name = "Drive that dies after the create"

    def __init__(self):
        self.files: dict[str, bytes] = {}

    def get(self, path):
        return self.files.get(path)

    def put(self, path, data):
        self.files[path] = data
        raise requests.ConnectionError("every try after the create failed")


class Spy:
    """A record writer that fails the test if it is ever asked to write."""

    def __getattr__(self, name):
        def fail(*args, **kwargs):
            raise AssertionError(f"a record was written ({name}) for a file Drive did not confirm")

        return fail


def test_archive_put_writes_no_manifest_row_for_a_file_that_was_not_confirmed(tmp_path):
    manifests = ManifestFolder(tmp_path / "manifests")
    store = FingerprintingStore(DropsAfterTheCreate(), manifests, [ParticipantOiSource])
    with pytest.raises(requests.ConnectionError):
        store.put(DAY_PATH, b"bytes")
    assert not list((tmp_path / "manifests").rglob("*.csv"))  # a file without a row: healed by the next run's re-put


def test_data_put_writes_no_receipt_for_a_file_that_was_not_confirmed(tmp_path):
    receipts = ReceiptFolder(tmp_path / "receipts")
    store = DataStore(DropsAfterTheCreate(), "data", receipts, "writer", "run1")
    with pytest.raises(requests.ConnectionError):
        store.put("closes/a.json", b"bytes")
    assert receipts.read("data/closes/a.json") is None and not list((tmp_path / "receipts").rglob("*"))


def test_receipt_repair_writes_no_receipt_when_the_file_cannot_be_read_back(tmp_path):
    from fno.ingestion.storage.receipt_repair import ReceiptRepair

    item = SimpleNamespace(folder=False, created="2026-10-12T00:00:00Z")

    class Items:
        def copies(self, path):
            return None, [item]

        def content(self, found):
            raise requests.ConnectionError("the read-back failed on every try")

    receipts = ReceiptFolder(tmp_path / "receipts")
    with pytest.raises(requests.ConnectionError):
        ReceiptRepair(Items(), receipts).receipt_for("data/closes/a.json", "w", "r1")
    assert not list((tmp_path / "receipts").rglob("*"))


def test_revision_archive_adds_no_index_row_for_a_revision_that_was_not_confirmed(tmp_path):
    from fno.ingestion.storage.raw_source import PublishedFile
    from fno.ingestion.storage.revisions import RevisionArchive, RevisionIndex

    class Raw(RawFileStore):
        name = "raw"

        def get(self, path):
            return b"the archived bytes"

        def put(self, path, data):
            raise AssertionError("raw files are never rewritten")

    index = RevisionIndex(tmp_path / "index", [ParticipantOiSource])
    archive = RevisionArchive(
        Raw(),
        DropsAfterTheCreate(),
        index,
        ManifestFolder(tmp_path / "m"),
        clock=lambda: datetime(2026, 10, 12, tzinfo=UTC),
    )
    with pytest.raises(requests.ConnectionError):
        archive.capture(DAY_PATH, PublishedFile(b"a NEWER version", None))
    assert not list((tmp_path / "index").rglob("*.csv")) and archive.stored == []


def test_global_cue_collector_logs_no_snapshot_row_for_a_copy_that_was_not_confirmed(tmp_path):
    from fno.ingestion.global_cues.collector import CueCollector
    from fno.ingestion.global_cues.snapshot_log import SnapshotLog

    log = SnapshotLog(tmp_path / "log")
    collector = CueCollector(None, DropsAfterTheCreate(), log, lambda: datetime(2026, 10, 12, tzinfo=UTC))
    source = SimpleNamespace(dataset="cues/x", cue="x")
    request = SimpleNamespace(name="f.csv", url="https://example.org/f.csv", form="csv")
    with pytest.raises(requests.ConnectionError):
        collector._archive(source, request, b"bytes", datetime(2026, 10, 12, 9, 0, tzinfo=UTC))
    assert not list((tmp_path / "log").rglob("*.csv"))


def test_candle_archive_writes_no_manifest_row_for_a_copy_that_was_not_confirmed(tmp_path):
    from datetime import date

    from fno.ingestion.intraday.candle_archive import CandleArchive
    from fno.ingestion.intraday.candle_source import FIFTEEN_MINUTES, CandleAnswer

    now = datetime(2026, 10, 12, tzinfo=UTC)
    answer = CandleAnswer(FIFTEEN_MINUTES, date(2026, 10, 1), date(2026, 10, 2), b"{}", [], now, now)
    with pytest.raises(requests.ConnectionError):
        CandleArchive(DropsAfterTheCreate(), tmp_path / "manifests").save(answer)
    assert not list((tmp_path / "manifests").rglob("*.csv"))


def test_snapshot_files_save_raises_before_any_ledger_row_can_name_the_copy(tmp_path):
    from datetime import date

    from fno.ingestion.intraday.snapshot_files import SnapshotFiles

    files = SnapshotFiles("groww", DropsAfterTheCreate(), Spy())  # the ledger is never touched by `save`
    with pytest.raises(requests.ConnectionError):
        files.save(date(2026, 10, 12), datetime(2026, 10, 12, 9, 30, tzinfo=UTC), b"bytes")


def test_filings_archive_records_no_manifest_row_for_a_filing_that_was_not_confirmed(monkeypatch):
    from fno.ingestion.filings import archive as filings_archive

    monkeypatch.setattr(filings_archive, "read_facts", lambda data: None)
    filing = SimpleNamespace(kind="other", path="filings/x/f.xml", url="https://example.org/f.xml")
    archive = filings_archive.FilingArchive(DropsAfterTheCreate(), Spy(), lambda: datetime(2026, 10, 12, tzinfo=UTC))
    with pytest.raises(requests.ConnectionError):
        archive.save(filing, b"<xbrl/>")


def test_quote_writer_marks_the_sidecar_not_saved_when_the_drive_save_fails():
    from fno.ingestion.quotes.recorder import RAW_FILE_NOT_SAVED, QuoteSnapshotRecorder

    recorder = SimpleNamespace(store=DropsAfterTheCreate())
    error, detail = QuoteSnapshotRecorder._save_quote_file(recorder, "quotes/a.csv", b"rows")
    assert error.startswith(RAW_FILE_NOT_SAVED) and "ConnectionError" in error and detail  # the sidecar says not saved


def test_index_file_replace_that_fails_changes_nothing_and_raises():
    """In-place index files keep no record. A replace whose every try fails raises and the previous version stays."""
    from fno.ingestion.storage.index_store import DriveIndexStore
    from tests.characterization.test_drive_behaviour import FakeGoogle, store

    fake = FakeGoogle()
    drive_store = store(fake, [])
    index = DriveIndexStore(drive_store, "index")
    index.replace("a.json", b"first")
    file_id = next(i for i, (n, _, _) in fake.items.items() if n == "a.json")
    fake.patch = lambda url, **kw: Reply(503)
    with pytest.raises(requests.HTTPError):
        index.replace("a.json", b"second")
    assert fake.items[file_id][2] == b"first"  # not half-written


# ---- the quote sidecar's reader (the one row-equivalent that may be written without its file) ------------------


def reader_store(sidecar, private_files):
    from fno.ingestion.quotes.drive_only_store import SIDECAR, DriveOnlyQuoteStore

    class Repo(RawFileStore):
        name = "repo"

        def __init__(self):
            self.files = {"quotes/day/s1" + SIDECAR: sidecar}

        def get(self, path):
            return self.files.get(path)

        def put(self, path, data):
            self.files[path] = data

    class Private(RawFileStore):
        name = "private"
        reads = 0

        def get(self, path):
            Private.reads += 1
            return private_files.get(path)

        def put(self, path, data):
            raise AssertionError

    return DriveOnlyQuoteStore(Repo(), lambda: Private(), "quotes", "unset"), Private


def quote_path():
    from fno.ingestion.quotes.drive_only_store import QUOTE_FILE

    return "quotes/day/s1" + QUOTE_FILE


def test_a_sidecar_that_says_not_saved_returns_none_and_never_reads_drive():
    store, private = reader_store(b'{"raw_file_saved": false, "csv_sha256": "x"}', {})
    assert store.get(quote_path()) is None and private.reads == 0


def test_a_sidecar_that_says_saved_with_no_file_in_drive_raises():
    from fno.ingestion.quotes.drive_only_store import RawQuoteMissing

    store, _ = reader_store(b'{"csv_sha256": "x"}', {})
    with pytest.raises(RawQuoteMissing):
        store.get(quote_path())


def test_a_file_whose_hash_differs_from_the_sidecar_raises():
    from fno.ingestion.quotes.drive_only_store import RawQuoteHashMismatch

    store, _ = reader_store(b'{"csv_sha256": "not-the-hash"}', {quote_path(): b"rows"})
    with pytest.raises(RawQuoteHashMismatch):
        store.get(quote_path())
    good, _ = reader_store(
        f'{{"csv_sha256": "{hashlib.sha256(b"rows").hexdigest()}"}}'.encode(), {quote_path(): b"rows"}
    )
    assert good.get(quote_path()) == b"rows"
