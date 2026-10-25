# Judge 9: story X1 re-judged (round 3)

Verdict: **FAIL, for owner action only.**
- **Builder findings:** none blocking and none should-fix. Judge 5's findings A and B are both ACCEPTED. Two new
  minor findings.
- **Still open:** judge 3's finding 1. The real-server criteria 1, 3, 4 and 5 have not been run yet, and the owner
  has not yet accepted or closed criterion 2's named exceptions.
- **When X1 is done:** when the owner's evidence files arrive with clean RESULT lines and the owner decides on the
  exceptions. No further builder work is needed for that.

**Judged:** `exepex/omenix-dashboard` commit 0fa812f, cloned read-only to `/tmp`. Response:
`reviews/claude/response_2_x1_azure_postgres.md` and the "judge 5" section of `platform/BUILDER_CLAIMS_X1.md`.

**Where this file lives:** trading's `reviews/judge/`, as agreed with the orchestrator; the owner may copy it to
omenix-dashboard.

**Numbering:** the orchestrator asked for "judge_6"; numbers 6-8 were already used (C1, A5, A6), so this is judge 9.

## My own runs (fresh local postgres:16, 16.15, via mirror.gcr.io)

```
$ PGHOST=localhost PGPORT=55432 platform/tests/ci.sh      exit 0
== 0. ok: 11 expected settings parsed from README.md
== 1-3. reference, convergence, idempotence: ok
== 4. role matrix: 428 checks, 372 passed, 0 failed, 56 open known exceptions
ok: no large object in any database; open per database: 3
== 6a. exception 1 closed in omenix only, exception 2 open: a large object elsewhere is still caught
FAIL  database postgres: 1 large object(s) exist
ok: with omenix closed, a large object made in postgres is detected
== 6b. role matrix: 428 checks, 407 passed, 0 failed, 21 open known exceptions
ok: large objects (every database) and other databases closed; only the self-change exceptions stay open
```

Step 6a is exactly my break scenario from judge 5 (object 18749 in `postgres` after closing `omenix`). It is now
detected, and the run fails on it as it should.

## Judge 5's findings: decisions

| # | Finding | Builder's fix | Judge's evidence | Decision |
|---|---|---|---|---|
| A | Exception 2 understated; large objects in other databases undetected | `sql/12_large_objects.sql` runs in every database the admin can connect to (`apply.sh` loop); `tests/large_objects.sh` counts large objects and lists open functions per database, and fails on any object or on a PUBLIC-reachable database it cannot check; `run_real_matrix.sh` RESULT adds "no large objects anywhere"; README rows 1 and 2 rewritten (disk fill, persistence, per-database closing) | Read `12_large_objects.sql`, `large_objects.sh`, `apply.sh:11-19` and `run_real_matrix.sh:32,42`. CI steps 6a and 6b reproduced (above). README rows now state the harm correctly. | ACCEPTED |
| B | Stale `05_server_wide.sql` reference | Now names 12 and 15 | `grep -rn 05_server_wide platform` finds only the claims table quoting the old finding | ACCEPTED |

## Criteria (state after round 3)

| # | Criterion | Result |
|---|---|---|
| 1 | Role matrix passes for every role | Locally MET (428 checks, 0 failed). Real server: NOT MET (pending owner) |
| 2 | A runtime role cannot create an object anywhere | Not met in full, by design of PostgreSQL. 4 named exceptions, each tested, detected and documented honestly. NOT MET until the owner accepts the exceptions or Azure lets the admin close 1 and 2 (`apply_real.sh` records which) |
| 3 | TLS required | NOT MET (pending owner) |
| 4 | Backups and a tested restore | NOT MET (pending owner) |
| 5 | Firewall policy matches the server | NOT MET (pending owner) |

## Claims vs reality

- "428/0/56": true, reproduced.
- "21 left OPEN after step 6b": true, reproduced.
- "Largest file 195 lines": true (`tests/ci.sh` 195, `README.md` 192). No `platform/` file is over 350 lines.

## Engineering standards

- Per-database large-object closing is its own file (12); server-wide revokes stay in 15; detection is its own script.
- Single purpose, no duplication of the function list beyond the SQL and the detector. Repeating the three function
  names in three places is tolerable; one shared list would be cleaner (minor, not raised).
- No breach.

## New findings (minor)

1. **Minor.** `apply.sh:14` builds its database list with `for db in $(psql ...)`. Under `set -e`, a failure of that
   `psql` inside the command substitution does not stop the script, so step 12 would be skipped silently. Expected:
   read the list into a variable first (`dbs="$(psql ...)"`, which `set -e` does check), then loop.
2. **Minor.** README row 2 should add one more effect: a large object created in `template1` is copied into every
   database created later from it (`CREATE DATABASE` copies `template1`). `large_objects.sh` already counts
   `template1`, so this is documentation only.
