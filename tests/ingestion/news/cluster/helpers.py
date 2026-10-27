"""Synthetic articles for the clustering tests: every title, URL and outlet is made up (no real feed bytes)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fno.ingestion.news.article.article_file import Article

AS_OF = datetime(2026, 10, 27, 12, 0, 0, tzinfo=UTC)
HOUR = timedelta(hours=1)


def words(first: int, last: int) -> str:
    """Made-up titles w01 w02 ...: which shingles two of them share is plain arithmetic."""
    return " ".join(f"w{n:02d}" for n in range(first, last + 1))


def at(hours_before: float) -> str:
    return (AS_OF - timedelta(hours=hours_before)).isoformat(timespec="seconds")


def art(
    key: str,
    title: str,
    published: str | None = None,
    seen: str | None = None,
    kind: str = "publisher",
    source: str = "Outlet",
) -> Article:
    published = at(3) if published is None else published
    return Article(key, kind, source, title, "summary", "", published, "published" if published else "seen",
                   seen or published or at(3))  # fmt: skip


def keys_of(result) -> list[tuple[str, ...]]:
    return [c.member_keys for c in result.clusters]
