"""Per-source resilience settings (story R1): the shipped defaults are TODAY'S numbers, copied from the code they
replace (a test pins each to its original), so wiring the layer in changes no behaviour. `config.yaml`'s `resilience:`
block can override any value per source without touching code. A new source starts as strict as NSE.

Never weaker than today: NSE opens at 2 consecutive refusals with a 15-minute cool-down (`RequestPacer`), NSE waits
5/15/45 s and honours Retry-After up to 120 s (`retry_policy.py`), Drive waits 2/8/30/60 s (`drive_session.py`)."""

from __future__ import annotations

from dataclasses import dataclass, replace

from fno.shared.resilience.breaker import BreakerSettings
from fno.shared.resilience.rate_limit import RateSettings
from fno.shared.resilience.retry import RetrySettings

DAY_SECONDS = 86400.0
SECTIONS = {"retry": RetrySettings, "breaker": BreakerSettings, "rate": RateSettings}


@dataclass(frozen=True)
class SourceSettings:
    retry: RetrySettings | None = None
    breaker: BreakerSettings | None = None
    rate: RateSettings | None = None


NSE_RETRY = RetrySettings(waits=(5.0, 15.0, 45.0), cap_seconds=90.0, retry_after_ceiling_seconds=120.0,
                          max_total_seconds=900.0)  # fmt: skip
DEFAULTS: dict[str, SourceSettings] = {
    "nse": SourceSettings(
        retry=NSE_RETRY,
        # every 403 and 429 response counts (the Verdict says so), so exhausted calls are not counted a second time
        breaker=BreakerSettings(
            threshold=2, cool_down_seconds=900.0, cool_down_cap_seconds=DAY_SECONDS, count_exhausted=False
        ),  # fmt: skip
        rate=RateSettings(min_spacing_seconds=1.0),
    ),
    "drive": SourceSettings(
        retry=RetrySettings(
            waits=(2.0, 8.0, 30.0, 60.0), cap_seconds=120.0, retry_after_ceiling_seconds=120.0, max_total_seconds=900.0
        ),  # fmt: skip
        breaker=BreakerSettings(threshold=5, cool_down_seconds=900.0, cool_down_cap_seconds=DAY_SECONDS),
        rate=RateSettings(min_spacing_seconds=0.0),
    ),
    "groww": SourceSettings(
        # a 429 pauses Groww reads for 60 s today; the breaker keeps exactly that (no doubling, so no longer pause)
        breaker=BreakerSettings(threshold=1, cool_down_seconds=60.0, cool_down_cap_seconds=60.0),
        rate=RateSettings(min_spacing_seconds=0.1, per_minute=300),  # Groww: 10 a second, 300 a minute
    ),
    "groww_sign_in": SourceSettings(rate=RateSettings(min_spacing_seconds=0.0, per_day=150)),  # 150 sign-ins a day
}
NEW_SOURCE = SourceSettings(
    retry=replace(NSE_RETRY),
    breaker=BreakerSettings(threshold=2, cool_down_seconds=900.0, cool_down_cap_seconds=DAY_SECONDS),
    rate=RateSettings(min_spacing_seconds=1.0),
)


def settings_for(source: str, cfg: dict | None = None) -> SourceSettings:
    """The defaults for `source` (NSE-strict for an unknown one) with any `resilience.<source>` override from `cfg`."""
    base = DEFAULTS.get(source, NEW_SOURCE)
    overrides = ((cfg or {}).get("resilience") or {}).get(source) or {}
    unknown = sorted(set(overrides) - set(SECTIONS))
    if unknown:
        raise ValueError(f"resilience.{source}: unknown section(s) {unknown}; allowed {sorted(SECTIONS)}")
    merged = {}
    for name, cls in SECTIONS.items():
        current = getattr(base, name)
        values = dict(overrides.get(name) or {})
        if "waits" in values:
            values["waits"] = tuple(float(w) for w in values["waits"])
        merged[name] = (replace(current, **values) if current is not None else cls(**values)) if values else current
    return SourceSettings(**merged)
