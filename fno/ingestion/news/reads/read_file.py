"""The read file (NP4b; NP0 section 2e): `news/reads/<key[:2]>/<key>.json`, write-once, one per article page read. Facts
and hashes only: the access outcome, which extractor found them, the body's length and SHA-256, times, names. **No
article body and no HTML**; the page snippet (NP10, owner decision E1 = YES: at most three sentences and 600
characters, in its own field `summary_extract`, private Drive only) is the only page text. `to_bytes` refuses a file
over `MAX_BYTES`, so a body cannot ride along even by mistake. The article key is the name, so the same page read
twice is the same file."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field

from fno.ingestion.news.reads.extract import PageFacts

FORMAT = 2  # NP10: 1 had no snippet. The Record held no read file when 2 replaced it, so only 2 is read or written.
READS_FOLDER = "news/reads"
MAX_BYTES = (
    6_000  # of UTF-8: five 80-character names (about 1,200) plus a 600-character snippet in a three-byte script (1,800)
)
FULL, PARTIAL, PAYWALLED = "full", "partial", "paywalled"
MIN_FULL_CHARS = 300  # a body this long (as measured, not stored) is a full read
KEYS = frozenset({"format", "key", "host", "access", "extractor", "body_chars", "body_sha256", "published_at",
                  "modified_at", "authors", "provider", "summary_extract"})  # fmt: skip


def read_path(key: str) -> str:
    return f"{READS_FOLDER}/{key[:2]}/{key}.json"


def key_of_path(path: str) -> str:
    return path.rsplit("/", 1)[-1].removesuffix(".json")


def access_of(facts: PageFacts) -> str:
    if facts.paywalled:
        return PAYWALLED
    return FULL if facts.body_chars >= MIN_FULL_CHARS else PARTIAL


@dataclass(frozen=True)
class ReadFile:
    key: str
    host: str
    access: str
    extractor: str
    body_chars: int
    body_sha256: str
    published_at: str
    modified_at: str
    authors: tuple[str, ...]
    provider: str
    summary_extract: str = field(default="", repr=False)  # private text: only in this file, never printed or logged

    def to_bytes(self) -> bytes:
        document = {"format": FORMAT, **asdict(self), "authors": list(self.authors)}
        data = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        if len(data) > MAX_BYTES:
            raise ValueError("a read file holds facts only")
        return data


def build_read(key: str, host: str, facts: PageFacts) -> ReadFile:
    return ReadFile(
        key, host, access_of(facts), facts.extractor, facts.body_chars, facts.body_sha256, facts.published_at,
        facts.modified_at, facts.authors, facts.provider, facts.summary_extract,
    )  # fmt: skip


def parse_read(data: bytes) -> ReadFile:
    document = json.loads(data)
    if not isinstance(document, dict) or set(document) != KEYS or document["format"] != FORMAT:
        raise ValueError("not a read file")
    fields = {k: v for k, v in document.items() if k != "format"}
    return ReadFile(**{**fields, "authors": tuple(fields["authors"])})
