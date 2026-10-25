# Judge 30: story X1 final (Azure PostgreSQL: server, schemas, roles and tests)

**Verdict: FAIL, by owner decisions only.** No builder work blocks X1.

Criteria 1, 3 and 4 are MET on the real server, from the owner's evidence files. Two criteria are not met, and neither
is a builder defect:
- **Criterion 5:** the firewall rule read-back is **NOT MET BY OWNER DECISION**. The owner chose not to rerun steps 3
  and 4 with the fixed script.
- **Criterion 2:** NOT MET in full. Four named exceptions are proven on the real server, documented, mitigated and
  detected. The owner's acceptance of them is **not recorded** anywhere I can find.

When the owner records that acceptance (one line in `docs/DESK_DECISIONS.md`), X1 can be closed as "done with named
exceptions and one owner-skipped check". That is not a clean PASS, and this file does not call it one.

**What I judged**
- **Repository:** `exepex/omenix-dashboard` at 046753d, cloned read-only to `/tmp`. That is a0bb4bb (the bash 3.2
  trap fix and the restore evidence) plus f3f1501 (the protect evidence and README).
- **Evidence:** `platform/evidence/2026-10-13-x1-{apply,real-matrix,tls,server,restore,protect}.txt` and
  `platform/evidence/README.md`.
- **Claims:** `platform/BUILDER_CLAIMS_X1.md`.
- **Owner decisions:** trading `docs/DESK_DECISIONS.md` (13 Oct 2026).
- **The real server:** I never connected to it. Everything real comes from the owner's evidence files.

## Checks run by the judge

### CI locally (fresh postgres:16 via mirror.gcr.io, trust auth, a throwaway container removed afterwards)

```
$ PGHOST=localhost PGPORT=55432 platform/tests/ci.sh                exit 0
== 4. role matrix: 428 checks, 372 passed, 0 failed, 56 open known exceptions
== 5. 15 drifts: each shows in the catalog and fails the matrix, and platform/sql removes it
== 6a. FAIL database postgres: 1 large object(s) exist  ->  ok: with omenix closed, a large object made in postgres is detected
== 6b. role matrix: 428 checks, 407 passed, 0 failed, 21 open known exceptions
```

### The bash 3.2 fix (requested by the orchestrator), run on `mirror.gcr.io/library/bash:3.2` (3.2.57) and bash 5.2

- **The builder's `tests/bash32_trap_test.sh`:** passes on both shells. On 3.2 it prints "confirmed root cause: the
  old pattern's trap does not run".
- **The builder's `tests/owner_scripts_test.sh` on 3.2:** passes, including "no owner script pipes a { } block into
  tee" and "every trap … set at the top level". `grep` finds the old pattern only in a comment.
- **My own variants:** the old structure is taken from `restore_test.sh` before a0bb4bb (`{ … trap on_exit EXIT …
  } 2>&1 | tee "$out"`), against the new one (`exec > >(tee "$out")`), both under `set -euo pipefail`:

| Pattern | End | bash 3.2: cleanup recorded | bash 5.2 |
|---|---|---|---|
| old | normal end | **NO** | yes |
| old | `exit 1` | yes | yes |
| new | normal end | yes | yes |
| new | `exit 1` | yes | yes |

  This reproduces the owner's failure exactly: the restore run ended normally on macOS's bash 3.2, and its evidence
  has no "marker table dropped" line after step 5. The fix records the cleanup in every case. **Strong evidence.**

### The evidence files: personal data and secrets (requested by the orchestrator)

My scans over all six files found:
- **IPv4:** none.
- **IPv6** (`([0-9a-f]{1,4}:){2,}`): none.
- **E-mail:** no `@`.
- **Home paths:** no `/Users/` or `/home/`.
- **Subscription IDs:** no GUIDs.
- **Credentials:** no "password=", "token=", "secret" or "subscription".

The only host name is the server's, and the admin login is shown as `<admin>`. **Clean.**

But the scrubber corrupts evidence text (minor 1):
- `x1-real-matrix.txt` shows `SELECT lo_from_bytea(0, 'x1'<IP address>ytea)` where the SQL was `'x1'::bytea`.
- `x1-server.txt` shows the README's public firewall range as `<IP address>-<IP address>`.

Reproduced with today's `owner/lib.sh redact_ips`: `x::date` becomes `x<IP address>te`, and
`0.0.0.0-255.255.255.255` becomes `<IP address>-<IP address>`.

### The named exceptions against the real evidence

