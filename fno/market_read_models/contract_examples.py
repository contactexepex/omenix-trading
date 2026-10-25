"""Compares built pages with the contract's India examples, field by field (stories P6 and P9, criterion 1). A paged
example is the route's page for its own query (`x-query`), made from our stored table by the contract's route
semantics (screener_route); a chain example asked for by a parameter is our page for that parameter; the others are
the whole block."""

from __future__ import annotations

from collections.abc import Iterator

from .chain_blocks import CONTRACT_PAGE, ROWS_PAGE
from .chain_route import strikes_view
from .screener_route import fno_page, stocks_page

QUERY_KEY = "x-query"
OPERATION_PAGE_KEYS = {  # the example's operation (its name before "_india") -> our page key
    "getScreenerSummaryIndia": "screener_summary",
    "getScreenerStocksIndia": "screener_stocks",
    "getFnoScreenerSummary": "fno_screener_summary",
    "getFnoScreenerRows": "fno_screener_rows",
    "getOverviewIndicesIndia": "overview_indices",
    "getIndiaSectors": "overview_sectors",
    "getChainUnderlying": "chain_underlying",
    "getChainExpiries": "chain_expiries",
    "getChainHistory": "chain_history",
    "getChainSources": "chain_sources",
}
PARAMETER_PAGES = {  # operations asked for by a parameter: our page key from the example's own payload
    "getChainRows": lambda p: ROWS_PAGE.format(expiry=p["expiry"]),
    "getContractHistory": lambda p: CONTRACT_PAGE.format(code=p["code"]),
}
NOT_PUBLISHED = {  # examples that are a view, not a page any publisher stores
    "getChainHistory_india_short": "the history cut to its last 30 sessions to show the nulls a short history gives",
}
PAGES = {"screener_stocks": stocks_page, "fno_screener_rows": fno_page}
INDIA = "_india"


def page_key(example_name: str, example: dict | None = None) -> str | None:
    """Our page key for an India example of a block we publish, else None (US blocks, other publishers, views)."""
    operation, india, _ = example_name.partition(INDIA)
    if not india or example_name in NOT_PUBLISHED:
        return None
    if operation in PARAMETER_PAGES:
        return PARAMETER_PAGES[operation](example["value"]["payload"]) if example else operation
    return OPERATION_PAGE_KEYS.get(operation)


def view(example: dict, page: str, block: dict, pages: dict[str, dict] | None = None) -> dict:
    """The served response the example shows, from the published page (a chain rows example: the route's strike set,
    from the expiry's page with every strike, NIFTY from the underlying block and the ATM strike from the expiries)."""
    query = example.get(QUERY_KEY)
    if query and page in PAGES:
        return PAGES[page](block, query)
    if page.startswith(ROWS_PAGE.format(expiry="")) and pages:
        expiry = next(e for e in pages["chain_expiries"]["expiries"] if e["expiry"] == block["expiry"])
        strikes = example["value"]["payload"]["strikes"]
        return strikes_view(block, strikes, pages["chain_underlying"]["spot"], expiry["stats"]["atm"])
    return block


def differences(ours, theirs, path: str = "") -> Iterator[tuple[str, object, object]]:
    """Every field where the two payloads differ, as (path, ours, theirs); numbers compare by value (1 == 1.0)."""
    if isinstance(ours, dict) and isinstance(theirs, dict):
        for key in sorted(set(ours) | set(theirs)):
            yield from differences(ours.get(key, "<absent>"), theirs.get(key, "<absent>"), f"{path}.{key}")
    elif isinstance(ours, list) and isinstance(theirs, list) and len(ours) == len(theirs):
        for i, (a, b) in enumerate(zip(ours, theirs)):
            yield from differences(a, b, f"{path}[{i}]")
    elif ours != theirs or type(ours) is bool and type(theirs) is not bool:
        yield path or ".", ours, theirs


def compare(pages: dict[str, dict], examples: dict) -> dict[str, list[tuple[str, object, object]]]:
    """Example name -> its differences from our pages (empty: equal field by field; a missing page: one difference)."""
    out = {}
    for name, example in examples.items():
        key = page_key(name, example)
        if key is None:
            continue
        if key not in pages:
            out[name] = [(".", "<no such page>", key)]
            continue
        out[name] = list(differences(view(example, key, pages[key], pages), example["value"]["payload"]))
    return out
