"""The fixed names of the market school's P0b capture probes (story MS-P0b): the list, the pace, the slots and the
messages. The owner's decision of 25 Oct 2026 ("read it as a study pace") is kept here as numbers, not settings: a
change to any of them is a lane-1 change of the story, never a config edit."""

from datetime import date, time, timedelta
from enum import StrEnum


class Source(StrEnum):
    GROWW = "groww"
    NSE = "nse"


class Quality(StrEnum):
    OK = "ok"
    EMPTY_BID_ASK = "empty_bid_ask"
    ONE_SIDED = "one_sided"
    LOT_UNKNOWN = "lot_unknown"
    MISSING = "missing"
    STALE = "stale"


class RowKind(StrEnum):
    FUTURE = "future"
    OPTION = "option"


FUTURES = ("NIFTY", "BANKNIFTY", "RELIANCE", "HDFCBANK", "INFY", "SBIN")
CHAINS = ("RELIANCE", "HDFCBANK", "INFY", "SBIN")
STRIKES_EACH_SIDE = 2  # ATM +-2 listed strikes, call and put: 10 legs a chain
OPTION_TYPES = ("CE", "PE")

MIN_GAP_SECONDS = {Source.GROWW: 1.0, Source.NSE: 3.0}
DAILY_CAP = {Source.GROWW: 240, Source.NSE: 50}
SLOT_BUDGET = {Source.GROWW: 50, Source.NSE: 11}  # reserved before a slot's first request (judge 626)
RATE_LIMIT_WAIT_SECONDS = 60.0  # NSE only: Groww stops at its first 429 (orchestrator's Groww audit)
SERVER_ERROR_WAIT_SECONDS = 30.0
REQUEST_TIMEOUT_SECONDS = 20.0
STOPPED_SESSIONS_FOR_GOOD = 2

SLOTS = (time(10, 7), time(11, 37), time(13, 7), time(14, 7))
LATE_START = timedelta(minutes=2)  # a slot not started by then is skipped
HARD_STOP = timedelta(minutes=6)  # 2 min before the next A16 mark
STALE_AFTER = timedelta(minutes=15)
MAX_SESSIONS = 5
BLACKOUT_DAYS = frozenset({date(2026, 10, 26), date(2026, 10, 27), date(2026, 10, 28)})  # v4 clean day; A16h days

NSE_HOST = "https://www.nseindia.com"
NSE_PAGE = "/option-chain"  # one visit a slot: the session cookie a browser would get
NSE_FUTURES_PATH = "/api/quote-derivative"
NSE_CHAIN_PATH = "/api/option-chain-equities"
NSE_USER_AGENT = "OmenixFnO-research/1.0 (personal, read-only, paced)"
NSE_ACCEPT = "application/json, text/plain, */*"
GROWW_FUTURE_SYMBOL = "{underlying}{expiry:%y}{month}FUT"  # e.g. RELIANCE26NOVFUT, the form A16 uses for NIFTY

DRIVE_AREA = "school/p0b"
COUNTS_FOLDER = "research/school/probes/p0b"
CAPTURE_JOB = "school-p0b"
WRITER = "school-p0b"
COMMIT_MESSAGE = "MS-P0b capture probe: {what}"
COMMIT_LABEL = "p0b records"

STOP_LINE = "p0b {source} stopped for the day at {slot}: {reason}"
STOPPED_FOR_GOOD = "p0b {source} stopped for good: blocked on {count} sessions; the owner decides"
CAP_LINE = "daily cap reached ({cap} requests)"
NOT_A_SESSION = "p0b: not a trading day; nothing read"
BLACKOUT_LINE = "p0b: {day} is kept clear for v4 and A16h; nothing read"
SESSIONS_DONE = "p0b: {count} sessions already captured; a sixth needs the owner"
SLOT_SKIPPED = "p0b slot {slot}: skipped, more than 2 min late"
SLOT_LINE = "p0b slot {slot} {source}: {used} requests, {ok} of {rows} rows ok, {stop}"
RESERVATION_NOT_PUSHED = "p0b slot {slot}: reservation not pushed ({reason}); slot not started"
DAY_DONE = "p0b {day}: done, {groww} Groww and {nse} NSE requests"
