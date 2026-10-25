# Judge 5: story X1 re-judged (round 2)

Verdict: **FAIL**.
- **Blocking (1):** finding 1 still holds. This is owner action, not a builder defect.
- **Should fix (1, new):** a builder defect.
- **Minor (1, new).**
- **Judge 3's findings 2-7:** finding 2 is PARTLY accepted; findings 3-7 are ACCEPTED.

## What was judged

- **Repository and commit:** `exepex/omenix-dashboard`. Fix commit 00c44ed; builder's response
  `reviews/claude/response_1_x1_azure_postgres.md` at 8ea2757. I checked `origin/main` at 8ea2757, read-only, in a
  clone under `/tmp`.
- **Where this verdict lives:** omenix-dashboard now has its own `reviews/judge/`, but this session cannot push there.
  The orchestrator agreed that every verdict stays in trading's `reviews/judge/`; the owner may copy it across.
- **Never connected to Azure.** Every server test below ran on a local `postgres:16` container: PostgreSQL 16.15,
  pulled through `mirror.gcr.io` because Docker Hub rate-limited the pull.

## My own runs

```
$ PGHOST=localhost PGPORT=55432 platform/tests/ci.sh                  exit 0
== 3. ... ok: second run of platform/sql changes nothing
== 4. role matrix: 428 checks, 372 passed, 0 failed, 56 open known exceptions (7 roles)
ok: named exceptions confirmed by real attempts (template1 connect, temp table in postgres, large object)
== 5. 16 drifts caught and removed (including two made by the role itself: ALTER ROLE CURRENT_USER SET statement_timeout = 0)
== 6. role matrix: 428 checks, 407 passed, 0 failed, 21 open known exceptions
ok: large objects and other databases closed; only the self-change exceptions (timeout, password) stay open
X1 platform tests: all passed
```

Break attempt on the most likely Azure outcome:
- **Exception 1 (large objects):** closed inside `omenix`.
- **Exception 2 (other databases):** stays open, because Azure's admin does not own `postgres`.

```
x1_admin: platform/sql/apply.sh      -> "still open for PUBLIC": postgres CONNECT/TEMPORARY, template1 CONNECT, 3 lo functions
superuser in omenix only: REVOKE EXECUTE ON FUNCTION lo_create, lo_creat, lo_from_bytea FROM PUBLIC
dashboard_app @omenix:   SELECT lo_from_bytea(0,'x')   -> ERROR: permission denied for function lo_from_bytea
dashboard_app @postgres: SELECT lo_from_bytea(0,'x')   -> large object 18749 created, persists
```

Two facts explain this:
- Function privileges are per database, and `15_server_wide.sql` revokes them only in `omenix` (it runs connected
  there).
- While exception 2 is open, a runtime role can still create **persistent** large objects in database `postgres`.
  The matrix's detection check (`pg_largeobject_metadata` empty) looks only in `omenix`, so it does not see them.

## Judge 3's findings: decisions

| # | Finding (judge 3) | Builder's answer | Judge's evidence | Decision |
|---|---|---|---|---|
| 1 | Blocking: real-server parts unrun | Owner action; checklist now 7 steps | Unchanged: no evidence file in `platform/evidence/` yet | Still open (owner) |
| 2 | Criterion 2 not met; real run would give a false PASS | `known:` checks (OPEN, never a pass), `15_server_wide.sql`, 4 named exceptions in the README, storage alert, CI steps 4 and 6 | **Reproduced as claimed:** 56 OPEN, 0 failed. OPEN lines are printed and counted, and the owner's RESULT line carries `open named exceptions: N`, so the false PASS is gone. Exceptions 1, 3 and 4 are described correctly. **Exception 2 is understated:** the README says its harm is "temporary tables use disk until the session ends; reading `postgres` shows nothing of ours", but it also allows persistent large objects in `postgres`. Detection is blind there, and closing exception 1 does not close this (break attempt above). | PARTLY ACCEPTED (new finding A) |
| 3 | Timeouts presented as limits | README "defaults, not limits"; drift tests made by the role itself; watchdog proposed, not built | README read. The two self-made drifts are caught and repaired in step 5. The claim that PostgreSQL 16 has no setting a non-superuser cannot override for itself is correct as far as I know. | ACCEPTED |
| 4 | Stray `.snapshot.32020` | File removed; `evidence/.gitignore`; traps | `ls -a evidence`: only `.gitignore` and `README.md`. Traps are in `apply_real.sh:17` and `run_real_matrix.sh:20`. | ACCEPTED |
| 5 | Restore marker left after a stop | Trap always drops the marker; a stop after the restore started prints the delete command | `restore_test.sh:48` (`trap on_exit EXIT`) read; untested (needs Azure), as the builder says | ACCEPTED |
| 6 | TLS RESULT ignores `require_secure_transport` | RESULT includes it | `check_tls.sh:44` | ACCEPTED |
| 7 | `server_evidence.sh` hard-codes values | Reads the README table; CI step 0 fails on a missing row | `server_evidence.sh:26-38`; README markers at lines 23 and 37; `ci.sh:49` | ACCEPTED |

