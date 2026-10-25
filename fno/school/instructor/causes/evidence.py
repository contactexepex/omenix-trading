"""What the cause rules read about one closed path (story MS-INS, part c), gathered once through the ports: the move
against the entry volatility, the market's moves, a known event, the stance, the stop, the hold-to-expiry outcome, the
card's replay, data faults and the model noise band. A value the inputs cannot give is None: "not testable".
Gathered as of a session (judge 525, orchestrator's ruling): a settlement counts only for an expiry before it, so the
same session's evidence is the same on every run, however late the run."""

from dataclasses import dataclass
from datetime import date

from ....constants import SIDE_BUY
from ....models import IST
from ...constants import ExitReason
from ...contracts.accounts import FillPort
from ...contracts.decisions import OpenPosition
from ...quality.prices import impossible_keys
from ..attribution.points import Point, signed_units, snapshot_point, years_left
from ..contracts import Attribution, HeldPath
from ..ports import CardReplay, EventCalendar, SnapshotArchive, StopSource
from .market import market_moves
from .terms import Stance, atm_volatility, inside_breakevens, move_z, noise_band, stance

PLAN_EXITS = (ExitReason.LOSS_LIMIT, ExitReason.PROFIT_TARGET)


@dataclass(frozen=True)
class Controls:
    """REF's and RC1's net on the path's entry road-slot; None while a control abstained, was refused or is open."""

    ref_net: float | None
    rc1_net: float | None


@dataclass(frozen=True)
class Evidence:
    net: float
    gross: float
    exit_reason: ExitReason
    attribution: Attribution | None
    data_fault: bool
    z: float | None
    market: tuple[float, ...]
    event_in_window: bool
    stance: Stance | None
    inside_breakevens: bool | None
    stop_rs: float | None
    hold_net: float | None
    replay_matches: bool | None
    noise: tuple[float, float] | None
    controls: Controls | None

    @property
    def won(self) -> bool:
        return self.net >= 0


class EvidenceBuilder:
    def __init__(self, archive: SnapshotArchive, events: EventCalendar, stops: StopSource, replay: CardReplay,
                 fills: FillPort, rate: float):  # fmt: skip
        self.archive, self.events, self.stops, self.replay, self.fills, self.rate = (
            archive, events, stops, replay, fills, rate)  # fmt: skip

    def build(self, path: HeldPath, attribution: Attribution | None, controls: Controls | None,
              as_of: date) -> Evidence:  # fmt: skip
        outcome = path.outcome
        terms = _Terms(path, self.rate) if path.snapshots and path.entry is not None else None
        first_day, last_day = _day(outcome.entry.filled_at), _day(outcome.exit.filled_at)
        return Evidence(
            net=outcome.net,
            gross=outcome.gross,
            exit_reason=outcome.exit_reason,
            attribution=attribution,
            data_fault=bool(path.faults) or (terms is not None and terms.off_market()),
            z=terms.z if terms else None,
            market=self._market(path),
            event_in_window=bool(self.events.known_between(first_day, first_day, last_day)),
            stance=terms.stance if terms else None,
            inside_breakevens=terms.inside_breakevens() if terms else None,
            stop_rs=self._stop(path),
            hold_net=self._hold(path, as_of),
            replay_matches=self._replayed(path),
            noise=terms.noise() if terms else None,
            controls=controls,
        )

    def _market(self, path: HeldPath) -> tuple[float, ...]:
        if not path.snapshots:
            return ()
        return market_moves(self.archive, path.snapshots[0].session, path.snapshots[-1].session, self.rate)

    def _stop(self, path: HeldPath) -> float | None:
        multiple = self.stops.loss_multiple(path.outcome.driver_id)
        return None if multiple is None else multiple * abs(path.outcome.entry.cash)

    def _hold(self, path: HeldPath, as_of: date) -> float | None:
        """The net had the position been held to expiry and settled; None until a session after the expiry (its
        settlement is published after the close) and until the settlement exists."""
        if path.outcome.exit_reason not in PLAN_EXITS or path.entry is None:
            return None
        proposal, outcome = path.entry.decision.proposal, path.outcome
        expiry = proposal.legs[0].key.expiry
        if expiry >= as_of:
            return None
        position = OpenPosition(
            outcome.position_id,
            outcome.driver_id,
            outcome.road,
            proposal.structure,
            proposal.legs,
            proposal.lot,
            path.entry.session,
            outcome.entry.cash,
            proposal.max_loss,
        )
        settled = self.fills.settle(position, expiry)
        return outcome.entry.cash + settled.cash if settled.filled else None

    def _replayed(self, path: HeldPath) -> bool | None:
        if path.entry is None:
            return None
        decision = self.replay.replay(path.entry)
        return None if decision is None else decision == path.entry.decision


class _Terms:
    """The path's own terms: its entry point, ATM volatility, time held and exit level."""

    def __init__(self, path: HeldPath, rate: float):
        self.path, self.rate = path, rate
        self.units = signed_units(path.outcome.entry.legs)
        self.expiry = min(k.expiry for k in self.units)
        first, last = path.snapshots[0], path.snapshots[-1]
        self.entry: Point = snapshot_point(first, tuple(self.units), rate)
        self.sigma = atm_volatility(first, self.expiry, self.entry.forwards[self.expiry], rate)
        self.left = 0.0 if path.settlement is not None else years_left(last.finished_at, self.expiry)
        self.held = years_left(first.finished_at, self.expiry) - self.left
        self.exit_level = path.settlement if path.settlement is not None else last.spot
        self.z = move_z(first.spot, self.exit_level, self.sigma, self.held)
        self.premium = -sum(leg.price * units for leg in path.outcome.entry.legs for units in (self.units[leg.key],))
        self.stance = stance(self.entry, self.units, rate, path.entry.decision.proposal.max_loss, self.premium)

    def inside_breakevens(self) -> bool | None:
        if self.stance is None or not self.stance.long_premium:
            return None
        return inside_breakevens(self.units, self.exit_level, -self.premium)

    def noise(self) -> tuple[float, float] | None:
        if self.sigma is None:
            return None
        return noise_band(self.entry, self.units, self.sigma, self.held, {self.expiry: self.left}, self.rate)

    def off_market(self) -> bool:
        """A fill away from its snapshot's touch, or a filled leg at an impossible price there."""
        first, last = self.path.snapshots[0], self.path.snapshots[-1]
        checks = [(self.path.outcome.entry.legs, first)]
        if self.path.settlement is None:
            checks.append((self.path.outcome.exit.legs, last))
        for legs, snapshot in checks:
            if impossible_keys(snapshot, {leg.key for leg in legs}) or any(_off_touch(leg, snapshot) for leg in legs):
                return True
        return False


def _off_touch(leg, snapshot) -> bool:
    quote = snapshot.quote(leg.key)
    touch = None if quote is None else (quote.ask if leg.side == SIDE_BUY else quote.bid)
    return touch is None or abs(leg.price - touch) > 1e-9


def _day(at) -> date:
    return at.astimezone(IST).date()
