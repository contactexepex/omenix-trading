"""The shipped defaults ARE today's numbers (copied from the code they replace); the config block overrides them."""

from pathlib import Path

import pytest

from fno.ingestion.storage import drive_session, retry_policy
from fno.shared import http_pacing
from fno.shared.config import ALLOWED_APP_KEYS, load_app_config
from fno.shared.resilience.settings import DEFAULTS, NEW_SOURCE, settings_for

ROOT = Path(__file__).resolve().parents[3]


def test_nse_defaults_equal_the_current_retry_policy_and_pacer():
    s = settings_for("nse")
    assert s.retry.waits == tuple(float(w) for w in retry_policy.RETRY_WAITS)
    assert s.retry.retry_after_ceiling_seconds == retry_policy.MAX_RETRY_AFTER_SECONDS
    assert s.breaker.threshold == http_pacing.REFUSALS_BEFORE_PAUSE == 2
    assert s.breaker.cool_down_seconds == http_pacing.COOL_OFF_SECONDS
    assert s.rate.min_spacing_seconds == http_pacing.HOST_SPACING_SECONDS["nsearchives.nseindia.com"]


def test_drive_defaults_equal_the_current_session_waits():
    assert settings_for("drive").retry.waits == tuple(float(w) for w in drive_session.RETRY_WAITS)


def test_groww_defaults_keep_the_sixty_second_pause_the_budgets_and_the_daily_sign_in_limit():
    s = settings_for("groww")
    assert (s.breaker.threshold, s.breaker.cool_down_seconds, s.breaker.cool_down_cap_seconds) == (1, 60.0, 60.0)
    assert (s.rate.per_minute, s.rate.min_spacing_seconds) == (300, 0.1)
    assert settings_for("groww_sign_in").rate.per_day == 150


def test_every_default_retry_cap_is_at_least_twice_its_largest_floor():
    for name, source in DEFAULTS.items():
        if source.retry:
            assert source.retry.cap_seconds >= 2 * max(source.retry.waits), name


def test_a_new_source_starts_as_strict_as_nse():
    new = settings_for("bse")
    assert new == NEW_SOURCE and new.breaker.threshold <= settings_for("nse").breaker.threshold
    assert new.retry.waits == settings_for("nse").retry.waits


def test_the_config_key_is_allowed_and_ships_empty_so_the_defaults_apply():
    assert "resilience" in ALLOWED_APP_KEYS
    assert load_app_config()["resilience"] == {}
    assert settings_for("nse", load_app_config()) == settings_for("nse")


def test_a_config_override_changes_only_what_it_names():
    cfg = {
        "resilience": {
            "nse": {"breaker": {"cool_down_seconds": 1800}, "retry": {"waits": [6, 16, 46], "cap_seconds": 100}}
        }
    }
    s = settings_for("nse", cfg)
    assert s.breaker.cool_down_seconds == 1800 and s.breaker.threshold == 2
    assert s.retry.waits == (6.0, 16.0, 46.0) and s.retry.retry_after_ceiling_seconds == 120.0
    assert settings_for("drive", cfg) == settings_for("drive")


def test_an_override_that_breaks_a_rule_is_refused_not_applied():
    with pytest.raises(ValueError, match="cap_seconds"):
        settings_for("nse", {"resilience": {"nse": {"retry": {"cap_seconds": 50}}}})
    with pytest.raises(ValueError, match="unknown section"):
        settings_for("nse", {"resilience": {"nse": {"colour": {}}}})


def test_the_transition_logs_are_union_merged_in_gitattributes():
    text = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "research/data/resilience/*.csv merge=union" in text
