# Judge 7: H1 credential isolation, design (judge #2)

Branch `story/H1-credential-isolation`, SHA `0fb33127310baf36468d51d805a6d75a015a1417`, design only.
**FAIL** (round 1), lane 1. The analysis is sound, but the recommendation's residual risk is misstated and E-B
conflicts with how this repo commits data.

## Criteria

| Item | Verdict | Evidence |
|---|---|---|
| (1) Measured problem | MET, one slip | 13 workflows hold `FNO_GDRIVE_OAUTH_REFRESH_TOKEN` (grep); `ops/gdrive_oauth_setup.py:20` is the full `drive` scope. But there are **14** workflow files, and `participant-oi-watch.yml` holds no Drive token: "all 13 workflows" is wrong (m1) |
| (2) Option tables honest | PARTLY | D1, D2, D3 and E-A are right about what each stops, and D3 is correctly marked unverified. E-B misses the data-commit conflict (B2); the Shared Drive option is missing (S1) |
| (3) Owner setup lists | PARTLY | D1 lacks a sharing check and the scope choice for S (S3); E-B's branch protection cannot be applied as written (B2) |
| (4) Recommendation and residual risk | NOT MET | B1, B2 |

## Findings

1. **B1 (blocking): the residual risk is misstated.** D1 does not stop the Record being poisoned. The story says that
   after D1 + E-B "a garbage-filled Staging is still possible and is exactly what the gate rejects". The gate rejects
   *malformed* files only: it checks layout, session, exceptions and the date. A compromised fetcher holding S's
   full-scope token can stage a **well-formed forged file** (right columns, right date, false numbers), and it gets
   promoted. With first-copy-wins, S can also **delete the earlier genuine staged copy**, so its forgery becomes the
   first passing copy for any day not yet recorded. So D1 closes overwrite and delete of the Record, but not
   injection into it. Fix: state this, and add a mitigation option. For example, the gate independently re-fetches
   the file from NSE (public, no key, in the gate's job) and promotes only a staged copy whose SHA-256 matches; or
   wait for the cross-source agreement of Phase 4. Label each one.
2. **B2 (blocking): E-B's branch protection conflicts with the 13 workflows that push to `main`.** Every data
   workflow commits manifest rows straight to `main` with `GITHUB_TOKEN` (`contents: write` in 13 files;
   CLAUDE.md "every push is `git push origin HEAD:main`"). Requiring a reviewed PR on `main` blocks those pushes.
   Letting the Actions bot bypass the rule lets any fetcher job, including a compromised dependency in it, push to
   `main` a change to `fno/ingestion/promotion/` or `requirements.txt`. `GITHUB_TOKEN` cannot change
   `.github/workflows/`, but it can change code. The next gate run then executes that code inside
   `environment: record-writer`, holding R's token. Fix: the gate job must run a judged, pinned commit or tag, not
   `main`'s head (the same pin as E-A, without a second repo); or use path-restricted push rules, if this repo's plan
   offers them (unverified); or move data commits off `main`. Also install the gate job's dependencies with
   `pip --require-hashes`, since the gate job is the one place where a dependency reaches R's token.
3. **S1 (should fix): a missing option.** In a Google Workspace Shared Drive, a service account can be a member and
   write: the no-quota limit (constraint 2) applies to My Drive. Two Shared Drives, Staging and Record, each with its
   own service account as the only writer, give per-area isolation with no consumer OAuth token and no 7-day
   Testing-mode expiry. It needs Workspace, which is a cost; some evidence (Google's Shared Drive model). List it,
   with that condition.
4. **S2 (should fix): R's token keeps full scope over the owner's personal Drive.** A gate compromise (B2) reaches
   everything the owner keeps there, not only the project. Recommend that R also be a dedicated account owning only
   the project folder, or state this residual.
5. **S3 (should fix): the D1 setup list is incomplete.**
   (a) Add a check that R shares nothing writable with S, and keep checking it (a permissions read by the gate's
   service account, or the owner's checklist).
   (b) S writes only files it creates, so S's token can be `drive.file`, not full `drive`. That shrinks its blast
   radius to its own files; it is the same unverified behaviour as D3, but here only S's own files are needed.
   (c) Publishing the OAuth app with the restricted `drive` scope stops the 7-day expiry, but keeps the
   "unverified app" consent screen. State it.
6. **m1:** 14 workflow files, of which 13 hold the token; `participant-oi-watch.yml` holds none.

## Answer to question (4) (some evidence: GitHub's documented model; settings not readable from here)

A repository secret is available to any workflow run started in this repo from any branch: anyone with write access
can push a branch whose workflow prints it. It is not available to fork PRs. An environment limited to `main` blocks
other branches. But any job on `main` that declares the environment gets the secret, so the protection is only as
strong as control over what reaches `main`. That control is exactly the gap in B2.

## Plants

Not applicable (design only).
