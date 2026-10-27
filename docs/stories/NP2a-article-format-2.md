# NP2a: article format 2 and the source facts (BUILT, awaiting two judges)

Lane 1, **two judges** (it changes what is written to the write-once Record and how a re-seen article is judged). Plan:
[NP0-news-port-plan.md](NP0-news-port-plan.md) section 3. Builds on [NP1](NP1-source-rules.md) only for the pure `plain_host`. It does
**not** resolve links (that is NP2b, held for the owner's terms and decoder answers) and fetches nothing.

## What it changes
- **The article file is format 2** (`Article` gains `source_domain`, `source_url`, `url_status`). Only format 2 is written; formats 1
  and 2 are read (`article_from_bytes`, now the one definition, used by the cluster source). An unknown format, a missing key or an
  unknown extra key is refused.
- **`RawItem.source_url`**: the `url` attribute of an item's `<source>` element, which Google News fills with the outlet's home page.
  It is Google's own claim of the outlet; no request is made for it.
- **`source_facts.py`** (pure): a publisher item with an https link has that link as its source (`publisher`); one with no usable link
  has none (`none`); a Google News item's link is a redirect wrapper and is never the source: its domain is the `<source>` host when
  that is an https plain host with no credentials and no port, its URL stays empty, its status is `undecoded`.
- **`planner.same_version`**: two article files are compared on the fields both carry.

## Decisions and why
- **Facts only; no tier in the file.** NP0 listed `tier`, `origin_wire`, `promotional`, `tickers` and `priority` among the new fields.
  **I am correcting that here:** each depends on a rule file (the allowlist, the watchlist), and a field that depends on a rule file
  would make every edit of the rule a "revision" of every re-seen article (the compared fields would change). So the file stores what
  the feed said (domain, URL, status) and NP5/NP6 compute the judgements on read. Contract row F5 pins it. (Strong evidence: the planner
  compares every non-`first_seen_at` field.)
- **The migration trap NP0 named is real and a second one was found.** (1) `planner.UNCOMPARED` would have treated every format 1 file
  as different from its format 2 twin: fixed by comparing on shared fields (F2). (2) `article_from_bytes` raised on any format other
  than the current one, so bumping the format would have made every format 1 article "unreadable" and the cluster run would have
  written nothing: fixed by `READABLE_FORMATS = (1, 2)` (F1). Both are reproduced by the new tests.
- **A source fact found later is a revision, never an overwrite** (F3): two format 2 files that differ in `source_url` are different
  versions, so NP2b can add a resolved URL through the existing revision path with no new mechanism.
- **A publisher feed's link host is taken as is.** NP0 said the feed host and the link host should agree. I did not build that: the
  fetcher's feed host is not known where the article is built, the tier comes from the link's own host (a feed cannot lift a domain
  above what that domain is), and a disagreement check would reject legitimate syndication. Reasoning only; the judges may overrule.
- **No article already in the Record is rewritten or back-filled.** (Contract: nothing has been promoted for real yet, so there may be
  none.)

## What is NOT established
- Google's `<source url>` has been seen in agentic's rows (its `source_domain` is built from it, strong evidence) but never checked
  against omenix's own feed list; NP2b's probe does that.
- `url_status` has three values today; NP2b adds `resolved` for a decoded URL.

## Judges: please try to break
1. A format 1 file that the new code reads or compares wrongly (try a v1 file with a `source_domain` key, a v1 file whose title differs).
2. A way to make the planner call different articles "the same version" (the shared-field rule) or the same article different.
3. A value from the feed that reaches `source_domain` or `source_url` without the https / plain-host / no-credentials / no-port check.
