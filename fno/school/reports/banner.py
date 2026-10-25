"""The banner rule (story MS-P1g, response 325 section 7.3 for the pilot): red on any capture or quality failure of a
shown road, or no candidate; else amber. Green is not a member of `Banner`, so no input can reach it."""

from ..contracts.reports import Banner

RED_MEANING = "do not trade real money today"
AMBER_MEANING = "paper only"
MEANINGS = {Banner.RED: RED_MEANING, Banner.AMBER: AMBER_MEANING}


def banner_for(closed_roads: int, candidates: int) -> Banner:
    return Banner.RED if closed_roads or not candidates else Banner.AMBER


def banner_line(banner: Banner) -> str:
    return f"Banner: {banner.value.upper()}, {MEANINGS[banner]}"
