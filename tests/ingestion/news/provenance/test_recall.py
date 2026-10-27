"""NP11: the recall report counts tagged articles by the kind of feed that found them; read only; counts only."""

from __future__ import annotations

import re
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

from fno.ingestion.news import codes
from fno.ingestion.news.cli import cmd_news_recall
from fno.ingestion.news.cluster_record.article_source import Candidates
from fno.ingestion.news.provenance import file
from fno.ingestion.news.provenance.index import ProvenanceIndex
from fno.ingestion.news.provenance.model import BROAD, TARGETED, UNKNOWN, path_of
from fno.ingestion.news.provenance.recall import BUCKETS, RecallRun, bucket_of
from fno.ingestion.storage.raw_store import AreaStore, LocalFolderStore
from tests.ingestion.news.cluster.helpers import art
from tests.ingestion.news.cluster_record.helpers import AS_OF
from tests.ingestion.news.tagging.helpers import TAGGER

ROOT = Path(__file__).resolve().parents[4]
SALT = "s" * 16
BROAD_FEED, TARGETED_FEED, OTHER_FEED = ("feed-01", BROAD), ("q-0123456789ab", TARGETED), ("feed-09", UNKNOWN)


class World:
    """Articles in memory, provenance files on a local drive, the tagger of the tagging tests."""

    def __init__(self, tmp_path, articles, held):
        self.articles, self.drive = articles, LocalFolderStore(tmp_path / "drive")
        record = AreaStore(self.drive, "raw")
        by_day: dict = {}
        for key, pairs in held.items():
            by_day.setdefault(AS_OF.date(), {})[key] = frozenset(pairs)
        for day, pairs in by_day.items():
            record.put(path_of(day), file.to_bytes(day, 0, SALT, pairs))
        self.index = ProvenanceIndex(record)

    def candidates(self, as_of, lookback=None):
        return Candidates(tuple(self.articles), 0)

    def inputs(self, articles, as_of):
        return SimpleNamespace(preparer=SimpleNamespace(tagger=TAGGER))

    def run(self, days=14):
        return RecallRun(self, self, self.index).run(AS_OF, days)


def world(tmp_path):
    articles = [
        art("a-broad", "Zzalpha posts record profit"),
        art("a-targeted", "Zzbeta wins a big order"),
        art("a-both", "Zzgamma Foods expands"),
        art("a-unknown", "Zzdelta launches a product"),
        art("a-none", "Zzomega opens a plant"),
        art("a-untagged", "Markets close flat on Tuesday"),
    ]
    held = {
        "a-broad": [BROAD_FEED],
        "a-targeted": [TARGETED_FEED],
        "a-both": [BROAD_FEED, TARGETED_FEED, OTHER_FEED],
        "a-unknown": [OTHER_FEED],
        "a-untagged": [BROAD_FEED],
    }
    return World(tmp_path, articles, held)


def test_each_tagged_article_is_in_exactly_one_bucket_and_untagged_ones_are_not_counted(tmp_path):
    report = world(tmp_path).run()
    assert report.ok and report.counts["tagged"] == 5
    assert {name: report.counts[name] for name in BUCKETS} == {
        "broad_only": 1, "targeted_only": 1, "both": 1, "unknown_only": 1, "no_provenance": 1,
    }  # fmt: skip
    assert (
        report.counts["with_unknown_feed"] == 2
    )  # the article found by both kinds and an unlabelled feed, and the unknown one
    assert report.line() == (
        "recall: window_days 14, tagged 5, broad_only 1, targeted_only 1, both 1, unknown_only 1, no_provenance 1, "
        "with_unknown_feed 2"
    )


def test_the_bucket_of_a_set_of_feeds_follows_their_scopes_only():
    assert bucket_of(frozenset()) == "no_provenance"
    assert bucket_of(frozenset({BROAD_FEED, OTHER_FEED})) == "broad_only"
    assert bucket_of(frozenset({TARGETED_FEED, OTHER_FEED})) == "targeted_only"
    assert bucket_of(frozenset({BROAD_FEED, TARGETED_FEED})) == "both"
    assert bucket_of(frozenset({OTHER_FEED})) == "unknown_only"


