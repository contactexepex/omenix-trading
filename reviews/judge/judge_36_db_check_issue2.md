# Judge 36: omenix-dashboard issue #2, scheduled read-only check for the accepted exceptions

**Verdict: FAIL.** There is 1 should-fix finding, 1 should-fix that depends on a fact I could not check, and 2 minor
findings.

What works:
- **`db_monitor` can read no data.** I verified this with my own probes over real rows, a large object and another
  session's query.
- **Every planted condition alerts,** and an unreachable server gives UNKNOWN and fails the run.
- **The secret is handled well.**

What fails: the workflow passes green when its secret is missing, which contradicts the claimed "UNKNOWN is never a
silent pass".

**What I judged**
- **Repository:** `exepex/omenix-dashboard` main at ed21a5a (issue #2 commits ffa0090 to 9cd1266, merged 9bd4206).
- **Claims:** `reviews/claude/response_13_db_check_issue2.md`.
- **Issue text:** I did not read issue #2 itself (my GitHub scope is trading only). I used its done-when items as the
  orchestrator quoted them.

## Checks run by the judge

### Platform CI locally (fresh postgres:16, trust auth, a throwaway container removed afterwards)

```
$ PGHOST=localhost PGPORT=55432 platform/tests/ci.sh                         exit 0
== 4. role matrix: 522 checks, 460 passed, 0 failed, 62 open known exceptions (8 roles incl. db_monitor)
== 6b. role matrix: 522 checks, 498 passed, 0 failed, 24 open known exceptions
== 7. the scheduled check (issue #2) alerts on each planted condition, and only then
ok: clean server, no alert
ok: alert fires for 640 kB of large objects in postgres (report and GitHub issue name it)
ok: first alert opens an issue / ok: a later alert comments on the open issue
ok: alert fires for persistent statement_timeout = 0 on dashboard_app
ok: alert fires for a CREATE grant on schema stock
ok: the report states that password changes are not detectable
ok: clean again after cleanup
ok: an unreachable server gives UNKNOWN (exit 2) and raises an alert saying so
```

### `db_monitor` cannot read data: my own probes

I created real rows as each owner (`stock.secret_t`, `fno.secret_t`, `app.secret_t`) and a large object as
`dashboard_app`, and kept a `stock_writer` session running a query that contained a secret.

`db_monitor`'s state: not superuser, no BYPASSRLS, **no role memberships** (so no `pg_monitor` and no
`pg_read_all_stats`), and a connection limit of 2.

| Probe as `db_monitor` | Result |
|---|---|
| `SELECT` from each of the three tables | permission denied for schema |
| `COPY stock.secret_t TO STDOUT` | denied |
| `pg_stats.most_common_vals` for the table | empty |
| `lo_get(<oid>)` of `dashboard_app`'s large object | permission denied for large object |
| `SELECT … FROM pg_largeobject` | permission denied |
| Another session's query text in `pg_stat_activity` | `<insufficient privilege>` |
| `pg_read_file`; `pg_authid.rolpassword`; `SET ROLE stock_writer` | all denied |

**No secret value leaked in any probe.**

What it *can* see is catalog metadata that PostgreSQL shows every role: table names and `n_live_tup` row counts
(`pg_stat_user_tables`). That is not data content, but see minor 2.

### The password-change claim

`pg_authid` is refused to a plain role (reproduced above), and PostgreSQL keeps no password-change time. "Not
detectable read-only" is **correct**. There is one possible route the claims do not mention: Azure's server logs with
pgaudit could record `ALTER ROLE … PASSWORD` statements. That is not read-only SQL, and it would be a separate owner
decision (reasoning only).

### The workflow and scripts (read in full)

- **Triggers:** `schedule` and `workflow_dispatch` only, never `pull_request` or `pull_request_target`, so no fork
  reaches the secret.
- **Permissions:** `contents: read` and `issues: write` only.
- **Untrusted input:** none interpolated into `run:`; only `github.server_url`, `repository` and `run_id`.
- **The password:** reaches only libpq through `PGPASSWORD`. There is no `set -x`, and libpq errors never print it.
- **Exit codes:** `run.sh` exits with `db_check.sh`'s code: 1 (ALERT) or 2 (UNKNOWN) fails the job, and the issue is
  raised (UNKNOWN text: "could NOT check the server"). A failed catalog read counts as ALERT, not OK.
- **The owner's `setup_monitor.sh`:** the password is generated in memory, sent to `scram_verifier.py` and `gh secret
  set` only through stdin, never printed, and unset afterwards. The `ALTER ROLE` goes through psql's stdin with its
  errors suppressed (they would quote the verifier). I did not reproduce the SCRAM login myself; the builder's local
  proof stands as claimed.

## Findings

1. **Should fix: a missing secret is a silent pass.**
   - `.github/workflows/db-check.yml`: `if [ -z "$PGPASSWORD" ]; then echo "::notice::… not configured yet"; exit
     0; fi`.
   - That is right before setup. But once the check is live, a deleted, renamed or expired secret makes every hourly
     run green with only a notice, which is exactly the "UNKNOWN is never a silent pass" property the claims promise.
   - **Expected:** a repository variable (e.g. `DB_CHECK_ENABLED=true`, set by `setup_monitor.sh` with `gh variable
     set`). While it is set, a missing secret is UNKNOWN: exit 2, with the alert. Add a test that plants an empty
     secret with the variable set.
2. **Should fix if the repository is public (I could not verify: the proxy refuses GitHub's pages here): the report is
   published.**
   - The report goes to the run log and into the alert issue's body. In a public repository both are world-readable.
   - A live drift finding (an unexpected grant, a role's timeout switched off, large objects filling a database)
     would be announced to everyone while it is open, including an attacker who caused it.
   - The builder's own text calls the repository public ("costs nothing on a public repository").
   - **Expected:** the public log and issue carry only "ALERT" or "UNKNOWN" and a count, and the details go to the
     owner privately (e-mail, or a private repository). Or the owner confirms the repository is private.
3. **Minor: scheduled workflows in public repositories stop after 60 days without activity** (the builder's own doubt).
   A stopped check is a silent pass of another kind. Expected: a "last successful check" date shown somewhere the
   owner looks (e.g. the dashboard's status page), or a monthly keep-alive commit by the routine.
4. **Minor: `db_monitor` sees table names and live row counts** (`pg_stat_user_tables`), as every PostgreSQL role
   does. This is not row content, so "no data access" holds. The README should say "no row data; catalog metadata
   such as table names and row counts is visible", so that nobody over-reads the claim.
