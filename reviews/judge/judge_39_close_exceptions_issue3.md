# Judge 39: omenix-dashboard issue #3, can named exceptions 1 and 2 be closed?

**Verdict: PASS.** The issue's done-when allows "a dated note on why they still can't be closed", and that is what was
delivered (`platform/README.md`, "Can exceptions 1 and 2 be closed? (issue #3, checked 13 Oct 2026)"). Its PostgreSQL
claim is confirmed against the official PostgreSQL 18 documentation, and the false-alarm fix is sound and tested.
There are 2 minor findings.

**What I judged:** `exepex/omenix-dashboard` at 241242a. The claims are `reviews/claude/response_16_close_exceptions_issue3.md`.
Nothing was run on the real server, by the builder or by me.

## Exception 1: the PostgreSQL 18 claim, checked against postgresql.org/docs/18

| Page | What it says | Supports the claim? |
|---|---|---|
| `lo-implementation` | "SELECT privileges are required to read a large object, and UPDATE privileges are required to write or truncate it." Creating one needs neither. | yes |
| `lo-interfaces` | `lo_create` / `lo_creat` "creates a new large object"; no privilege is named for creation | yes |
| `sql-grant` | `GRANT … ON LARGE OBJECT loid`: SELECT or UPDATE only | yes |
| `release-18` (Privileges) | "Add function `has_largeobject_privilege()`"; "Allow ALTER DEFAULT PRIVILEGES to define large object default privileges" | yes: these govern read and write rights, not creation |
| `sql-alterdefaultprivileges` | `… ON LARGE OBJECTS TO/FROM …`; IN SCHEMA not allowed for large objects | yes |
| `runtime-config-compatible` | `lo_compat_privileges` "disables the new privilege checks"; "Only superusers **and users with the appropriate SET privilege** can change this setting" | yes for the conclusion (it only relaxes checks); the builder's "superuser-only" is slightly inexact (minor 2) |

**Conclusion:** no PostgreSQL version up to 18 has a privilege for *creating* a large object. The only lever is
revoking `EXECUTE` on the creating functions, and those belong to the bootstrap superuser. Exception 1 stays open on
Azure without Microsoft's help. **Confirmed (strong evidence).**

The Azure part ("no documented route") rests on the docs being silent, and I did not re-read Azure's pages. The
builder rates it "some evidence"; I agree with that rating. The optional support-request text is a sensible route to
offer.

## Exception 2: the CLOSED/FAIL change in `tests/large_objects.sh`

- **The builder's tests:** `owner_scripts_test.sh` passes (the 3 new checks: CLOSED, FAIL, no IP printed).
- **My own refusal messages** through a fake `psql` for a database where PUBLIC has CONNECT:

| Connection error | Result | Right? |
|---|---|---|
| `no pg_hba.conf entry for host …, user "db_monitor", database "azure_sys"` | CLOSED | yes (the server refuses access) |
| `password authentication failed for user "db_monitor"` | FAIL | yes (a credential problem is not "closed") |
| `too many connections for role "db_monitor"` | FAIL | yes |
| `database "azure_sys" does not exist` | FAIL | yes |

The false-alarm fix is real: before it, an Azure-refused database would have made the hourly check alert forever.
**ACCEPTED.**

## Findings (minor)

1. **A refusal of `db_monitor` is taken as proof for all plain roles, but `pg_hba.conf` rules can name users.** On
   Azure, the refusal of `azure_maintenance` and `azure_sys` is very likely the same for every customer role. Azure's
   docs say "You don't have access to this database". But the runtime roles' real connection was never tried: judge
   30's matrix measured `has_database_privilege`, which says CONNECT is granted. Expected: one owner check, a runtime
   role (e.g. `dashboard_app`) trying `psql -d azure_maintenance` once, recorded as evidence. CLOSED then holds for
   the roles that matter, not by inference.
2. **`lo_compat_privileges` is not superuser-only:** since PostgreSQL 15 it can be granted through `GRANT SET`.
   Correct the README's wording. The conclusion is unchanged, since the setting only relaxes checks.