def test_a_damaged_provenance_file_stops_the_report_with_its_code(tmp_path):
    w = world(tmp_path)
    w.drive.put(f"raw/{path_of(AS_OF.date(), 1)}", b"damaged")
    report = w.run()
    assert not report.ok and report.line() == "news provenance-recall stopped, provenance_unreadable 1"


def test_days_before_the_window_are_not_read_and_the_window_is_a_parameter(tmp_path):
    w = world(tmp_path)
    old = AS_OF.date() - timedelta(days=30)
    AreaStore(w.drive, "raw").put(path_of(old), file.to_bytes(old, 0, SALT, {"a-none": frozenset({BROAD_FEED})}))
    assert w.run(days=14).counts["no_provenance"] == 1  # the 30-day-old file is outside the window
    assert w.run(days=40).counts["no_provenance"] == 0 and w.run(days=40).counts["broad_only"] == 2


LABELS = {"recall:", "window_days", "tagged", "with_unknown_feed", *BUCKETS, "news", "provenance-recall", "stopped"}
NUMBER = re.compile(r"^\d+$")


def unexplained_words(text: str) -> list[str]:
    words = [word.strip(":,") for line in text.splitlines() for word in line.split()]
    return [w for w in words if w and w.rstrip(":") not in {x.rstrip(":") for x in LABELS} and not NUMBER.match(w)]


def test_every_word_the_command_prints_is_a_fixed_label_or_a_count(tmp_path, monkeypatch, capsys):
    """The NP3c whitelist, over ALL output including the command line's own stdout and the failure line."""
    w = world(tmp_path)
    monkeypatch.setattr("fno.ingestion.news.provenance.wiring.build_recall", lambda: RecallRun(w, w, w.index))
    shown = []
    assert cmd_news_recall(SimpleNamespace(as_of=AS_OF, days=14), out=shown.append) == 0
    text = "\n".join(shown) + "\n" + capsys.readouterr().out
    assert unexplained_words(text) == []
    assert unexplained_words("recall: tagged 5, q-0123456789ab 3") == ["q-0123456789ab"]  # the whitelist does bite
    assert unexplained_words("broad_only feed-01") == ["feed-01"] and unexplained_words("tagged ZZAL") == ["ZZAL"]

    def boom():
        raise RuntimeError("https://secret.example/q-0123456789ab")

    monkeypatch.setattr("fno.ingestion.news.provenance.wiring.build_recall", boom)
    shown.clear()
    assert cmd_news_recall(SimpleNamespace(as_of=AS_OF, days=14), out=shown.append) == 1
    assert "secret" not in shown[0] and codes.UNEXPECTED in shown[0]


def test_the_report_has_no_way_to_write_and_the_workflow_is_manual_read_only_and_alerts_nothing():
    for module in ("recall", "wiring"):
        text = (ROOT / f"fno/ingestion/news/provenance/{module}.py").read_text()
        for word in ("ProvenanceWriter", "DataStore", "WriteOnceWriter", ".put(", "batch_receipt_writer", "alert("):
            assert word not in text.split('"""', 2)[2], (module, word)
    text = (ROOT / ".github/workflows/news-provenance-recall.yml").read_text()
    body = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
    assert "workflow_dispatch" in body and "schedule:" not in body
    assert "contents: read" in body and "contents: write" not in body
    for word in ("commit_news_record", "git push", "FNO_SLACK_BOT_TOKEN", "--apply"):
        assert word not in body, word


def test_the_command_exits_one_when_the_report_is_not_ok(tmp_path, monkeypatch):
    w = world(tmp_path)
    w.drive.put(f"raw/{path_of(AS_OF.date(), 1)}", b"damaged")
    monkeypatch.setattr("fno.ingestion.news.provenance.wiring.build_recall", lambda: RecallRun(w, w, w.index))
    shown = []
    assert cmd_news_recall(SimpleNamespace(as_of=AS_OF, days=14), out=shown.append) == 1
    assert shown == ["news provenance-recall stopped, provenance_unreadable 1"]
