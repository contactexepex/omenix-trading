"""Story P11, the per-page hold: a page that must not be shown, for a rule its block's story names, is held on its own,
while every other page publishes (owner, 16 Oct 2026; judge 251 addendum 1).

- A block raises `PageHeld(rule)` from `build`; `rule` is a fixed sentence, never a value.
- Its held page is what the block's `held(previous_payload, rule)` makes of the previous publication's page: the
  previous payload unchanged (a page that stays true for its own session: its row is kept byte for byte), a changed
  one (the card's `withheld`), or None (no row: a page whose old payload states what the rule says is no longer true).
- A held copy is checked against the current pin like any page; one that no longer matches gets no row, never a
  whole-run stop, and its line says why.
- Every publication says which pages are held (`page_holds`), each with the first session held in a row (`since`);
  the page_holds page itself is never held."""

from __future__ import annotations

from datetime import date

from .blocks import BlockBuilder, SessionRows

PAGE_HOLDS = "page_holds"
SHOWS_PREVIOUS, SHOWS_NOTHING = "previous_page", "nothing"
HELD_LINE = "{day}: {page} held back: {rule}"
COPY_BROKEN = "; its previous page no longer matches contract {version}, so it is not published"


class PageHeld(Exception):
    """This page must not be published today, for `rule`: a fixed sentence its block's story writes, shown on screen
    as the hold's reason, so it holds no value and no digit (contract 2.13.0 refuses digits)."""

    def __init__(self, rule: str):
        super().__init__(rule)
        self.rule = rule


def page_holds_payload(holds: dict[str, str], shown: set[str], previous: dict | None, day: date) -> dict:
    """Each held page (contract 2.13.0 `FnoPageHolds`), oldest hold first: its reason, whether the screen shows its
    previous page or nothing, and the first session it has been held in a row: carried from the previous publication's
    page_holds while the page stays held, reset when a hold lifts and returns."""
    before = {h["page_key"]: h["since"] for h in (previous or {}).get("holds", [])}
    rows = [{"page_key": key, "since": before.get(key, day.isoformat()), "reason": reason,
             "shows": SHOWS_PREVIOUS if key in shown else SHOWS_NOTHING} for key, reason in holds.items()]  # fmt: skip
    return {"holds": sorted(rows, key=lambda h: (h["since"], h["page_key"]))}


def held_lines(day: date, held: dict[str, str], broken: list[str], version: str) -> list[str]:
    """One line per held page (the alert and the run status), naming the rule and never a value."""
    return [HELD_LINE.format(day=day, page=page, rule=rule) + (COPY_BROKEN.format(version=version) if page in broken
            else "") for page, rule in sorted(held.items())]  # fmt: skip


class PageHoldsBlock(BlockBuilder):
    """The `page_holds` page's key and schema, for the publication's contract check. Its payload is the publication's
    own (`page_holds_payload`), built after every other page, so it can never itself be held."""

    page_key, served_schema = PAGE_HOLDS, "FnoPageHoldsResponse"

    def build(self, rows: SessionRows) -> dict:
        raise NotImplementedError("page_holds is built by the publication from its held pages, never from the rows")
