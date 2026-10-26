# Judge 12: SEC1 hash-pinned requirements, story text (judge #2)

Branch `story/SEC1-hash-pinning`, SHA `bfcd6a8fa8ef26de979ce3ec8697723584eb2c41`, story only. **FAIL** (round 1),
lane 1, on 4 should-fix and no blocking finding. The approach is right. The story misses install paths, one cheap
hardening step, and two gaps in the static test.

## Criteria

| Item | Verdict | Evidence |
|---|---|---|
| (1) Measured problem | MET | 14 workflow `pip install -r requirements.txt` lines and `ops/routine_setup.sh:43` (grep). `>=` ranges, nothing hashed |
| (1) No other install path missed | NOT MET | S1 |
| (2) Tool and one universal lock | MET | Reproduced: `uv pip compile requirements.txt --generate-hashes --universal --python-version 3.13` gives 21 lines with `==` and 438 hashes. The story says 20/436; counts drift as wheels are published, so record them at build time |
| (3) Risks honest | PARTLY | Correct and well stated. But the build-requirements risk can be closed for the workflows (S2) |
| (4) Static tests would catch a new unhashed install | NOT MET | S3 |
| (5) DOC2 minors folded into the same revision | MET | Claim 5 names all three |

Text gates: doc-reading tests 53 passed; record scan clean.

## Findings

1. **S1 (should fix): install paths not listed.**
   (a) `ops/gdrive_oauth_setup.py:4` says `pip install google-auth-oauthlib`, unhashed, on the owner's machine. That
   process **mints and prints the full-scope refresh token**, so a compromised package there steals the token at its
   source. Give it a hashed lock (or a pinned `--require-hashes` line in its docstring), or name it in the gap list
   with that reason.
   (b) Every workflow has `cache-dependency-path: requirements.txt`. Point it at the lock, or the pip cache key stops
   tracking what is installed. The cache cannot bypass `--require-hashes`, so this is consistency, not a hole.
   (c) Install commands in prose: `docs/GROWW_CANDLE_ROUTINE.md:73` and the error text at
   `fno/ingestion/providers/groww.py:138` (`pip install growwapi`). Point them at the locked command.
   (d) The cloud environment's setup script lives outside the repo, and sessions there hold Drive secrets. Name it in
   the gap list as the owner's to update.
2. **S2 (should fix): forbid source builds in the workflow lock.** Add `--only-binary :all:` to the 14 workflow
   installs. I checked it: `pip install --dry-run --ignore-installed --only-binary=:all: --require-hashes -r <lock>`
   on Linux, Python 3.13, against my compiled `requirements.txt` lock, exits 0, so every package has a wheel. That
   closes the unhashed build-requirements path for every token-holding job. If a wheel is missing, the install fails
   closed instead of quietly building from source with an unhashed `setuptools`. (Some evidence: one platform and
   interpreter; the routine's 3.11 and Groww's `clint`/`args` stay source-only, as the story says.)
3. **S3 (should fix): the static test as written would miss common forms.** Say the test matches any install
   command, not only the string `pip install`: `python -m pip install`, `python3 -m pip`, `pip3`, `uv pip install`,
   and commands inside multi-line `run: |` blocks. It should cover every file under `.github/` and every `ops/`
   script (not only `*.sh`), and fail if `cache-dependency-path` names a non-lock file. Add a plant to the evidence:
   a fixture workflow line `python -m pip install foo` must fail the test.
4. **S4 (should fix): the lock can lag behind its input.** "Every pinned version satisfies the specifier in its
   source file" walks the pins. It would not catch a new line added to `requirements.txt` without a relock: the jobs
   install the lock, so the new package is missing at run time. Add the reverse check: every requirement in each
   input file has a pin in its lock (names normalised).

## Minor

1. `ops/relock.sh` runs `uv`, so it is a trust root for every hash. Say how the maintainer installs `uv` (a pinned
   release with a checksum).
2. `pip` itself comes unpinned from `setup-python`. That is acceptable (it is the verifier), but say so in the risks.

## Notes

The "a hash proves the file is the one we locked, not that it is safe" risk and the test-tools-in-runtime risk are
honest, and correctly out of scope.

## Addendum 1: round 2, `a8efd5b815bd3947bede207367fc991d1115fd0c` (story text)

**PASS**, lane 1, judge #2: the story may proceed to the build. Text gates: doc-reading tests 53 passed; record scan
clean.

