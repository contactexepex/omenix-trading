"""The fixed reason codes of a news fetch (invariant 1 of P2): the only words a log line, an alert or a report may use
about a poll. A code never carries a URL, a query, a headline or an exception message."""

FETCHED, UNCHANGED = "fetched", "unchanged"  # saved to Staging / the same bytes as the newest staged poll
BLOCK_PAGE = (
    "block_page"  # a redirect, or an answer that is not a feed (consent, CAPTCHA, "sorry"): a stop for the host
)
REFUSED = "refused"  # HTTP 403 or 429
HOST_PAUSED = "host_paused"  # the shared pacer has paused the host after earlier refusals
HOST_BLOCKED = "host_blocked"  # not asked: the host was blocked earlier in this run
FETCH_FAILED = "fetch_failed"  # no answer, or an HTTP status that is not a refusal
STAGE_FAILED = "stage_failed"  # Staging (Drive) would not take the bytes
UNEXPECTED = "unexpected_error"  # anything else; only the exception class is ever named
FEED_LIST_MISSING = "feed_list_missing"
FEED_LIST_INVALID = "feed_list_invalid"
FEED_LIST_ROLLED_BACK = "feed_list_rolled_back"  # the newest version is older than one already used
FEED_KIND_CHANGED = "feed_kind_changed"  # two versions of the list give one feed id different kinds: promotion stops
FEED_LIST_DAMAGED = "feed_list_damaged"  # a version already used has been edited in place; the last good one is used

OK_CODES = (FETCHED, UNCHANGED)
HOST_STOPS = (BLOCK_PAGE, REFUSED, HOST_PAUSED)  # after one of these no other feed on the host is asked this run

# the article gate (P2b): why a staged poll or one of its items stays in Staging
POLL_TOO_LARGE, UNSAFE_XML = "poll_too_large", "unsafe_xml"
NOT_A_FEED, NO_ITEMS = "not_a_feed", "no_items"
ITEM_MISSING_TITLE, ITEM_MISSING_LINK, ITEM_TOO_LONG = "item_missing_title", "item_missing_link", "item_too_long"
ITEM_UNREADABLE = "item_unreadable"  # a link or time the standard library cannot read: counted, the poll goes on
# the writer (P2b2): outcomes of promoting a staged poll's articles to the Record
FEED_UNKNOWN = (
    "feed_unknown"  # a staged poll whose feed id is not in the feed list: its kind is unknown, it stays staged
)
RECORD_FAILED = "record_failed"  # Drive or the manifest would not take an article (only the code is kept)
RECORD_CONFLICT = (
    "record_conflict"  # the manifest or the Record holds other bytes for this id, or a revision name collides
)
NOT_RECONCILED = "not_reconciled"  # items != recorded + revisions + no-ops + rejected: an item went missing