## Is the framing honest? Could an exception be closed and isn't?

The framing is mostly honest: "criterion 2 met inside `omenix` for schema objects, NOT met in full; the owner decides
on the exceptions". The README no longer says "cannot create anything", and OPEN is never a pass. Two parts overstate:
- **The README's exception 2 row** (harm and detection), finding A.
- **CI step 6's line "large objects and other databases closed"** is true only because step 6 closes both. Its
  superuser revokes the functions only in `omenix`; it never shows what happens when only exception 1 closes.

**Closable but not closed.** One part is:
- `15_server_wide.sql` revokes the large-object functions only in `omenix`.
- Where the admin is allowed to revoke them, the same revoke must also run in every other database that still accepts
  connections. Today it does not.

**Not closable by the admin**, as far as I can verify:
- **Exceptions 3 and 4:** no PostgreSQL 16 privilege for either.
- **Exception 1 on Azure:** the functions belong to the bootstrap superuser.

**Exception 2 depends on who owns `postgres` on Azure.** The owner's `apply_real.sh` run will show it; the script
records the outcome.

## Criteria

| # | Criterion | Judge's evidence | Result |
|---|---|---|---|
| 1 | Role matrix passes for every role | Locally: 428 checks, 0 failed (reproduced). Real server unrun. | NOT MET (pending owner) |
| 2 | A runtime role cannot create an object anywhere | Schema objects in `omenix`: refused (reproduced). Large objects (in `omenix` and in `postgres`), temporary tables in `postgres`, connections to `template1`: allowed unless closed on Azure. Stated as named exceptions for the owner; exception 2 understated (finding A). | NOT MET (owner to accept or close exceptions; finding A first) |
| 3 | TLS required | Script sound; RESULT now uses the server parameter; unrun | NOT MET (pending owner) |
| 4 | Backups and a tested restore | Script sound, marker always dropped; unrun | NOT MET (pending owner) |
| 5 | Firewall policy written and matching | README is the single source; CI checks the table; unrun | NOT MET (pending owner) |

## Claims vs reality (round 2)

- "428 checks, 372 passed, 0 failed, 56 open": true, reproduced.
- "CI step 6 leaves 21 OPEN": true, reproduced.
- "15 never locks the admin out": true in step 6 (the admin grants itself CONNECT and TEMPORARY before revoking
  PUBLIC's, and connects afterwards).
- "Exception 4 (own password) found while fixing": true. `ALTER ROLE CURRENT_USER PASSWORD NULL` is checked as `known:`.
- "A naive REVOKE on a function by a non-privileged role is an error": I saw a WARNING, not an error, as
  `x1_admin` on 16.15 (judge 3 run). The builder's guarded form handles both, so this is harmless; the reason given
  may be imprecise.
- "Code-size CI red only because of the design session's `platform.js` (637 lines)": not verified by me (no CI
  access). All `platform/` files are under 350 lines; the largest is `tests/role_matrix.txt` at 191.

## Engineering standards

- **Sizes:** all `platform/` files are under 350 lines (largest 191).
- **KISS / single purpose:** server-wide revokes have their own file (`15_server_wide.sql`); the matrix extension is
  one expectation prefix.
- **DRY:** the expected server settings now live only in the README.
- No breach found.

## Findings

A. **Should fix.** The README's exception 2 understates the harm, and detection is blind outside `omenix`.
   - While other databases accept connections, a runtime role can create persistent large objects there. In this
     run: object 18749 in `postgres` after exception 1 was closed in `omenix`.
   - Expected:
     1. README row 2 says so (harm: disk fill as for exception 1).
     2. `15_server_wide.sql`, or the apply script, tries the large-object revokes in every database that accepts
        connections, not only in `omenix`, and reports per database what stays open.
     3. Detection counts large objects in every database that accepts connections. For example, the admin step of
        `run_real_matrix.sh` / `apply_real.sh` connects to each and counts `pg_largeobject_metadata`.
     4. CI step 6 adds the case "exception 1 closed, exception 2 open", so the large-object check stays OPEN there.

B. **Minor.** `tests/role_matrix.txt:26` refers to `sql/05_server_wide.sql`; the file is `sql/15_server_wide.sql`.
