# Judge 84: NP4 page-reads plan (plan document, lane 1), judge #2

Frozen SHA `c886e5a` (branch `story/NP4-plan`). The branch adds one file, `docs/stories/NP4-page-reads.md` (80 lines).
Text only, so the gates are the record scan and `check_numbers`. I checked the plan's facts against main and against a
dry install.

## Your six points

1. **The dependency call: agreed, and the cost is higher than stated.**
   - `pip install --dry-run --only-binary=:all: trafilatura` in a venv that already holds the whole `requirements.lock`
     would install **15** packages: babel, courlan, dateparser, htmldate, jusText, **lxml**, lxml_html_clean,
     **python-dateutil**, pytz, regex, **six**, tld, trafilatura, **tzdata**, tzlocal. That is not 11. The four in bold
     are missing from the plan's list (should-fix 1).
   - This strengthens the decision: JSON-LD and OpenGraph through the already-locked `selectolax` for NP4a and NP4b,
     with trafilatura an optional NP4c. Agentic's 422/92/82 counts cannot be checked here (no access); they are cited
     from NP0.
2. **SSRF: right in direction, but one rule is too narrow (F2) and one claim is wrong (F1).**
   - The hand-followed hops with the allowlist at each one, the https-only and no-port/userinfo rules, the cap of 5
     and the TLS verification are all right.
   - The check-then-connect gap is stated honestly.
3. **Facts and hashes only, key sentences left to the owner, and the lede loss for wire detection said plainly:**
   honest and correct. Recording it as an owner decision that does not block NP4a is right.
4. **robots.txt honoured by default: agreed.** Agentic's code cannot be checked here, so "agentic did not read it" is
   the builder's claim. See should-fix 3 on how robots.txt itself is fetched.
5. **Per-host stop, and 1.5 s across hosts through NP2b's `RequestSpacer` (reused): correct.** The spacer floors at
   1.5 s (`resolve/pacing.py`).
6. **The outlet probe from a runner, read-only, with the result going to the owner before the allowlist changes:
   correct.** The allowlist is public, so naming an outlet in its output is fine.

## Findings

1. **F1 (must fix): the inheritance claim at line 36 is wrong about NP1.**
   - The plan says a subdomain of a `fetch: false` outlet inherits `false`, as "the rule NP1 already has; alias
     inherits".
   - On main, that holds for an *unlisted* subdomain, because `lookup` finds the parent. It does **not** hold for a
     *separately listed* child. I reproduced it: `a.example.com` with `fetch: false`, plus `in.a.example.com` listed
     without `fetch`, gives `may_fetch("in.a.example.com") == True`.
   - That is the NP4 forward note from my judge_72 Addendum 1, recorded by the implementer. NP4a is the first story that
     requests a page on the strength of `may_fetch`, so it must close the gap. Either the loader refuses a listed
     child under a `fetch: false` parent, or `may_fetch` walks up the parents. Write it into NP4a as a requirement, with
     a contract row and a plant, and correct line 36.
2. **F2 (must fix): "refuse a private, loopback, link-local or reserved address" misses shared address space.**
   - Python's `ipaddress` gives `100.64.0.1` (the carrier-grade NAT range, `100.64.0.0/10`) `is_private == False`
     and `is_reserved == False`. So a check built from those flags passes it, although it is not a public address.
   - `is_global` is False for it and for every case the plan names (I checked `::ffff:127.0.0.1`, `169.254.169.254`
     and `fd00::1`).
   - Specify the rule as "connect only when every resolved address `is_global`", checked on **every** address the
     name resolves to (IPv4 and IPv6) and at every hop.

## Should fix (not blocking)

1. Correct the count to 15, and name the four missing packages.
2. Say that the 4 MB cap counts **decoded** bytes. A gzip page decompresses inside `iter_content`, so a small encoded
   body can still exceed the cap.
3. **robots.txt goes through the same `PageFetcher`:** the same allowlist at every hop, the same address rule, the same
   spacer, the same per-host stop. It is cached for the run. A robots.txt that redirects to another host counts as
   unreadable.
4. Optional, and it closes the check-then-connect gap: connect to the address that was checked (an adapter that pins
   it, with SNI and the Host header kept). It is cheap, so the gap need not be "accepted".

**Verdict: FAIL** (round 1, `c886e5a`). F1 and F2 are one paragraph each, and both are rules NP4a must hold before its
first request.

Separately, NP2c at `feb5fa9` was already reviewed: **PASS**, with two should-fix items (judge_83, main `9fe3166`).
