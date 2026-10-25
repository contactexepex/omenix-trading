# Judge 57: story W2, the Azure read path for F&O (Screener and Markets blocks)

**Verdict: PASS**, with one dependency gap and two notes I could not verify myself.
- **What I verified:**
  - all 3 criteria, by the integration test on a throwaway PostgreSQL with TLS (it ran, not skipped);
  - 3 plants of mine, each caught;
  - no examples at runtime in database mode;
  - TLS verify-full with pinned roots;
  - the session calendar equal to trading's.
- **The dependency gap:** "stale with the reason" names what is missing and when it was due, but not why a run
  failed. That needs a run-status table, which no publisher writes yet (P3 or P6, not W2).
- **Unverified by me:** the real Vercel to Azure read (the owner's smoke test), and the stock pages' environment-name
  claim against the stock repository (outside my reach).

**What I judged**
- **Repository:** `exepex/omenix-dashboard` at 0a1fa0e (W2 code 5a8792c).
- **Claims:** `reviews/claude/response_28_w2_fno_azure_read.md`.
- **Owner checklist:** `docs/W2_OWNER_STEPS.md`.
- **Story:** trading `docs/stories/X-cross-repository.md`, W2.

## Checks run by the judge

```
$ npm ci --ignore-scripts; npx tsc --noEmit                    clean
$ npm test                                                     417 tests, 417 pass
$ node --test lib/fno/tests/*.test.ts lib/screener/tests/query-engine.test.ts      24 pass, 0 skipped (real PostgreSQL 16 with TLS)
$ node tools/check_code_size.mjs                               within limits
$ diff design/mockups/_platform/nse_sessions.csv  trading research/data/calendar/nse_sessions.csv      identical
```

**My plants (each reverted; `git status` clean):**

| Plant | Caught by |
|---|---|
| The driver's message appended to `FnoUnavailable` (`db.ts:48`) | integration test 3: "database errors reach the page as a class only" fails |
| `checkServerIdentity` disabled (any host name accepted) | integration test 5: "TLS: verified against the pinned roots and the server's name" fails |
| The Screener fixture module imported eagerly in `wiring.ts` | `no-examples.test.ts`: "with the database configured, no example or fixture adapter is ever loaded" fails |

## Criteria

| # | Criterion | Judge's evidence | Result |
|---|---|---|---|
| 1 | During a publication, the previous complete one shows with "publishing"; after a failed run, the previous one with "stale" and the reason | Integration test 1 on the throwaway server: a half-written 12 Oct with the pointer unmoved serves 9 Oct, "publishing" at 07:40 IST, and "stale" at 09:15 IST with "The NSE close of 2026-10-12 should have arrived by 08:30 IST and has not …". Once the pointer moves, "fresh". The calendar is held equal to NSE's file by a test, and the files are identical. | MET for the states. The **reason is the missing data, not the run's failure cause**: no `fno.run_status` table exists (dependency gap). |
| 2 | An unexpected major version shows the incompatibility screen, never a broken page | Integration test 2: a 3.0.0 row is `BlockIncompatible`, and the part shows its own alert while the rest of the page works. The app's major is tied to `api/openapi.yaml` by a test. | MET |
| 3 | Database errors never leak driver text or credentials to the browser | Integration test 3 on the real server (wrong password, closed port, revoked grant). My leak plant is caught. `outcomeOf` never reads `error.message`, and the log line carries the class only. | MET |

**The other points asked:**
- **No examples at runtime in database mode:** MET. The test has a control (without a database the examples do load),
  and my eager-import plant was caught. The builder states the limit: the fixture chunk still exists in the build; it
  is just never loaded.
- **TLS:** `ssl: { ca: <three pinned Azure roots>, rejectUnauthorized: true, servername }`. No variable weakens it.
  The real-TLS test refuses a server signed by other roots and a certificate for another name, and my host-check plant
  is caught. MET (the real Azure chain is unverified from here).

## Not verified by me (stated plainly)

1. **The stock pages need the same environment names.** The builder compared this tree with the stock repository's
   frozen `web/` (29955dd). The stock repository is outside this session's reach and read-only by rule, so I cannot
   re-check the comparison.
   - **What I can confirm:** `lib/data`, `app/api`, `app/brief` and `app/slack` are this tree's code.
   - **The claimed behaviour change after the switch is real and visible:** Home shows signed-off examples labelled
     "Example data" where it showed live stock data, until W9's backend lands.
   - **The owner's smoke test is the check.** Keep the existing variables, and make sure `MB_GATEWAY` is unset.
2. **The real Vercel to Azure read** (certificate chain, host name, firewall). That is the owner's smoke test in
   `W2_OWNER_STEPS.md`.

## Notes (not findings)

- **The calendar ends on 31 Dec 2026.** From 1 Jan 2027 the freshness line says it cannot tell, until 2027's NSE rows
  are added, here and in trading's file together. Never guessed. **Due in 11 weeks.**
- **In database mode most of the Markets page is honestly empty:** "No backend publishes this part yet". That is
  review 28's rule (examples are not a runtime state), and a visible step back from today's pages. The owner should
  expect it.
- **HALEOSLABS** (renamed from SMSLIFE): its `y1` is empty in the W11 examples and 35.18 in 33's `data.json`. This is
  the rename-join gap judge 49 routed to design. The builder correctly excluded and named the field rather than
  editing either file.
- **Two parts of one page from two publications:** possible in a window of milliseconds once a day, and both are
  complete publications. Acceptable (reasoning only).
