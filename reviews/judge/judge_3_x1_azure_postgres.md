# Judge 3: story X1, Azure Database for PostgreSQL (server, schemas, roles, tests)

Verdict: **FAIL**.
- 1 blocking finding. It is owner action, not a builder defect: the real-server criteria have not been run yet.
- 2 should-fix findings for the builder.
- 4 minor findings.

Judged `exepex/omenix-dashboard` at 51ca61d (X1 commits 6d456c3, b4d3dba, 51ca61d). I cloned it read-only to `/tmp`.
X1 changes only `platform/` and `.github/workflows/platform-tests.yml`; `web/` is untouched.

Read in full: everything in `platform/` (sql, tests, owner scripts, README, checklist, claims) and the workflow.
Judged against the story `docs/stories/X-cross-repository.md#x1` and the orchestrator's scope decisions:
- infrastructure only;
- no PUBLIC EXECUTE on functions;
- delete lock and alert steps for the owner.

I never connected to the Azure server.

## My own runs (local postgres:16)

The Docker Hub image was rate-limited (HTTP 429), so I ran the same image from Google's mirror
(`mirror.gcr.io/library/postgres:16`): PostgreSQL 16.15, trust authentication, port 55432.

```
$ PGHOST=localhost PGPORT=55432 platform/tests/ci.sh          exit 0
ok: reference/azure_setup.sql gives reference_catalog.txt
ok: platform/sql differs from the original only by catalog_difference.txt
ok: platform/sql on top of the owner's server / on an empty server / second run changes nothing
role matrix: 365 checks, 365 passed, 0 failed (7 roles)
14 drifts: each shown by the catalog (13 also fail the matrix, 1 latent) and each removed by platform/sql
X1 platform tests: all passed
$ sha256 of trading a8cdad4 docs/migration/azure_setup.sql, of trading HEAD's copy and of platform/sql/reference/azure_setup.sql
7315f0ac…3491 (all three identical)
$ role_matrix.sh for the 4 runtime roles only: 272 checks (+4 TLS checks on the real run = the claimed 276)
```

Break attempts, each logged in as a runtime role after `ci.sh` had converged the server:

```
stock_writer  @omenix:    SELECT lo_from_bytea(0, ...)            -> large object 18072 created, persists after the session
dashboard_app @omenix:    SELECT lo_from_bytea(0, ...)            -> large object 18078 created, persists
stock_writer  @postgres:  CREATE TEMP TABLE t ...; INSERT         -> succeeds (database "postgres" keeps PUBLIC TEMP and CONNECT)
dashboard_app @postgres:  same                                    -> succeeds
both          @template1: connect                                 -> succeeds
both:         SET statement_timeout = 0                           -> 0
both:         ALTER ROLE CURRENT_USER SET statement_timeout = 0   -> stored persistently (rolconfig {statement_timeout=0})
then role_matrix.sh: 272 checks, 270 passed, 2 failed (the two timeouts): the next owner run would see it
as x1_admin (non-superuser, like Azure's admin):
  REVOKE EXECUTE ON FUNCTION lo_from_bytea, lo_create, lo_creat FROM PUBLIC -> WARNING: no privileges could be revoked
  REVOKE TEMP, CONNECT ON DATABASE postgres FROM PUBLIC                     -> WARNING: no privileges could be revoked
```

## Criteria

