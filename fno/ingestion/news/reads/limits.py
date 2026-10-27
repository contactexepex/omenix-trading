"""The page-read pass's numeric limits (NP4b), apart from the pass itself so that the command line can show them without
importing the HTML parser."""

LOOKBACK_DAYS = 3
PAGES = 80  # pages fetched per run
MAX_RECORD_READS = 400  # Record files read to choose them
BUDGET_SECONDS = 900.0  # the whole run
