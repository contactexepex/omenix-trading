"""Story FL1's Slack channels beside #fno-desk (owner, 21 Oct 2026, DESK_DECISIONS): #fno-forecast takes the 09:15 and
15:45 forecast reports, #fno-intraday the fills and the hourly lines; every alert and the card stay in #fno-desk. Their
IDs are public by design, like #fno-desk's, and the record scan allows exactly these three. Apart from
`fno/constants.py`, which is at the size limit."""

__all__ = ["FNO_FORECAST_CHANNEL_ID", "FNO_INTRADAY_CHANNEL_ID"]

FNO_FORECAST_CHANNEL_ID = "C0CAZS76WBC"
FNO_INTRADAY_CHANNEL_ID = "C0CAZRX0ZQA"
