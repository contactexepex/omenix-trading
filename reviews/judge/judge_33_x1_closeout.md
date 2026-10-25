# Judge 33: story X1 close-out (addendum to judge 30)

**Verdict, stated plainly: X1 is DONE, with criterion 5 NOT MET BY OWNER DECISION and deferred to omenix-dashboard
issue #1.** This is not a clean pass, and nothing here calls it one.

| Criterion | Status |
|---|---|
| 1, 3 and 4 | MET on the real server (judge 30) |
| 2 | MET **with the 4 named exceptions the owner accepted in writing** |
| 5 | The firewall rule read-back was never recorded. The owner chose to skip it, so that one check is open. |

Judge 30's three minor findings are all fixed and verified. There is no remaining builder work.

**What I judged**
- **Repository:** `exepex/omenix-dashboard` at b4e217d (merge of 433a3b6), cloned read-only.
- **Owner decision:** trading `docs/DESK_DECISIONS.md` at 6764f78.
- **Issues:** I did not read issues #1 to #4. This session's GitHub access covers exepex/trading only. The orchestrator
  reports them.

## Criterion 2: the owner's acceptance

`docs/DESK_DECISIONS.md` (6764f78) reads: "X1: the 4 named database exceptions are **accepted** (owner: 'accept')".
It names all four:
- large objects;
- connect and temporary tables on Azure's system databases;
- the role's own statement timeout;
- the role's own password.

It gives the reason (none lets a stolen credential read or change data) and the mitigations (the storage and
failed-connection alerts). These are exactly the exceptions proven open on the real server (judge 30: 32 OPEN, 8 per
runtime role). **Criterion 2: MET with owner-accepted exceptions.**

## Judge 30's minors: decisions

| # | Finding | Fix | Judge's evidence | Decision |
|---|---|---|---|---|
| 1 | `redact_ips` over-matches SQL casts and the public range | `owner/redact_ips.awk` (49 lines): valid whole-word addresses only; tests in `owner_scripts_test.sh` | My own input through `redact_ips`: `'x1'::bytea`, `::date`, `::text`, `::double`, times, `16.4`, `TLSv1.3` and `0.0.0.0-255.255.255.255` all kept. `203.0.113.45`, `20.192.0.17`, `2001:db8::1`, a full 8-group IPv6 and `::1` are all redacted. An IPv4-mapped `::ffff:198.51.100.7` comes out as two placeholders, which is harmless because nothing leaks. `owner_scripts_test.sh` passes on bash 3.2. | ACCEPTED |
| 1b | The evidence lines corrupted by the old scrubber | Regenerated from the Drive originals with the fixed scrubber | The diff 046753d..b4e217d over `platform/evidence/` changes exactly the five lines named: four `'x1'::bytea` in `x1-real-matrix.txt`, and `0.0.0.0-255.255.255.255` in `x1-server.txt`. The TLS file is untouched, so its two real addresses stay redacted. A correction note is added to the evidence README. I cannot see the Drive originals; the claim that the files were regenerated from them rests on the builder, but the diff is exactly what that would produce. | ACCEPTED |
| 2 | `apply.sh` loops over `$(psql …)` under `set -e` | `dbs="$(psql …)"` first, then the loop | With a fake `psql` that fails only on the database-list query, `apply.sh` (which has `set -euo pipefail`) now stops with exit 2 instead of skipping step 12 | ACCEPTED |
| 3 | README note on `template1` | Exception 2 now says a large object in `template1` is copied into every database created later | Read | ACCEPTED |

## Criterion 5, deferred

The firewall rule (0.0.0.0-255.255.255.255) is written down in the README, and the owner set it when creating the
server. Its read-back from Azure was never recorded: the old script had a bug, and the owner chose not to rerun the
fixed one. It stays **NOT MET BY OWNER DECISION**. The orchestrator says it is tracked as omenix-dashboard issue #1
("owner, 2 minutes"). When the owner runs the fixed `owner/server_evidence.sh` and the RESULT shows "0 difference(s)",
criterion 5 becomes MET.

The other follow-ups the orchestrator lists are improvements, not X1 criteria:
- #2: a scheduled check for the accepted exceptions;
- #3: retry closing exceptions 1 and 2;
- #4: the restore cost and a quarterly restore.

## Addendum: criterion 5 read back (omenix-dashboard 990c463)

**Criterion 5: MET.** X1 has no criterion left open.
- **The evidence:** the owner's run of `owner/server_evidence.sh`, committed as
  `platform/evidence/2026-10-13-x1-server.txt` (17:23 UTC), reads back the firewall rule `vercel-and-routines
  0.0.0.0 - 255.255.255.255` and shows **RESULT: 0 difference(s) from platform/README.md; 0 setting(s) could not be
  read**.
- **My condition is met:** this is exactly what this verdict set ("RESULT shows 0 difference(s)").
- **Closing issue #1 on this evidence is correct.**

**What this criterion does and does not mean:**
- It proves the server matches its written design. It does not make an open firewall safe.
- The rule admits every address, and the protection rests on TLS (`require_secure_transport = on`, TLS 1.2 minimum)
  and the role passwords. That was the owner's accepted exception, recorded at the time.

**Note:** the evidence file's last line ("Saved: …") shows the owner's local home-folder path, including the account
name, in a public repository. No secret or e-mail is shown. If the owner prefers, the script can print only the path
relative to the repository.
