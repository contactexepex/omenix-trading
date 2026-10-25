"""The gate for paper decisions on live features (story B7 criterion 3): a playbook strategy may reach status `paper`
only if every live feature it uses passes the strategy's own frozen use rule (story D1's playbook loader calls this).

The gate never trusts a report's `validated` flag or its summary numbers: it recomputes days, state agreement and live
availability from the report's per-day (live, close) values and checks them against the strategy's rule (judge 44: a
95% strategy must not pass on a 90% report, and an edited flag must not pass)."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

from .live_validation import LiveUseRule, agreement_numbers


class LiveFeaturesNotValidated(ValueError):
    """The strategy uses a live feature without a report that passes its frozen use rule."""


def report_passes(report: Mapping, rule: LiveUseRule) -> bool:
    pairs = [(row["live"], row["close"]) for row in report.get("comparisons", [])]
    return rule.passes(*agreement_numbers(pairs))


def unvalidated(live_features: Sequence[str], reports: Mapping[str, Mapping], rule: LiveUseRule) -> list[str]:
    """The live features with no report, or whose report's per-day values fail the rule."""
    return [name for name in live_features if name not in reports or not report_passes(reports[name], rule)]


def require_validated(
    strategy: str, live_features: Sequence[str], reports: Mapping[str, Mapping], rule: LiveUseRule
) -> None:
    missing = unvalidated(live_features, reports, rule)
    if missing:
        raise LiveFeaturesNotValidated(
            f"{strategy} cannot reach status paper: live features not validated under its rule {rule}: {missing}"
        )


def reports_from_folder(folder: Path) -> dict[str, dict]:
    """Live feature name -> its committed validation report (`python -m fno research validate-live`)."""
    reports = (json.loads(path.read_text(encoding="utf-8")) for path in sorted(folder.glob("*.json")))
    return {report["live_feature"]: report for report in reports}