| Round-1 finding | Verdict | Evidence (story, round 2) |
|---|---|---|
| S1 (a) the token-minting OAuth setup | FIXED | `requirements-oauth.lock`, with the install line quoted in `ops/gdrive_oauth_setup.py` (build item 1) |
| S1 (b), (c), (d) | FIXED | `cache-dependency-path` points at the lock; the Groww doc and the `groww.py` error text point at locked installs; the cloud setup script and the runner image are in the gap list |
| S2 `--only-binary :all:` | FIXED | the 14 workflow installs; the Groww routine is the documented exception, confined to its session |
| S3 scanner coverage | FIXED | pip, pip3, `python -m pip` and `uv pip`, multi-line `run: |` blocks, `.github/**`, `ops/**`, docs and `fno/**/*.py`, `cache-dependency-path`, with a plant fixture that must fail |
| S4 reverse check | FIXED | every input requirement name must have a lock pin |
| Minors (uv trust root, unpinned pip, drifting counts) | FIXED | in the risks and build item 5 |

### For the build round (not findings now)

1. Check the plant in the evidence, not only that the test exists. I will plant `python -m pip install foo` in a
   `run: |` block, `pip3 install x` in an `ops/` script, and a `requirements.txt` line with no lock pin, and expect each
   to fail.
2. The OAuth script was "from any folder; it needs nothing else" (`ops/gdrive_oauth_setup.py` docstring). A locked
   install needs the lock file, so say where the owner gets it (the repo checkout). Consider `--only-binary :all:` on
   that install too: it is the token-minting moment, and pure-Python wheels exist for its set (unverified here; check
   at build).
3. Claim 5's DOC2 minors are checked line by line in the build round.

## Addendum 2: build, `7ed5fe03efeda88aca99f37a36ae6eb57fd11999` (28 files)

**PASS**, lane 1, judge #2 of two. Gates re-run by me: 251 passed; `ruff check`, `check_imports`, `test_code_size`
clean; the new files are formatted. The record scan over the changed files flags only `fno/ingestion/providers/
groww.py:156`; the same line on `main` gives the identical finding, so it predates this change.

| Claim | Verdict | My evidence |
|---|---|---|
| 1: three locks, generated, exact hashed pins | MET | I re-ran `uv pip compile --generate-hashes --universal --python-version 3.11`: `requirements.lock` and `requirements-oauth.lock` are identical apart from comment lines. Counts: 21/53/14 pins, 438/1,561/353 hashes |
| Locks install | MET | Fresh venv, Python 3.13 Linux, `pip install --dry-run --ignore-installed --require-hashes`. With `--only-binary=:all:`, the base and OAuth locks exit 0. The Groww lock with `--use-pep517` exits 0 |
| 2: every install is locked | MET | A YAML parse of all 14 workflows: each one installs `"pip install --require-hashes --only-binary=:all: -r requirements.lock"`, and each `cache-dependency-path` is the lock. `ops/routine_setup.sh` uses `--require-hashes` with the right lock for each flavour |
| 3: the routine keeps every interpreter and its import checks | MET | The diff touches only the `requirements` variables and comments |
| 4: bump process | MET | `ops/relock.sh`: uv as the trust root, review the diff, never hand-edited |
| 5: SEC1 truth plus the DOC2 minors | MET | Supply chain "narrowed, not closed", with the open roots listed; the zones row, the receipt-check scope and the Record contract are each marked as the target |
| S1 (c) prose installs | MET | `groww.py:138` and `GROWW_CANDLE_ROUTINE.md:73` now point at `routine_setup.sh --groww`; the OAuth docstring gives the locked install from a checkout |

### Plants

12 in the real repo files (not the test's fixtures), 10 caught:
- an unhashed `python -m pip install` in a `run: |` block of a real workflow;
- `pip3 install` in `ops/`;
- a new `requirements.txt` line;
- `--only-binary` removed;
- the cache path reverted;
- the OAuth docstring reverted;
- a README install;
- `python3.13 -m pip install`;
- a range in a lock;
- a new OAuth input line.

Not caught:
- `pandas>=2` added to `requirements-groww.txt`. An invalid plant: pandas is already pinned in the Groww lock as a
  dependency of growwapi. A truly new name (`zzznotapkg>=1`) is caught.
- `pipx install foo` (minor 1).

### Minor (not blocking)

1. The scanner does not match `pipx install`. pipx is used nowhere in the repo; add it to `INSTALL` on the next
   touch.
2. `tests/test_pinned_installs.py` imports `packaging`, which comes only from pytest's dependencies. That works today
   (`packaging==26.3` is in the lock); naming it in `requirements.txt` would make it explicit.
3. `PIPELINE_DESIGN.md:127` still says "a compromised dependency installed in any job can use it". After SEC1 it is
   narrower: a dependency already malicious when locked, or the open roots listed above it. Align the wording on the
   next touch.

### Notes

The first real dispatch is still the proof on the runner (the story says so). Whether the owner's own machine
installs the OAuth lock binary-only depends on that machine (wheels exist for Python 3.11 and 3.13; I checked Linux
only).
