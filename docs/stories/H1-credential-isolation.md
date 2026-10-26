# H1: credential isolation, so a fetcher's credential cannot write the Record (design)

Lane 1, two judges, **design only** (no build, no infrastructure change). Owner decision (26 Oct 2026, via the
orchestrator): harden, do not defer the gap P1 disclosed. This document gives the real constraints, the options, what
the owner must set up for each, and a recommendation. **The owner picks the mechanism**; nothing here is built before
that choice and a second, build-level story. Parent design: `docs/PIPELINE_DESIGN.md` (Security section).

## The problem, measured

- All 13 workflows put the same owner Drive OAuth refresh token in their environment (`grep -l
  FNO_GDRIVE_OAUTH_REFRESH_TOKEN .github/workflows/*.yml` -> 13), including `pipeline-staging.yml`.
- That token was minted with the **full Drive scope** (`ops/gdrive_oauth_setup.py:20`,
  `https://www.googleapis.com/auth/drive`). Any job holding it can write, change or delete anything in the owner's
  Drive, including `raw/` (the Record) and `revisions/`. *(Strong evidence: the code.)*
- So today "only the gate writes the Record" is a property of the code (P1: the `Stager` can only hold a
  `StagingArea`; a test asserts it), **not** of the credential. A changed workflow file, a compromised dependency, or
  a mistake in any of the 13 jobs can overwrite or delete the Record. Write-once is enforced by our code and by
  Drive's content check, not by Drive permissions.

## Constraints that shape every option

1. **A Drive OAuth user token cannot be limited to a folder.** The usable scopes are whole-Drive (`drive`), or
   per-file `drive.file` (only files the app created or the user opened with it). There is no "this folder only"
   scope. *(Strong evidence for `drive`; the `drive.file` behaviour is documented by Google but its exact effect on
   creating files in a folder the app did not create is **not verified here**: see option D3.)*
2. **A service account has no storage quota** (our docstring in `google_drive_upload.py`: it cannot create files in a
   user's Drive), so it can **read** a shared folder (it already does: `DRIVE_READ_SCOPE`) but cannot be the writer.
3. **GitHub Actions secrets are visible to every workflow in the repo that names them.** A repository secret is
   exposed to any job in a workflow file on a branch the job runs from; so "fetchers use a different secret" only
   helps if a changed fetcher workflow cannot simply reference the Record secret. *(Strong evidence: GitHub's documented
   secrets model. How hard a reference is to add depends on branch protection: see below.)*
4. **Isolation has to be at the account and execution-environment level, not by naming.** Two things must both be
   true for a fetcher compromise to be unable to damage the Record: (i) the fetcher's Drive token has no write
   permission on the Record anywhere (Drive-level), and (ii) the Record-writing token is not reachable from fetcher
   jobs (execution-level). Either alone leaves a hole.

## Drive-level options (what the fetcher's token can physically write)

| | D1: dedicated Staging Google account | D2: same account, two folders | D3: same account, two OAuth clients on `drive.file` |
|---|---|---|---|
| Idea | Account **S** owns Staging; the existing account **R** owns the Record. Fetchers hold only S's token. The gate reads Staging through a share (S shares the staging folder, read-only, with the gate's reader) and writes R with R's token. | What exists today, with folders only. | Fetchers use a token whose client can only touch files it created; the gate uses a different client. |
| Can a leaked fetcher token write the Record? | **No.** S's token has no access to R's Drive unless R shares it, and R shares nothing writable with S. Physical, not conventional. | **Yes** (full scope; constraint 1). | **Unverified.** Likely no for existing files, but it may still be able to create new files in a folder it can address by ID. Needs a test by the owner before anyone relies on it. |
| Owner setup | Create account S (or use a second existing one); a Google Cloud project + OAuth client for S; run `ops/gdrive_oauth_setup.py` as S; create the staging folder; share it read-only with the gate's reader; publish the OAuth app (Testing-mode refresh tokens expire after 7 days: seen on 26 Oct). Keep R as is. | None. | A second OAuth client on the same account, a re-consent with a narrower scope, and a written test showing the fetcher client cannot create or change anything under `raw/`. |
| Cost / risk | One more account and token to keep alive; the Staging area moves to S's Drive (empty today, so no migration). Two Drive quotas. | Zero. Does not meet the goal. | Cheapest if the test passes; **reasoning only** until tested. |
| Verdict | **Recommended**: the only option that makes the property hold by Google's permissions. | Fails. | Worth a one-hour test as a cheaper fallback; do not rely on it unverified. |

