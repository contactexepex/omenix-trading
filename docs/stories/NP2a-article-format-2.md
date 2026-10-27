# NP2a: article format 2 and the source facts (BUILT, awaiting two judges)

Lane 1, **two judges** (it changes what is written to the write-once Record and how a re-seen article is judged). Plan:
[NP0-news-port-plan.md](NP0-news-port-plan.md) (judge 70 PASS, merged) section 3. Stacked on [NP1](NP1-source-rules.md) only for the
pure `plain_host`; **merges after NP1**, and NP1 waits for the owner's decision H. It resolves no link (that is NP2b/NP2c, held for the
owner's terms and decoder answers) and makes no request.

## What it changes
- **The article file is format 2.** `Article` gains `source_domain` and `wrapper_link`. Only format 2 is written; formats 1 and 2 are
  read through one definition (`article_from_bytes`, also used by the cluster source). An unknown format, a missing key or an
  unknown extra key is refused.
- **`RawItem.source_url`**: the `url` attribute of an item's `<source>` element (Google News: the outlet's home page). Google's claim of
  the outlet; no request is made for it.
- **`source_facts.py`** (pure): a publisher item's `source_domain` is the host of its https link; a Google News item's is the host of its
  `<source url>` when that is an https plain host with no credentials and no port. A Google News item also keeps its redirect link as
  `wrapper_link` when it is a plain https link, **so the resolve pass (NP2c) can work from the Record alone**.
- **`planner.same_version`**: two article files are compared on the fields both carry; `wrapper_link` is not compared at all.

## Decisions and why
- **Facts only.** No tier, wire, promotional flag, tickers, priority, resolved URL or URL status in the file (NP0 section 3, row F5).
- **The wrapper key is unchanged** (`keys.py` is not touched): it never depends on the link, the source facts or whether a link was
  resolved (row F8). So resolving can never re-key a Google article.
- **Two migration traps, both reproduced by the tests:** the version comparison (rows F2, F3) and the cluster reader that refused any
  format but the current one (row F1; bumping the format would have made every old article "unreadable" and the cluster run write nothing).
- **`wrapper_link` is not compared** (row F7): a redirect token may change between polls of one item, and a changed link must not
  record a revision. It is kept only when it is a plain https link (row F6).
- **No host name of a news service is written in code.** `tests/ingestion/news/test_privacy.py` (P2's invariant 1) fails on the string of
  the Google News host anywhere in `fno/`. So `wrapper_link` accepts any plain https link here, and the **resolver (NP2b) must accept
  only Google hosts** (its egress guard) and refuse the rest; a wrapper link that points elsewhere is simply never requested.
  **Heads-up for NP0 section 2a:** the planned entry for the Google host in `HOST_SPACING_SECONDS` (`fno/shared/nse_pacer.py`) would
  trip the same test. NP2b/NP3 must either read the host from the private feed list (the wrapper-kind feed's own host) or the owner/judges
  relax the test for one named constant. I did not decide that here.
- **A publisher feed's link host is taken as is** (NP0 round 1 asked for host agreement; not built: the feed host is not known where
  the article is built, the tier comes from the link's own host so a feed cannot lift a domain, and agreement would reject legitimate
  syndication; reasoning only, judges may overrule).
- **Reversal of a P2 test assertion:** `test_a_wrapper_article_holds_no_url...` used to assert the redirect link is not in the file at all.
  It now asserts it is only in `wrapper_link` and not in `canonical_url`. This is NP0's approved N3 mechanism, not a slip.

## Known limits (intended, stated so they are not silent gaps)
- **Every Google article recorded before this story has no `wrapper_link` and can never be resolved**: its source URL stays empty and its
  tier stays `unlisted`. No back-fill (judge 70). Nothing has been promoted for real yet, so there may be none.
- Google's `<source url>` has been seen in agentic's rows (strong evidence) but not in omenix's own feeds; NP2b's probe checks.

## Judges: please try to break
1. A format 1 file that the new code reads or compares wrongly.
2. A way to make the planner call different articles "the same version" (shared fields, `wrapper_link` excluded) or one article different.
3. A value from the feed that reaches `source_domain` or `wrapper_link` without the https / plain-host / no-credentials / no-port check.
4. Anything that changes a wrapper key.
