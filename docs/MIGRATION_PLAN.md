# Migration plan: shared dashboard repository and MotherDuck to Azure PostgreSQL

Status: **proposed 12 Oct 2026, for the owner (and ChatGPT review)**. Step-by-step guide for stories X1, W1-W7 and
K1-K3 of `docs/IMPLEMENTATION_PLAN.md` (design 13.2-13.3). The stock tool's steps are done by its own sessions in its
own repository (this repository never writes there); the facts below were read from `agentic-stock-prediction`
(public, read only) on 12 Oct 2026.

## What exists today (facts)

- **Dashboard:** `web/` in `agentic-stock-prediction`, a Next.js 15 app (TypeScript, React 19, `pg`), about 4 MB of
  source. **One app, two Vercel projects** (`web/next.config.ts`): `omenix` (the dashboard, owner-only Vercel
  Authentication) and `omenix-gateway` (`MB_GATEWAY=1`; serves only `/slack/*`, `/mcp` and the MCP OAuth routes). Both
  projects use `web/` as root directory. **Automatic deployments are off** (`web/vercel.json`:
  `{"git": {"deploymentEnabled": false}}`, after merges used up the free tier's 100 deployments a day); the owner
  deploys by hand from the Vercel dashboard. CI: `.github/workflows/web-tests.yml` (typecheck, offline tests, build).
- **Data path:** the stock routines run `scripts/warehouse_sync.py`, which writes MotherDuck (`market_brief`, schema
  `rm`: one JSON row per page) from the committed `data/` folder, then calls the dashboard's
  `POST /api/v1/internal/revalidate` (`REVALIDATE_SECRET`, `VERCEL_AUTOMATION_BYPASS_SECRET`; `config/warehouse.yaml`
  `app_url: https://omenix.vercel.app`) so the cached pages refresh.
- **Dashboard writes:** the inbox (commands, paper trades from the dashboard) and the assistant conversation log live
  only in MotherDuck's `market_brief_inbox` (not rebuildable). The stock post-close routine imports the inbox
  (`company.py import-inbox`, `portfolio.py import-inbox`).
- **Environment variable names** used by the app (values never in files): `MOTHERDUCK_READ_TOKEN`,
  `MOTHERDUCK_INBOX_TOKEN`, `GITHUB_DISPATCH_TOKEN`, `SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET`, `REVALIDATE_SECRET`,
  `ANTHROPIC_API_KEY`, `GITHUB_OAUTH_CLIENT_ID`, `GITHUB_OAUTH_CLIENT_SECRET`, `SESSION_SECRET`,
  `MB_OWNER_GITHUB_ID`, `MCP_ALLOWED_GITHUB_LOGIN`, `MB_GATEWAY`.
- **Stock code that refers to `web/`:** warehouse contract and read-model code, the revalidate client, `api/`
  (OpenAPI files describing the dashboard's API), design catalogue scripts and several tests
  (`tests/test_b8_assistant.py`, `test_b11_commands.py`, `test_w1_catalogue.py` and others). These must keep passing
  or move with the dashboard.

## The key idea: keep the two Vercel projects, change only the repository they deploy from

A Vercel project can be reconnected to a different Git repository (Project, Settings, Git) and given a new root
directory, **keeping its domains, environment variables, authentication and deployment history**. So the production
URLs `omenix.vercel.app` and `omenix-gateway.vercel.app` stay the same, and the Slack app's request URLs and the MCP
OAuth callback URLs need **no change**. Parity testing happens on separate staging projects first. Rollback is
Vercel's "promote previous deployment" (instant), plus reconnecting the old repository if needed.

## Decisions the owner makes first (step 0)

1. **Repository name and owner account** for the dashboard: **`exepex/omenix-dashboard`** (created by the owner on
   12 Oct 2026; public during development, private when stable).
2. **Azure region:** put the database and the Vercel functions close together. Today the database is in
   `eu-central-1` (MotherDuck) and the owner is in India. Suggestion: Azure **Central India**, and set the Vercel
   functions' region to Mumbai (`bom1`) in both projects. Check that latency to the cloud routines is acceptable.
3. **Azure server size:** start with the smallest Burstable tier (check its price on Azure's pricing page; low tens of
   dollars a month from memory) and PostgreSQL 16; scale later.
4. **Network policy:** Vercel functions and the cloud routines have **no fixed IP addresses** on standard plans, so
   the server cannot be limited to known IPs. The realistic policy is public access with TLS required, strong
   per-role passwords, least-privilege roles (X1), connection limits and logging. State this in X1 instead of
   pretending it is network-isolated.
5. **Who does the stock-side work:** the stock tool's own sessions (recommended) for K1-K3 and for removing `web/`.

## Phase 1: Azure server and roles (story X1, platform)

1. In the Azure portal: create an **Azure Database for PostgreSQL, Flexible Server** (region and size from step 0),
   authentication "PostgreSQL authentication" (or Microsoft Entra later), backups on (7-35 days retention), TLS
   enforced (`require_secure_transport` on).
2. Networking: public access; firewall rule set per the step-0 policy; record the decision in `platform/README.md`.
3. Create the database `omenix` and run the idempotent scripts `platform/sql/00_roles.sql` ...
   `40_default_privileges.sql` (written in the dashboard repository, story X1) with the server admin:
   - owner roles (never used at runtime): `stock_owner`, `fno_owner`, `app_owner`;
   - schemas `stock` (owner `stock_owner`), `fno` (`fno_owner`), `app` (`app_owner`);
   - runtime roles: `stock_writer`, `fno_writer`, `dashboard_reader` (SELECT on `stock` and `fno` read-model tables,
     row operations on named `app` tables), `stock_inbox_reader` (K3);
   - `REVOKE CREATE ON DATABASE omenix FROM PUBLIC; REVOKE CREATE ON SCHEMA public FROM PUBLIC;` and default
     privileges so new tables are readable only by `dashboard_reader` and writable only by their backend.
4. Run the **role matrix test** (X1) against the real server with each runtime credential: every allowed operation
   passes, every forbidden one (DDL, cross-schema writes, creating in `public`) fails.
5. Test one **restore** of a backup to a scratch server; record it.
6. Store each runtime credential only where it runs: `stock_writer` in the stock routines' environment,
   `fno_writer` in this repository's routine environment (`FNO_DB_URL`), `dashboard_reader` in the Vercel projects.

## Phase 2: the stock tool also publishes to Azure (story K1, stock repository)

7. Add an Azure writer beside the MotherDuck one in `scripts/marketbrief/warehouse/` (a Postgres connection with
   `stock_writer`; the read-model rows and their envelope unchanged). Use P3's publication pattern: all pages of one
   sync in **one transaction**, a current-publication pointer, a unique key per page and publication.
8. Run both writers on every sync (**dual publication**); MotherDuck stays the one the production dashboard reads.
9. Run a **parity script** each day for a week: for a fixed set of pages and dates, the payload hashes in Azure equal
   those in MotherDuck. Any difference is fixed before going further.

## Phase 3: the new dashboard repository (story W1, dashboard repository)

**Done 12 Oct 2026 (steps 10-12):** `exepex/omenix-dashboard` holds `web/`, `api/`, the web-tests workflow and the
files the app's tests and design-sync tool read (`design/system/`, `design/mockups/`, `config/warehouse.yaml`, the
vendored chart file), with 298 commits of history, byte-identical to the stock repository at `0435bd1`; typecheck,
303 of 303 tests and the production build pass. Repository constants were **not** moved yet (step 11 waits until a
second backend needs them). Until the cutover, dashboard changes must be made in one repository only.

10. Create the repository (step 0). Bring over `web/` **with its history**:
    `git clone agentic-stock-prediction tmp && cd tmp && git filter-repo --path web/ --path api/ --path .github/workflows/web-tests.yml`
    then move `web/*` to the repository root (or keep `web/` as the root directory; keeping `web/` is simpler: the
    Vercel root directory stays the same). `api/` (the dashboard's OpenAPI contract) moves with it; the stock tests
    that read `api/` are changed in phase 8 to read the contract from the dashboard repository or are retired.
11. Move repository-specific constants (repository names for GitHub dispatch, the Slack channel) into configuration
    so one app can serve two backends.
12. CI: the copied `web-tests.yml` (typecheck, tests, build) runs green in the new repository.
13. In Vercel, create **two staging projects** from the new repository (for example `omenix-staging` and
    `omenix-gateway-staging`), root directory as above, Vercel Authentication on, functions region from step 0, and
    the **same environment variable names** with staging values (still MotherDuck at this point). Keep automatic
    deployments off (`vercel.json`) if the daily deployment limit still matters.
14. Deploy staging by hand; run a **response comparison**: for a fixed list of pages and API routes, staging and
    production return the same data (record the result). Production is untouched.

## Phase 4: the dashboard reads Azure (stories W2 for F&O, W6 for stock)

15. Add an Azure `RowStore` (same interface as the MotherDuck one in `web/lib/data/store.ts`) using
    `dashboard_reader`; reads only the **current publication** of each product (fixes today's `rows[0]` without a
    uniqueness rule).
16. A configuration switch per environment chooses MotherDuck or Azure; staging switches to Azure.
17. Stock parity (W6): staging on Azure returns the same responses as production on MotherDuck for the comparison set.
18. Revalidation: the stock sync calls the revalidate endpoint of **both** production and staging while both exist
    (two URLs in `config/warehouse.yaml`), so staging pages refresh too.
19. F&O: the `/fno` screens (W3) can be built and tested on staging from here on, reading the `fno` schema; the F&O
    launch never waits for the stock cutover.

## Phase 5: the dashboard's own writes move to Azure (stories W7 and K3)

20. Create the `app` tables (inbox, command log, assistant conversations, any control state) with `app_owner`.
21. Add Azure implementations of the inbox and conversation stores (`web/lib/tools/motherduck.ts` inbox writes,
    `web/lib/assistant/store.ts`) behind their existing interfaces, with idempotency keys.
22. **Rehearsal on the disposable server** (O3 test 4): copy the history (row counts and hashes match), flip the
    one-writer switch under concurrent writes (nothing lost or doubled), then roll back (post-switch writes copied
    back). K3: the stock inbox readers switch to `stock_inbox_reader` on Azure in the same window and import each
    request exactly once.

## Phase 6: cutover (story W5)

23. Pick a quiet time (a weekend, after the last stock routine of the day). Announce it in #fno-desk and the stock
    channel.
24. Freeze: pause the stock routines that write the inbox or sync (or let them finish), turn off dashboard writes
    for a few minutes (maintenance banner).
25. Final copy of the inbox and assistant history to Azure; check counts and hashes.
26. In the **production** Vercel projects `omenix` and `omenix-gateway`: reconnect Git to the new repository (Settings,
    Git), set the root directory, set the environment variables for Azure (`dashboard_reader` credential, the
    store switch to Azure, the write switch to Azure), set the functions region, then **deploy**.
27. Flip K3 (stock inbox readers to Azure) and resume the stock routines; their sync now writes Azure (and
    MotherDuck, still, during the rollback period) and revalidates the production URL.
28. Smoke tests right away: log in; open every stock screen; send one inbox request and see it imported by the next
    routine; one assistant question; Slack interaction through the gateway; MCP login; the W4 access suite (an
    unauthenticated request is refused).
29. **Rollback** if anything fails: in each Vercel project, promote the previous production deployment (instant),
    switch writes back, and copy any post-switch writes back (the rehearsed procedure). Keep this possible for the
    fixed rollback period (proposed 14 days).

## Phase 7: clean up after the rollback period (stories W5, K2)

30. Remove `web/` (and the moved `api/` and workflow) from the stock repository; update its tests and docs that
    referred to `web/`; the stock CI stays green.
31. Stop the MotherDuck writer; revoke every MotherDuck token (`MOTHERDUCK_TOKEN`, `MOTHERDUCK_READ_TOKEN`,
    `MOTHERDUCK_INBOX_TOKEN`); remove MotherDuck code, config and docs (K2). Record that Azure can be rebuilt from the
    stock repository's `data/` (run the rebuild once).
32. Delete the staging Vercel projects or keep them as the permanent staging environment (recommended: keep).

## Order and timing

Phases 1-3 can start now and run in parallel with F&O milestones M1-M3 (they do not block F&O research). Phase 4's
F&O part (W2, W3) is needed for F&O milestone M4. Phases 5-7 are M6. Rough effort: phase 1 one day; phase 2 two to
three days plus a week of daily parity; phase 3 one to two days; phase 4 two to three days; phase 5 two to three
days; phase 6 half a day plus monitoring; phase 7 one day after the rollback period.

## Gaps found while writing this (to fix in the plan, reasoning only)

- **F&O page refresh:** the dashboard caches pages and the stock tool refreshes them through the revalidate endpoint
  after each sync. P3 (the F&O publisher) does not yet call it, so F&O screens could show cached data until the cache
  expires. Proposed fix: P3 calls the revalidate endpoint with its own secret after a successful publication (and W2
  tags F&O pages by publication). Needs a small change to P3 and W2, reviewed like any plan change.
- **Network isolation** of the database is not achievable with dynamic IPs on standard Vercel plans (step 0.4); X1's
  "network access limited where practical" should state this explicitly.
- **Deployment limit:** automatic deployments are off because of Vercel's free-tier daily limit; with two backends
  and more screens, decide whether manual deploys stay or a paid plan is worth it.
