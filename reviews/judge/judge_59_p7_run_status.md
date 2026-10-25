# Judge 59: story P7, run status for every publish run

Date: 13 Oct 2026 (UTC). Claims: `reviews/claude/response_66_2026-10-13-p7-p8-p9-publishing.md`, addendum P7.

## Verdict: FAIL, one must-fix (small, and cheap now because the owner has not run migration 002 yet)

The database lets the runtime role rewrite a finished row. Criterion 5 says "a finished row never changes ... (grants
in the migration, tested as each role)". Only the Python adapter's `where ... result = 'running'` stops it; the
migration's grants do not.

## Per criterion

| # | Criterion | My check | Result |
|---|---|---|---|
| 1 | A successful run leaves one row, published, publication ID set, finished after started | Tests pass (106 in `tests/market_read_models`, none skipped: the PostgreSQL tests ran on local binaries) | MET |
| 2 | Each failure class has its own reason code, a test per code | `test_each_failure_leaves_its_reason_code_and_the_alerted_line` plus the contract-copy test; the table's check list equals the code list | MET |
| 3 | A closed day leaves skipped / not_a_session | Test | MET |
| 4 | A second run of the same day adds its own row, never changing an earlier one | Test; the primary key is (product, run_id) and the run ID includes the attempt | MET |
| 5 | Runtime role can insert, update, read but never delete; a finished row never changes; dashboard role only reads; tested as each role | **My run on a throwaway PostgreSQL 16 with 001 and 002:** as `fno_writer` I inserted a row, finished it as `published`, then ran `update fno.run_status set result='failed', reason_code='crashed', reason='rewritten' where run_id='gh-1-1' and result='published'`: **1 row changed**, the row now reads `failed / rewritten`. Delete as `fno_writer`: refused (InsufficientPrivilege). `dashboard_app`: reads, update refused | **PARTLY** |
| 6 | Size, lint, imports, tests | Files under 350 lines; full suite at ea4459f: 1,702 passed; ruff and imports clean (my run) | MET |

**Why it matters (risk manager):** the run status is what the dashboard shows as the reason for stale data. A bug, a
re-run with a reused run ID or a wrong manual command under the runtime role can silently turn a failure into a
success after the fact. The claim "a finished row never changes" is tested only through the adapter
(`test_postgres_rows_written_by_the_publisher_role...` calls `status.finish` twice), not as the role.