| # | Criterion | Builder's claim | Judge's own evidence | Result |
|---|---|---|---|---|
| 1 | Role matrix passes for every role | CI: 365/365 over 7 roles; real server waits on the owner | **Local part met.** I reproduced 365/365. The pass/fail logic is sound: a denial needs 42501, an allow needs 00000, a missing result or a failed connection counts as failure (`tests/role_matrix.sh`). 14 drift injections are caught. **Real-server part not met:** it is unrun, and the story's "judge verifies" step needs the runtime credentials, which I must not have. **Would `owner/run_real_matrix.sh` prove it?** Yes, for the checks in the matrix: verified TLS on every connection, snapshot diff, probe tables created by the owner roles so the default privileges are what gets tested. | NOT MET (pending owner) |
| 2 | A runtime role cannot create an object anywhere | Every runtime role is refused a table, view, sequence, function, type, index, schema, role and temporary table in `public`, `stock`, `fno` and `app` | The listed refusals hold. But runtime roles **can** create persistent large objects in `omenix` and temporary tables in database `postgres`, and can connect to `template1` (runs above). A non-superuser admin cannot revoke either. The matrix tests neither, so **the owner's real run would report a false PASS** for this criterion. | NOT MET |
| 3 | TLS required; non-TLS refused | Mechanism shown on a local TLS-only cluster; real check waits on the owner | Not run on the server. **Would `owner/check_tls.sh` prove it?** Mostly. A plain connection under an unknown user must be refused with "no encryption" / "SSL off"; a client-side refusal is rejected; a verified-TLS connection must work. Gap: the RESULT line ignores the `require_secure_transport` value it prints (finding 6). The "no encryption" text also appears for any pg_hba non-match (for example a future narrower firewall), but then step 3 from the same address fails too, so the combined RESULT should not falsely pass. | NOT MET (pending owner) |
| 4 | Backups enabled, retention stated, one restore tested and recorded | README: 14 days; `owner/restore_test.sh` waits on the owner | README states 14 days. The script's proof is real: a random token written, a point-in-time restore to a new server, the token read back there, and the scratch server's catalog diffed. It is not run, and its `az` calls are unexecuted (builder's doubt 7). | NOT MET (pending owner) |
| 5 | Firewall and public-access policy written and matching the server | README "Network"; `owner/server_evidence.sh` | The policy is written: one rule, 0.0.0.0-255.255.255.255, with reasons and accepted risk. The script compares the server with values typed into the script, not read from the README (finding 7). It is not run. | NOT MET (pending owner) |

## Claims vs reality

- **"365 checks over all 7 roles, 0 failed"**: true, reproduced.
- **"13 injected drifts each make it fail (and the catalog snapshot shows a 14th, latent one)"**: true, reproduced.
- **"276 checks for the 4 runtime credentials"**: true (272 plus 4 TLS checks).
- **"A denial counts only with SQLSTATE 42501"**: true.
- **Reference script "byte-identical … sha256 7315f0ac…"**: true, verified.
- **README: "No runtime role can create anything (… no temporary tables)"**: **false**. Large objects in `omenix` and temporary tables in `postgres` (finding 2).
- **README "Limits: … statement timeouts 60 s, 15 s, 30 s"**: **overstated**.
  - These are defaults the role itself can turn off per session, or persistently with
    `ALTER ROLE CURRENT_USER SET` (shown above).
  - A leaked credential can therefore run unbounded queries on a 1-vCore B1ms server.
  - `apply.sh` (`RESET ALL`) and the matrix catch the persistent change only when someone runs them (finding 3).
- **"CI: … all steps passed" on GitHub**: not verified by me (this session has no GitHub API access to that repository). It is replaced by my own local run, which passed.
- **Checklist: "Azure does not copy firewall rules to a restored server"**: reasoning only, unverified. The script handles both cases, so it causes no harm.
- **Builder's doubts 1-7**: honest and accurate as far as I can check. Doubt 3 (`public` USAGE for PUBLIC) and doubt 6 (schema-wide `app` defaults) are accepted under the orchestrator's infrastructure-only scope. The W7 follow-up is written down in the README.
- **Stray file**: `platform/evidence/.snapshot.32020` is an empty temporary file of `run_real_matrix.sh`, committed in 6d456c3. It is what the script leaves when it dies between writing and removing the snapshot, so some builder run failed mid-way and the leftover was committed unnoticed (finding 4).

## Project rules

- No secrets: grep finds no password, token or connection string; passwords are typed at hidden prompts only.
- Evidence files exclude IDs, subscription and e-mail.
- The CI workflow uses `contents: read` and no secrets, and `ci.sh` refuses an Azure host name.
- Scripts are small and single-purpose; `web/` is untouched.
- The orchestrator's three scope decisions are implemented:
  - no `app` table and no table-specific grant;
  - PUBLIC EXECUTE revoked through global default privileges, pinned in `tests/catalog_difference.txt` and checked by CI;
  - `protect_server.sh` creates the delete lock and the failed-connection alert.
- The decision to revoke PUBLIC EXECUTE is right: on the original setup `dashboard_app` could run any owner-role function (the builder showed 9 failing checks on it).

## Findings

1. **Blocking (owner action, not a builder defect).** Criteria 1, 3, 4 and 5 have real-server parts that are not done. Expected: the owner runs `owner/CHECKLIST_X1.md` steps 1-6 and commits the evidence. The judge then reads the six files; any "no" in a RESULT line, or a snapshot difference, is a finding.
2. **Should fix. Criterion 2 is not met, and the real-server test cannot show it.**
   - Runtime roles create persistent large objects in `omenix` (a leaked credential can fill the 32 GiB disk).
   - They can also connect to `postgres` and `template1` and create temporary tables in `postgres`.
   - The matrix tests neither, and README and claims say "cannot create anything".

   Expected:
   1. Add matrix checks for these exact cases: `lo_from_bytea` in `omenix`, a connection to `postgres` and `template1`, `CREATE TEMP TABLE` in `postgres`. Each check gets the expectation the server can actually enforce.
   2. In `apply.sh`/`apply_real.sh`, try `REVOKE CONNECT, TEMP ON DATABASE postgres, template1 FROM PUBLIC` and `REVOKE EXECUTE ON FUNCTION lo_create, lo_creat, lo_from_bytea, lo_import FROM PUBLIC`. On Azure the admin may or may not be allowed (locally as a non-superuser: "no privileges could be revoked"). Record the real outcome in the evidence.
   3. State whatever cannot be removed as a named exception in the README and claims, for the story owner to accept or not. Include a mitigation, such as a storage alert.
3. **Should fix. Timeouts are described as limits but are not.** Expected:
   - The README says they are defaults a role can change.
   - A matrix or snapshot run after the owner's setup shows any persistent change. The snapshot already lists role settings, so state that this is how it is caught.
   - If a real limit is wanted, propose one the server can enforce (for example `idle_in_transaction_session_timeout` / `statement_timeout` set at the database level and checked, while noting it can still be changed per session) and say plainly what it cannot stop.
4. **Minor.** Remove the committed `platform/evidence/.snapshot.32020` and ignore `platform/evidence/.snapshot.*`, `.before.*`, `.after.*` and `.restore.*`. Each owner script's die paths should remove their temporary files, for example with a `trap` inside the subshell.
5. **Minor.** `restore_test.sh`: the die paths after step 1 leave `fno.x1_restore_marker` behind, and a die after step 2 also leaves the scratch server running. The checklist tells the owner what to do by hand, which is acceptable; a trap that drops the marker would be better.
6. **Minor.** `check_tls.sh`: make the RESULT line also require `require_secure_transport = on` (it is printed but not used).
7. **Minor.** `server_evidence.sh` "compared field by field with the README" compares with values typed into the script. If the README changes, the script does not. Expected: read the values from one place, or a test that the script's expected values equal the README table.
