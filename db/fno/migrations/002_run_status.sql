-- The fno schema's run-status table (story P7; P3 named it; the W11 catalog's source for the dashboard's bell, W8).
-- One row per product and publish run, written by the runtime publisher role: `running` at the start, then
-- `published`, `failed` (with a reason code) or `skipped` (not a session) at the end; a row is born running and once
-- finished never changes (trigger below). Rows are never deleted; a run
-- that crashed without finishing stays `running` (the dashboard treats a `running` row older than the run's time limit
-- as a run that did not report). Run by the migration role (fno_owner), like 001. Also narrows the runtime role's
-- rights on 001's tables (privileges at the end).

create table if not exists fno.run_status (
    product         text        not null,
    run_id          text        not null,
    session         date        not null,
    started_at      timestamptz not null,
    finished_at     timestamptz,
    result          text        not null check (result in ('running', 'published', 'failed', 'skipped')),
    reason_code     text        check (reason_code is null or reason_code in (
                        'not_a_session', 'archive_incomplete', 'contract_changed', 'schema_invalid', 'publish_refused',
                        'read_back_mismatch', 'database_network', 'database_firewall', 'database_tls',
                        'database_authentication', 'database_privilege', 'database_other', 'figures_not_computed',
                        'crashed')),
    reason          text,
    publication_id  text,
    primary key (product, run_id),
    check ((result = 'running') = (finished_at is null)),
    check ((result in ('failed', 'skipped')) = (reason_code is not null))
);

create index if not exists run_status_latest on fno.run_status (product, started_at desc);

-- A run is born `running`, keeps its identity, and once finished never changes (judge 59, addendum 1): no bug, reused
-- run ID or manual command under the runtime role can record a success that never ran, or turn a recorded failure into
-- a success, or the reverse.
create or replace function fno.run_status_guard() returns trigger language plpgsql as $$
begin
    if tg_op = 'INSERT' then
        if new.result <> 'running' or new.finished_at is not null or new.reason_code is not null
           or new.reason is not null or new.publication_id is not null then
            raise exception 'fno.run_status: run % must be recorded as running first', new.run_id
                using errcode = 'restrict_violation';
        end if;
    elsif old.result <> 'running' then
        raise exception 'fno.run_status: run % finished as %; a finished run never changes', old.run_id, old.result
            using errcode = 'restrict_violation';
    elsif (new.product, new.run_id, new.session, new.started_at)
          is distinct from (old.product, old.run_id, old.session, old.started_at) then
        raise exception 'fno.run_status: run % keeps its product, ID, session and start', old.run_id
            using errcode = 'restrict_violation';
    end if;
    return new;
end
$$;

drop trigger if exists run_status_guard on fno.run_status;
create trigger run_status_guard before insert or update on fno.run_status
    for each row execute function fno.run_status_guard();

-- Privileges. X1's step 40 gives fno_writer SELECT, INSERT, UPDATE and DELETE on every table fno_owner creates in
-- schema fno (and dashboard_app SELECT), so each table's runtime rights are narrowed here to what the publisher needs.
-- Nothing at runtime deletes: a retention or rebuild job would run as fno_owner.
revoke update, delete, truncate on fno.pages_history from fno_writer;  -- history: append only (insert, select)
revoke delete, truncate on fno.current_publication from fno_writer;  -- a pointer: upserted (insert, update, select)
revoke delete, truncate on fno.run_status from fno_writer;  -- one row per run: insert, then finish once (update)
grant select, insert on fno.pages_history to fno_writer;
grant select, insert, update on fno.current_publication to fno_writer;
grant select, insert, update on fno.run_status to fno_writer;
grant select on fno.pages_history, fno.current_publication, fno.run_status to dashboard_app;
