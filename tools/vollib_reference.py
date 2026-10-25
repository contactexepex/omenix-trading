"""Writes the outside reference for the project's three option pricers (OSS1 part a, response 319): vollib's Black-76
and spot Black-Scholes prices on a fixed grid, into `tests/fixtures/pricing/vollib_reference.json`, which
`tests/checks/test_pricing_reference.py` reads. vollib is needed only to regenerate this file, never by the app or the
gates (a new runtime dependency needs the owner):

    pip install --target /tmp/vl py_vollib==1.0.12 && PYTHONPATH=/tmp/vl python tools/vollib_reference.py
"""

from __future__ import annotations

import itertools
import json
from importlib.metadata import version
from pathlib import Path

OUTPUT = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "pricing" / "vollib_reference.json"
FORWARDS, STRIKES = (20000.0, 25000.0), (19000.0, 25000.0, 26500.0)
YEARS = (1 / 365, 7 / 365, 30 / 365, 0.5)
RATES, SIGMAS, KINDS = (0.0, 0.065), (0.05, 0.13, 0.4), ("CE", "PE")


def grid() -> list[dict]:
    from py_vollib.black import black
    from py_vollib.black_scholes import black_scholes

    rows = []
    for forward, strike, years, rate, sigma, kind in itertools.product(FORWARDS, STRIKES, YEARS, RATES, SIGMAS, KINDS):
        flag = "c" if kind == "CE" else "p"
        rows.append({"underlying": forward, "strike": strike, "years": years, "rate": rate, "sigma": sigma,
                     "kind": kind, "black76": black(flag, forward, strike, years, rate, sigma),
                     "black_scholes": black_scholes(flag, forward, strike, years, rate, sigma)})  # fmt: skip
    return rows


def main() -> None:
    document = {"source": f"py_vollib {version('py_vollib')}", "rows": grid()}
    OUTPUT.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8")
    print(f"{len(document['rows'])} rows written to {OUTPUT.relative_to(OUTPUT.parents[3])}")


if __name__ == "__main__":
    main()
