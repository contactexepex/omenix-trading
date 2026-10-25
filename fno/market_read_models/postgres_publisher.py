"""A ReadModelPublisher writing to the Azure Postgres `fno` schema (story P6; tables of db/fno/migrations, P3's
design) with the publisher role's connection string from the environment only. One transaction per publication: every
page inserted, the publication checked complete, then the current-publication pointer moved; any failure rolls all of
it back, so the dashboard keeps reading the previous publication."""

from __future__ import annotations

from collections.abc import Callable

from .db_errors import described, failure_class
from .publication import PRODUCT, Publication, hashes
from .publisher import PublishFailed, ReadModelPublisher

INSERT_PAGE = """
insert into fno.pages_history (product, page_key, publication_id, market, as_of, cutoff, built_at, schema_version,
                               source_commit, payload_sha256, payload)
values (%(product)s, %(page_key)s, %(publication_id)s, %(market)s, %(as_of)s, %(cutoff)s, %(built_at)s,
        %(schema_version)s, %(source_commit)s, %(payload_sha256)s, %(payload)s)
on conflict (product, page_key, publication_id) do nothing
"""
STORED_HASHES = "select page_key, payload_sha256 from fno.pages_history where product = %s and publication_id = %s"
MOVE_CURRENT = """
insert into fno.current_publication (product, publication_id, as_of, published_at) values (%s, %s, %s, now())
on conflict (product) do update set publication_id = excluded.publication_id, as_of = excluded.as_of,
                                    published_at = excluded.published_at
where fno.current_publication.publication_id is distinct from excluded.publication_id
"""
CURRENT_PAGES = """
select h.page_key, h.market, h.as_of::text, to_char(h.cutoff at time zone 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'),
       to_char(h.built_at at time zone 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'), h.schema_version, h.source_commit,
       h.payload_sha256, h.product, h.publication_id, h.payload
from fno.pages_history h join fno.current_publication c using (product, publication_id)
where h.product = %s
"""
COLUMNS = ("page_key", "market", "as_of", "cutoff", "built_at", "schema_version", "source_commit", "payload_sha256",
           "product", "publication_id", "payload")  # fmt: skip


def psycopg_connect(url: str):
    import psycopg

    return psycopg.connect(url, autocommit=False)


class PostgresPublisher(ReadModelPublisher):
    name = "Azure Postgres (fno schema)"

    def __init__(self, url: str, connect: Callable = psycopg_connect):
        self._url, self._connect = url, connect  # the URL holds the credential: never printed

    def publish(self, publication: Publication) -> int:
        from psycopg import Error
        from psycopg.types.json import Jsonb

        added = 0
        try:
            with self._connect(self._url) as connection, connection.cursor() as cursor:
                for record in publication.records.values():
                    cursor.execute(INSERT_PAGE, {**record, "payload": Jsonb(record["payload"])})
                    added += cursor.rowcount
                cursor.execute(STORED_HASHES, (PRODUCT, publication.publication_id))
                if dict(cursor.fetchall()) != hashes(publication):
                    raise PublishFailed(f"{publication.publication_id}: stored pages differ from this publication")
                cursor.execute(MOVE_CURRENT, (PRODUCT, publication.publication_id, publication.day))
        except Error as exc:
            raise PublishFailed(f"{publication.publication_id}: {described(exc)}", failure_class(exc)) from exc
        return added

    def stored(self, publication_id: str) -> dict[str, str]:
        from psycopg import Error

        try:
            with self._connect(self._url) as connection, connection.cursor() as cursor:
                cursor.execute(STORED_HASHES, (PRODUCT, publication_id))
                return dict(cursor.fetchall())
        except Error as exc:
            raise PublishFailed(f"{publication_id}: read-back: {described(exc)}", failure_class(exc)) from exc

    def current(self) -> dict[str, dict]:
        from psycopg import Error

        try:
            with self._connect(self._url) as connection, connection.cursor() as cursor:
                cursor.execute(CURRENT_PAGES, (PRODUCT,))
                return {row[0]: dict(zip(COLUMNS[1:], row[1:])) | {"page_key": row[0]} for row in cursor.fetchall()}
        except Error as exc:
            raise PublishFailed(f"current publication: {described(exc)}", failure_class(exc)) from exc
