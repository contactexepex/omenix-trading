"""One session's publication (story P6): every block's stored row (the read-model columns W11 and P3 name, with the
payload and its SHA-256), checked against the pinned W11 contract the way the dashboard serves it, before anything may
be published. A block that breaks its schema stops the whole publication. The publication ID names the session and
its content (`nse-<day>-<12 hex of the pages' hashes>`), never the code commit: a second run of the same day with
the same pages has the same ID and adds nothing, and NSE's later version of a file makes a new one."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date

from ..models import now_utc
from .blocks import BlockBuilder, SessionRows
from .contract import ContractBroken, PinnedContract
from .page_holds import PAGE_HOLDS, PageHeld, page_holds_payload

MARKET, PRODUCT, PUBLISHER, PAPER = "india", "fno", "fno", "Paper"
FRESHNESS_RULE = "fno_calendar"
ID_HEX = 12  # hex digits of the content hash in a publication ID
PAGED_HOLD = "{block} stores one page per parameter: a paged block cannot be held (story P11 holds single pages only)"
ROW_FIELDS = (
    "market",
    "page_key",
    "as_of",
    "cutoff",
    "built_at",
    "source_commit",
    "product",
    "publication_id",
    "payload_sha256",
)  # a held copy keeps these of its previous row (its id and hash are then this publication's)


@dataclass(frozen=True)
class Publication:
    day: date
    publication_id: str
    records: dict[str, dict]  # page key -> stored row
    inputs: dict[str, list] = field(default_factory=dict)  # page key -> the archived copies it read (P8, judge 66)
    held: dict[str, str] = field(default_factory=dict)  # page key -> the rule it is held for (story P11)
    broken: list[str] = field(default_factory=list)  # held pages whose previous copy no longer matches the pin


def canonical(payload) -> bytes:
    """The payload's bytes for its SHA-256 (sorted keys, no spaces), as the contract's examples hash them."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def utc_now() -> str:
    return now_utc().strftime("%Y-%m-%dT%H:%M:%SZ")


class PublicationBuilder:
    def __init__(self, builders: list[BlockBuilder], contract: PinnedContract, source_commit: str, clock=utc_now,
                 holds_page: BlockBuilder | None = None):  # fmt: skip
        self.builders, self.contract, self.source_commit, self.clock = builders, contract, source_commit, clock
        self.holds_page = holds_page  # story P11's `page_holds` (None until its schema is pinned)

    def build(self, rows: SessionRows, previous: Callable[[], dict[str, dict]] = dict) -> Publication:
        """`previous`: the current publication's rows by page key, read only when a page is held (story P11)."""
        built_at, before = self.clock(), _once(previous)
        pages, held, broken = [], {}, []
        for builder in self.builders:
            try:
                pages += [(builder, key, payload, None) for key, payload in builder.pages(rows).items()]
            except PageHeld as hold:
                if type(builder).pages is not BlockBuilder.pages:  # one page per parameter: no single row to keep
                    raise TypeError(PAGED_HOLD.format(block=type(builder).__name__)) from hold
                held[builder.page_key] = hold.rule
                kept = self._held(builder, before().get(builder.page_key), hold.rule, broken)
                if kept is not None:
                    pages.append((builder, builder.page_key, kept["payload"], kept))
        if self.holds_page is not None:
            previous_holds = before().get(PAGE_HOLDS, {}).get("payload") if held else None
            shown = {key for _, key, _, kept in pages if kept is not None}
            notice = page_holds_payload(held, shown, previous_holds, rows.day)
            pages.append((self.holds_page, PAGE_HOLDS, notice, None))
        sha256 = {key: hashlib.sha256(canonical(payload)).hexdigest() for _, key, payload, _ in pages}
        publication_id = publication_id_for(rows.day, sha256)
        records = {}
        for builder, key, payload, kept in pages:
            if kept is not None:  # a held copy: its own session, build time and code, under this publication
                records[key] = {**kept, "payload_sha256": sha256[key], "publication_id": publication_id}
                continue
            record = {
                "market": MARKET, "page_key": key, "as_of": rows.day.isoformat(), "cutoff": built_at,
                "built_at": built_at, "schema_version": self.contract.version, "source_commit": self.source_commit,
                "payload_sha256": sha256[key], "product": PRODUCT, "publication_id": publication_id, "payload": payload,
            }  # fmt: skip
            self.check(builder, record)
            records[key] = record
        inputs = {builder.page_key: builder.inputs(rows) for builder in self.builders}
        used = {key: used for key, used in inputs.items() if used}
        return Publication(rows.day, publication_id, records, used, held, broken)

    def _held(self, builder: BlockBuilder, previous: dict | None, rule: str, broken: list[str]) -> dict | None:
        """The held page's row (story P11), or None: no earlier page, the block shows none while held, or the copy no
        longer matches the current pin (listed in `broken`; never a whole-run stop)."""
        payload = builder.held(previous["payload"], rule) if previous else None
        if payload is None:
            return None
        record = {key: previous[key] for key in ROW_FIELDS} | {
            "payload": payload,
            "schema_version": self.contract.version,
        }
        try:
            self.check(builder, record)
        except ContractBroken:
            broken.append(builder.page_key)
            return None
        return record

    def check(self, builder: BlockBuilder, record: dict) -> None:
        """ContractBroken unless the stored payload matches W11's stored schema (where W11 names one) and the response
        the route serves from it alone matches W11's response schema (a paged block: its default page)."""
        if builder.stored_schema:
            self.contract.validate(builder.stored_schema, record["payload"])
        if builder.served_schema:
            self.contract.validate(builder.served_schema, served(record, builder.served(record["payload"])))


def hashes(publication: Publication) -> dict[str, str]:
    """Page key -> payload SHA-256: what a store must hold for the publication."""
    return {page_key: record["payload_sha256"] for page_key, record in publication.records.items()}


def publication_id_for(day: date, sha256: dict[str, str]) -> str:
    """The session and its content: the same pages always give the same ID."""
    content = canonical(sha256)
    return f"nse-{day.isoformat()}-{hashlib.sha256(content).hexdigest()[:ID_HEX]}"


def served(record: dict, payload: dict) -> dict:
    """The response the route makes of a stored row: its envelope fields added (fresh: just built)."""
    freshness = {"state": "fresh", "rule": FRESHNESS_RULE, "built_at": record["built_at"], "age_minutes": 0,
                 "reason": None}  # fmt: skip
    return {**record, "publisher": PUBLISHER, "freshness": freshness, "paper": PAPER, "payload": payload}


def _once(read: Callable[[], dict[str, dict]]) -> Callable[[], dict[str, dict]]:
    """`read`, called at most once (the store is read only when a page is held)."""
    found: list[dict[str, dict]] = []

    def cached() -> dict[str, dict]:
        if not found:
            found.append(read())
        return found[0]

    return cached