## Execution-level options (what a fetcher *job* can read)

| | E-A: separate repository for the gate | E-B: protected GitHub Environment in this repo |
|---|---|---|
| Idea | The gate runs in repo **G**, which alone holds R's token. This repo (fetchers) holds only S's token. G checks out this repo's code at a pinned commit SHA to run `promote`. | A GitHub Environment `record-writer` holds R's token; only jobs that declare `environment: record-writer` can read it. The environment accepts deployments only from branch `main`, and `main` needs a reviewed PR for any change to workflows or the gate code. |
| Strength | Strongest: a change in the fetchers' repo cannot reach R's token at all; separate admins and permissions. | Strong only as long as branch protection holds. Anyone who can merge to `main` (or an admin) can add `environment: record-writer` to a workflow and read the secret. Required reviewers on the environment add a manual approval per run. |
| Owner setup | Create repo G; copy only the gate workflow and the Record secret there; set up the pinned-SHA checkout and a process to bump the pin after each judged merge; mirror manifests/receipts commits back (G needs push rights to this repo, a token the owner must create, itself a credential to protect). | Create the environment; add R's secrets to it only; limit deployment branches to `main`; turn on branch protection for `main` (required PR review, required status checks); add `.github/CODEOWNERS` for `.github/workflows/`, `fno/ingestion/promotion/` and `config.yaml`; remove R's secrets from the repository level. |
| Cost / risk | Two repos to run; the pin and the cross-repo write-back are new failure points; slower to change the gate. | One repo; but "required reviewers" on every run blocks unattended schedules, so use branch restriction plus branch protection and no per-run approval. Protection is a setting, not code: the owner must confirm it, and it is not checked from this container. |
| Verdict | Best if the owner wants the strongest guarantee and accepts the operational cost. | **Recommended to start**: most of the benefit, far less moving parts, once D1 removes the fetchers' ability to write R at all. |

## Recommendation (reasoning only, not data; owner decides)

**D1 + E-B.** With D1, a compromised fetcher job holds only account S's token, which has no access to the Record, so the
main risk (the Record overwritten or deleted by a fetcher) is closed by Google's permissions. E-B then limits R's
token to the gate's environment. What remains after D1 + E-B, stated plainly: whoever can merge to `main` or is a
repository admin can still reach R's token (mitigated by judged merges, CODEOWNERS and branch protection, not removed);
a garbage-filled Staging is still possible and is exactly what the gate rejects. If the owner wants even that closed,
E-A is the upgrade, and D3 is a cheaper-but-unverified alternative to D1.

## What changes in code under D1 + E-B (for the later build story, not now)

- `promotion/wiring.py`: `build_staging_area` and the Stager take S's settings (new `FNO_STAGING_GDRIVE_*` names in
  `fno/shared/constants.py`); the gate reads Staging with a read-only token (the existing `DRIVE_READ_SCOPE` service
  account fits) and writes R only through the existing owner-drive settings.
- Workflows: the 13 live fetchers keep R's token until each is moved (P-series switch); only `pipeline-staging.yml`
  and later the promote workflow change first. The `promote` job moves to a new workflow with `environment:
  record-writer`; `stage` runs without it. P1b's `promote` input already separates the two steps.
- Tests: a wiring test that the Stager's Drive settings are the staging ones and cannot be the Record's; an AST/grep
  test that no fetcher workflow names the Record secret once the move is done.

## Claims (what a judge can check in this design)

1. The measured problem is correct (13 workflows, full scope): `grep` and `ops/gdrive_oauth_setup.py:20`.
2. Each option states what the owner must do and what it does not protect against.
3. Anything unverified is labelled (D3's `drive.file` behaviour; GitHub settings that cannot be read from here).
4. The recommendation is labelled as reasoning, with the residual risk stated.

## Gap list

- Not verified from this container: GitHub branch-protection and Environment settings, Google's `drive.file`
  behaviour for creating files in an unowned folder, and the current OAuth consent-screen mode.
- Slack alerting credentials (`FNO_SLACK_BOT_TOKEN`) are also shared by every workflow; out of scope here.
- The Groww routine's credentials live in the routine's session, not in GitHub; unchanged.
- Cost of running a second Google account (any Workspace or consumer limits) is the owner's to check.
- Migration order of the 13 live fetchers is a separate story after the owner's pick.
