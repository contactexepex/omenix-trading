"""NP3b: the discovery file, read with the discipline of every versioned private file."""

from __future__ import annotations

import json
from copy import deepcopy

import pytest

from fno.ingestion.news import codes
from fno.ingestion.news.planning.discovery import DiscoveryError, PrivateDiscoveryFile, parse_discovery
from fno.ingestion.storage.raw_store import AreaStore, LocalFolderStore
from tests.ingestion.news.planning.helpers import SEARCH_URL, discovery, discovery_document


def refused(document) -> str:
    data = document if isinstance(document, bytes) else json.dumps(document).encode()
    with pytest.raises(DiscoveryError) as caught:
        parse_discovery(data, 1)
    return str(caught.value)


def test_a_good_file_is_read():
    plan = discovery()
    assert plan.search_url == SEARCH_URL and plan.query_param == "q" and plan.params == (("gl", "XX"), ("hl", "en"))
    assert plan.broad == ("zzmarket outlook", "Zzsector news") and plan.publisher_feeds[0][0] == "feed-01"


def mutated(path, value):
    document = deepcopy(discovery_document())
    target = document
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return document


BAD = [
    b"not json", b"[]", json.dumps({"format": 2}).encode(),
    mutated(["format"], 2), mutated(["surprise"], 1), mutated(["search", "url"], "http://search.svc.example/x"),
    mutated(["search", "url"], "https://"), mutated(["search", "query_param"], "hl"), mutated(["search", "extra"], 1),
    mutated(["search", "params"], {"a": 1}), mutated(["broad"], "text"), mutated(["broad"], [""]),
    mutated(["broad"], ["x" * 201]), mutated(["broad"], ["q"] * 301), mutated(["targeted_template"], "no slot"),
    mutated(["targeted_template"], "{name} and {name}"), mutated(["targeted_template"], "{name} {other}"),
    mutated(["targeted_template"], "{name} }"), mutated(["publisher_feeds"], [{"id": "q-abcdef12", "url": "https://h.example/x"}]),
    mutated(["publisher_feeds"], [{"id": "feed-01", "url": "http://h.example/x"}]),
    mutated(["publisher_feeds"], [{"id": "feed-01", "url": "https://h.example/x"}] * 2),
    mutated(["publisher_feeds"], [{"id": "feed-01"}]),
]  # fmt: skip


@pytest.mark.parametrize("document", BAD)
def test_a_file_with_a_mistake_is_refused_with_one_fixed_code_and_no_text(document):
    assert refused(document) == codes.DISCOVERY_INVALID


def test_the_adapter_reads_the_newest_version_and_stops_on_a_missing_or_rolled_back_one(tmp_path):
    config = AreaStore(LocalFolderStore(tmp_path / "drive"), "config")
    with pytest.raises(DiscoveryError) as missing:
        PrivateDiscoveryFile(config).plan()
    assert str(missing.value) == codes.DISCOVERY_MISSING
    config.put("discovery/discovery-v1.json", json.dumps(discovery_document(broad=["older"])).encode())
    config.put("discovery/discovery-v2.json", json.dumps(discovery_document(broad=["newer"])).encode())
    plan = PrivateDiscoveryFile(config).plan()
    assert plan.version == 2 and plan.broad == ("newer",)
    with pytest.raises(DiscoveryError) as rolled_back:
        PrivateDiscoveryFile(config, lowest_version=3).plan()
    assert str(rolled_back.value) == codes.DISCOVERY_ROLLED_BACK
