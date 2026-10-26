# SEC1: hash-pinned requirements for every job that installs packages

Lane 1, two judges (a security control on the jobs that hold the full-scope Drive token). Branch
`story/SEC1-hash-pinning`. **Story text only**; the lock files and the install changes follow once the judges accept this
text. Owner approved the work (26 Oct 2026, via the orchestrator). Context: `docs/PIPELINE_DESIGN.md` "Security" names
unpinned dependencies as an open path ("hash-pinning is not done").

## The problem, measured

- 14 workflow files run `pip install -r requirements.txt` (13 of them hold the Drive token; `participant-oi-watch.yml`
  holds none). All run Python 3.13. `ops/routine_setup.sh` installs `-r requirements.txt` (and `-r requirements-groww.txt`
  with `--groww`) with `--use-pep517` into **every** interpreter it finds (`python3` and `python`; on 15 Oct these were
  3.11 and 3.13).
- `requirements.txt` has `>=` ranges (and `xlrd==2.0.2`); `requirements-groww.txt` has `growwapi>=1.5`, `pyotp>=2.9`.
  Nothing is hashed. A malicious or hijacked release of any direct or transitive dependency is installed on the next
  run, by a job holding the full-scope Drive token. *(Strong evidence: the files and `grep "pip install"`.)*

## What this story will do (build, after acceptance)

1. **Lock files with exact pins and all hashes**, generated (never hand-written) from the existing files, which stay the
   editable inputs:
   - `requirements.lock` from `requirements.txt` (the 14 workflows);
   - `requirements-groww.lock` from both files together (`ops/routine_setup.sh --groww`; adds numpy, `clint`, `args`);
   - `requirements-oauth.lock` from a one-line `requirements-oauth.txt` (`google-auth-oauthlib`), for
     `ops/gdrive_oauth_setup.py`: the owner-run script that **mints the full-scope token** must not install unhashed.
2. **Every install uses `pip install --require-hashes -r <lock>`**: the 14 workflow steps (**plus `--only-binary :all:`**,
   so no source package is built and a missing wheel fails closed; the Drive-token jobs then have no unhashed build
   requirements at all), `ops/routine_setup.sh` (keeping `--use-pep517`, its retry and import checks; the Groww set is
   the documented exception: `clint` and `args` are source-only, so no `--only-binary` there), and the install lines
   quoted in `ops/gdrive_oauth_setup.py`, `docs/GROWW_CANDLE_ROUTINE.md` and the error text in
   `fno/ingestion/providers/groww.py`. Each workflow's `cache-dependency-path` points at the lock.
3. **A documented bump process** (`ops/relock.sh`, run by a maintainer, reviewed as a lock diff, committed), so pins do
   not go stale. The `uv` version is recorded in each lock's header and in `relock.sh`; `uv` is a maintainer tool, not
   installed in any job, and is the **trust root for every hash** (it asks PyPI for the files' hashes at relock time).
4. **Static tests** (offline), scanning `.github/**`, `ops/**`, `docs/**/*.md` (not stories, reviews or logs) and
   `fno/**/*.py`:
   - every `pip install`, `pip3 install`, `python -m pip install` and `uv pip install`, including inside multi-line
     `run: |` blocks, uses `--require-hashes` with a `.lock` file, and the 14 workflow installs also `--only-binary`;
   - every `cache-dependency-path` names a lock;
   - every requirement line in a lock is an exact `==` pin with at least one `--hash=sha256:`, and every pinned version
     satisfies the specifier in its source file;
   - **reverse check:** every requirement name in each source file has a pin in its lock (a line added to
     `requirements.txt` without a re-lock fails);
   - a **plant** fixture (a workflow line `python -m pip install foo`, and one in a `run: |` block) must fail the scanner.
5. **Build evidence step** (runs here, recorded in the story's Evidence section, no dispatch): `pip install --dry-run
   --ignore-installed --only-binary :all: --require-hashes -r requirements.lock` on Linux Python 3.13 resolves and
   hash-checks every package (both judges reproduced this for the base lock before the build), and the same compile on
   3.11. Exact package and hash counts are recorded at build time (they drift as PyPI changes: 20-21 packages,
   436-438 hashes during review).

## Tool and coverage (checked in this container before writing this text; nothing is committed)

- Tool: `uv pip compile --generate-hashes --universal` (maintainer-only). The brief allowed `pip-compile` or an
  equivalent; `pip-compile` resolves only for the running interpreter, so it needs one lock per Python.
- Measured by the builder and reproduced by both judges: `requirements.txt` resolves to 20 packages (21 on a later day)
  with 436-438 hashes; with the Groww file, **51 packages with 1,487 hashes**. `--python-version 3.11` and `3.13` give
  **identical pins**; the only differences against a non-universal compile are platform markers. So **one lock covers
  3.11, 3.13 and the Linux runner** (and the macOS and Windows maintainer machines). If the build finds a difference, it
  uses two locks, not a guess.
- If PyPI cannot be reached when the build runs, the build stops and says so; hashes are never hand-written.

## Risks, stated plainly

- **`--require-hashes` fails closed.** A wheel the runner needs without a listed hash makes the install fail and the job
  go red. The dry run above retires most of this risk before any dispatch; the first real dispatch (the stage-only
  validation run) is the proof on the real runner.
- **Build requirements.** For the Drive-token jobs, `--only-binary :all:` removes the path: nothing is built. For the
  Groww routine they stay unhashed (`clint`, `args` are source-only, built with `--use-pep517` in an isolated
  environment that pulls a current `setuptools`; pip cannot hash build requirements). `requirements-groww.txt`
  installs only in the Groww **routine session** (its key is off GitHub), not in the Drive-token Actions jobs, so
  that residual gap is in the routine's session environment, not on the public-repo Actions path.
- **Roots of trust left open:** `pip` itself comes unpinned from `actions/setup-python`; the runner image and the
  cloud container's own setup script (outside this repo, so it cannot be locked or tested here) are also outside the lock;
  `uv` is the trust root for the hashes.
- **Pins go stale** without the bump process; the cadence (monthly, or on an advisory) is the owner's call.
- **A hash proves the file is the one we locked, not that it is safe.** A package already malicious when locked stays
  malicious; the review of the lock diff on each bump is the control.

## Future work (not in SEC1)

- **SEC2: split runtime from test dependencies.** `pytest` and `pytest-xdist` are in `requirements.txt`, so every
  token-holding job installs them. Hash-pinning them is still an improvement; the split would cut what is installed.
  Proposed to the owner as SEC2; not built here.

## Claims (what a judge can check once built)

1. The three lock files exist, are generated by the documented command, and contain only exact pins with hashes.
2. The static tests above pass, and their plant fails the scanner.
3. The routine setup still installs into every interpreter and still runs its import checks.
4. The bump process is documented and runnable (`ops/relock.sh`).
5. The Security section of `docs/PIPELINE_DESIGN.md` changes "hash-pinning is not done" to what is true, **and** carries
   the deferred DOC2 minors (the zones table "(target)", "readers through the verified cache", the Record contract marked
   as the target), in the same revision.
6. Full gates pass; the record scan passes (hashes and pins are not secrets).

## Gap list

- Not proven on the real runner until the first dispatch; the dry run is the strongest pre-dispatch evidence.
- Groww build-time requirements stay unhashed (routine session only); the Groww SDK is closed source.
- The cloud environment's setup script and the runner image are outside the repo and outside the lock.
- No automated staleness alert for pins.
- `numpy` is imported by the routine's import check but is not in `requirements.txt`; it arrives only through the Groww
  set. Not changed here; flagged so nobody is surprised.