**Fix (reasoning only, the builder's choice):** in 002, a `before update` trigger that refuses any update when
`old.result <> 'running'`, or allow updates only through a narrow function. Then add a test that runs a raw `update`
as `fno_writer` on a finished row and expects a refusal.

## Claims vs reality

| Claim | Reality |
|---|---|
| "a finished row never changes" (tested) | True for the adapter only; false for the role (above) |
| `fno_writer` cannot delete; `dashboard_app` read-only | Confirmed on my throwaway server |
| Unknown code or failure without code refused | Matches the table checks I read |
| A status write failure never changes the run's result | Test passes; I did not plant it |
| Before the migration runs, publishes still work with one "NOT recorded" line | Reasoning plus test with an unreachable store; not tested against a real missing table |

## Project rules

Migration runs as `fno_owner` from the owner's Mac (no secret in files); composition root `fno/market_read_models/wiring.py`
listed in CLAUDE.md; no secret, host or user in `reason` (db_errors). I did not connect to Azure.

## Addendum 1 (re-judge of 8cf2584, merged 2344965): still FAIL, a new must-fix (DELETE on Azure)

**The trigger works.** On a throwaway PostgreSQL 16 (001 and 002 applied), as `fno_writer`:

| Attempt | Result |
|---|---|
| My exact plain `update ... set result='failed' ... where result='published'` | refused (RestrictViolation, "a finished run never changes") |
| `insert ... on conflict do update` over the finished row | refused by the same trigger |
| `alter table ... disable trigger`, `drop trigger` | refused (must be owner) |
| `create or replace function fno.run_status_finished_never_changes` | refused (no CREATE on schema fno) |
| `set session_replication_role = replica` | refused |
| `truncate`, `delete` | refused **in the test fixture** |

**But on Azure, DELETE is granted.** X1's `platform/sql/40_default_privileges.sql` (omenix-dashboard) sets, as
`fno_owner`: `ALTER DEFAULT PRIVILEGES IN SCHEMA fno GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO fno_writer`.
Migration 002 is run as `fno_owner`, so `fno.run_status` is born with DELETE for `fno_writer`; the migration's
`grant select, insert, update` adds, it does not take away. I rebuilt this on a throwaway server: roles as X1,
`fno_owner`'s default privileges as in step 40, both migrations run as `fno_owner`. Then as `fno_writer`:
`delete from fno.run_status` **deleted 1 row**. `information_schema.role_table_grants` shows
`DELETE, INSERT, SELECT, UPDATE` for `fno_writer` on `run_status`, `pages_history` and `current_publication`.

The repository's PostgreSQL fixture (`tests/market_read_models/postgres_server.py`, `PLATFORM`) creates the schema and
roles but not X1's default privileges, so the test "fno_writer cannot delete" passes locally and would be false on
Azure. A delete also bypasses the update trigger: the run history can still be erased.

**Fix (reasoning only):** in 002, `revoke delete, truncate on fno.run_status from fno_writer;` (or a `before delete`
trigger), and make the fixture apply X1's step-40 defaults as `fno_owner` and run the migrations as `fno_owner`, so the
tests see Azure's grants. The owner should not run 002 until then.

**Also noted, not a criterion:** `fno_writer` can insert a row that is born finished (`result='published'` with a made-up
publication ID); I did. The criterion speaks of changes, not inserts, so this is information. A `before insert`
check that new rows are `running` would close it if every code path starts with `running` (reasoning only).
`pages_history` and `current_publication` (001) carry the same default DELETE; whether P6 meant them to be
append-only is for the builder to state.

## Addendum 2 (re-judge of ab629ff, merged e5c4e91): PASS; the owner may run 002

I reproduced Azure's set-up on a throwaway PostgreSQL 16 with **X1's own platform files** (omenix-dashboard
`platform/sql/00_roles.sql`, `20_schemas.sql`, `30_grants.sql`, `40_default_privileges.sql`), not the repository's
fixture copy. Then:
1. I ran 001 as `fno_owner`.
2. As `fno_writer`, I inserted one `pages_history` row and one `current_publication` row (001's live state, with the
   step-40 rights including DELETE).
3. I ran 002 as `fno_owner`, then ran it again.

**Migration:** the first run exit 0, the second run exit 0 (idempotent: only "already exists, skipping" notices).
Both rows were kept.

**Rights after 002 (information_schema):**

| Role | `pages_history` | `current_publication` | `run_status` |
|---|---|---|---|
| `fno_writer` | INSERT, SELECT | INSERT, SELECT, UPDATE | INSERT, SELECT, UPDATE |
| `dashboard_app` | SELECT | SELECT | SELECT |

**Probes as `fno_writer`:**

| Attempt | Result |
|---|---|
| `delete` and `truncate` on each of the three tables | refused, all six |
| `update` on `pages_history` | refused |
| Insert a run born `published` | refused ("must be recorded as running first") |
| Insert a run born `running` with a reason | refused |
| Insert a proper `running` row, then finish it once | allowed |
| Change a running row's run ID | refused (identity kept) |
| Rewrite the finished row | refused |
| Upsert over the finished row | refused |
| Update the pointer, as the publisher needs | allowed |
| Disable or drop the trigger, replace its function, `session_replication_role` | refused |

**Probes as `dashboard_app`:** insert refused, select allowed.

**The publisher's own SQL fits the narrowed rights:**
- pages: `insert ... on conflict do nothing` needs INSERT only;
- pointer: an upsert, which needs INSERT and UPDATE;
- run status: the insert as `running`, then one update.

`tests/market_read_models`: 129 passed (the fixture now mirrors X1 steps 00-40 and runs the migrations as `fno_owner`).

All six criteria are now MET. **Verdict: PASS.** The owner can run 002 as `fno_owner`. Expect two NOTICE lines on the
first run, about the trigger and index not existing yet; they are harmless.
