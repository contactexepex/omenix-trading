"""The page-read pass's numeric limits (NP4b), apart from the pass itself so that the command line can show them without
importing the HTML parser."""

LOOKBACK_DAYS = 3
PAGES = 80  # pages fetched per run
MAX_RECORD_READS = 400  # Record files read to choose them, in total (NP8: SCORE_READS + RESOLVE_READS)
SCORE_READS = 300  # of those, article files read to rank them (material first order)
RESOLVE_READS = 100  # of those, resolution files read to find the page of a Google News item
BUDGET_SECONDS = 900.0  # the whole run
