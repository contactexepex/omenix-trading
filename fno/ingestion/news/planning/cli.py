"""`python -m fno news plan-feeds [--apply]` (NP3b): the next private feed list from the company list and the discovery
file. Report only without `--apply`. The line it prints is counts and a fixed code: no query, no company and no URL,
because all of them are the owner's private content."""

from __future__ import annotations

from fno.ingestion.news import codes
from fno.ingestion.news.companies.parse import CompanyListError
from fno.ingestion.news.feeds import FeedListError
from fno.ingestion.news.planning.discovery import DiscoveryError
from fno.ingestion.news.planning.planner import FeedPlanError

LINE = (
    "news plan-feeds ({mode}): feeds {total} (broad {broad}, targeted {targeted}, publisher {publisher}), "
    "new {new}, dropped {dropped}"
)
STOPPED = "news plan-feeds stopped: {code}"


def add_plan_parser(actions) -> None:
    plan = actions.add_parser("plan-feeds", help="the next private feed list from the company list (story NP3b)")
    plan.add_argument("--apply", action="store_true", help="write the next feeds-vN.json (default: report only)")
    plan.set_defaults(func=cmd_plan_feeds)


def cmd_plan_feeds(args, out=print) -> int:
    from fno.ingestion.news.planning.wiring import plan_next_feed_list

    try:
        plan = plan_next_feed_list(args.apply)
    except (CompanyListError, DiscoveryError, FeedPlanError, FeedListError) as stopped:
        out(STOPPED.format(code=stopped))
        return 1
    except Exception as unexpected:  # noqa: BLE001 - the message of a Drive error can name a path
        out(STOPPED.format(code=f"{codes.UNEXPECTED} {type(unexpected).__name__}"))
        return 1
    mode = "written" if args.apply else "report only"
    out(LINE.format(mode=mode, total=plan.total, broad=plan.broad, targeted=plan.targeted,
                    publisher=plan.publisher, new=plan.new, dropped=plan.dropped))  # fmt: skip
    return 0