`x1-real-matrix.txt`: 312 checks, 280 passed, 0 failed, **32 OPEN = 8 per runtime role**:
- 3 large-object functions;
- connect, and temporary tables, on another database (`azure_maintenance`, `azure_sys`);
- the session timeout and the persistent timeout;
- its own password.

These are exactly README exceptions 1 to 4. The README's "Real outcome on omenix-pg" section matches the file:
- exception 1 is open in all 5 databases;
- exception 2 is closed on `postgres` and `template1` and open on the two Azure-owned databases;
- exceptions 3 and 4 are unchanged.

The RESULT line also confirms "no large objects anywhere: yes".

## Criteria (final)

| # | Criterion | Evidence | Result |
|---|---|---|---|
| 1 | Role matrix passes for every role | Real server, all 4 runtime credentials over verify-full TLS: 312 checks, 0 failed; the catalog snapshot is identical (apply RESULT "catalog identical … yes"). Locally: 428 checks, 0 failed, all 7 roles. | **MET** |
| 2 | A runtime role cannot create an object anywhere | Met inside `omenix` for every schema object (every create, alter, drop and temp refused with 42501, on the real server). Not met in full: 4 named exceptions, proven open on the real server, documented with harm, mitigation and detection; the storage and failed-connection alerts are in place (protect RESULT). **The owner's acceptance of the exceptions is not recorded.** | **NOT MET in full** (exceptions named; awaiting owner acceptance) |
| 3 | TLS required, non-TLS refused | `x1-tls.txt` RESULT: require_secure_transport on: yes; non-TLS refused: yes; verified TLS works: yes (TLSv1.3) | **MET** |
| 4 | Backups with stated retention; one restore tested and recorded | Retention 14 days, matching the README. Point-in-time restore to `omenix-pg-x1restore`: the marker token written at 08:58:07 is present on the scratch server; the catalog is identical; the scratch server was deleted ("gone: yes"). RESULT is clean. Cost line "____": pending, the owner fills it in a day later (not part of the criterion's wording; recorded as pending). | **MET** (cost pending) |
| 5 | Firewall and public-access policy written down and matching the server | Policy written (README "Network"). Every listed setting matches except the firewall rule: `x1-server.txt` RESULT "1 difference(s)", because the old script could not read the rule (`unrecognized arguments`, fixed in 742443d). The rerun was skipped by the owner. | **NOT MET BY OWNER DECISION** (firewall read-back) |

## Items only the owner can attest (not verifiable by me)

- **The marker table `fno.x1_restore_marker` dropped by hand on `omenix-pg`:** owner-attested via the orchestrator.
  No evidence file shows the drop. It held one random token and no secret, so the risk if it remains is nil, but its
  removal is **owner-attested, not verified**.
- **The restore cost line:** pending, owner.

## Claims vs reality

- **"Criterion 1 PASS, criterion 3 PASS, criterion 4 PASS"** (evidence README): true from the files.
- **"Criterion 5 mostly read; firewall rule UNREAD":** true. The README correctly calls it "not met by owner decision".
- **"Root cause fixed in every owner script and tested on bash 3.2 in CI":** reproduced locally on bash 3.2; CI itself
  not seen by me.
- **"Committed unchanged except for scrubbing":** not quite. The scrubber also changed two SQL casts' text and hid the
  public range (minor 1). No secret or personal data was involved.

## Engineering standards

- `record_evidence` in `lib.sh` is one shared helper for every owner script (DRY), and two tests guard against the
  pattern returning.
- No file is over 350 lines.
- No new breach.

## Findings (all minor)

1. **`redact_ips` over-matches.** Its IPv6 rule (`[0-9A-Fa-f:]*::[0-9A-Fa-f:]*[0-9A-Fa-f]`) eats PostgreSQL casts to
   types starting with a hex letter (`::bytea`, `::date`, `::double precision`). It also redacts the public firewall
   range, which is policy, not a secret. Expected: IPv6 only with at least two hex groups and word boundaries;
   leave `0.0.0.0` and `255.255.255.255` alone; a test with SQL casts; and a note in the evidence README that two
   lines show this artefact.
2. **Judge 9 minor 1 is still open:** `platform/sql/apply.sh:14` still loops over `$(psql …)`. Under `set -e`, a
   failure of that `psql` silently skips step 12 in every database. Expected: `dbs="$(psql …)"` first, then the loop.
3. **Judge 9 minor 2 is still open:** README exception 2 should say that a large object in `template1` is copied into
   every database created later. On `omenix-pg` `template1` is now closed to connections, but large objects in it
   remain possible for the admin path; documentation only.
