"""The comparison's unit (story MS-P1h): the five roads of one session are one cluster, so a session counts as one
session, not five tests. The common group is the road-days on which a driver and every one of its matched controls
have a counted decision, so no driver is compared on days its control missed. It is computed from the counted
decisions at report time, per card version (`CountVerdict.card_commit`): the rule that decides which decisions count is
what the card freezes, so the group cannot be chosen after the results."""

from collections.abc import Iterable, Sequence
from datetime import date

from ..constants import RoadCode
from .counting import CountCandidate

RoadDay = tuple[date, RoadCode]


def common_road_days(counted: Iterable[CountCandidate], driver_ids: Sequence[str]) -> frozenset[RoadDay]:
    """The (session, road) pairs on which every named driver has a counted decision."""
    if not driver_ids:
        return frozenset()
    by_driver: dict[str, set[RoadDay]] = {driver: set() for driver in driver_ids}
    for candidate in counted:
        if candidate.driver_id in by_driver:
            by_driver[candidate.driver_id].add((candidate.session, candidate.road))
    return frozenset.intersection(*(frozenset(days) for days in by_driver.values()))


def session_clusters(road_days: Iterable[RoadDay]) -> dict[date, frozenset[RoadCode]]:
    """One cluster per session: the roads counted that day."""
    clusters: dict[date, set[RoadCode]] = {}
    for session, road in road_days:
        clusters.setdefault(session, set()).add(road)
    return {session: frozenset(roads) for session, roads in sorted(clusters.items())}
