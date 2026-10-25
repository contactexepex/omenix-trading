-- The fno schema's read-model tables (story P6, following story P3's design: one history table with a unique
-- (product, page_key, publication_id), and one current-publication pointer per product). Run by the migration role
-- (X1); the runtime publisher role only inserts into fno.pages_history and upserts fno.current_publication.
-- The fno schema itself is created by X1's platform SQL (omenix-dashboard platform/sql); fno_owner has no CREATE on the
-- database by design, so even "create schema if not exists" is refused (13 Oct 2026, first real run).

create table if not exists fno.pages_history (
    product         text        not null,
    page_key        text        not null,
    publication_id  text        not null,
    market          text        not null,
    as_of           date        not null,
    cutoff          timestamptz not null,
    built_at        timestamptz not null,
    schema_version  text        not null,
    source_commit   text        not null,
    payload_sha256  text        not null check (payload_sha256 ~ '^[0-9a-f]{64}$'),
    payload         jsonb       not null,
    primary key (product, page_key, publication_id)
);

create table if not exists fno.current_publication (
    product         text        primary key,
    publication_id  text        not null,
    as_of           date        not null,
    published_at    timestamptz not null default now()
);
