"""`python -m fno intraday feed-probe --plan <coverage|ramp|ramp-day|alongside> [--minutes N]` (story A16h): a
read-only probe of Groww's streaming feed, run by hand. It prints counts and times only."""

from __future__ import annotations

FEED_PROBE = "feed-probe"
PLAN_SIDES = {
    "coverage": 10,
    "alongside": 10,
    "ramp": 50,
    "ramp-day": 50,
}  # ±50 on every expiry to ~3 months: over 3,000 (23 Oct)  # strikes either side of ATM
MAX_FOR = {"alongside": 1000}
# The universe lists index values, futures, then options index by index: a cut keeps those first (judge 499 addendum 5)
CUT = (
    "feed probe {plan}: kept the first {kept} of {found} instruments (index values, futures, then options; "
    "the last kept: {last})"
)


def add_feed_probe_parser(actions) -> None:
    probe = actions.add_parser(FEED_PROBE, help="A16h: probe Groww's streaming feed read-only (counts and times only)")
    probe.add_argument("--plan", required=True, choices=sorted(PLAN_SIDES))
    probe.add_argument("--minutes", type=float, help="stop earlier than the plan's hard end time")


def cmd_feed_probe(args) -> int:
    from ..config import load_app_config
    from ..models import now_ist
    from .feed_probe import PLANS, ProbeRefused, summary, window_refusal
    from .feed_wiring import FeedNotConnected, build_catch_up_gate, build_feed_probe, build_gate, build_universe

    now = now_ist()
    day, plan = now.date(), PLANS[args.plan]
    refused = window_refusal(plan, day, now)  # before any sign-in or quote (judge 499 addendum 5)
    if refused:
        print(f"feed probe {args.plan}: refused: {refused}")
        return 1
    gate = {"alongside": build_gate, "ramp": build_catch_up_gate}.get(args.plan)
    blocked = gate()(day) if gate else ""
    if blocked:
        print(blocked)
        return 1
    try:
        probe, client = build_feed_probe(load_app_config(args.config))
    except FeedNotConnected as error:
        print(f"feed probe {args.plan}: stopped: {error}")
        return 1
    try:
        probe.check_start(plan, day)  # again after the sign-in: the list and the quotes come inside the window too
        instruments = build_universe(client, PLAN_SIDES[args.plan], every_expiry=args.plan.startswith("ramp"))
        kept = instruments[: MAX_FOR.get(args.plan, len(instruments))]
        if len(kept) < len(instruments):
            print(CUT.format(plan=args.plan, kept=len(kept), found=len(instruments), last=kept[-1].feed_class()))
        outcome = probe.run(plan, kept, day, args.minutes)
    except ProbeRefused as refused:
        print(f"feed probe {args.plan}: refused: {refused}")
        return 1
    print("\n".join(summary(outcome)))
    return 0
