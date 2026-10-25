"""T1's card in a rehearsal starts with the label (story REH1), chosen by `build_card_poster`; its clock checks say that
a replay clock is not checked (story T1f, REH1c's pattern and text), chosen by `build_card_clocks`, which then builds
no server client at all."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping

from ..cards.card_clocks import GITHUB, SLACK, CardClocks, ClockChecks
from ..cards.posting import CardPoster
from ..server_clock import unchecked
from .mode import labelled, rehearsal
from .preopen_wiring import NOT_CHECKED


class LabelledCardPoster(CardPoster):
    def __init__(self, inner: CardPoster, label: str):
        self.inner, self.label = inner, label

    def post(self, text: str):
        return self.inner.post(labelled(self.label, text))


def rehearsed_card_poster(poster: CardPoster, env: Mapping[str, str] = os.environ) -> CardPoster:
    mode = rehearsal(env)
    return poster if mode is None else LabelledCardPoster(poster, mode.label)


class RehearsalCardClocks(CardClocks):
    SERVERS = (SLACK, GITHUB)

    def check(self, receipt, before, after) -> ClockChecks:
        return ClockChecks(tuple(unchecked(server, NOT_CHECKED) for server in self.SERVERS))


def rehearsed_card_clocks(real: Callable[[], CardClocks], env: Mapping[str, str] = os.environ) -> CardClocks:
    """`real` is a builder: in a rehearsal it is never called, so no GitHub client exists (REH1's owner, 24 Oct)."""
    return real() if rehearsal(env) is None else RehearsalCardClocks()
