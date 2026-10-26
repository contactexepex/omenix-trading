# Judge 13: SEC1 hash-pinned requirements (story text), branch `story/SEC1-hash-pinning`, SHA bfcd6a8

**FAIL (round 1), lane 1, judge 1; nothing blocking, 2 should-fix.** Story text only (one file, 80 lines). The approach
is sound and its measurements reproduce. Two install surfaces or drift cases are missing from the tests and the gap
list.

## Criteria

| Check | Verdict | Evidence (my own runs) |
|---|---|---|
| (1) Measured problem | MET | 14 workflow files `pip install -r requirements.txt` (grep); all `python-version: "3.13"`; `ops/routine_setup.sh:43` installs into every `python3`/`python` it finds |
| (2) Approach | MET | `uv` 0.11.32 here: `uv pip compile --generate-hashes --universal` resolves `requirements.txt` to 20 Linux packages (21 lines, one being `colorama ; sys_platform == 'win32'`) and 438 hashes. The story says 436, so counts drift with new uploads; the build must record its own. With the Groww file: 51 packages and 1,487 hashes, exactly as stated. `--python-version 3.11` and `3.13` give identical pins |
| (3) Risks honest | MET, with a note | Fail-closed, unhashed build requirements, staleness, test tools in the runtime and "hash is not safety" are all stated. Note: the runner risk can be cut before any dispatch. `pip install --dry-run --ignore-installed --require-hashes -r <universal lock>` on Linux Python 3.13 here resolves and hash-checks all 20 packages. Make that a build evidence step |
| (4) Tests stop a new unhashed install | PARTLY | Findings 1 and 2 |
| (5) DOC2 minors in the same revision | MET | Acceptable: same owning document, same lane, listed explicitly. The DOC2 minors then wait for SEC1's merge; that is a timing cost only |

## Findings

1. **Should fix: one install path is outside the tests and the gap list.** `ops/gdrive_oauth_setup.py:4` tells the
   owner to run `pip install google-auth-oauthlib`, unpinned and unhashed. That is the tool that mints the full-scope
   Drive refresh token, so it is the most sensitive install in the repository, even though it runs on the owner's
   machine. Either lock it (a third small lock, or an extra in `requirements.lock`), or list it in the gap list with
   the reason. The planned test covers only `.github/workflows/*.yml` and `ops/*.sh`, so it would not see this one.
2. **Should fix: the tests do not catch a lock that has drifted from its source.** "Every pinned version satisfies its
   specifier" passes when a package is added to `requirements.txt` but the lock is never regenerated. The jobs then
   install the lock without the new package and fail at import. Add a test that every requirement name in each
   source file appears in its lock (normalised names).

Minor:
- `actions/setup-python` `cache-dependency-path: requirements.txt` (pipeline-staging and others) should key on the
  lock file, so the cache changes when the pins do.

## Plants

None yet (story text). The build review will plant an unhashed `pip install` and a stale lock.
