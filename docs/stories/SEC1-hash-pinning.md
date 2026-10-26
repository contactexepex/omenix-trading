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
   - `requirements.lock` from `requirements.txt` (used by the 14 workflows);
   - `requirements-groww.lock` from both files together (used by `ops/routine_setup.sh --groww`; it brings in numpy,
     `clint`, `args`).
2. **Every install uses `pip install --require-hashes -r <lock>`**: the 14 workflow steps, and `ops/routine_setup.sh`
   (keeping `--use-pep517`, `--ignore-installed` retry and its import checks).
3. **A documented bump process** (`ops/relock.sh` plus a short section in `ops/` or the storage README, whichever owns
   routine setup), so pins do not go stale: re-run it, review the lock diff, commit. Without it the pins would rot.
4. **Tests** (static, offline): every `pip install` in `.github/workflows/*.yml` and `ops/*.sh` uses `--require-hashes`
   with a `.lock` file; every requirement line in a lock is an exact `==` pin with at least one `--hash=sha256:`; every
   pinned version satisfies the specifier in its source file; a new workflow that installs unhashed fails the test.

## Tool and coverage (checked in this container before writing this text; nothing is committed)

- Tool: `uv pip compile --generate-hashes --universal` (a maintainer tool only; it is not installed in any job, jobs only
  run pip). The orchestrator's brief allowed `pip-compile` or an equivalent. `pip-compile` was also run: it resolves for
  the running interpreter only, so it needs one lock per Python; `--universal` gives one lock for all.
- Measured: `requirements.txt` resolves to **20 packages with 436 hashes**; with the Groww file, **51 packages with
  1,487 hashes**. `uv pip compile --python-version 3.11` and `3.13` give **identical pins** (the only differences against
  the non-universal compile are platform markers, e.g. `colorama ; sys_platform == 'win32'`). So **one lock covers the
  3.11 and 3.13 interpreters and the Linux runner**, and the macOS and Windows maintainer machines.
- The build story step re-runs this and records the commands and counts in the Evidence section. If PyPI cannot be
  reached when the build runs, the build stops and says so; hashes are never guessed or hand-written.

## Risks, stated plainly

- **`--require-hashes` fails closed.** If a wheel the runner needs has no listed hash (a platform tag the compile missed,
  or a package that gained a new wheel after the lock was made, which pip would not fetch anyway because the version is
  pinned and the lock lists all its files at compile time), the install fails and the job goes red. The real proof is
  the first workflow dispatch (the stage-only validation run will exercise it on the real runner); until then the
  claim is "locks cover 3.11 and 3.13 on linux by compile", not "proven on the runner".
- **Build requirements stay unhashed.** pip does not hash the build-time requirements of source-only packages (`clint`,
  `args` in the Groww set are source-only, built with `--use-pep517` in an isolated environment that pulls a current
  `setuptools`). That path is the Groww routine, not the Drive-token workflows, but it remains an open supply-chain edge.
- **Pins go stale** without the bump process: security fixes reach us only when someone re-locks. The process is in the
  build; the cadence (monthly, or when a dependency has an advisory) is the owner's call.
- **Test tools are installed with the runtime** (`pytest`, `pytest-xdist` are in `requirements.txt`, so every
  token-holding job installs them). Locking them hashes them too, but it does not reduce what is installed. Splitting
  runtime and test dependencies would, and is out of scope here.
- **A hash proves the file is the one we locked, not that it is safe.** A package that was already malicious when
  locked stays malicious. The review of the lock diff on each bump is the control for that.

## Claims (what a judge can check once built)

1. Both lock files exist, are generated by the documented command, and contain only exact pins with hashes.
2. No `pip install` in any workflow or `ops/` script installs without `--require-hashes` and a lock file (a test).
3. The routine setup still installs into every interpreter and still runs its import checks.
4. The bump process is documented and runnable (`ops/relock.sh`).
5. The Security section of `docs/PIPELINE_DESIGN.md` changes "hash-pinning is not done" to what is true, **and** carries
   the deferred minor wording fixes from DOC2 (the zones table "(target)", "readers through the verified cache", the
   Record contract marked as the target), in the same revision.
6. Full gates pass; the record scan passes (hashes and pins are not secrets).

## Gap list

- Not proven on the real runner until the first dispatch (above). No dispatch is part of this story.
- Build-time requirements are unhashed (above). The Groww SDK itself is a closed-source package we cannot audit.
- No automated staleness alert for pins (the owner sets the cadence).
- `numpy` is imported by the routine's import check but is not in `requirements.txt`; it arrives only through the Groww
  set. Not changed here; flagged so nobody is surprised when the plain routine setup lacks it.
