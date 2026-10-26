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

## Addendum 1: SHA a8efd5b (round 2)

**PASS (story text), lane 1, judge 1.** Both findings and the minor point are fixed:
- **1** A third lock, `requirements-oauth.lock` (from a one-line `requirements-oauth.txt`), is planned for
  `ops/gdrive_oauth_setup.py`. The scanner now covers `ops/**`, `docs/**/*.md` and `fno/**/*.py` text, not just
  `ops/*.sh`. Reproduced: `google-auth-oauthlib` locks universally to 14 packages, and a binary-only hash-checked dry
  run installs all 14.
- **2** Reverse check (every source requirement has a pin in its lock) added to the tests.
- **Minor** `cache-dependency-path` is to name the lock, and a test checks it.

Also verified: the new `--only-binary :all:` on the 14 workflow installs works today. A dry run
(`--only-binary :all: --require-hashes`, Linux Python 3.13) of the base universal lock resolves and hash-checks all
20 packages, so nothing in the Drive-token path needs a source build. The roots-of-trust and Groww exceptions are
stated honestly.

The build review will plant an unhashed install (one plain, one inside a `run: |` block), a source requirement
without a lock pin, and a non-lock `cache-dependency-path`.

## Addendum 2: build, SHA 7ed5fe0 (code review, round 1)

**FAIL on one should-fix (an unmet story claim), nothing blocking; lane 1, judge 1.** 28 files: 14 workflows (one
install line and the cache path each), 3 locks, 3 inputs, `ops/relock.sh`, `ops/routine_setup.sh`, the OAuth script
docstring, one error string in `groww.py`, docs and `tests/test_pinned_installs.py`.

| Check | Verdict | Evidence (my own runs) |
|---|---|---|
| Gates | MET | 251 passed; ruff, check_imports, check_numbers and code size clean (the `ruff format` finding is the pre-existing `test_paths.py`); all 14 workflow YAMLs parse |
| Locks generated, not hand-written | MET | I re-ran the three `ops/relock.sh` compiles with uv 0.11.32 in a scratch folder. All three are byte-identical outside comments: base 21/438, Groww 53/1,561, OAuth 14/353 (packages/hashes) |
| Locks install on the runner's Python | MET | Hash-checked dry runs: base with `--only-binary=:all:` resolves 20/20 on 3.13 and 20/20 on 3.11; OAuth 14/14; Groww (`--use-pep517`, no only-binary) 51/51 on 3.13 |
| Every install is hashed | MET | 14 workflow lines, `routine_setup.sh` (both flavours), the OAuth docstring, the Groww doc and the `groww.py` message |
| Tests stop a regression | MET | 13 plants, 13 caught: plain unhashed workflow install; `python -m pip install` inside a `run: |` block; missing `--only-binary`; non-lock cache path; source requirement with no lock pin; pin outside its specifier; lock line with no hash; both `routine_setup.sh` flavours unhashed; OAuth docstring unhashed; README instruction unhashed; `uv pip install` in `ops/`; `pip3` with a backslash continuation |
| Story claim 3: "the uv version is recorded in each lock's header and in relock.sh" | NOT MET | Lock headers say only "autogenerated by uv"; `relock.sh` never prints or records the version. Only the story's Evidence names 0.11.32, so the next bump loses it |
| DOC2 minors carried | MET | zones table "(target ...)", the contract marked as the target, and "readers that go through the verified cache" (it honestly notes the coverage check, librarian and gate read `raw/` directly) |

## Findings

1. **Should fix:** record the uv version as the story claims. For example, `relock.sh` writes `# uv <version>` as the
   first line of each lock (or echoes it, and the header carries it), with a test that every lock names a uv version.
   Or change the claim, with a reason.

Minor (optional): `tools/` is not scanned (no install there today); the test imports `packaging`, which arrives only
transitively through `pytest`.

## Addendum 3: build, SHA 817686e (round 2)

**PASS, lane 1, judge 1.** 7ed5fe0..817686e changes 7 files.
- **Finding 1 FIXED.** `ops/relock.sh` writes `# uv-version: <x.y.z>` as the first line of each lock, and a new test
  requires it. Plant: deleting that line from `requirements.lock` makes 1 test fail.
- **Reproduced end to end.** Running the committed `ops/relock.sh` (uv 0.11.32) in a clean scratch tree regenerates all
  three locks **byte-identical** to the branch: 21/438, 53/1,561, 14/353. The only lock-body change since 7ed5fe0 is
  the `# via -r requirements.txt` annotation for `packaging`, which is now a direct requirement (same version and
  hashes).
- **Minors FIXED.** `tools/` is scanned (plant: a `pip install requests` in `tools/plant.sh` fails 1 test), and
  `packaging` is a direct requirement.
- Gates: 254 passed; ruff, check_imports and check_numbers clean. Dry runs with `--only-binary=:all:
  --require-hashes`: 20/20 on Python 3.13 and on 3.11.

Note (not a finding): `sed -i.bak "1i # ..."` is GNU sed syntax. BSD/macOS sed needs `1i\` followed by a newline, so
`relock.sh` would stop with an error (loudly, `set -eu`) on a Mac. It works in the Linux containers where sessions
relock. If the owner ever relocks on a Mac, a portable form is `{ echo "# uv-version: $v"; cat "$output"; } > tmp && mv
tmp "$output"`.

## Addendum 4: final SHA be23751 (supersedes 817686e)

**PASS, lane 1, judge 1.** 817686e..be23751 changes 4 files (`ops/relock.sh`, the test, the design doc's residual
wording and the story). Locks, inputs and workflows are unchanged (`git diff --quiet`). Against `origin/main`, the
branch touches only the SEC1 paths.
- `relock.sh` now refuses any uv but `expected_uv=0.11.32`, and a test ties every lock header to that pin. Plant:
  `expected_uv=0.11.31` makes 3 tests fail. The committed `relock.sh`, run in a clean tree, regenerates all three locks
  byte-identical.
- The scanner now covers `pipx install` too.
- The design doc's residual wording now names "a dependency that was malicious when locked". That is accurate now
  that hash-pinning is in place.
- Gates: 255 passed; ruff, check_imports and check_numbers clean.

The note on GNU-only `sed` (Addendum 3) still stands as a note.
