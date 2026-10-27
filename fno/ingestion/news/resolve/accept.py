"""What a resolver may hand back (NP2b): a clean https link that is not the service's own. The same cleaner as the
redirect link (`clean_https_link`), because the result is written once and never changed."""

from __future__ import annotations

from urllib.parse import urlsplit

from fno.ingestion.news.article.source_facts import clean_https_link
from fno.ingestion.news.resolve.guard import EgressGuard
from fno.ingestion.news.resolve.model import BAD_RESULT, RESOLVED, Resolved
from fno.ingestion.news.sources.rules import plain_host


def accept(decoded: object, guard: EgressGuard) -> Resolved:
    if not isinstance(decoded, str):
        return Resolved(BAD_RESULT)
    url = clean_https_link(decoded)
    if not url or guard.allows_host(plain_host(urlsplit(url).hostname)):
        return Resolved(BAD_RESULT)  # a link back to the service is a failure to resolve, not a publisher
    return Resolved(RESOLVED, url)
