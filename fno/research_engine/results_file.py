"""Writes a period's results (story B3): `results_<period>.json` (sorted keys, every float rounded to a fixed number of
decimals, nothing that changes between runs) and a readable `results_<period>.md`. Rounding happens only here, after
the verdict was computed on unrounded numbers."""

from __future__ import annotations

import json
from pathlib import Path

JSON_DECIMALS = 6
RESULTS_JSON, RESULTS_MD = "results_{period}.json", "results_{period}.md"
NONE_TEXT = "-"


def rounded(value):
    if isinstance(value, float):
        return round(value, JSON_DECIMALS) + 0.0  # + 0.0 turns -0.0 into 0.0
    if isinstance(value, dict):
        return {str(k): rounded(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [rounded(v) for v in value]
    return value


def results_json(document: dict) -> str:
    return json.dumps(rounded(document), sort_keys=True, indent=1, ensure_ascii=True) + "\n"


def _money(value) -> str:
    return NONE_TEXT if value is None else f"{value:,.2f}"


def _share(value) -> str:
    return NONE_TEXT if value is None else f"{value:.0%}"


def results_markdown(document: dict) -> str:
    period = document["period"]
    lines = [
        f"# {document['experiment']}: {period['name']} results ({period['start']} to {period['end']})",
        "",
        document["note"],
        "",
        f"Opportunities: {len(document['opportunities'])}. "
        + ("Pass/fail applies (protocol section 8)." if document["decisive"] else "Reported only: no pass/fail."),
        "",
        "| Policy | Total net (Rs) | Mean per opportunity | Traded | Win rate (traded) | Worst | Max drawdown | "
        "No-settlement total | Impossible exits (count, net) | Best-year share | Statuses |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for code, policy in document["policies"].items():
        s = policy["summary"]
        statuses = ", ".join(f"{k} {v}" for k, v in s["status_counts"].items())
        lines.append(
            f"| {code} | {_money(s['total_net'])} | {_money(s['mean_net'])} | {s['traded']} | "
            f"{_share(s['win_rate_traded'])} | {_money(s['worst_opportunity'])} | {_money(s['max_drawdown'])} | "
            f"{_money(s['no_settlement_total_net'])} | {s['exits_outside_payoff']}, "
            f"{_money(s['exits_outside_payoff_net'])} | {_share(s['best_year_share'])} | {statuses} |"
        )
    if document["decisive"]:
        lines += _verdict_lines(document)
    return "\n".join(lines) + "\n"


def _verdict_lines(document: dict) -> list[str]:
    overall = document["overall"]
    lines = ["", f"## Verdict: {overall['status']}; passing: {', '.join(overall['passing_policies']) or 'none'}", ""]
    lines += ["| Policy | Criterion | Value | Rule | Threshold | Pass |", "|---|---|---|---|---|---|"]
    for code, policy in document["policies"].items():
        for c in policy.get("verdict", {}).get("criteria", []):
            lines.append(
                f"| {code} | {c['name']} | {_money(c['value'])} | {c['rule']} | {_money(c['threshold'])} | "
                f"{'yes' if c['passed'] else 'no'} |"
            )
    return lines


def write_results(folder: Path, document: dict) -> tuple[Path, Path]:
    period = document["period"]["name"]
    json_path, md_path = folder / RESULTS_JSON.format(period=period), folder / RESULTS_MD.format(period=period)
    json_path.write_text(results_json(document), encoding="utf-8")
    md_path.write_text(results_markdown(rounded(document)), encoding="utf-8")
    return json_path, md_path
