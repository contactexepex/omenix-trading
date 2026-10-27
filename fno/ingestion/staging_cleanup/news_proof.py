"""When a staged news poll may be removed (story S1, owner's choice (b), 27 Oct 2026: trash after promote).

**What removing a promoted poll loses, stated plainly.** The Record keeps an article's FIELDS (key, kind, source, title,
summary, canonical link, times); it does not keep the raw poll. Removing the poll therefore permanently loses, once
Drive's trash is emptied (about 30 days after the move), what the Record never took: the full item body, author,
categories, media, and, for wrapper items such as Google News, the real link. That is the owner's accepted trade-off.

A poll is "promoted" only when ALL of this holds (anything else keeps it, including every poll the promotion gate
left staged on purpose, which are re-read on every run):
- its feed has a kind in the feed list (otherwise the gate left it staged: `feed_unknown`);
- it still parses as a whole poll (a refused poll stays);
- NONE of its items was rejected (a rejected item stays staged with its code), and it has at least one article;
- EVERY article is already held by the Record exactly as the writer would treat it (a NO_OP in the writer's own rule,
  `ArticlePlanner`, in the article file or the revision file of that version) AND has its manifest row, and a Google
  News article with a redirect link also has its row in the wrapper index (NP2d);
- EVERY (article, feed) pair of the poll is held by the provenance files of the poll's IST day (NP11): otherwise the
  poll stays staged (it is re-read on every run, so a later promotion writes what is missing) and which feed found an
  article is never lost silently. An explicit gate, not a timing assumption.
A refused poll answers False. Any other error (Drive down, a collision, a bug) is NOT swallowed here: it propagates and
`StagingCleanup` keeps the copy, counts it as `proof_error` and turns the run red."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping

from fno.ingestion.news.article.article_file import Article
from fno.ingestion.news.article.parse_feed import PollRejected
from fno.ingestion.news.article.read_poll import read_poll
from fno.ingestion.news.provenance.index import ProvenanceIndex
from fno.ingestion.news.provenance.model import day_of
from fno.ingestion.news.record.manifest import RECORDED, NewsManifest
from fno.ingestion.news.record.planner import ArticlePlanner, Outcome
from fno.ingestion.news.record.wrapper_index import is_resolvable
from fno.ingestion.promotion.staging import StagedCopy
from fno.ingestion.staging_cleanup.proof import PromotedProof

POLL_FOLDER = "poll"  # a staged poll lives at <feed>/<Y>/<m>/<d>/poll/<stamp>


class NewsPollProof(PromotedProof):
    def __init__(
        self,
        kinds: Mapping[str, str],
        planner: ArticlePlanner,
        manifest: NewsManifest,
        wrappers: NewsManifest,
        provenance: ProvenanceIndex,
    ):
        """`kinds`: feed id -> kind; `planner`: the Record, read only; `manifest`: the checkout's articles manifest;
        `wrappers`: the wrapper index (NP2d), REQUIRED so the check can never be silently off: a Google News article
        with a link must also have its row there, so a
        poll is never trashed while its resolve marker is missing (judge 86); `provenance` (NP11), REQUIRED for the same
        reason: a poll is never trashed while the feeds that found its articles are not recorded."""
        self.kinds, self.planner, self.manifest, self.wrappers = kinds, planner, manifest, wrappers
        self.provenance = provenance

    def promoted(self, copy: StagedCopy) -> bool:
        parts = copy.path.split("/")
        kind = self.kinds.get(parts[0])
        if kind is None or parts[-1] != POLL_FOLDER:
            return False
        try:
            reading = read_poll(copy.data, kind, copy.fetched_at)
            if reading.rejected or not reading.articles:
                return False
            return all(self._held(article) for article in reading.articles) and self._recorded_feeds(
                parts[0], copy, reading.articles
            )
        except PollRejected:  # the one expected refusal: the gate left such a poll staged
            return False

    def _recorded_feeds(self, feed: str, copy: StagedCopy, articles: list[Article]) -> bool:
        day = day_of(copy.fetched_at)
        return all(feed in self.provenance.feeds_of(day, article.key) for article in articles)

    def _held(self, article: Article) -> bool:
        plan = self.planner.plan(article)
        return (
            plan.outcome is Outcome.NO_OP
            and plan.held is not None
            and self.manifest.has(article.key, plan.status, hashlib.sha256(plan.held).hexdigest())
            and self._indexed(article, plan)
        )

    def _indexed(self, article: Article, plan) -> bool:
        """A resolvable article's main file also has its row in the wrapper index (revision files are never indexed)."""
        if plan.status != RECORDED or not is_resolvable(article):
            return True
        return self.wrappers.has(article.key, RECORDED, hashlib.sha256(plan.held).hexdigest())
