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
BATCH_TORN = (
    "batch_torn"  # a receipt batch file ended in a half line (a write cut short): the half line is not committed
)
MANIFEST_BROKEN = "manifest_broken"  # the news manifest ends in a torn line: nothing is written until it is trimmed
MANIFEST_ROW_SKIPPED = "manifest_row_skipped"  # rows of the news manifest that are not whole (counted, never ignored)
# the cluster record (P2d)
CLUSTER_NOT_RECONCILED = (
    "cluster_not_reconciled"  # the clusters do not account for the articles read: nothing is written
)
CLUSTER_CONFLICT = "cluster_conflict"  # the closed window's file exists with other bytes: investigate, never overwrite
CLUSTER_RECORD_FAILED = "cluster_record_failed"  # Drive or the manifest would not take the file (only the code is kept)
ARTICLE_UNREADABLE = (
    "article_unreadable"  # a recorded article's file is missing or damaged: counted, nothing is written
)
WINDOW_IN_FUTURE = (
    "window_in_future"  # a window end later than now (floored to the hour): it would write a file that cannot be stable
)
PREVIOUS_UNREADABLE = (
    "previous_unreadable"  # the earlier run's cluster file is damaged: the replaced ids cannot be named
)
# the company list (NP3a): fixed codes; the list is the owner's private content, so no code carries a symbol or a name
COMPANY_LIST_MISSING = "company_list_missing"
COMPANY_LIST_INVALID = "company_list_invalid"
COMPANY_LIST_ROLLED_BACK = "company_list_rolled_back"
COMPANY_LIST_DAMAGED = "company_list_damaged"
COMPANY_LIST_EXISTS = "company_list_exists"  # a seed is never written over an existing list
SEED_SOURCE_MISSING = "seed_source_missing"  # the archived NSE list the seed is built from could not be read
# the feed plan (NP3b): fixed codes; the discovery file and the plan are the owner's private content
DISCOVERY_MISSING = "discovery_missing"
DISCOVERY_INVALID = "discovery_invalid"
DISCOVERY_ROLLED_BACK = "discovery_rolled_back"
DISCOVERY_DAMAGED = "discovery_damaged"
FEED_PLAN_COLLISION = "feed_plan_collision"  # two different queries hash to one feed id: nothing is written
FEED_PLAN_KIND_CONFLICT = (
    "feed_plan_kind_conflict"  # a planned id was used before with another kind: nothing is written
)
FEED_PLAN_INVALID = "feed_plan_invalid"  # the plan's own bytes fail the feed list checks (too many feeds, a bad URL)
# the resolve pass (NP2c)
RESOLVER_FAILING = (
    "resolver_failing"  # the resolver resolved nothing (or under half of a real batch): loud, never green
)
RESOLUTION_CONFLICT = "resolution_conflict"  # the resolution file exists with other bytes: nothing is overwritten
RESOLUTION_WRITE_FAILED = (
    "resolution_write_failed"  # Drive or the manifest would not take the file (only the code kept)
)
# the page-read pass (NP4b)
READER_FAILING = (
    "reader_failing"  # the pages asked for were refused, blocked or failed (nothing of three or more, or under half)
)
READ_CONFLICT = "read_conflict"  # the read file exists with other bytes: nothing is overwritten
READ_WRITE_FAILED = "read_write_failed"  # Drive or the manifest would not take the file (only the code is kept)
